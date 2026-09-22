from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.centre import ProcurementCentre


class CentreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_centres(
        self,
        offset: int,
        limit: int,
    ) -> tuple[list[ProcurementCentre], int]:
        count_stmt = select(func.count()).select_from(ProcurementCentre)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(ProcurementCentre)
            .options(selectinload(ProcurementCentre.counters))
            .order_by(ProcurementCentre.name)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        centres = list(result.scalars().all())

        return centres, total

    async def get_by_id(self, centre_id: UUID) -> ProcurementCentre | None:
        stmt = (
            select(ProcurementCentre)
            .options(selectinload(ProcurementCentre.counters))
            .where(ProcurementCentre.id == centre_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
