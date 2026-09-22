from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.rbac import Role
from app.dependencies.auth import CurrentUserDep
from app.dependencies.db import SessionDep
from app.dependencies.rbac import require_role
from app.repositories.capacity import CapacityRepository
from app.repositories.centre import CentreRepository
from app.repositories.crop import CropRepository
from app.repositories.farmer import FarmerRepository
from app.schemas.capacity import CapacityRecordResponse
from app.services.capacity import CapacityService

router = APIRouter(prefix="/centres", tags=["capacity"])


def _get_capacity_service(session: SessionDep) -> CapacityService:
    return CapacityService(
        capacity_repo=CapacityRepository(session),
        centre_repo=CentreRepository(session),
        crop_repo=CropRepository(session),
        farmer_repo=FarmerRepository(session),
        session=session,
    )


CapacityServiceDep = Annotated[CapacityService, Depends(_get_capacity_service)]


@router.get(
    "/{id}/capacity",
    response_model=CapacityRecordResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(Role.FARMER, Role.OFFICER))],
)
async def get_centre_capacity(
    id: UUID,
    crop_id: Annotated[UUID, Query(...)],
    date: Annotated[date, Query(...)],
    current_user: CurrentUserDep,
    service: CapacityServiceDep,
) -> CapacityRecordResponse:
    return await service.get_centre_capacity(
        centre_id=id,
        crop_id=crop_id,
        target_date=date,
        current_user=current_user,
    )
