from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.procurement import IntentStatus


class ProcurementIntentCreate(BaseModel):
    farmer_id: UUID | None = None
    centre_id: UUID
    crop_id: UUID
    land_holding_id: UUID
    expected_quantity_kg: Decimal = Field(gt=Decimal("0"))
    ready_date: date

    model_config = ConfigDict(from_attributes=True)


class ProcurementIntentResponse(BaseModel):
    id: UUID
    farmer_id: UUID
    centre_id: UUID
    crop_id: UUID
    land_holding_id: UUID
    expected_quantity_kg: Decimal
    ready_date: date
    status: IntentStatus
    cancellation_reason: str | None = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
