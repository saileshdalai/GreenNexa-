"""
GreenNexa — Shared Core Common Helpers.
"""

from typing import Any


def is_municipality(org_or_type: Any) -> bool:
    """
    Authoritative predicate for Municipality organisations.
    Returns True ONLY for Municipality.
    Returns False for Municipal Office, Hospital, School, etc.
    """
    if not org_or_type:
        return False
    if hasattr(org_or_type, "org_type"):
        t = (org_or_type.org_type or "").strip().lower()
    elif isinstance(org_or_type, str):
        t = org_or_type.strip().lower()
    elif isinstance(org_or_type, dict):
        t = (
            org_or_type.get("org_type")
            or org_or_type.get("facility_type")
            or org_or_type.get("type")
            or ""
        ).strip().lower()
    else:
        return False

    if t in ("municipal office", "municipal_office"):
        return False

    return t in ("municipality", "municipality_civic")
