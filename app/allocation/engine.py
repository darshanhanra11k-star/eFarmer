import hashlib
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.allocation.schemas import (
    AllocationDecision,
    AllocationPlan,
    OrderingReason,
)
from app.models.procurement import IntentStatus


def compute_tie_break_digest(
    centre_id: UUID | str,
    allocation_date: date,
    farmer_id: UUID | str,
) -> str:
    cid = str(centre_id).lower()
    fid = str(farmer_id).lower()
    raw = f"{cid}|{allocation_date.isoformat()}|{fid}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest().lower()


def _is_approved(status: Any) -> bool:
    if isinstance(status, IntentStatus):
        return status == IntentStatus.APPROVED
    if isinstance(status, str):
        return status.upper() == IntentStatus.APPROVED.value
    return False


def _is_candidate_eligible(
    candidate: Any,
    centre_id: UUID,
    crop_id: UUID,
    allocation_date: date,
) -> bool:
    if getattr(candidate, "centre_id", None) != centre_id:
        return False
    if getattr(candidate, "crop_id", None) != crop_id:
        return False
    if getattr(candidate, "ready_date", None) != allocation_date:
        return False
    if not _is_approved(getattr(candidate, "status", None)):
        return False
    qty = Decimal(
        str(
            getattr(
                candidate,
                "expected_quantity_kg",
                getattr(candidate, "requested_quantity_kg", Decimal("0")),
            )
        )
    )
    return qty > Decimal("0")


def _to_uuid(val: Any) -> UUID:
    if isinstance(val, UUID):
        return val
    return UUID(str(val))


class AllocationEngine:
    @staticmethod
    def allocate(
        centre_id: UUID,
        crop_id: UUID,
        allocation_date: date,
        available_capacity_kg: Decimal,
        candidates: Sequence[Any],
    ) -> AllocationPlan:
        available_cap = Decimal(str(available_capacity_kg))
        if available_cap < Decimal("0"):
            available_cap = Decimal("0")

        eligible: list[Any] = []
        ineligible: list[Any] = []

        for c in candidates:
            if _is_candidate_eligible(c, centre_id, crop_id, allocation_date):
                eligible.append(c)
            else:
                ineligible.append(c)

        created_at_counts: dict[datetime, int] = {}
        for c in eligible:
            created_at_counts[c.created_at] = created_at_counts.get(c.created_at, 0) + 1

        def sort_key(c: Any) -> tuple[datetime, str]:
            digest = compute_tie_break_digest(centre_id, allocation_date, c.farmer_id)
            return (c.created_at, digest)

        sorted_eligible = sorted(eligible, key=sort_key)

        decisions: list[AllocationDecision] = []
        current_remaining_cap = available_cap
        total_allocated = Decimal("0")
        current_rank = 1

        for c in sorted_eligible:
            intent_id = _to_uuid(getattr(c, "id", getattr(c, "intent_id", None)))
            farmer_id = _to_uuid(c.farmer_id)
            requested_qty = Decimal(
                str(
                    getattr(
                        c,
                        "expected_quantity_kg",
                        getattr(c, "requested_quantity_kg", Decimal("0")),
                    )
                )
            )

            is_tied = created_at_counts[c.created_at] > 1
            tie_digest = (
                compute_tie_break_digest(centre_id, allocation_date, farmer_id)
                if is_tied
                else None
            )

            if requested_qty <= current_remaining_cap:
                allocated_qty = requested_qty
                current_remaining_cap -= allocated_qty
                total_allocated += allocated_qty
                selected = True
                reason = (
                    OrderingReason.SHA256_TIE_BREAK
                    if is_tied
                    else OrderingReason.WAITING_AGE
                )
            else:
                allocated_qty = Decimal("0")
                selected = False
                reason = OrderingReason.CAPACITY_EXCEEDED

            decisions.append(
                AllocationDecision(
                    intent_id=intent_id,
                    farmer_id=farmer_id,
                    requested_quantity_kg=requested_qty,
                    allocated_quantity_kg=allocated_qty,
                    remaining_capacity_kg=current_remaining_cap,
                    selected=selected,
                    rank=current_rank,
                    ordering_reason=reason,
                    tie_break_digest=tie_digest,
                )
            )
            current_rank += 1

        for c in ineligible:
            intent_id = _to_uuid(getattr(c, "id", getattr(c, "intent_id", None)))
            farmer_id = _to_uuid(getattr(c, "farmer_id", None))
            requested_qty = Decimal(
                str(
                    getattr(
                        c,
                        "expected_quantity_kg",
                        getattr(c, "requested_quantity_kg", Decimal("0")),
                    )
                )
            )

            decisions.append(
                AllocationDecision(
                    intent_id=intent_id,
                    farmer_id=farmer_id,
                    requested_quantity_kg=requested_qty,
                    allocated_quantity_kg=Decimal("0"),
                    remaining_capacity_kg=current_remaining_cap,
                    selected=False,
                    rank=current_rank,
                    ordering_reason=OrderingReason.NOT_SELECTED,
                    tie_break_digest=None,
                )
            )
            current_rank += 1

        return AllocationPlan(
            centre_id=centre_id,
            crop_id=crop_id,
            allocation_date=allocation_date,
            available_capacity_kg=available_cap,
            total_allocated_kg=total_allocated,
            remaining_capacity_kg=current_remaining_cap,
            decisions=decisions,
        )
