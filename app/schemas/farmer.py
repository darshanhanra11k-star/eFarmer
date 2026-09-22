from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import IdentifierResponse

PHONE_PATTERN = r"^\d{10}$"


class FarmerCreate(BaseModel):
    farmer_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    village: str | None = Field(default=None, min_length=1, max_length=120)
    block: str | None = Field(default=None, min_length=1, max_length=120)
    district: str | None = Field(default=None, min_length=1, max_length=120)
    state: str | None = Field(default=None, min_length=1, max_length=120)


class FarmerResponse(IdentifierResponse):
    farmer_id: str = Field(min_length=1, max_length=64)
    name: str
    phone: str | None = None
    village: str | None = None
    block: str | None = None
    district: str | None = None
    state: str | None = None
    active: bool = True
    updated_at: datetime
