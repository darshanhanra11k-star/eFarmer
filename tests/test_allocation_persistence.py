from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.allocation.schemas import (
    AllocationDecision as EngineDecision,
)
from app.allocation.schemas import (
    AllocationPlan,
    OrderingReason,
)
from app.core.exceptions import ConflictError
from app.models.allocation import AllocationDecision, AllocationRun
from app.models.capacity import CapacityRecord
from app.models.procurement import IntentStatus, ProcurementIntent
from app.repositories.allocation import AllocationRepository
from app.repositories.capacity import CapacityRepository
from app.repositories.procurement import ProcurementRepository
from app.services.allocation import AllocationService


class MockAsyncSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.committed = False
        self.rolled_back = False

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def add_all(self, instances: list[object]) -> None:
        self.added.extend(instances)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def execute(self, statement: object) -> object:
        class MockResult:
            def scalar_one_or_none(self) -> object:
                return None

            def scalars(self) -> object:
                class MockScalars:
                    def all(self) -> list[object]:
                        return []

                return MockScalars()

        return MockResult()


@pytest.mark.asyncio
async def test_run_allocation_persists_run_and_decisions() -> None:
    session = MockAsyncSession()
    async_session = cast(AsyncSession, session)

    cap_repo = CapacityRepository(async_session)
    proc_repo = ProcurementRepository(async_session)
    alloc_repo = AllocationRepository(async_session)

    centre_id = uuid4()
    crop_id = uuid4()
    target_date = date(2026, 10, 1)

    record = CapacityRecord(
        centre_id=centre_id,
        crop_id=crop_id,
        date=target_date,
        total_capacity_kg=Decimal("1000"),
        allocated_quantity_kg=Decimal("100"),
        procured_quantity_kg=Decimal("0"),
        active=True,
    )
    cap_repo.get_capacity_record = AsyncMock(return_value=record)  # type: ignore[method-assign]
    cap_repo.save = AsyncMock(side_effect=cap_repo.save)  # type: ignore[method-assign]

    alloc_repo.get_run_by_cycle = AsyncMock(return_value=None)  # type: ignore[method-assign]
    created_runs: list[AllocationRun] = []
    created_decisions: list[list[AllocationDecision]] = []

    async def fake_create_run(run: AllocationRun) -> AllocationRun:
        created_runs.append(run)
        return run

    async def fake_create_decisions(
        decisions: list[AllocationDecision],
    ) -> list[AllocationDecision]:
        created_decisions.append(decisions)
        return decisions

    alloc_repo.create_run = AsyncMock(side_effect=fake_create_run)  # type: ignore[method-assign]
    alloc_repo.create_decisions = AsyncMock(side_effect=fake_create_decisions)  # type: ignore[method-assign]

    farmer1 = uuid4()
    farmer2 = uuid4()
    intent1 = ProcurementIntent(
        id=uuid4(),
        farmer_id=farmer1,
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=target_date,
        expected_quantity_kg=Decimal("400"),
        status=IntentStatus.APPROVED,
        created_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC),
    )
    intent2 = ProcurementIntent(
        id=uuid4(),
        farmer_id=farmer2,
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=target_date,
        expected_quantity_kg=Decimal("700"),
        status=IntentStatus.APPROVED,
        created_at=datetime(2026, 9, 1, 10, 5, 0, tzinfo=UTC),
    )
    proc_repo.get_approved_intents_for_cycle = AsyncMock(  # type: ignore[method-assign]
        return_value=[intent1, intent2]
    )

    service = AllocationService(
        capacity_repo=cap_repo,
        procurement_repo=proc_repo,
        session=async_session,
        allocation_repo=alloc_repo,
    )

    plan = await service.run_allocation(
        centre_id=centre_id,
        crop_id=crop_id,
        allocation_date=target_date,
    )

    # 1. Deterministic output unchanged
    assert plan.centre_id == centre_id
    assert plan.crop_id == crop_id
    assert plan.allocation_date == target_date
    assert plan.available_capacity_kg == Decimal("900")
    assert plan.total_allocated_kg == Decimal("400")
    assert plan.remaining_capacity_kg == Decimal("500")
    assert len(plan.decisions) == 2
    assert plan.decisions[0].selected is True
    assert plan.decisions[1].selected is False

    # 2. Run persisted
    assert len(created_runs) == 1
    run = created_runs[0]
    assert run.centre_id == centre_id
    assert run.crop_id == crop_id
    assert run.allocation_date == target_date

    # 3. Decisions persisted (both selected and unselected)
    assert len(created_decisions) == 1
    decisions = created_decisions[0]
    assert len(decisions) == 2
    d1 = next(d for d in decisions if d.intent_id == intent1.id)
    d2 = next(d for d in decisions if d.intent_id == intent2.id)
    assert d1.selected is True
    assert d1.allocated_quantity_kg == Decimal("400")
    assert d1.rank == 1
    assert d1.ordering_reason == OrderingReason.WAITING_AGE.value
    assert d2.selected is False
    assert d2.allocated_quantity_kg == Decimal("0")
    assert d2.rank == 2
    assert d2.ordering_reason == OrderingReason.CAPACITY_EXCEEDED.value

    # 4. Capacity record updated
    assert record.allocated_quantity_kg == Decimal("500")  # 100 + 400
    cap_repo.save.assert_awaited_once_with(record)

    # 5. Service-owned transaction committed
    assert session.committed is True
    assert session.rolled_back is False


