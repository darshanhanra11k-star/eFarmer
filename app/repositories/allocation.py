from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.models.allocation import AllocationDecision, AllocationRun


def _is_unique_violation(exc: IntegrityError) -> bool:
    orig = getattr(exc, "orig", None)
    if orig is not None:
        sqlstate = getattr(orig, "sqlstate", None)
        if sqlstate == "23505":
            return True
        if (
            hasattr(orig, "sqlite_errorname")
            and orig.sqlite_errorname == "SQLITE_CONSTRAINT_UNIQUE"
        ):
            return True
    return "unique" in str(exc.orig or exc).lower()


class AllocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_run_by_cycle(
        self,
        centre_id: UUID,
        crop_id: UUID,
        allocation_date: date,
    ) -> AllocationRun | None:
        stmt = select(AllocationRun).where(
            AllocationRun.centre_id == centre_id,
            AllocationRun.crop_id == crop_id,
            AllocationRun.allocation_date == allocation_date,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_run(self, run: AllocationRun) -> AllocationRun:
        self.session.add(run)
        try:
            await self.session.flush()
            return run
        except IntegrityError as exc:
            await self.session.rollback()
            if _is_unique_violation(exc):
                raise ConflictError(
                    message=(
                        "An allocation run already exists for this centre, crop, "
                        "and date."
                    ),
                ) from None

            raise

    async def create_decisions(
        self,
        decisions: list[AllocationDecision],
    ) -> list[AllocationDecision]:
        self.session.add_all(decisions)
        try:
            await self.session.flush()
            return decisions
        except IntegrityError as exc:
            await self.session.rollback()
            if _is_unique_violation(exc):
                raise ConflictError(
                    message="Duplicate allocation decision detected in this run.",
                ) from None
            raise

    async def get_decision_by_intent(
        self,
        intent_id: UUID,
    ) -> AllocationDecision | None:
        stmt = (
            select(AllocationDecision)
            .where(AllocationDecision.intent_id == intent_id)
            .order_by(AllocationDecision.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_decisions_for_centre(
        self,
        centre_id: UUID,
        crop_id: UUID | None = None,
        allocation_date: date | None = None,
    ) -> list[AllocationDecision]:
        stmt = (
            select(AllocationDecision)
            .join(
                AllocationRun,
                AllocationDecision.allocation_run_id == AllocationRun.id,
            )
            .where(AllocationRun.centre_id == centre_id)
        )
        if crop_id is not None:
            stmt = stmt.where(AllocationRun.crop_id == crop_id)
        if allocation_date is not None:
            stmt = stmt.where(AllocationRun.allocation_date == allocation_date)
        stmt = stmt.order_by(
            AllocationRun.allocation_date.desc(),
            AllocationDecision.rank.asc(),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
