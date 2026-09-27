"""
GreenNexa — Core Security & Authorization Dependencies.

Provides reusable FastAPI dependencies for:
  - User authentication via JWT Bearer token
  - Role-Based Access Control (RBAC)
  - Organisation data isolation
"""

from __future__ import annotations

import json
import logging
from typing import Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core import security
from app.db.database import get_db
from app.db.models import Organisation, OrganisationSensorConfig, User

logger = logging.getLogger(__name__)


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security.security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Authenticate request via JWT Bearer token and return User ORM object.
    Raises 401 if missing/invalid/expired token.
    Raises 404 if user account no longer exists.
    """
    if auth is None or not auth.credentials or auth.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header (expected 'Bearer <token>').",
        )

    token = auth.credentials
    claims = security.verify_token(token)

    if not claims or "sub" not in claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    user = db.query(User).filter(User.id == claims["sub"]).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    if user.organisation_id and user.role != User.ROLE_SUPER_ADMIN:
        org = db.query(Organisation).filter_by(id=user.organisation_id).first()
        if org and not org.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organisation is deactivated. Access is blocked.",
            )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    valid_roles = (User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)
    if user.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{user.role}' is not recognized or permitted. Only SUPER_ADMIN and ADMIN are supported.",
        )

    return user


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    """
    Dependency factory that enforces Role-Based Access Control (RBAC).

    SUPER_ADMIN is always permitted.
    Other roles must be present in `allowed_roles`.
    Raises 403 Forbidden if user lacks required role.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == User.ROLE_SUPER_ADMIN:
            return current_user

        if current_user.role not in allowed_roles:
            logger.warning(
                "Access denied for user %s (role=%s). Allowed roles: %s",
                current_user.email,
                current_user.role,
                allowed_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Insufficient role permissions for this operation.",
            )
        return current_user

    return role_checker


def verify_organisation_access(
    requested_org_id: Optional[str],
    current_user: User,
) -> str:
    """
    Enforce organisation data isolation.

    - SUPER_ADMIN: Allowed to access any requested_org_id (or falls back to user's org_id).
    - ADMIN: Must ONLY access their own current_user.organisation_id.
      If a different requested_org_id is passed, raises 403 Forbidden.
      If requested_org_id is None or empty, defaults to current_user.organisation_id.

    Returns the resolved organisation_id for database queries.
    """
    user_org = current_user.organisation_id

    # SUPER_ADMIN bypasses org restrictions
    if current_user.role == User.ROLE_SUPER_ADMIN:
        if requested_org_id and requested_org_id.strip():
            return requested_org_id.strip()
        if user_org:
            return user_org
        return ""

    # Non-SUPER_ADMIN: Must match current user's organisation
    if requested_org_id and requested_org_id.strip() and requested_org_id.strip() != user_org:
        logger.warning(
            "Organisation isolation violation by user %s (user_org=%s, requested_org=%s)",
            current_user.email,
            user_org,
            requested_org_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only access data for your own organisation.",
        )

    if not user_org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User is not assigned to an organisation.",
        )

    return user_org


def verify_oversight_read_access(
    requested_org_id: Optional[str],
    current_user: User,
    db: Session,
) -> str:
    """
    READ-ONLY access control for telemetry endpoints (dashboard summaries,
    anomaly lists, recommendation lists).

    - SUPER_ADMIN: may access any requested organisation.
    - ADMIN: may ALWAYS access their own organisation. In addition, a
      Municipality Administrator may READ (oversight intelligence) the data of
      the GOVERNMENT organisations associated with their municipality
      (stored in the municipality's OrganisationSensorConfig json as
      associated_gov_org_ids / _municipality_assoc).

    NEVER use this helper for WRITE endpoints. Writes stay gated behind
    verify_organisation_access / require_roles.
    """
    user_org = current_user.organisation_id

    if current_user.role == User.ROLE_SUPER_ADMIN:
        if requested_org_id and requested_org_id.strip():
            return requested_org_id.strip()
        if user_org:
            return user_org
        return requested_org_id.strip() if requested_org_id else ""

    if not user_org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User is not assigned to an organisation.",
        )

    if not requested_org_id or not requested_org_id.strip():
        return user_org

    target_org_id = requested_org_id.strip()
    if target_org_id == user_org:
        return target_org_id

    # Municipality Admin → read-only oversight of ASSOCIATED GOVERNMENT orgs
    if current_user.role == User.ROLE_ADMIN:
        my_org = db.query(Organisation).filter_by(id=user_org).first()
        if my_org and my_org.org_type and "municipality" in my_org.org_type.lower():
            my_cfg = db.query(OrganisationSensorConfig).filter_by(organisation_id=user_org).first()
            if my_cfg is not None and my_cfg.sensor_configs:
                try:
                    stored = json.loads(my_cfg.sensor_configs)
                except Exception:
                    stored = {}
                assoc_ids = stored.get("associated_gov_org_ids") or stored.get("_municipality_assoc") or []
                if assoc_ids and target_org_id in assoc_ids:
                    return target_org_id

    logger.warning(
        "Oversight read isolation violation by user %s (user_org=%s, requested_org=%s)",
        current_user.email,
        user_org,
        target_org_id,
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied. You can only access data for your own organisation (or associated government organisations in read-only oversight).",
    )
