from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DesignCreate(BaseModel):
    design_type: str
    gif_name: str
    callsign: str = Field(min_length=6, max_length=6)
    num_frames: int = Field(default=0, ge=0)
    num_packets: int = Field(default=0, ge=0)
    creator: str | None = None
    description: str | None = None


class DesignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    callsign: str
    design_type: str
    gif_name: str
    creator: str | None
    description: str | None
    num_frames: int
    num_packets: int
    download_count: int
    created_at: datetime
    updated_at: datetime


class DesignWithPreviewOut(DesignOut):
    preview_storage_bucket: str | None = None
    preview_storage_path: str | None = None
    preview_content_type: str | None = None
