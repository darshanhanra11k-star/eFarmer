from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.rbac import Role
from app.dependencies.auth import AuthenticatedUser
from app.models.farmer import Farmer
from app.repositories.farmer import FarmerRepository
from app.schemas.farmer import FarmerCreate, FarmerResponse


class FarmerService:
    def __init__(
        self,
        farmer_repo: FarmerRepository,
        session: AsyncSession | None = None,
    ) -> None:
        self.farmer_repo = farmer_repo
        self.session = session or farmer_repo.session

    async def create_farmer(self, data: FarmerCreate) -> FarmerResponse:
        farmer = Farmer(
            farmer_id=data.farmer_id,
            name=data.name,
            phone=data.phone,
            village=data.village,
            block=data.block,
            district=data.district,
            state=data.state,
            active=True,
        )
        created = await self.farmer_repo.create(farmer)
        try:
            await self.session.commit()
            await self.session.refresh(created)
            return FarmerResponse.model_validate(created)
        except Exception:
            await self.session.rollback()
            raise

    async def get_farmer(
        self,
        farmer_id: UUID,
        current_user: AuthenticatedUser,
    ) -> FarmerResponse:
        if current_user.role == Role.FARMER:
            user = await self.farmer_repo.get_user_by_subject(current_user.subject)
            if user is None or user.farmer_id != farmer_id:
                raise PermissionDeniedError()
        elif current_user.role != Role.OFFICER:
            raise PermissionDeniedError()

        farmer = await self.farmer_repo.get_by_id(farmer_id)
        if farmer is None:
            raise NotFoundError(message="Farmer not found.")

        return FarmerResponse.model_validate(farmer)
