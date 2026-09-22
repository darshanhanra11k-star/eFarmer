from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import IdentifierResponse


class CounterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    centre_id: UUID
    name: str
    active: bool = True
    created_at: datetime
    updated_at: datetime


class CentreResponse(IdentifierResponse):
    name: str
    district: str
    block: str | None = None
    state: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    active: bool = True
    updated_at: datetime
    counters: list[CounterResponse] = Field(default_factory=list)
