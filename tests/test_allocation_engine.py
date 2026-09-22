import hashlib
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.allocation.engine import AllocationEngine, compute_tie_break_digest
from app.allocation.schemas import (
    AllocationCandidate,
    OrderingReason,
)
from app.models.procurement import IntentStatus, ProcurementIntent


def test_compute_tie_break_digest_canonical_format() -> None:
    centre_id = UUID("11111111-1111-1111-1111-111111111111")
    farmer_id = UUID("22222222-2222-2222-2222-222222222222")
    alloc_date = date(2026, 10, 1)

    expected_canonical = (
        "11111111-1111-1111-1111-111111111111|2026-10-01|"
        "22222222-2222-2222-2222-222222222222"
    )
    expected_digest = (
        hashlib.sha256(expected_canonical.encode("utf-8")).hexdigest().lower()
    )

    digest = compute_tie_break_digest(centre_id, alloc_date, farmer_id)
    assert digest == expected_digest


def test_compute_tie_break_digest_case_insensitivity() -> None:
    centre_str_upper = "11111111-1111-1111-1111-111111111111".upper()
    farmer_str_upper = "22222222-2222-2222-2222-222222222222".upper()
    alloc_date = date(2026, 10, 1)

    digest_upper = compute_tie_break_digest(
        centre_str_upper, alloc_date, farmer_str_upper
    )
    digest_lower = compute_tie_break_digest(
        centre_str_upper.lower(), alloc_date, farmer_str_upper.lower()
    )
    assert digest_upper == digest_lower


def test_fifo_ordering_by_created_at() -> None:
    centre_id = uuid4()
    crop_id = uuid4()
    alloc_date = date(2026, 10, 1)

    c1 = AllocationCandidate(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=alloc_date,
        expected_quantity_kg=Decimal("100"),
        status=IntentStatus.APPROVED,
        created_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC),
    )
    c2 = AllocationCandidate(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=alloc_date,
        expected_quantity_kg=Decimal("100"),
        status=IntentStatus.APPROVED,
        created_at=datetime(2026, 9, 1, 10, 5, 0, tzinfo=UTC),
    )
    c3 = AllocationCandidate(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=alloc_date,
        expected_quantity_kg=Decimal("100"),
        status=IntentStatus.APPROVED,
        created_at=datetime(2026, 9, 1, 10, 10, 0, tzinfo=UTC),
    )

    plan = AllocationEngine.allocate(
        centre_id=centre_id,
        crop_id=crop_id,
        allocation_date=alloc_date,
        available_capacity_kg=Decimal("300"),
        candidates=[c3, c1, c2],
    )

    assert len(plan.decisions) == 3
    assert plan.decisions[0].intent_id == c1.id
    assert plan.decisions[0].rank == 1
    assert plan.decisions[0].ordering_reason == OrderingReason.WAITING_AGE
    assert plan.decisions[0].tie_break_digest is None
    assert plan.decisions[0].selected is True

    assert plan.decisions[1].intent_id == c2.id
    assert plan.decisions[1].rank == 2
    assert plan.decisions[1].ordering_reason == OrderingReason.WAITING_AGE
    assert plan.decisions[1].tie_break_digest is None
    assert plan.decisions[1].selected is True

    assert plan.decisions[2].intent_id == c3.id
    assert plan.decisions[2].rank == 3
    assert plan.decisions[2].ordering_reason == OrderingReason.WAITING_AGE
    assert plan.decisions[2].tie_break_digest is None
    assert plan.decisions[2].selected is True

    assert plan.total_allocated_kg == Decimal("300")
    assert plan.remaining_capacity_kg == Decimal("0")


def test_deterministic_sha256_tie_break() -> None:
    centre_id = uuid4()
    crop_id = uuid4()
    alloc_date = date(2026, 10, 1)
    common_time = datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)

    farmer_a = uuid4()
    farmer_b = uuid4()

    digest_a = compute_tie_break_digest(centre_id, alloc_date, farmer_a)
    digest_b = compute_tie_break_digest(centre_id, alloc_date, farmer_b)

    c_a = AllocationCandidate(
        id=uuid4(),
        farmer_id=farmer_a,
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=alloc_date,
        expected_quantity_kg=Decimal("150"),
        status=IntentStatus.APPROVED,
        created_at=common_time,
    )
    c_b = AllocationCandidate(
        id=uuid4(),
        farmer_id=farmer_b,
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=alloc_date,
        expected_quantity_kg=Decimal("150"),
        status=IntentStatus.APPROVED,
        created_at=common_time,
    )

    plan = AllocationEngine.allocate(
        centre_id=centre_id,
        crop_id=crop_id,
        allocation_date=alloc_date,
        available_capacity_kg=Decimal("300"),
        candidates=[c_a, c_b],
    )

    assert len(plan.decisions) == 2

    if digest_a < digest_b:
        first, second = plan.decisions[0], plan.decisions[1]
        assert first.intent_id == c_a.id
        assert first.tie_break_digest == digest_a
        assert second.intent_id == c_b.id
        assert second.tie_break_digest == digest_b
    else:
        first, second = plan.decisions[0], plan.decisions[1]
        assert first.intent_id == c_b.id
        assert first.tie_break_digest == digest_b
        assert second.intent_id == c_a.id
        assert second.tie_break_digest == digest_a

    assert first.rank == 1
    assert first.ordering_reason == OrderingReason.SHA256_TIE_BREAK
    assert first.selected is True

    assert second.rank == 2
    assert second.ordering_reason == OrderingReason.SHA256_TIE_BREAK
    assert second.selected is True


