"""
GreenNexa — Core Security & Authentication Utilities.

Provides secure password hashing (PBKDF2-HMAC-SHA256) and token handling.
No external native library dependencies required.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

from fastapi.security import HTTPBearer

SECRET_KEY = os.getenv("SECRET_KEY", "greennexa-super-secret-key-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_SECONDS = 86400 * 7  # 7 days

security_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2 with SHA-256 and a random salt.
    Format: pbkdf2_sha256$iterations$salt_hex$hash_hex
    """
    salt = os.urandom(16)
    iterations = 100_000
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    salt_hex = salt.hex()
    hash_hex = hash_bytes.hex()
    return f"pbkdf2_sha256${iterations}${salt_hex}${hash_hex}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a pbkdf2_sha256 stored hash string."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hash = parts[3]

        hash_bytes = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt, iterations
        )
        return hmac.compare_digest(hash_bytes.hex(), expected_hash)
    except Exception:
        return False


def create_access_token(data: dict, expires_in: int = TOKEN_EXPIRE_SECONDS) -> str:
    """
    Generate a signed access token.
    Payload contains token claims + signature.
    """
    payload = data.copy()
    payload["exp"] = int(time.time()) + expires_in
    payload["iat"] = int(time.time())

    payload_json = json.dumps(payload, sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")

    signature = hmac.new(
        SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return f"{payload_b64}.{signature}"


def verify_token(token: str) -> Optional[dict]:
    """Verify access token signature and expiration, returning claims payload."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None

        payload_b64, signature = parts[0], parts[1]

        # Verify signature
        expected_sig = hmac.new(
            SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return None

        # Add back base64 padding
        padding = "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Check expiration
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None


try:
    from dotenv import load_dotenv
    _backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    _env_path = os.path.join(_backend_dir, ".env")
    if os.path.exists(_env_path):
        load_dotenv(dotenv_path=_env_path)
except Exception:
    pass


def verify_confirmation_password(provided_password: Optional[str]) -> bool:
    """
    Authoritatively verify the confirmation password for destructive operations
    (Reset Password and Clear All Data) using constant-time comparison.
    Never exposes or logs the secret.
    """
    if not provided_password:
        return False
    expected = os.getenv("GREENNEXA_DESTRUCTIVE_ACTION_PASSWORD")
    if not expected:
        return False
    return hmac.compare_digest(provided_password.strip(), expected.strip())


