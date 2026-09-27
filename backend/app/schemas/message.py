"""
GreenNexa — Pydantic schemas for In-App Messaging API.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class MessageSendRequest(BaseModel):
    """
    Request payload to send an in-app message.
    """
    recipient_id: str = Field(..., description="ID of the recipient user")
    subject: Optional[str] = Field(None, max_length=200, description="Optional subject line (max 200 chars)")
    body: str = Field(..., max_length=5000, description="Message text content (max 5000 chars)")

    @field_validator("body")

    def validate_body_non_empty(cls, v: str) -> str:
        clean = v.strip() if v else ""
        if not clean:
            raise ValueError("Message body cannot be empty or whitespace only.")
        if len(v) > 5000:
            raise ValueError("Message body exceeds maximum length of 5000 characters.")
        return v

    @field_validator("subject")

    def validate_subject(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 200:
            raise ValueError("Subject line exceeds maximum length of 200 characters.")
        return v


class MessageResponse(BaseModel):
    """
    Response schema for single message item.
    """
    id: str
    sender_id: str
    sender_name: Optional[str] = None
    recipient_id: str
    recipient_name: Optional[str] = None
    organisation_id: Optional[str] = None
    subject: Optional[str] = None
    body: str
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    """
    Paginated list of messages (inbox or sent).
    """
    total: int
    items: List[MessageResponse]


class UnreadCountResponse(BaseModel):
    """
    Count of unread inbox messages.
    """
    unread_count: int


class RecipientUserItem(BaseModel):
    """
    User item returned for populating the recipient 'To' dropdown.
    Explicitly excludes sensitive fields (password, tokens).
    """
    id: str
    full_name: str
    email: str
    role: str
    organisation_id: Optional[str] = None

    model_config = {"from_attributes": True}
