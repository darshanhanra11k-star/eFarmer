from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.models.farmer import Farmer
from app.models.land_holding import FarmerLandHolding
from app.models.user import User


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


class FarmerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, farmer: Farmer) -> Farmer:
        self.session.add(farmer)
        try:
            await self.session.flush()
            return farmer
        except IntegrityError as exc:
            await self.session.rollback()
            if _is_unique_violation(exc):
                raise ConflictError(
                    message="A farmer with this identifier already exists.",
                ) from None
            raise

    async def get_by_id(self, farmer_id: UUID) -> Farmer | None:
        stmt = select(Farmer).where(Farmer.id == farmer_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_land_holdings_by_farmer_id(
        self, farmer_id: UUID
    ) -> list[FarmerLandHolding]:
        stmt = select(FarmerLandHolding).where(FarmerLandHolding.farmer_id == farmer_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_by_subject(self, subject: str) -> User | None:
        try:
            user_id = UUID(subject)
            stmt = select(User).where(User.id == user_id)
        except ValueError:
            stmt = select(User).where(User.username == subject)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
