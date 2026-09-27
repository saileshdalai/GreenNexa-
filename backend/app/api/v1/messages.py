"""
GreenNexa — In-App Messaging API Router.

Routes:
  POST  /api/v1/messages               — Send in-app message
  GET   /api/v1/messages/inbox         — List received inbox messages
  GET   /api/v1/messages/sent          — List sent messages
  GET   /api/v1/messages/unread-count  — Get count of unread inbox messages
  GET   /api/v1/messages/recipients    — List valid recipients for current user
  GET   /api/v1/messages/{message_id}  — Read single message
  PATCH /api/v1/messages/{message_id}/read — Mark message as read
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.message import (
    MessageListResponse,
    MessageResponse,
    MessageSendRequest,
    RecipientUserItem,
    UnreadCountResponse,
)
from app.services.messaging import messaging_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/messages", tags=["In-App Messaging"])


@router.post(
    "",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send an in-app message",
    description="Send an in-app text message to an authorized recipient.",
)
def send_message(
    body: MessageSendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Send an in-app text message to another user.
    """
    try:
        res = messaging_service.send_message(
            db=db,
            sender=current_user,
            recipient_id=body.recipient_id,
            subject=body.subject,
            body=body.body,
        )
        return res
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        detail_str = str(e)
        if "not found" in detail_str.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail_str,
            )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail_str,
        )
    except Exception as e:
        logger.exception("Unexpected error sending message: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while sending the message.",
        )


@router.get(
    "/inbox",
    response_model=MessageListResponse,
    summary="List inbox messages",
    description="Return received inbox messages for the authenticated user (newest first).",
)
def get_inbox(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageListResponse:
    """
    Retrieve inbox messages for the current user.
    """
    total, items = messaging_service.get_inbox(db=db, user=current_user, limit=limit, offset=offset)
    return MessageListResponse(total=total, items=items)


@router.get(
    "/sent",
    response_model=MessageListResponse,
    summary="List sent messages",
    description="Return sent messages for the authenticated user (newest first).",
)
def get_sent_messages(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageListResponse:
    """
    Retrieve sent messages for the current user.
    """
    total, items = messaging_service.get_sent_messages(db=db, user=current_user, limit=limit, offset=offset)
    return MessageListResponse(total=total, items=items)


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread inbox count",
    description="Return total count of unread inbox messages for the authenticated user.",
)
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnreadCountResponse:
    """
    Return count of unread inbox messages.
    """
    count = messaging_service.get_unread_count(db=db, user=current_user)
    return UnreadCountResponse(unread_count=count)


@router.get(
    "/recipients",
    response_model=List[RecipientUserItem],
    summary="List valid recipients",
    description="Return active users that current user is authorized to message.",
)
def get_valid_recipients(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RecipientUserItem]:
    """
    Return valid recipients for the recipient 'To' dropdown.
    """
    return messaging_service.get_valid_recipients(db=db, user=current_user)


@router.get(
    "/{message_id}",
    response_model=MessageResponse,
    summary="Get message details",
    description="Retrieve a single message by ID. Marks message as read if opened by recipient.",
)
def get_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Get single message by ID.
    """
    try:
        return messaging_service.get_message_by_id(db=db, user=current_user, message_id=message_id)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.patch(
    "/{message_id}/read",
    response_model=MessageResponse,
    summary="Mark message as read",
    description="Mark a received message as read explicitly by the recipient.",
)
def mark_message_read(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Mark message as read.
    """
    try:
        return messaging_service.mark_as_read(db=db, user=current_user, message_id=message_id)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