@pytest.mark.asyncio
async def test_run_allocation_duplicate_cycle_conflict() -> None:
    session = MockAsyncSession()
    async_session = cast(AsyncSession, session)

    cap_repo = CapacityRepository(async_session)
    proc_repo = ProcurementRepository(async_session)
    alloc_repo = AllocationRepository(async_session)

    centre_id = uuid4()
    crop_id = uuid4()
    target_date = date(2026, 10, 1)

    existing_run = AllocationRun(
        id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        allocation_date=target_date,
    )
    alloc_repo.get_run_by_cycle = AsyncMock(return_value=existing_run)  # type: ignore[method-assign]

    service = AllocationService(
        capacity_repo=cap_repo,
        procurement_repo=proc_repo,
        session=async_session,
        allocation_repo=alloc_repo,
    )

    with pytest.raises(ConflictError, match="already exists"):
        await service.run_allocation(
            centre_id=centre_id,
            crop_id=crop_id,
            allocation_date=target_date,
        )

    assert session.committed is False


@pytest.mark.asyncio
async def test_run_allocation_capacity_overflow_raises_error() -> None:
    session = MockAsyncSession()
    async_session = cast(AsyncSession, session)

    cap_repo = CapacityRepository(async_session)
    proc_repo = ProcurementRepository(async_session)
    alloc_repo = AllocationRepository(async_session)

    centre_id = uuid4()
    crop_id = uuid4()
    target_date = date(2026, 10, 1)

    # Initial capacity already at 900 / 1000
    record = CapacityRecord(
        centre_id=centre_id,
        crop_id=crop_id,
        date=target_date,
        total_capacity_kg=Decimal("1000"),
        allocated_quantity_kg=Decimal("950"),
        procured_quantity_kg=Decimal("0"),
        active=True,
    )
    cap_repo.get_capacity_record = AsyncMock(return_value=record)  # type: ignore[method-assign]
    alloc_repo.get_run_by_cycle = AsyncMock(return_value=None)  # type: ignore[method-assign]

    # Force an edge case where total_allocated exceeds remaining capacity somehow
    intent = ProcurementIntent(
        id=uuid4(),
        farmer_id=uuid4(),
        centre_id=centre_id,
        crop_id=crop_id,
        ready_date=target_date,
        expected_quantity_kg=Decimal("50"),
        status=IntentStatus.APPROVED,
        created_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC),
    )
    proc_repo.get_approved_intents_for_cycle = AsyncMock(return_value=[intent])  # type: ignore[method-assign]

    mock_engine = MagicMock()

    mock_engine.allocate.return_value = AllocationPlan(
        centre_id=centre_id,
        crop_id=crop_id,
        allocation_date=target_date,
        available_capacity_kg=Decimal("100"),
        total_allocated_kg=Decimal("50"),
        remaining_capacity_kg=Decimal("50"),
        decisions=[
            EngineDecision(
                intent_id=intent.id,
                farmer_id=intent.farmer_id,
                requested_quantity_kg=Decimal("50"),
                allocated_quantity_kg=Decimal("50"),
                remaining_capacity_kg=Decimal("50"),
                selected=True,
                rank=1,
                ordering_reason=OrderingReason.WAITING_AGE,
                tie_break_digest="abc",
            )
        ],
    )

    service = AllocationService(
        capacity_repo=cap_repo,
        procurement_repo=proc_repo,
        session=async_session,
        allocation_repo=alloc_repo,
        allocation_engine=mock_engine,
    )

    # 950 + 50 = 1000 > 980
    record.total_capacity_kg = Decimal("980")
    with pytest.raises(ConflictError, match="exceeds total"):
        await service.run_allocation(
            centre_id=centre_id,
            crop_id=crop_id,
            allocation_date=target_date,
        )

    assert session.rolled_back is True


@pytest.mark.asyncio
async def test_run_allocation_rollback_on_failure() -> None:
    session = MockAsyncSession()
    async_session = cast(AsyncSession, session)

    cap_repo = CapacityRepository(async_session)
    proc_repo = ProcurementRepository(async_session)
    alloc_repo = AllocationRepository(async_session)

    centre_id = uuid4()
    crop_id = uuid4()
    target_date = date(2026, 10, 1)

    record = CapacityRecord(
        centre_id=centre_id,
        crop_id=crop_id,
        date=target_date,
        total_capacity_kg=Decimal("1000"),
        allocated_quantity_kg=Decimal("0"),
        procured_quantity_kg=Decimal("0"),
        active=True,
    )
    cap_repo.get_capacity_record = AsyncMock(return_value=record)  # type: ignore[method-assign]
    alloc_repo.get_run_by_cycle = AsyncMock(return_value=None)  # type: ignore[method-assign]
    proc_repo.get_approved_intents_for_cycle = AsyncMock(return_value=[])  # type: ignore[method-assign]

    alloc_repo.create_run = AsyncMock(side_effect=RuntimeError("Database write error"))  # type: ignore[method-assign]

    service = AllocationService(
        capacity_repo=cap_repo,
        procurement_repo=proc_repo,
        session=async_session,
        allocation_repo=alloc_repo,
    )

    with pytest.raises(RuntimeError, match="Database write error"):
        await service.run_allocation(
            centre_id=centre_id,
            crop_id=crop_id,
            allocation_date=target_date,
        )

    assert session.rolled_back is True
    assert session.committed is False


def test_repositories_have_zero_commits() -> None:
    import inspect

    for repo_cls in [AllocationRepository, CapacityRepository]:
        source = inspect.getsource(repo_cls)
        assert "session.commit()" not in source, (
            f"{repo_cls.__name__} contains session.commit()!"
        )
