from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crop import Crop


class CropRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, crop_id: UUID) -> Crop | None:
        stmt = select(Crop).where(Crop.id == crop_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Crop | None:
        stmt = select(Crop).where(Crop.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
