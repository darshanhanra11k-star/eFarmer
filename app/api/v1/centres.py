from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.rbac import Role
from app.dependencies.auth import CurrentUserDep
from app.dependencies.db import SessionDep
from app.dependencies.rbac import require_role
from app.repositories.allocation import AllocationRepository
from app.repositories.capacity import CapacityRepository
from app.repositories.centre import CentreRepository
from app.repositories.farmer import FarmerRepository
from app.repositories.procurement import ProcurementRepository
from app.schemas.allocation import AllocationDecisionResponse
from app.schemas.centre import CentreResponse
from app.schemas.common import PaginationParams, PaginationResponse
from app.services.allocation import AllocationService
from app.services.centre import CentreService

router = APIRouter(prefix="/centres", tags=["centres"])


def _get_allocation_service(session: SessionDep) -> AllocationService:
    return AllocationService(
        capacity_repo=CapacityRepository(session),
        procurement_repo=ProcurementRepository(session),
        session=session,
        allocation_repo=AllocationRepository(session),
        farmer_repo=FarmerRepository(session),
    )


AllocationServiceDep = Annotated[AllocationService, Depends(_get_allocation_service)]


@router.get(
    "/{centre_id}/allocation",
    response_model=list[AllocationDecisionResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(Role.OFFICER))],
)
async def get_centre_allocations(
    centre_id: UUID,
    current_user: CurrentUserDep,
    service: AllocationServiceDep,
    crop_id: Annotated[UUID | None, Query()] = None,
    allocation_date: Annotated[date | None, Query()] = None,
) -> list[AllocationDecisionResponse]:
    decisions = await service.get_centre_allocations(
        centre_id=centre_id,
        current_user=current_user,
        crop_id=crop_id,
        allocation_date=allocation_date,
    )

    return [AllocationDecisionResponse.model_validate(d) for d in decisions]


@router.get(
    "",
    response_model=PaginationResponse[CentreResponse],
    status_code=status.HTTP_200_OK,
)
async def list_centres(
    _current_user: CurrentUserDep,
    session: SessionDep,
    params: Annotated[PaginationParams, Depends()],
) -> PaginationResponse[CentreResponse]:
    service = CentreService(CentreRepository(session))
    return await service.list_centres(params)


@router.get(
    "/{id}",
    response_model=CentreResponse,
    status_code=status.HTTP_200_OK,
)
async def get_centre(
    id: UUID,
    _current_user: CurrentUserDep,
    session: SessionDep,
) -> CentreResponse:
    service = CentreService(CentreRepository(session))
    return await service.get_centre(id)
