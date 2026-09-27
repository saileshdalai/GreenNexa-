"""
GreenNexa — SMS Delivery Service.

Handles delivery of One-Time Passwords (OTP) and system SMS alerts.
Reuses existing project environment configurations and supports standard
SMS gateways (Fast2SMS, MSG91, Twilio) when configured via environment variables.

Credentials strictly remain server-side in environment variables and are never
exposed to frontend clients. If no provider is configured, avoids inventing
fake credentials and provides clean logging without leaking OTP in production logs.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    _env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
except Exception:
    pass


def mask_phone(phone: Optional[str]) -> str:
    """Mask phone number to protect privacy in logs and UI (e.g. ******1868)."""
    if not phone or len(phone) < 4:
        return "******"
    digits_only = re.sub(r"\D", "", phone)
    if len(digits_only) >= 4:
        return f"******{digits_only[-4:]}"
    return f"******{phone[-4:]}"


class SMSService:
    """Service to send transactional SMS / OTPs via configured provider."""

    @property
    def provider(self) -> str:
        return os.getenv("SMS_PROVIDER", "").strip().lower()

    @property
    def app_env(self) -> str:
        return os.getenv("APP_ENV", "development").strip().lower()

    @property
    def twofactor_api_key(self) -> str:
        return os.getenv("TWOFACTOR_API_KEY", "").strip()

    @property
    def twofactor_otp_template(self) -> str:
        return os.getenv("TWOFACTOR_OTP_TEMPLATE", "").strip()

    @property
    def fast2sms_api_key(self) -> str:
        return os.getenv("FAST2SMS_API_KEY", "").strip()

    @property
    def msg91_auth_key(self) -> str:
        return os.getenv("MSG91_AUTH_KEY", "").strip()

    @property
    def msg91_sender_id(self) -> str:
        return os.getenv("MSG91_SENDER_ID", "GRNNEX").strip()

    @property
    def msg91_template_id(self) -> str:
        return os.getenv("MSG91_TEMPLATE_ID", "").strip()

    @property
    def twilio_account_sid(self) -> str:
        return os.getenv("TWILIO_ACCOUNT_SID", "").strip()

    @property
    def twilio_auth_token(self) -> str:
        return os.getenv("TWILIO_AUTH_TOKEN", "").strip()

    @property
    def twilio_from_number(self) -> str:
        return os.getenv("TWILIO_FROM_NUMBER", "").strip()

    def is_configured(self) -> bool:
        """Returns True if a real SMS provider is configured with credentials."""
        p = self.provider
        if p == "2factor" and self.twofactor_api_key:
            return True
        if p == "fast2sms" and self.fast2sms_api_key:
            return True
        if p == "msg91" and self.msg91_auth_key:
            return True
        if p == "twilio" and self.twilio_account_sid and self.twilio_auth_token and self.twilio_from_number:
            return True
        return False

    def send_otp_sms(self, phone: str, otp: str) -> bool:
        """
        Deliver a 6-digit OTP code to the recipient's phone number.
        Returns True if delivered or simulated successfully.
        """
        masked = mask_phone(phone)
        p = self.provider

        # 0. 2Factor Provider (Official API/V1 endpoint)
        if p == "2factor" and self.twofactor_api_key:
            return self._send_2factor(phone, otp, masked)

        # 1. Fast2SMS Provider
        if p == "fast2sms" and self.fast2sms_api_key:
            return self._send_fast2sms(phone, otp, masked)

        # 2. MSG91 Provider
        if p == "msg91" and self.msg91_auth_key:
            return self._send_msg91(phone, otp, masked)

        # 3. Twilio Provider
        if p == "twilio" and self.twilio_account_sid and self.twilio_auth_token and self.twilio_from_number:
            return self._send_twilio(phone, otp, masked)

        # 4. Fallback / Dev Mode — No SMS provider configured
        if self.app_env == "development":
            # In development only, log simulation notice
            logger.info(
                "SMS Provider not configured (set SMS_PROVIDER and API key in .env). "
                "Simulated OTP dispatch to %s.",
                masked,
            )
            return True

        logger.warning(
            "SMS delivery failed: No production SMS provider configured (SMS_PROVIDER='%s'). "
            "Recipient: %s.",
            p,
            masked,
        )
        return False

    def _send_2factor(self, phone: str, otp: str, masked: str) -> bool:
        """
        Send custom 6-digit OTP via official 2Factor.in API.
        Endpoint: https://2factor.in/API/V1/{api_key}/SMS/{phone}/{otp_value}
        Optionally supports custom DLT template name if TWOFACTOR_OTP_TEMPLATE is specified.
        Handles provider HTTP errors safely without leaking keys or OTP in logs.
        """
        try:
            api_key = self.twofactor_api_key
            template = self.twofactor_otp_template
            clean_digits = re.sub(r"\D", "", phone)
            if len(clean_digits) == 10:
                clean_phone = f"91{clean_digits}"
            elif len(clean_digits) == 12 and clean_digits.startswith("91"):
                clean_phone = clean_digits
            else:
                clean_phone = clean_digits

            sanitized_path = (
                f"/API/V1/<REDACTED_API_KEY>/SMS/{masked}/<OTP>/{template}"
                if template
                else f"/API/V1/<REDACTED_API_KEY>/SMS/{masked}/<OTP>"
            )
            logger.info("2Factor request started: Host=2factor.in, Path=%s, Method=GET", sanitized_path)

            if template:
                url = (
                    f"https://2factor.in/API/V1/{urllib.parse.quote(api_key)}"
                    f"/SMS/{clean_phone}/{urllib.parse.quote(otp)}/{urllib.parse.quote(template)}"
                )
            else:
                url = (
                    f"https://2factor.in/API/V1/{urllib.parse.quote(api_key)}"
                    f"/SMS/{clean_phone}/{urllib.parse.quote(otp)}"
                )

            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "GreenNexa-SMS/1.0",
                    "Accept": "application/json",
                },
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_text = resp.read().decode("utf-8")
                try:
                    result = json.loads(resp_text)
                except Exception:
                    result = {}

                provider_status = result.get("Status")
                session_ref = result.get("Details", "")

                logger.info(
                    "2Factor response received: HTTP Status=%d, Provider Status=%s, SessionRef=%s",
                    resp.status,
                    provider_status,
                    session_ref,
                )

                if resp.status == 200 and provider_status == "Success":
                    logger.info("2Factor dispatch SUCCESS: SessionRef=%s for recipient %s", session_ref, masked)
                    return True
                else:
                    logger.error(
                        "2Factor dispatch FAILURE: Status=%s, Details=%s",
                        provider_status,
                        session_ref,
                    )
                    return False
        except urllib.error.HTTPError as he:
            try:
                err_text = he.read().decode("utf-8")
                err_json = json.loads(err_text)
                logger.error("2Factor HTTP error %d: %s", he.code, err_json.get("Details", "Request failed"))
            except Exception:
                logger.error("2Factor HTTP error %d for recipient %s", he.code, masked)
            return False
        except Exception as e:
            logger.error("2Factor dispatch exception for %s: %s", masked, type(e).__name__)
            return False

    def _send_fast2sms(self, phone: str, otp: str, masked: str) -> bool:
        """Send OTP via Fast2SMS Quick SMS / OTP route."""
        try:
            url = "https://www.fast2sms.com/dev/bulkV2"
            payload = {
                "variables_values": otp,
                "route": "otp",
                "numbers": phone,
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "authorization": self.fast2sms_api_key,
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                if result.get("return") is True:
                    logger.info("Fast2SMS OTP sent successfully to %s", masked)
                    return True
                logger.error("Fast2SMS error response: %s", result.get("message"))
                return False
        except Exception as e:
            logger.error("Fast2SMS dispatch failed for %s: %s", masked, e)
            return False

    def _send_msg91(self, phone: str, otp: str, masked: str) -> bool:
        """Send OTP via MSG91 Send OTP endpoint."""
        try:
            url = (
                f"https://control.msg91.com/api/v5/otp"
                f"?template_id={urllib.parse.quote(self.msg91_template_id)}"
                f"&mobile=91{phone}"
                f"&authkey={urllib.parse.quote(self.msg91_auth_key)}"
                f"&otp={urllib.parse.quote(otp)}"
            )
            req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info("MSG91 OTP sent successfully to %s (Status: %s)", masked, resp.status)
                return True
        except Exception as e:
            logger.error("MSG91 dispatch failed for %s: %s", masked, e)
            return False

    def _send_twilio(self, phone: str, otp: str, masked: str) -> bool:
        """Send OTP via Twilio SMS API."""
        try:
            import base64
            sid = self.twilio_account_sid
            token = self.twilio_auth_token
            from_num = self.twilio_from_number

            url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
            formatted_phone = f"+91{phone}" if not phone.startswith("+") else phone
            body_text = f"Your GreenNexa password reset verification code is: {otp}. Valid for 5 minutes. Do not share this code."

            data = urllib.parse.urlencode({
                "To": formatted_phone,
                "From": from_num,
                "Body": body_text,
            }).encode("utf-8")

            auth_str = f"{sid}:{token}"
            auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Authorization": f"Basic {auth_b64}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info("Twilio SMS OTP sent successfully to %s (Status: %s)", masked, resp.status)
                return True
        except Exception as e:
            logger.error("Twilio dispatch failed for %s: %s", masked, e)
            return False


sms_service = SMSService()
