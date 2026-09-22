from datetime import date as dt_date
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.queue import QueueStatus
from app.schemas.common import IdentifierResponse


class QueueCreate(BaseModel):
    centre_id: UUID
    crop_id: UUID | None = None
    date: dt_date | None = None


class QueueJoinRequest(BaseModel):
    farmer_id: UUID | None = Field(
        default=None,
        description="Farmer ID (required for officers)",
    )


class QueueResponse(IdentifierResponse):
    centre_id: UUID
    crop_id: UUID | None = None
    date: dt_date
    status: QueueStatus
    updated_at: datetime


class QueueStatusResponse(BaseModel):
    queue_id: UUID
    centre_id: UUID
    date: dt_date
    status: QueueStatus
    total_waiting: int
    total_called: int
    total_processing: int
    total_completed: int
    total_cancelled: int
    current_called_token: str | None = None
    last_issued_token: str | None = None
