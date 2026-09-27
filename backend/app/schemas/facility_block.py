"""
GreenNexa — Pydantic schemas for Facility Block Management.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class BlockCreateItem(BaseModel):
    block_id: Optional[str] = Field(None, description="Unique block ID e.g. BLK-001. Generated if omitted.")
    block_name: str = Field(..., min_length=1, max_length=200, description="Block display name e.g. Academic Block")

    @field_validator("block_name")
    @classmethod
    def validate_block_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Block name cannot be empty or whitespace.")
        return clean


class BlockUpdateRequest(BaseModel):
    block_name: Optional[str] = Field(None, min_length=1, max_length=200)
    is_active: Optional[bool] = None

    @field_validator("block_name")
    @classmethod
    def validate_block_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        clean = v.strip()
        if not clean:
            raise ValueError("Block name cannot be empty or whitespace.")
        return clean


class BlockResponse(BaseModel):
    id: str
    organisation_id: str
    block_id: str
    block_name: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BlockListResponse(BaseModel):
    total: int
    items: List[BlockResponse]