def test_mixed_fifo_and_tie_break_ordering() -> None:
    centre_id = uuid4()
    crop_id = uuid4()
    alloc_date = date(2026, 10, 1)

    t1 = datetime(2026, 9, 1, 9, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    t3 = datetime(2026, 9, 1, 11, 0, 0, tzinfo=UTC)

    c_early = AllocationCandidate(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=alloc_date,
        expected_quantity_kg=Decimal("50"),
        status=IntentStatus.APPROVED,
        created_at=t1,
    )
    c_tied_1 = AllocationCandidate(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=alloc_date,
        expected_quantity_kg=Decimal("50"),
        status=IntentStatus.APPROVED,
        created_at=t2,
    )
    c_tied_2 = AllocationCandidate(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=alloc_date,
        expected_quantity_kg=Decimal("50"),
        status=IntentStatus.APPROVED,
        created_at=t2,
    )
    c_late = AllocationCandidate(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=alloc_date,
        expected_quantity_kg=Decimal("50"),
        status=IntentStatus.APPROVED,
        created_at=t3,
    )

    plan = AllocationEngine.allocate(
        centre_id=centre_id,
        crop_id=crop_id,
        allocation_date=alloc_date,
        available_capacity_kg=Decimal("500"),
        candidates=[c_late, c_tied_2, c_early, c_tied_1],
    )

    assert len(plan.decisions) == 4
    assert plan.decisions[0].intent_id == c_early.id
    assert plan.decisions[0].ordering_reason == OrderingReason.WAITING_AGE
    assert plan.decisions[0].tie_break_digest is None

    assert plan.decisions[1].ordering_reason == OrderingReason.SHA256_TIE_BREAK
    assert plan.decisions[1].tie_break_digest is not None

    assert plan.decisions[2].ordering_reason == OrderingReason.SHA256_TIE_BREAK
    assert plan.decisions[2].tie_break_digest is not None

    assert plan.decisions[3].intent_id == c_late.id
    assert plan.decisions[3].ordering_reason == OrderingReason.WAITING_AGE
    assert plan.decisions[3].tie_break_digest is None


def test_capacity_exceeded_skip_and_subsequent_allocation() -> None:
    centre_id = uuid4()
    crop_id = uuid4()
    alloc_date = date(2026, 10, 1)

    c1 = AllocationCandidate(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=alloc_date,
        expected_quantity_kg=Decimal("300"),
        status=IntentStatus.APPROVED,
        created_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC),
    )
    c2 = AllocationCandidate(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=alloc_date,
        expected_quantity_kg=Decimal("400"),
        status=IntentStatus.APPROVED,
        created_at=datetime(2026, 9, 1, 10, 5, 0, tzinfo=UTC),
    )
    c3 = AllocationCandidate(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=alloc_date,
        expected_quantity_kg=Decimal("150"),
        status=IntentStatus.APPROVED,
        created_at=datetime(2026, 9, 1, 10, 10, 0, tzinfo=UTC),
    )

    plan = AllocationEngine.allocate(
        centre_id=centre_id,
        crop_id=crop_id,
        allocation_date=alloc_date,
        available_capacity_kg=Decimal("500"),
        candidates=[c1, c2, c3],
    )

    assert len(plan.decisions) == 3

    d1 = plan.decisions[0]
    assert d1.selected is True
    assert d1.allocated_quantity_kg == Decimal("300")
    assert d1.remaining_capacity_kg == Decimal("200")
    assert d1.ordering_reason == OrderingReason.WAITING_AGE

    d2 = plan.decisions[1]
    assert d2.selected is False
    assert d2.allocated_quantity_kg == Decimal("0")
    assert d2.remaining_capacity_kg == Decimal("200")
    assert d2.ordering_reason == OrderingReason.CAPACITY_EXCEEDED

    d3 = plan.decisions[2]
    assert d3.selected is True
    assert d3.allocated_quantity_kg == Decimal("150")
    assert d3.remaining_capacity_kg == Decimal("50")
    assert d3.ordering_reason == OrderingReason.WAITING_AGE

    assert plan.total_allocated_kg == Decimal("450")
    assert plan.remaining_capacity_kg == Decimal("50")


