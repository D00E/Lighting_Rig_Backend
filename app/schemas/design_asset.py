from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DesignAssetCreate(BaseModel):
    design_id: UUID
    asset_type: str
    storage_bucket: str
    storage_path: str
    content_type: str | None = None
    size_bytes: int | None = None


class DesignAssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    design_id: UUID
    asset_type: str
    storage_bucket: str
    storage_path: str
    content_type: str | None
    size_bytes: int | None
    created_at: datetime
