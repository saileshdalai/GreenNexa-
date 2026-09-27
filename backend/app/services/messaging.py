"""
GreenNexa — In-App Messaging Service.

Handles message delivery, recipient authorization, organisation boundary enforcement,
inbox/sent queries, unread count tracking, and message state transitions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db.models import Message, User
from app.schemas.message import (
    MessageResponse,
    RecipientUserItem,
)

logger = logging.getLogger(__name__)


class MessagingService:
    """
    Service handling in-app messaging operations, recipient permission checks,
    and organisation isolation rules.
    """

    def send_message(
        self,
        db: Session,
        sender: User,
        recipient_id: str,
        subject: Optional[str],
        body: str,
    ) -> MessageResponse:
        """
        Send an in-app message from sender to recipient_id.
        Enforces recipient validity and organisation boundaries.
        """
        # 1. Recipient lookup
        recipient = db.query(User).filter(User.id == recipient_id).first()
        if not recipient or not recipient.is_active:
            raise ValueError(f"Recipient user '{recipient_id}' not found or inactive.")

        # 2. Organisation access check
        if sender.role != User.ROLE_SUPER_ADMIN:
            if recipient.organisation_id != sender.organisation_id:
                raise PermissionError("Users can only message members within their authorized organisation.")

        # 3. Create message record
        msg = Message(
            sender_id=sender.id,
            recipient_id=recipient.id,
            organisation_id=sender.organisation_id,
            subject=subject.strip() if subject else None,
            body=body,
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        return self._to_response(msg, sender_name=sender.full_name, recipient_name=recipient.full_name)

    def get_inbox(
        self,
        db: Session,
        user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[int, List[MessageResponse]]:
        """
        Retrieve inbox messages received by the user.
        """
        query = (
            db.query(Message)
            .filter(Message.recipient_id == user.id, Message.is_archived == False)
        )
        total = query.count()
        messages = query.order_by(Message.created_at.desc()).offset(offset).limit(limit).all()

        items = [self._to_response(m) for m in messages]
        return total, items

    def get_sent_messages(
        self,
        db: Session,
        user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[int, List[MessageResponse]]:
        """
        Retrieve sent messages delivered by the user.
        """
        query = (
            db.query(Message)
            .filter(Message.sender_id == user.id, Message.is_archived == False)
        )
        total = query.count()
        messages = query.order_by(Message.created_at.desc()).offset(offset).limit(limit).all()

        items = [self._to_response(m) for m in messages]
        return total, items

    def get_unread_count(self, db: Session, user: User) -> int:
        """
        Count unread inbox messages for the user.
        """
        return (
            db.query(Message)
            .filter(
                Message.recipient_id == user.id,
                Message.is_read == False,
                Message.is_archived == False,
            )
            .count()
        )

    def get_message_by_id(
        self,
        db: Session,
        user: User,
        message_id: str,
    ) -> MessageResponse:
        """
        Retrieve a single message by ID.
        Marks message as read if recipient opens an unread message.
        """
        msg = db.query(Message).filter(Message.id == message_id).first()
        if not msg:
            raise ValueError(f"Message '{message_id}' not found.")

        # Access check
        if user.id not in {msg.sender_id, msg.recipient_id} and user.role != User.ROLE_SUPER_ADMIN:
            raise PermissionError("Access to this message is forbidden.")

        # Mark read if opened by recipient
        if user.id == msg.recipient_id and not msg.is_read:
            msg.is_read = True
            msg.read_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(msg)

        return self._to_response(msg)

    def mark_as_read(
        self,
        db: Session,
        user: User,
        message_id: str,
    ) -> MessageResponse:
        """
        Explicitly mark a message as read by the recipient.
        """
        msg = db.query(Message).filter(Message.id == message_id).first()
        if not msg:
            raise ValueError(f"Message '{message_id}' not found.")

        if user.id != msg.recipient_id:
            raise PermissionError("Only the recipient can mark a message as read.")

        if not msg.is_read:
            msg.is_read = True
            msg.read_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(msg)

        return self._to_response(msg)

    def get_valid_recipients(
        self,
        db: Session,
        user: User,
    ) -> List[RecipientUserItem]:
        """
        Retrieve valid users that current user can message.
        Excludes self, inactive users, and cross-organisation users (unless SUPER_ADMIN).
        """
        query = db.query(User).filter(User.is_active == True, User.id != user.id)

        if user.role != User.ROLE_SUPER_ADMIN:
            query = query.filter(User.organisation_id == user.organisation_id)

        users = query.order_by(User.full_name.asc()).all()
        return [RecipientUserItem.model_validate(u) for u in users]

    def _to_response(
        self,
        msg: Message,
        sender_name: Optional[str] = None,
        recipient_name: Optional[str] = None,
    ) -> MessageResponse:
        """Convert Message ORM object to MessageResponse schema."""
        s_name = sender_name or (msg.sender.full_name if msg.sender else None)
        r_name = recipient_name or (msg.recipient.full_name if msg.recipient else None)

        return MessageResponse(
            id=msg.id,
            sender_id=msg.sender_id,
            sender_name=s_name,
            recipient_id=msg.recipient_id,
            recipient_name=r_name,
            organisation_id=msg.organisation_id,
            subject=msg.subject,
            body=msg.body,
            is_read=msg.is_read,
            created_at=msg.created_at,
            read_at=msg.read_at,
        )


# Singleton instance
messaging_service = MessagingService()
