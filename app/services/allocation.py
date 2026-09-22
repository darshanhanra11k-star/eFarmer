from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.allocation.engine import AllocationEngine
from app.allocation.schemas import AllocationPlan
from app.capacity.engine import CapacityEngine, CapacityStatus
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.rbac import Role
from app.dependencies.auth import AuthenticatedUser
from app.models.allocation import AllocationDecision, AllocationRun
from app.repositories.allocation import AllocationRepository
from app.repositories.capacity import CapacityRepository
from app.repositories.farmer import FarmerRepository
from app.repositories.procurement import ProcurementRepository


class AllocationService:
    def __init__(
        self,
        capacity_repo: CapacityRepository,
        procurement_repo: ProcurementRepository,
        session: AsyncSession,
        allocation_repo: AllocationRepository | None = None,
        farmer_repo: FarmerRepository | None = None,
        capacity_engine: CapacityEngine | None = None,
        allocation_engine: AllocationEngine | None = None,
    ) -> None:
        self.capacity_repo = capacity_repo
        self.procurement_repo = procurement_repo
        self.session = session
        self.allocation_repo = allocation_repo or AllocationRepository(session)
        self.farmer_repo = farmer_repo or FarmerRepository(session)
        self.capacity_engine = capacity_engine or CapacityEngine()
        self.allocation_engine = allocation_engine or AllocationEngine()

    async def run_allocation(
        self,
        centre_id: UUID,
        crop_id: UUID,
        allocation_date: date,
    ) -> AllocationPlan:
        # Pre-check for duplicate cycle run
        existing_run = await self.allocation_repo.get_run_by_cycle(
            centre_id=centre_id,
            crop_id=crop_id,
            allocation_date=allocation_date,
        )
        if existing_run is not None:
            raise ConflictError(
                message=(
                    "An allocation run already exists for this centre, crop, and date."
                ),
            )

        # 1 & 2. Fetch capacity record with SELECT FOR UPDATE
        capacity_record = await self.capacity_repo.get_capacity_record(
            centre_id=centre_id,
            crop_id=crop_id,
            target_date=allocation_date,
            for_update=True,
        )
        if capacity_record is None:
            raise NotFoundError(
                message=(
                    "Capacity record not found for the specified "
                    "centre, crop, and date."
                ),
            )

        # 3. Run existing CapacityEngine
        metrics = self.capacity_engine.calculate(
            total_capacity_kg=capacity_record.total_capacity_kg,
            allocated_quantity_kg=capacity_record.allocated_quantity_kg,
            active=capacity_record.active,
        )

        # 4. Fetch approved intents
        candidates = await self.procurement_repo.get_approved_intents_for_cycle(
            centre_id=centre_id,
            crop_id=crop_id,
            ready_date=allocation_date,
        )

        available_capacity_kg = (
            Decimal("0")
            if metrics.capacity_status == CapacityStatus.INACTIVE
            else metrics.available_capacity_kg
        )

        # 5. Run existing AllocationEngine unchanged
        plan = self.allocation_engine.allocate(
            centre_id=centre_id,
            crop_id=crop_id,
            allocation_date=allocation_date,
            available_capacity_kg=available_capacity_kg,
            candidates=candidates,
        )

        try:
            # 6. Create allocation_runs row
            run = AllocationRun(
                centre_id=centre_id,
                crop_id=crop_id,
                allocation_date=allocation_date,
            )
            await self.allocation_repo.create_run(run)

            # 7. Persist every AllocationDecision
            db_decisions = [
                AllocationDecision(
                    allocation_run_id=run.id,
                    intent_id=d.intent_id,
                    farmer_id=d.farmer_id,
                    requested_quantity_kg=d.requested_quantity_kg,
                    allocated_quantity_kg=d.allocated_quantity_kg,
                    remaining_capacity_kg=d.remaining_capacity_kg,
                    selected=d.selected,
                    rank=d.rank,
                    ordering_reason=(
                        d.ordering_reason.value
                        if hasattr(d.ordering_reason, "value")
                        else str(d.ordering_reason)
                    ),
                    tie_break_digest=d.tie_break_digest,
                )
                for d in plan.decisions
            ]
            if db_decisions:
                await self.allocation_repo.create_decisions(db_decisions)

            # 8 & 9. Calculate total newly allocated quantity from selected decisions
            newly_allocated = sum(
                (d.allocated_quantity_kg for d in plan.decisions if d.selected),
                Decimal("0"),
            )
            capacity_record.allocated_quantity_kg += newly_allocated

            # 10. Ensure allocated_quantity_kg <= total_capacity_kg
            if (
                capacity_record.allocated_quantity_kg
                > capacity_record.total_capacity_kg
            ):
                raise ConflictError(
                    message="Allocated quantity exceeds total centre capacity.",
                )

            await self.capacity_repo.save(capacity_record)

            # 11. Commit in ONE service-owned transaction
            await self.session.commit()
            return plan

        except Exception:
            await self.session.rollback()
            raise

    async def get_intent_allocation(
        self,
        intent_id: UUID,
        current_user: AuthenticatedUser,
    ) -> AllocationDecision:
        decision = await self.allocation_repo.get_decision_by_intent(intent_id)
        if decision is None:
            raise NotFoundError(
                message="Allocation decision not found for the specified intent.",
            )

        if current_user.role == Role.FARMER:
            user = await self.farmer_repo.get_user_by_subject(current_user.subject)
            if (
                user is None
                or user.farmer_id is None
                or user.farmer_id != decision.farmer_id
            ):
                raise PermissionDeniedError(
                    message="You are not authorized to view this allocation decision.",
                )
        elif current_user.role == Role.OFFICER:
            pass
        else:
            raise PermissionDeniedError(
                message="You do not have permission to view allocation decisions.",
            )

        return decision

    async def get_centre_allocations(
        self,
        centre_id: UUID,
        current_user: AuthenticatedUser,
        crop_id: UUID | None = None,
        allocation_date: date | None = None,
    ) -> list[AllocationDecision]:
        if current_user.role != Role.OFFICER:
            raise PermissionDeniedError(
                message="Only officers may access centre allocations.",
            )

        user = await self.farmer_repo.get_user_by_subject(current_user.subject)
        if user is None or user.centre_id is None or user.centre_id != centre_id:
            raise PermissionDeniedError(
                message=(
                    "Officers may only access allocations for their assigned centre."
                ),
            )

        return await self.allocation_repo.get_decisions_for_centre(
            centre_id=centre_id,
            crop_id=crop_id,
            allocation_date=allocation_date,
        )
