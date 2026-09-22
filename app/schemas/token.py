from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.token import TokenStatus
from app.schemas.common import IdentifierResponse


class TokenCallNextRequest(BaseModel):
    counter_id: UUID | None = Field(
        default=None,
        description="Optional counter ID calling the token",
    )


class TokenResponse(IdentifierResponse):
    token_number: str
    sequence_number: int
    queue_id: UUID
    queue_entry_id: UUID
    farmer_id: UUID
    counter_id: UUID | None = None
    status: TokenStatus
    called_at: datetime | None = None
    processing_started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    updated_at: datetime
