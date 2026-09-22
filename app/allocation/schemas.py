from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.models.procurement import IntentStatus


class OrderingReason(StrEnum):
    WAITING_AGE = "WAITING_AGE"
    SHA256_TIE_BREAK = "SHA256_TIE_BREAK"
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"
    NOT_SELECTED = "NOT_SELECTED"


@dataclass(frozen=True)
class AllocationDecision:
    intent_id: UUID
    farmer_id: UUID
    requested_quantity_kg: Decimal
    allocated_quantity_kg: Decimal
    remaining_capacity_kg: Decimal
    selected: bool
    rank: int
    ordering_reason: OrderingReason
    tie_break_digest: str | None = None


@dataclass
class AllocationCandidate:
    id: UUID
    farmer_id: UUID
    centre_id: UUID
    crop_id: UUID
    ready_date: date
    expected_quantity_kg: Decimal
    status: IntentStatus | str
    created_at: datetime


@dataclass(frozen=True)
class AllocationPlan:
    centre_id: UUID
    crop_id: UUID
    allocation_date: date
    available_capacity_kg: Decimal
    total_allocated_kg: Decimal
    remaining_capacity_kg: Decimal
    decisions: list[AllocationDecision]
