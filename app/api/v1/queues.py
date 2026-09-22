from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.rbac import Permission, Role
from app.dependencies.auth import CurrentUserDep
from app.dependencies.db import SessionDep
from app.dependencies.rbac import require_permission, require_role
from app.repositories.queue import QueueRepository
from app.repositories.token import TokenRepository
from app.schemas.queue import QueueJoinRequest, QueueStatusResponse
from app.schemas.token import TokenCallNextRequest, TokenResponse
from app.services.queue import QueueService

router = APIRouter(prefix="/queues", tags=["queues"])


@router.post(
    "/{id}/join",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Role.FARMER, Role.OFFICER))],
)
async def join_queue(
    id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    body: QueueJoinRequest | None = None,
) -> TokenResponse:
    service = QueueService(QueueRepository(session), TokenRepository(session))
    requested_farmer_id = body.farmer_id if body else None
    return await service.join_queue(id, requested_farmer_id, current_user)


@router.get(
    "/{id}",
    response_model=QueueStatusResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission(Permission.QUEUE_READ))],
)
async def get_queue_status(
    id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> QueueStatusResponse:
    service = QueueService(QueueRepository(session), TokenRepository(session))
    return await service.get_queue_status(id, current_user)


@router.post(
    "/{id}/call-next",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission(Permission.QUEUE_MANAGE))],
)
async def call_next_token(
    id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    body: TokenCallNextRequest | None = None,
) -> TokenResponse:
    service = QueueService(QueueRepository(session), TokenRepository(session))
    counter_id = body.counter_id if body else None
    return await service.call_next(id, counter_id, current_user)
