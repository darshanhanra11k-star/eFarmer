from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.rbac import Permission, Role
from app.dependencies.auth import CurrentUserDep
from app.dependencies.db import SessionDep
from app.dependencies.rbac import require_permission, require_role
from app.repositories.centre import CentreRepository
from app.repositories.crop import CropRepository
from app.repositories.farmer import FarmerRepository
from app.repositories.procurement import ProcurementRepository
from app.schemas.procurement import (
    ProcurementIntentCreate,
    ProcurementIntentResponse,
)
from app.services.procurement import ProcurementService

router = APIRouter(prefix="/procurement", tags=["procurement"])


def _get_procurement_service(session: SessionDep) -> ProcurementService:
    return ProcurementService(
        procurement_repo=ProcurementRepository(session),
        farmer_repo=FarmerRepository(session),
        centre_repo=CentreRepository(session),
        crop_repo=CropRepository(session),
        session=session,
    )


ProcurementServiceDep = Annotated[ProcurementService, Depends(_get_procurement_service)]


@router.post(
    "",
    response_model=ProcurementIntentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Role.FARMER, Role.OFFICER))],
)
async def create_procurement(
    body: ProcurementIntentCreate,
    current_user: CurrentUserDep,
    service: ProcurementServiceDep,
) -> ProcurementIntentResponse:
    intent = await service.create_procurement_intent(body, current_user)
    return ProcurementIntentResponse.model_validate(intent)


@router.get(
    "/{id}",
    response_model=ProcurementIntentResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_READ))],
)
async def get_procurement_record(
    id: UUID,
    current_user: CurrentUserDep,
    service: ProcurementServiceDep,
) -> ProcurementIntentResponse:
    intent = await service.get_procurement_by_id(id, current_user)
    return ProcurementIntentResponse.model_validate(intent)
