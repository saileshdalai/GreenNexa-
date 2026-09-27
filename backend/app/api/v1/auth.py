"""
GreenNexa — Authentication API Router.

Routes:
  POST /api/v1/auth/login          — Authenticate email + password and issue token
  GET  /api/v1/auth/me             — Get currently authenticated user details
  GET  /api/v1/auth/demo-accounts  — List available demo login accounts
  POST /api/v1/auth/seed           — Manually trigger demo account creation
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core import security
from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.db.models import Organisation, User
from app.db.seed_demo import DEMO_ACCOUNTS, seed_demo_data
from app.schemas.auth import (
    DemoAccountsResponse,
    DemoUserAccount,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TokenResponse,
    UserResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
)
from app.services.otp_service import otp_service
from app.services.synthetic_simulator import simulator_instance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and obtain access token",
    description=(
        "Authenticates a user by User ID or email and password. "
        "Returns a Bearer token and user profile."
    ),
)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate User ID or email and password against stored database hash."""
    raw_identifier = body.email or body.username or body.user_id
    if not raw_identifier or not raw_identifier.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID, username, or email is required.",
        )
    login_val = raw_identifier.lower().strip()

    user = (
        db.query(User)
        .filter(
            or_(
                func.lower(User.email) == login_val,
                func.lower(User.id) == login_val,
                func.lower(func.replace(User.id, "_demo", "")) == login_val,
            )
        )
        .first()
    )

    if user is None or not security.verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # 1. Super Admin is a global platform role and bypasses organisation ownership checks
    if user.role == User.ROLE_SUPER_ADMIN:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated.",
            )
    else:
        # Organisation ADMIN authentication
        if not user.organisation_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not assigned to an organisation.",
            )

        org = db.query(Organisation).filter_by(id=user.organisation_id).first()
        if not org or not org.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organisation is deactivated. Access is blocked.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated.",
            )

        # Validate ownership type: mandatory for organisation ADMIN login
        if not body.organisation_type or not body.organisation_type.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organisation type is required for organisation admin login.",
            )

        selected_type = body.organisation_type.strip().upper()
        if selected_type not in (Organisation.OWNERSHIP_GOVERNMENT, Organisation.OWNERSHIP_PRIVATE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organisation type. Allowed values are GOVERNMENT or PRIVATE.",
            )

        stored_type = (org.ownership_type or "").strip().upper()
        if stored_type != selected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Selected organisation type does not match these credentials.",
            )

    # Issue token containing user claims
    token_claims = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "organisation_id": user.organisation_id,
    }
    access_token = security.create_access_token(data=token_claims)

    logger.info("User logged in successfully: email=%s role=%s", user.email, user.role)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Decodes Authorization Bearer header and returns the current user profile.",
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Return user profile for the supplied Bearer token."""
    return UserResponse.model_validate(current_user)


# ---------------------------------------------------------------------------
# GET /auth/demo-accounts
# ---------------------------------------------------------------------------
@router.get(
    "/demo-accounts",
    response_model=DemoAccountsResponse,
    summary="List demo login accounts for testing",
    description="Returns pre-seeded demo user credentials for Super Admin.",
)
def get_demo_accounts():
    """Return demo login accounts for documentation and testing."""
    accounts = [DemoUserAccount(**acc) for acc in DEMO_ACCOUNTS]
    return DemoAccountsResponse(
        message="Use this Super Admin demo account to log in and manage the platform.",
        accounts=accounts,
    )


# ---------------------------------------------------------------------------
# POST /auth/seed
# ---------------------------------------------------------------------------
@router.post(
    "/seed",
    summary="Seed demo organisations and demo users",
    description="Idempotent endpoint to create demo user accounts in the database.",
)
def trigger_seed(
    force: bool = Query(False, description="Force re-seeding even after a destructive reset"),
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """Seed demo accounts on demand (requires ADMIN or SUPER_ADMIN role)."""
    return seed_demo_data(db, force=force)


# ---------------------------------------------------------------------------
# POST /auth/forgot-password/request
# ---------------------------------------------------------------------------
@router.post(
    "/forgot-password/request",
    response_model=ForgotPasswordResponse,
    summary="Request password reset OTP",
    description="Generates a server-side OTP sent to the registered mobile number for the user identifier.",
)
def forgot_password_request(
    body: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Initiate password reset: lookup user, generate OTP, send via SMS."""
    res = otp_service.request_otp(db, identifier=body.identifier)
    return ForgotPasswordResponse(**res)


# ---------------------------------------------------------------------------
# POST /auth/forgot-password/verify-otp
# ---------------------------------------------------------------------------
@router.post(
    "/forgot-password/verify-otp",
    response_model=VerifyOTPResponse,
    summary="Verify password reset OTP",
    description="Verifies the submitted OTP against the session and issues a short-lived reset token.",
)
def forgot_password_verify_otp(
    body: VerifyOTPRequest,
    db: Session = Depends(get_db),
):
    """Verify OTP and return single-use reset token."""
    res = otp_service.verify_otp(db, session_id=body.session_id, otp=body.otp)
    return VerifyOTPResponse(**res)


# ---------------------------------------------------------------------------
# POST /auth/forgot-password/reset-password
# ---------------------------------------------------------------------------
@router.post(
    "/forgot-password/reset-password",
    response_model=ResetPasswordResponse,
    summary="Reset password with verified token",
    description="Updates password, applies GreenNexa security rules, and invalidates the OTP.",
)
def forgot_password_reset(
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Reset password using verified reset token."""
    res = otp_service.reset_password(
        db,
        reset_token=body.reset_token,
        new_password=body.new_password,
        confirm_password=body.confirm_password,
    )
    return ResetPasswordResponse(**res)


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------
@router.post(
    "/logout",
    summary="Logout user and automatically disable demo mode",
    description="Logs out the user and guarantees all demo mode scopes and simulator activity are disabled.",
)
def logout_endpoint(
    organisation_id: Optional[str] = Query(None, description="Optional target organisation ID to unenroll from demo mode"),
    current_user: User = Depends(get_current_user),
):
    """Logout handler: stops demo simulator activity for the session/org."""
    target_org = organisation_id or current_user.organisation_id
    if target_org:
        simulator_instance.stop(organisation_id=target_org)
        logger.info("Demo mode stopped on logout for org=%s by user=%s", target_org, current_user.email)
    elif current_user.role == User.ROLE_SUPER_ADMIN:
        simulator_instance.stop()
        logger.info("Simulator global stop on logout by SUPER_ADMIN %s", current_user.email)

    return {
        "status": "success",
        "message": "Logged out successfully and demo mode state cleared.",
    }


