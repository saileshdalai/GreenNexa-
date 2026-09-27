"""
GreenNexa — Seed Demo Data.

Seeds standard organisations and demo user accounts on startup.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import Organisation, PlatformState, User, _utcnow

logger = logging.getLogger(__name__)

DEMO_ACCOUNTS = [
    {
        "id": "superadmin_demo",
        "user_id": "superadmin_demo",
        "role": User.ROLE_SUPER_ADMIN,
        "email": "superadmin@greennexa.com",
        "password": "SuperAdmin123!",
        "full_name": "Global Super Admin",
        "organisation_id": None,
        "description": "System-wide administrator with access across all organisations.",
    },
]

STATE_KEY_DATA_CLEARED = "data_cleared"


def is_platform_data_cleared(db: Session) -> bool:
    """
    Check if the platform has undergone a destructive Clear All Data reset.
    Returns True if data_cleared flag is set to 'true'.
    """
    try:
        state = db.query(PlatformState).filter_by(key=STATE_KEY_DATA_CLEARED).first()
        return state is not None and state.value.lower() == "true"
    except Exception as e:
        logger.warning("Could not read platform state: %s", e)
        return False


def set_platform_data_cleared(db: Session, cleared: bool = True) -> None:
    """
    Record or update whether the platform is in a cleared / reset state.
    """
    try:
        state = db.query(PlatformState).filter_by(key=STATE_KEY_DATA_CLEARED).first()
        val_str = "true" if cleared else "false"
        if not state:
            state = PlatformState(key=STATE_KEY_DATA_CLEARED, value=val_str)
            db.add(state)
        else:
            state.value = val_str
            state.updated_at = _utcnow()
        db.flush()
    except Exception as e:
        logger.error("Failed to set platform cleared state: %s", e)
        raise


def seed_demo_data(db: Session, force: bool = False) -> dict:
    """
    Ensure demo organisations and single Super Admin demo user exist in the database.
    Idempotent — removes legacy demo accounts (admin@college.edu, demo@greennexa.com, and any VIEWER users)
    while preserving all organisations, telemetry, anomalies, recommendations, and IoT devices.

    If a destructive 'Clear All Data' reset was executed (and force=False), default demo
    organisations (ORG-COL-001, ORG-HOSP-002) are NOT recreated on startup.
    Only the fixed Super Admin demo account is verified and preserved.
    """
    from app.db.models import Message, OrganisationSensorConfig

    if force:
        set_platform_data_cleared(db, False)

    cleared = is_platform_data_cleared(db)

    # 1. Seed / verify Organisations (only if not in post-reset cleared state)
    if not cleared:
        org1 = db.query(Organisation).filter_by(id="ORG-COL-001").first()
        if not org1:
            org1 = Organisation(
                id="ORG-COL-001",
                name="Green Valley University",
                org_type="college",
                ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
                location="Building A, Campus North",
            )
            db.add(org1)
        elif org1.ownership_type is None:
            # Safe backward-compatible backfill for explicitly known seed organization
            org1.ownership_type = Organisation.OWNERSHIP_GOVERNMENT

        org2 = db.query(Organisation).filter_by(id="ORG-HOSP-002").first()
        if not org2:
            org2 = Organisation(
                id="ORG-HOSP-002",
                name="City Central Hospital",
                org_type="hospital",
                ownership_type=Organisation.OWNERSHIP_PRIVATE,
                location="Block B, Medical Campus",
            )
            db.add(org2)
        elif org2.ownership_type is None:
            # Safe backward-compatible backfill for explicitly known seed organization
            org2.ownership_type = Organisation.OWNERSHIP_PRIVATE

        db.commit()

        # Ensure all organisations have an OrganisationSensorConfig with default baseline/thresholds
        for o in [org1, org2]:
            cfg = db.query(OrganisationSensorConfig).filter_by(organisation_id=o.id).first()
            if not cfg:
                cfg = OrganisationSensorConfig(
                    organisation_id=o.id,
                    data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
                    enabled_sensors="energy|water|waste|air_quality|temperature|humidity",
                    is_active=True,
                )
                db.add(cfg)
        db.commit()
    else:
        logger.info("Platform is in cleared/reset state — skipping default organisation seeding.")

    # 2. Safely remove legacy demo accounts (Admin ORG-COL-001, Viewer ORG-COL-001, old demo users)
    legacy_emails = {"admin@college.edu", "demo@greennexa.com"}
    legacy_users = db.query(User).filter(
        (User.email.in_(legacy_emails)) |
        (User.role == "VIEWER") |
        (User.id.in_(legacy_emails))
    ).all()

    deleted_count = 0
    for u in legacy_users:
        # Clean up any messages referencing this legacy user
        db.query(Message).filter((Message.sender_id == u.id) | (Message.recipient_id == u.id)).delete(synchronize_session=False)
        db.delete(u)
        deleted_count += 1
    db.commit()
    if deleted_count > 0:
        logger.info("Removed %d legacy demo / viewer user accounts.", deleted_count)

    # 3. Seed / verify single fixed Super Admin Demo account
    super_admin_cfg = DEMO_ACCOUNTS[0]
    existing_super = (
        db.query(User)
        .filter((User.id == super_admin_cfg["id"]) | (User.email == super_admin_cfg["email"]))
        .first()
    )

    created_count = 0
    if not existing_super:
        user = User(
            id=super_admin_cfg["id"],
            email=super_admin_cfg["email"],
            hashed_password=hash_password(super_admin_cfg["password"]),
            full_name=super_admin_cfg["full_name"],
            role=super_admin_cfg["role"],
            organisation_id=super_admin_cfg["organisation_id"],
            is_active=True,
        )
        db.add(user)
        created_count += 1
    else:
        existing_super.id = super_admin_cfg["id"]
        existing_super.role = User.ROLE_SUPER_ADMIN
        # Only initialize hashed_password if missing; NEVER overwrite an existing user's password on startup/bootstrap
        if not existing_super.hashed_password:
            existing_super.hashed_password = hash_password(super_admin_cfg["password"])
        existing_super.is_active = True

    db.commit()

    logger.info("Demo data seed complete. Added %d new demo user accounts. Organisations seeded: %s", created_count, not cleared)
    return {
        "status": "ok",
        "created_users": created_count,
        "deleted_legacy_users": deleted_count,
        "organisations_seeded": not cleared,
    }
