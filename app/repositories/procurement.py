from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError
from app.models.procurement import (
    IntentStatus,
    ProcurementIntent,
    ProcurementStatusHistory,
)


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


class ProcurementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_intent(self, intent: ProcurementIntent) -> ProcurementIntent:
        self.session.add(intent)
        try:
            await self.session.flush()
            return intent
        except IntegrityError as exc:
            await self.session.rollback()
            if _is_unique_violation(exc):
                raise ConflictError(
                    message=(
                        "A procurement intent already exists for this "
                        "farmer, centre, crop, and ready date."
                    ),
                ) from None
            raise

    async def get_intent_by_id(
        self, intent_id: UUID, load_relations: bool = False
    ) -> ProcurementIntent | None:
        stmt = select(ProcurementIntent).where(ProcurementIntent.id == intent_id)
        if load_relations:
            stmt = stmt.options(
                selectinload(ProcurementIntent.tokens),
                selectinload(ProcurementIntent.records),
                selectinload(ProcurementIntent.status_history),
            )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_intents_for_farmer(
        self,
        farmer_id: UUID,
        centre_id: UUID | None = None,
        crop_id: UUID | None = None,
    ) -> list[ProcurementIntent]:
        active_statuses = [IntentStatus.PENDING, IntentStatus.APPROVED]
        stmt = select(ProcurementIntent).where(
            ProcurementIntent.farmer_id == farmer_id,
            ProcurementIntent.status.in_(active_statuses),
        )
        if centre_id:
            stmt = stmt.where(ProcurementIntent.centre_id == centre_id)
        if crop_id:
            stmt = stmt.where(ProcurementIntent.crop_id == crop_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_intents_by_farmer(self, farmer_id: UUID) -> list[ProcurementIntent]:
        stmt = (
            select(ProcurementIntent)
            .where(ProcurementIntent.farmer_id == farmer_id)
            .order_by(ProcurementIntent.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_intents_by_centre(self, centre_id: UUID) -> list[ProcurementIntent]:
        stmt = (
            select(ProcurementIntent)
            .where(ProcurementIntent.centre_id == centre_id)
            .order_by(ProcurementIntent.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_status_history(
        self,
        intent_id: UUID,
        from_status: str,
        to_status: str,
        changed_by: UUID,
        token_id: UUID | None = None,
        remarks: str | None = None,
    ) -> ProcurementStatusHistory:
        history = ProcurementStatusHistory(
            intent_id=intent_id,
            token_id=token_id,
            from_status=from_status,
            to_status=to_status,
            changed_by=changed_by,
            remarks=remarks,
        )
        self.session.add(history)
        await self.session.flush()
        return history

    async def get_approved_intents_for_cycle(
        self,
        centre_id: UUID,
        crop_id: UUID,
        ready_date: date,
    ) -> list[ProcurementIntent]:
        stmt = (
            select(ProcurementIntent)
            .where(
                ProcurementIntent.centre_id == centre_id,
                ProcurementIntent.crop_id == crop_id,
                ProcurementIntent.ready_date == ready_date,
                ProcurementIntent.status == IntentStatus.APPROVED,
            )
            .order_by(ProcurementIntent.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
