from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer


class AllocationDecisionResponse(BaseModel):
    id: UUID
    allocation_run_id: UUID
    intent_id: UUID
    farmer_id: UUID
    requested_quantity_kg: Decimal
    allocated_quantity_kg: Decimal
    remaining_capacity_kg: Decimal
    selected: bool
    rank: int
    ordering_reason: str
    tie_break_digest: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer(
        "requested_quantity_kg",
        "allocated_quantity_kg",
        "remaining_capacity_kg",
        when_used="json",
    )
    def serialize_quantity(self, v: Decimal) -> str:
        return str(v)


class AllocationRunResponse(BaseModel):
    id: UUID
    centre_id: UUID
    crop_id: UUID
    allocation_date: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
