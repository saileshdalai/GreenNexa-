"""
GreenNexa — OTP & Password Reset Service.

Implements secure OTP generation, verification, and password reset workflows:
- Indian mobile number validation & normalization.
- Cryptographically secure server-side OTP generation.
- Salted hashing (SHA-256) — plaintext OTP is never stored in the database.
- Configurable expiration (default: 5 minutes).
- Single-use OTPs with immediate invalidation upon use.
- Incorrect attempt rate limiting (max 5 attempts).
- Resend cooldown enforcement (default: 60 seconds).
- Protection against account enumeration.
- Confidentiality: OTP is never returned in API responses.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core import security
from app.db.models import PasswordResetOTP, User, _utcnow
from app.services.sms_service import mask_phone, sms_service

logger = logging.getLogger(__name__)

OTP_EXPIRE_SECONDS = int(os.getenv("OTP_EXPIRE_SECONDS", "300"))
OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))


def validate_and_normalize_indian_phone(phone: Optional[str]) -> Optional[str]:
    """
    Validates and normalizes an Indian mobile phone number to standard 10 digits.
    Returns normalized 10-digit string if valid (starts with 6-9), or None if invalid.
    """
    if not phone or not str(phone).strip():
        return None

    raw = str(phone).strip()
    cleaned = re.sub(r"[\s\-\(\)\.]", "", raw)

    if cleaned.startswith("+91"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]

    if re.match(r"^[6-9]\d{9}$", cleaned):
        return cleaned
    return None


def generate_numeric_otp(length: int = 6) -> str:
    """Generate cryptographically secure numeric OTP string."""
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


def hash_otp_value(otp: str, salt: str) -> str:
    """Compute SHA-256 HMAC/digest of OTP and salt."""
    return hashlib.sha256(f"{otp.strip()}:{salt}".encode("utf-8")).hexdigest()


class OTPService:
    """Service handling password reset OTP lifecycle, security rules, and validation."""

    def request_otp(self, db: Session, identifier: str) -> dict:
        """
        Initiate password reset request for a given user identifier (email, user ID, or phone).
        Enforces cooldown and account enumeration protections.
        """
        clean_id = (identifier or "").strip()
        if not clean_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID or Email identifier is required.",
            )

        clean_phone = validate_and_normalize_indian_phone(clean_id)

        # Lookup user across email, ID, or phone
        user = (
            db.query(User)
            .filter(
                or_(
                    func.lower(User.email) == clean_id.lower(),
                    func.lower(User.id) == clean_id.lower(),
                    (User.phone == clean_phone) if clean_phone else False,
                )
            )
            .first()
        )

        now = _utcnow()

        # If user does not exist or is inactive, return anti-enumeration generic response
        if not user or not user.is_active:
            logger.info("Password reset requested for non-existent/inactive identifier: %s", clean_id)
            return {
                "status": "success",
                "message": "If an active account is associated with this identifier, an OTP has been sent to your registered phone number.",
                "masked_phone": None,
                "session_id": str(uuid.uuid4()),
                "cooldown_seconds": OTP_RESEND_COOLDOWN_SECONDS,
            }

        # Check if user has a registered phone number
        user_phone = validate_and_normalize_indian_phone(user.phone)
        if not user_phone:
            logger.warning("User %s does not have a valid registered mobile number.", user.id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No registered mobile number found for this account. Please contact Super Admin.",
            )

        # Enforce resend cooldown
        latest_otp = (
            db.query(PasswordResetOTP)
            .filter(PasswordResetOTP.user_id == user.id)
            .order_by(PasswordResetOTP.created_at.desc())
            .first()
        )

        if latest_otp and not latest_otp.is_used:
            created_ts = latest_otp.created_at
            if created_ts.tzinfo is None:
                created_ts = created_ts.replace(tzinfo=timezone.utc)
            elapsed = (now - created_ts).total_seconds()
            if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
                remaining = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Please wait {remaining} seconds before requesting a new OTP.",
                )

        # Invalidate any older active OTP records for this user
        db.query(PasswordResetOTP).filter(
            PasswordResetOTP.user_id == user.id,
            PasswordResetOTP.is_used == False,
        ).update({"is_used": True})

        # Generate secure OTP & salt
        raw_otp = generate_numeric_otp(6)
        salt = secrets.token_hex(16)
        hashed_otp = hash_otp_value(raw_otp, salt)

        otp_record = PasswordResetOTP(
            id=str(uuid.uuid4()),
            user_id=user.id,
            hashed_otp=hashed_otp,
            salt=salt,
            attempts=0,
            max_attempts=OTP_MAX_ATTEMPTS,
            is_used=False,
            is_verified=False,
            expires_at=now + timedelta(seconds=OTP_EXPIRE_SECONDS),
            created_at=now,
        )
        db.add(otp_record)
        db.commit()
        db.refresh(otp_record)

        # Dispatch via SMS service
        sms_service.send_otp_sms(user_phone, raw_otp)

        masked = mask_phone(user_phone)
        logger.info("Password reset OTP session created for user: %s (Phone: %s)", user.id, masked)

        return {
            "status": "success",
            "message": "If an active account is associated with this identifier, an OTP has been sent to your registered phone number.",
            "masked_phone": masked,
            "session_id": otp_record.id,
            "cooldown_seconds": OTP_RESEND_COOLDOWN_SECONDS,
        }

    def verify_otp(self, db: Session, session_id: str, otp: str) -> dict:
        """
        Verify the user-provided OTP code against the hashed record for this session.
        Returns a single-use password reset token if valid.
        """
        if not session_id or not str(session_id).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID is required.",
            )

        if not otp or not str(otp).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP code is required.",
            )

        otp_record = (
            db.query(PasswordResetOTP)
            .filter(PasswordResetOTP.id == session_id.strip())
            .first()
        )

        if not otp_record or otp_record.is_used or otp_record.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP session. Please request a new OTP.",
            )

        now = _utcnow()
        exp_ts = otp_record.expires_at
        if exp_ts.tzinfo is None:
            exp_ts = exp_ts.replace(tzinfo=timezone.utc)

        if exp_ts < now:
            otp_record.is_used = True
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new OTP.",
            )

        if otp_record.attempts >= otp_record.max_attempts:
            otp_record.is_used = True
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum incorrect OTP attempts exceeded. Please request a new OTP.",
            )

        # Check hash
        calculated_hash = hash_otp_value(otp, otp_record.salt)
        if not hmac.compare_digest(calculated_hash, otp_record.hashed_otp):
            otp_record.attempts += 1
            remaining = otp_record.max_attempts - otp_record.attempts
            if remaining <= 0:
                otp_record.is_used = True
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Maximum incorrect OTP attempts exceeded. Please request a new OTP.",
                )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Incorrect OTP. {remaining} attempt(s) remaining.",
            )

        # OTP is verified! Generate single-use reset token
        reset_token = secrets.token_urlsafe(32)
        otp_record.is_verified = True
        otp_record.verified_at = now
        otp_record.reset_token = reset_token
        db.commit()

        logger.info("OTP verified successfully for session %s (User: %s)", otp_record.id, otp_record.user_id)

        return {
            "status": "success",
            "message": "OTP verified successfully. You may now set your new password.",
            "reset_token": reset_token,
        }

    def reset_password(
        self,
        db: Session,
        reset_token: str,
        new_password: str,
        confirm_password: str,
    ) -> dict:
        """
        Validate reset token, verify password rules, update user's password,
        and invalidate the OTP record to prevent reuse.
        """
        if not reset_token or not str(reset_token).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token is required.",
            )

        clean_token = reset_token.strip()
        otp_record = (
            db.query(PasswordResetOTP)
            .filter(PasswordResetOTP.reset_token == clean_token)
            .first()
        )

        if not otp_record or otp_record.is_used or not otp_record.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset session.",
            )

        now = _utcnow()
        exp_ts = otp_record.expires_at
        if exp_ts.tzinfo is None:
            exp_ts = exp_ts.replace(tzinfo=timezone.utc)

        if exp_ts < now:
            otp_record.is_used = True
            otp_record.reset_token = None
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset session has expired. Please request a new OTP.",
            )

        if not new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password is required.",
            )

        if len(new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long.",
            )

        if new_password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password and confirm password do not match.",
            )

        user = db.query(User).filter(User.id == otp_record.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated user account not found.",
            )

        # Update password hash using standard GreenNexa pbkdf2_sha256 hashing
        user.hashed_password = security.hash_password(new_password)

        # Invalidate OTP record permanently (single-use)
        otp_record.is_used = True
        otp_record.reset_token = None
        db.commit()

        logger.info("Password successfully updated for user %s via OTP verification.", user.id)

        return {
            "status": "success",
            "message": "Password updated successfully. Please return to login.",
        }


otp_service = OTPService()
