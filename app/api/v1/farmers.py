from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

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
from app.schemas.farmer import FarmerCreate, FarmerResponse
from app.schemas.priority_centre import (
    PriorityCentreSelectionRequest,
    PriorityCentreSelectionResponse,
)
from app.services.allocation import AllocationService
from app.services.farmer import FarmerService
from app.services.priority_centre import PriorityCentreService

router = APIRouter(prefix="/farmers", tags=["farmers"])


def _get_allocation_service(session: SessionDep) -> AllocationService:
    return AllocationService(
        capacity_repo=CapacityRepository(session),
        procurement_repo=ProcurementRepository(session),
        session=session,
        allocation_repo=AllocationRepository(session),
        farmer_repo=FarmerRepository(session),
    )


AllocationServiceDep = Annotated[AllocationService, Depends(_get_allocation_service)]


def _get_priority_centre_service(session: SessionDep) -> PriorityCentreService:
    return PriorityCentreService(
        centre_repo=CentreRepository(session),
        capacity_repo=CapacityRepository(session),
        farmer_repo=FarmerRepository(session),
    )


PriorityCentreServiceDep = Annotated[
    PriorityCentreService, Depends(_get_priority_centre_service)
]


@router.post(
    "/me/centre-selection",
    response_model=PriorityCentreSelectionResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(Role.FARMER))],
)
async def select_priority_centre(
    payload: PriorityCentreSelectionRequest,
    current_user: CurrentUserDep,
    service: PriorityCentreServiceDep,
) -> PriorityCentreSelectionResponse:
    return await service.select_priority_centre(payload, current_user)


@router.get(
    "/me/intents/{intent_id}/allocation",
    response_model=AllocationDecisionResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(Role.FARMER, Role.OFFICER))],
)
async def get_farmer_intent_allocation(
    intent_id: UUID,
    current_user: CurrentUserDep,
    service: AllocationServiceDep,
) -> AllocationDecisionResponse:
    decision = await service.get_intent_allocation(intent_id, current_user)
    return AllocationDecisionResponse.model_validate(decision)


@router.post(
    "",
    response_model=FarmerResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Role.OFFICER))],
)
async def create_farmer(
    data: FarmerCreate,
    session: SessionDep,
) -> FarmerResponse:
    service = FarmerService(FarmerRepository(session))
    return await service.create_farmer(data)


@router.get(
    "/{id}",
    response_model=FarmerResponse,
    status_code=status.HTTP_200_OK,
)
async def get_farmer(
    id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> FarmerResponse:
    service = FarmerService(FarmerRepository(session))
    return await service.get_farmer(id, current_user)