def test_zero_available_capacity() -> None:
    centre_id = uuid4()
    crop_id = uuid4()
    alloc_date = date(2026, 10, 1)

    c1 = AllocationCandidate(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=alloc_date,
        expected_quantity_kg=Decimal("100"),
        status=IntentStatus.APPROVED,
        created_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC),
    )

    plan = AllocationEngine.allocate(
        centre_id=centre_id,
        crop_id=crop_id,
        allocation_date=alloc_date,
        available_capacity_kg=Decimal("0"),
        candidates=[c1],
    )

    assert len(plan.decisions) == 1
    assert plan.decisions[0].selected is False
    assert plan.decisions[0].allocated_quantity_kg == Decimal("0")
    assert plan.decisions[0].remaining_capacity_kg == Decimal("0")
    assert plan.decisions[0].ordering_reason == OrderingReason.CAPACITY_EXCEEDED
    assert plan.total_allocated_kg == Decimal("0")
    assert plan.remaining_capacity_kg == Decimal("0")


def test_empty_candidate_list() -> None:
    centre_id = uuid4()
    crop_id = uuid4()
    alloc_date = date(2026, 10, 1)

    plan = AllocationEngine.allocate(
        centre_id=centre_id,
        crop_id=crop_id,
        allocation_date=alloc_date,
        available_capacity_kg=Decimal("1000"),
        candidates=[],
    )

    assert len(plan.decisions) == 0
    assert plan.total_allocated_kg == Decimal("0")
    assert plan.remaining_capacity_kg == Decimal("1000")


def test_ineligible_candidates_not_selected() -> None:
    centre_id = uuid4()
    other_centre_id = uuid4()
    crop_id = uuid4()
    alloc_date = date(2026, 10, 1)

    c_valid = AllocationCandidate(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=alloc_date,
        expected_quantity_kg=Decimal("100"),
        status=IntentStatus.APPROVED,
        created_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC),
    )
    c_pending = AllocationCandidate(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=alloc_date,
        expected_quantity_kg=Decimal("100"),
        status=IntentStatus.PENDING,
        created_at=datetime(2026, 9, 1, 9, 0, 0, tzinfo=UTC),
    )
    c_wrong_centre = AllocationCandidate(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=other_centre_id,
        crop_id=crop_id,
        ready_date=alloc_date,
        expected_quantity_kg=Decimal("100"),
        status=IntentStatus.APPROVED,
        created_at=datetime(2026, 9, 1, 8, 0, 0, tzinfo=UTC),
    )

    plan = AllocationEngine.allocate(
        centre_id=centre_id,
        crop_id=crop_id,
        allocation_date=alloc_date,
        available_capacity_kg=Decimal("500"),
        candidates=[c_pending, c_valid, c_wrong_centre],
    )

    assert len(plan.decisions) == 3

    assert plan.decisions[0].intent_id == c_valid.id
    assert plan.decisions[0].selected is True
    assert plan.decisions[0].ordering_reason == OrderingReason.WAITING_AGE

    assert plan.decisions[1].intent_id == c_pending.id
    assert plan.decisions[1].selected is False
    assert plan.decisions[1].ordering_reason == OrderingReason.NOT_SELECTED

    assert plan.decisions[2].intent_id == c_wrong_centre.id
    assert plan.decisions[2].selected is False
    assert plan.decisions[2].ordering_reason == OrderingReason.NOT_SELECTED


def test_procurement_intent_model_compatibility() -> None:
    centre_id = uuid4()
    crop_id = uuid4()
    alloc_date = date(2026, 10, 1)

    intent = ProcurementIntent(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=alloc_date,
        expected_quantity_kg=Decimal("250.75"),
        status=IntentStatus.APPROVED,
        created_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC),
    )

    plan = AllocationEngine.allocate(
        centre_id=centre_id,
        crop_id=crop_id,
        allocation_date=alloc_date,
        available_capacity_kg=Decimal("500"),
        candidates=[intent],
    )

    assert len(plan.decisions) == 1
    d = plan.decisions[0]
    assert d.intent_id == intent.id
    assert d.farmer_id == intent.farmer_id
    assert d.requested_quantity_kg == Decimal("250.75")
    assert d.allocated_quantity_kg == Decimal("250.75")
    assert d.remaining_capacity_kg == Decimal("249.25")
    assert d.selected is True
    assert d.ordering_reason == OrderingReason.WAITING_AGE
