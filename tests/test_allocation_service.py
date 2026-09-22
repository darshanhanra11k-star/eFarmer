from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.allocation.schemas import OrderingReason
from app.core.exceptions import NotFoundError
from app.models.capacity import CapacityRecord
from app.models.procurement import IntentStatus, ProcurementIntent
from app.repositories.capacity import CapacityRepository
from app.repositories.procurement import ProcurementRepository
from app.services.allocation import AllocationService


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def add_all(self, instances: list[object]) -> None:
        self.added.extend(instances)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def execute(self, statement: object) -> object:
        class FakeResult:
            def scalar_one_or_none(self) -> object:
                return None

            def scalars(self) -> object:
                class FakeScalars:
                    def all(self) -> list[object]:
                        return []

                return FakeScalars()

        return FakeResult()


@pytest.fixture
def service_deps() -> tuple[
    CapacityRepository,
    ProcurementRepository,
    AsyncSession,
]:
    fake_session = cast(AsyncSession, FakeSession())
    cap_repo = CapacityRepository(fake_session)
    proc_repo = ProcurementRepository(fake_session)
    return cap_repo, proc_repo, fake_session


@pytest.mark.asyncio
async def test_allocation_service_success(
    monkeypatch: pytest.MonkeyPatch,
    service_deps: tuple[
        CapacityRepository,
        ProcurementRepository,
        AsyncSession,
    ],
) -> None:
    cap_repo, proc_repo, fake_session = service_deps
    centre_id = uuid4()
    crop_id = uuid4()
    target_date = date(2026, 10, 1)

    record = CapacityRecord(
        centre_id=centre_id,
        crop_id=crop_id,
        date=target_date,
        total_capacity_kg=Decimal("1000"),
        allocated_quantity_kg=Decimal("200"),
        procured_quantity_kg=Decimal("0"),
        active=True,
    )
    monkeypatch.setattr(
        cap_repo,
        "get_capacity_record",
        AsyncMock(return_value=record),
    )

    intent1 = ProcurementIntent(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=target_date,
        expected_quantity_kg=Decimal("300"),
        status=IntentStatus.APPROVED,
        created_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC),
    )
    intent2 = ProcurementIntent(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=target_date,
        expected_quantity_kg=Decimal("600"),
        status=IntentStatus.APPROVED,
        created_at=datetime(2026, 9, 1, 10, 5, 0, tzinfo=UTC),
    )
    monkeypatch.setattr(
        proc_repo,
        "get_approved_intents_for_cycle",
        AsyncMock(return_value=[intent1, intent2]),
    )

    service = AllocationService(
        capacity_repo=cap_repo,
        procurement_repo=proc_repo,
        session=fake_session,
    )

    plan = await service.run_allocation(
        centre_id=centre_id,
        crop_id=crop_id,
        allocation_date=target_date,
    )

    assert plan.centre_id == centre_id
    assert plan.crop_id == crop_id
    assert plan.allocation_date == target_date
    assert plan.available_capacity_kg == Decimal("800")
    assert plan.total_allocated_kg == Decimal("300")
    assert plan.remaining_capacity_kg == Decimal("500")
    assert len(plan.decisions) == 2

    assert plan.decisions[0].intent_id == intent1.id
    assert plan.decisions[0].selected is True
    assert plan.decisions[0].ordering_reason == OrderingReason.WAITING_AGE

    assert plan.decisions[1].intent_id == intent2.id
    assert plan.decisions[1].selected is False
    assert plan.decisions[1].ordering_reason == OrderingReason.CAPACITY_EXCEEDED


@pytest.mark.asyncio
async def test_allocation_service_capacity_record_not_found(
    monkeypatch: pytest.MonkeyPatch,
    service_deps: tuple[
        CapacityRepository,
        ProcurementRepository,
        AsyncSession,
    ],
) -> None:
    cap_repo, proc_repo, fake_session = service_deps
    centre_id = uuid4()
    crop_id = uuid4()
    target_date = date(2026, 10, 1)

    monkeypatch.setattr(
        cap_repo,
        "get_capacity_record",
        AsyncMock(return_value=None),
    )

    service = AllocationService(
        capacity_repo=cap_repo,
        procurement_repo=proc_repo,
        session=fake_session,
    )

    with pytest.raises(NotFoundError, match="Capacity record not found"):
        await service.run_allocation(
            centre_id=centre_id,
            crop_id=crop_id,
            allocation_date=target_date,
        )


@pytest.mark.asyncio
async def test_inactive_capacity_no_selection(
    monkeypatch: pytest.MonkeyPatch,
    service_deps: tuple[
        CapacityRepository,
        ProcurementRepository,
        AsyncSession,
    ],
) -> None:
    cap_repo, proc_repo, fake_session = service_deps
    centre_id = uuid4()
    crop_id = uuid4()
    target_date = date(2026, 10, 1)

    record = CapacityRecord(
        centre_id=centre_id,
        crop_id=crop_id,
        date=target_date,
        total_capacity_kg=Decimal("1000"),
        allocated_quantity_kg=Decimal("200"),
        procured_quantity_kg=Decimal("0"),
        active=False,
    )
    monkeypatch.setattr(
        cap_repo,
        "get_capacity_record",
        AsyncMock(return_value=record),
    )

    intent = ProcurementIntent(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=target_date,
        expected_quantity_kg=Decimal("300"),
        status=IntentStatus.APPROVED,
        created_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC),
    )
    monkeypatch.setattr(
        proc_repo,
        "get_approved_intents_for_cycle",
        AsyncMock(return_value=[intent]),
    )

    service = AllocationService(
        capacity_repo=cap_repo,
        procurement_repo=proc_repo,
        session=fake_session,
    )

    plan = await service.run_allocation(
        centre_id=centre_id,
        crop_id=crop_id,
        allocation_date=target_date,
    )

    assert len(plan.decisions) == 1
    for decision in plan.decisions:
        assert decision.selected is False
        assert decision.allocated_quantity_kg == Decimal("0")
    assert plan.total_allocated_kg == Decimal("0")
    assert plan.remaining_capacity_kg == Decimal("0")
