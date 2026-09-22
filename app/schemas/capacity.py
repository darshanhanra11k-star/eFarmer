from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer

from app.capacity.engine import CapacityStatus

__all__ = ["CapacityRecordResponse", "CapacityStatus"]


class CapacityRecordResponse(BaseModel):
    centre_id: UUID
    crop_id: UUID
    date: date
    total_capacity_kg: Decimal
    allocated_quantity_kg: Decimal
    procured_quantity_kg: Decimal
    available_capacity_kg: Decimal
    utilisation: Decimal
    capacity_status: CapacityStatus
    active: bool

    model_config = ConfigDict(from_attributes=True)

    @field_serializer(
        "total_capacity_kg",
        "allocated_quantity_kg",
        "procured_quantity_kg",
        "available_capacity_kg",
        when_used="json",
    )
    def serialize_quantity(self, v: Decimal) -> str:
        return str(v)

    @field_serializer("utilisation", when_used="json")
    def serialize_utilisation(self, v: Decimal) -> str:
        return f"{v:.4f}"
