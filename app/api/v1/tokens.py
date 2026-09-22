from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.rbac import Permission
from app.dependencies.auth import CurrentUserDep
from app.dependencies.db import SessionDep
from app.dependencies.rbac import require_permission
from app.repositories.queue import QueueRepository
from app.repositories.token import TokenRepository
from app.schemas.token import TokenResponse
from app.services.queue import QueueService

router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.get(
    "/{id}",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission(Permission.QUEUE_READ))],
)
async def get_token(
    id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> TokenResponse:
    service = QueueService(QueueRepository(session), TokenRepository(session))
    return await service.get_token(id, current_user)


@router.post(
    "/{id}/process",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission(Permission.QUEUE_MANAGE))],
)
async def process_token(
    id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> TokenResponse:
    service = QueueService(QueueRepository(session), TokenRepository(session))
    return await service.process_token(id, current_user)


@router.post(
    "/{id}/complete",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission(Permission.QUEUE_MANAGE))],
)
async def complete_token(
    id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> TokenResponse:
    service = QueueService(QueueRepository(session), TokenRepository(session))
    return await service.complete_token(id, current_user)


@router.post(
    "/{id}/cancel",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def cancel_token(
    id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> TokenResponse:
    service = QueueService(QueueRepository(session), TokenRepository(session))
    return await service.cancel_token(id, current_user)
