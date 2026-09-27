"""
GreenNexa — Pydantic schemas for Authentication & User API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request — login
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: Optional[str] = Field(None, description="User email address or user ID")
    username: Optional[str] = Field(None, description="Alternative field for user ID / username")
    user_id: Optional[str] = Field(None, description="Alternative field for user ID")
    password: str = Field(..., description="User password")
    organisation_type: Optional[str] = Field(
        None,
        description="Organisation ownership type: GOVERNMENT or PRIVATE (required for organisation ADMIN)",
    )

    model_config = {"json_schema_extra": {
        "example": {
            "email": "admin@college.edu",
            "password": "Admin123!",
            "organisation_type": "GOVERNMENT",
        }
    }}


# ---------------------------------------------------------------------------
# Response — user profile
# ---------------------------------------------------------------------------
class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    organisation_id: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Response — login token with user profile
# ---------------------------------------------------------------------------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ---------------------------------------------------------------------------
# Response — demo user list for documentation/UI preview
# ---------------------------------------------------------------------------
class DemoUserAccount(BaseModel):
    user_id: Optional[str] = None
    role: str
    email: str
    password: str
    full_name: str
    organisation_id: Optional[str]
    description: Optional[str] = None


class DemoAccountsResponse(BaseModel):
    message: str
    accounts: list[DemoUserAccount]


# ---------------------------------------------------------------------------
# OTP & Forgot Password Schemas
# ---------------------------------------------------------------------------
class ForgotPasswordRequest(BaseModel):
    identifier: str = Field(..., description="User ID, Email address, or registered Phone Number")


class ForgotPasswordResponse(BaseModel):
    status: str = "success"
    message: str
    masked_phone: Optional[str] = None
    session_id: Optional[str] = None
    cooldown_seconds: int = 60


class VerifyOTPRequest(BaseModel):
    session_id: str = Field(..., description="OTP session ID returned from request endpoint")
    otp: str = Field(..., min_length=4, max_length=10, description="One-time password")


class VerifyOTPResponse(BaseModel):
    status: str = "success"
    message: str
    reset_token: str


class ResetPasswordRequest(BaseModel):
    reset_token: str = Field(..., description="Reset authorization token from successful OTP verification")
    new_password: str = Field(..., min_length=6, max_length=100, description="New password")
    confirm_password: str = Field(..., min_length=6, max_length=100, description="Confirm new password")


class ResetPasswordResponse(BaseModel):
    status: str = "success"
    message: str
