from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CentrePreference(BaseModel):
    centre_id: UUID
    priority: Annotated[int, Field(ge=1, description="Priority starting at 1")]


class PriorityCentreSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crop_id: UUID
    ready_date: date
    requested_quantity_kg: Annotated[
        Decimal,
        Field(gt=0, description="Requested quantity must be positive"),
    ]
    preferred_centres: Annotated[
        list[CentrePreference],
        Field(min_length=1, description="At least one centre preference is required"),
    ]

    @field_validator("requested_quantity_kg")
    @classmethod
    def validate_quantity_decimals(cls, v: Decimal) -> Decimal:
        if v.as_tuple().exponent < -2:  # type: ignore[operator]
            raise ValueError("requested_quantity_kg must have at most 2 decimal places")
        return v

    @model_validator(mode="after")
    def validate_centre_preferences(self) -> "PriorityCentreSelectionRequest":
        centres = [p.centre_id for p in self.preferred_centres]
        if len(centres) != len(set(centres)):
            raise ValueError(
                "Duplicate centre IDs are not allowed in preferred_centres"
            )

        priorities = [p.priority for p in self.preferred_centres]
        if len(priorities) != len(set(priorities)):
            raise ValueError(
                "Duplicate priorities are not allowed in preferred_centres"
            )

        expected_priorities = set(range(1, len(self.preferred_centres) + 1))
        if set(priorities) != expected_priorities:
            raise ValueError(
                f"Priorities must start at 1 and be consecutive integers without gaps. "
                f"Expected {sorted(expected_priorities)}, got {sorted(priorities)}"
            )

        return self


class CentreEvaluationDetail(BaseModel):
    centre_id: UUID
    priority: int
    status: str
    reason: str


class PriorityCentreSelectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    success: bool
    selected_centre_id: UUID | None = None
    selected_priority: int | None = None
    crop_id: UUID
    ready_date: date
    requested_quantity_kg: str
    available_capacity_kg: str | None = None
    evaluated_centres: list[CentreEvaluationDetail]
    message: str
