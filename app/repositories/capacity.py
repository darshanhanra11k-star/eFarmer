from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capacity import CapacityRecord


class CapacityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_capacity_record(
        self,
        centre_id: UUID,
        crop_id: UUID,
        target_date: date,
        for_update: bool = False,
    ) -> CapacityRecord | None:
        stmt = select(CapacityRecord).where(
            CapacityRecord.centre_id == centre_id,
            CapacityRecord.crop_id == crop_id,
            CapacityRecord.date == target_date,
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def save(self, record: CapacityRecord) -> CapacityRecord:
        self.session.add(record)
        await self.session.flush()
        return record
