"""
GreenNexa — Pydantic schemas for Notification & Read State Management.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class UnreadNotificationsResponse(BaseModel):
    has_unread: bool = Field(False, description="True if organisation has any unread/unseen active events")
    total_unread: int = Field(0, description="Total count of unread anomalies/events")
    modules: Dict[str, bool] = Field(default_factory=dict, description="Module-level unread state (e.g. energy: True)")
    blocks: Dict[str, bool] = Field(default_factory=dict, description="Block-level unread state across all modules (e.g. BLK-001: True)")
    wards: Dict[str, bool] = Field(default_factory=dict, description="Ward-level unread state for municipalities (e.g. '1': True)")
    module_blocks: Dict[str, Dict[str, bool]] = Field(
        default_factory=dict,
        description="Per-module, per-block unread state (e.g. energy: { BLK-002: True })"
    )
    sections: Dict[str, bool] = Field(
        default_factory=dict,
        description="Section-level unread state for sidebar/nav items (e.g. anomalies: True)"
    )
    unseen_anomaly_ids: List[str] = Field(
        default_factory=list,
        description="List of unread anomaly IDs"
    )


class MarkReadRequest(BaseModel):
    anomaly_ids: Optional[List[str]] = Field(None, description="Specific anomaly IDs to mark as seen")
    metric: Optional[str] = Field(None, description="Module/metric name whose unread anomalies should be marked as seen")
    block_id: Optional[str] = Field(None, description="Block ID whose unread anomalies should be marked as seen")
    ward_id: Optional[str] = Field(None, description="Ward number whose unread anomalies should be marked as seen (municipalities) or a real ward identifier")
    organisation_id: Optional[str] = Field(None, description="Optional target organisation ID")
    all_unseen: Optional[bool] = Field(False, description="Mark all unread anomalies for this organisation as seen")
    mark_all: Optional[bool] = Field(False, description="Alias for all_unseen")


class MarkReadResponse(BaseModel):
    status: str = "success"
    marked_count: int = 0
    message: str = "Unread notifications updated"
