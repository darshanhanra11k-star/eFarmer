from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.core.rbac import Permission, Role, has_permission
from app.core.retry import run_with_retry
from app.dependencies.auth import AuthenticatedUser
from app.models.queue import QueueStatus
from app.models.token import TokenStatus
from app.repositories.queue import QueueRepository
from app.repositories.token import TokenRepository
from app.schemas.queue import QueueStatusResponse
from app.schemas.token import TokenResponse


class QueueService:
    def __init__(
        self,
        queue_repo: QueueRepository,
        token_repo: TokenRepository,
        session: AsyncSession | None = None,
    ) -> None:
        self.queue_repo = queue_repo
        self.token_repo = token_repo
        self.session = session or token_repo.session

    async def _verify_officer_centre(
        self,
        current_user: AuthenticatedUser,
        expected_centre_id: UUID,
    ) -> None:
        user = await self.queue_repo.get_user_by_subject(current_user.subject)
        if (
            user is None
            or user.centre_id is None
            or user.centre_id != expected_centre_id
        ):
            raise PermissionDeniedError(
                message=(
                    "You do not have permission to operate on another "
                    "centre's queue or tokens."
                ),
            )

    async def resolve_target_farmer_id(
        self,
        current_user: AuthenticatedUser,
        requested_farmer_id: UUID | None,
    ) -> UUID:
        if current_user.role == Role.FARMER:
            user = await self.queue_repo.get_user_by_subject(current_user.subject)
            if user is None or user.farmer_id is None:
                raise PermissionDeniedError(
                    message="Authenticated user is not linked to a farmer record.",
                )
            if (
                requested_farmer_id is not None
                and requested_farmer_id != user.farmer_id
            ):
                raise PermissionDeniedError(
                    message=(
                        "You do not have permission to join the queue "
                        "for another farmer."
                    ),
                )
            return user.farmer_id

        if current_user.role == Role.OFFICER:
            if requested_farmer_id is None:
                raise ValidationError(
                    message=(
                        "farmer_id is required when an officer creates a queue token."
                    ),
                )
            return requested_farmer_id

        raise PermissionDeniedError(
            message="You do not have permission to join the queue.",
        )

    async def join_queue(
        self,
        queue_id: UUID,
        requested_farmer_id: UUID | None,
        current_user: AuthenticatedUser,
    ) -> TokenResponse:
        if not (
            has_permission(current_user.role, Permission.QUEUE_JOIN)
            or has_permission(current_user.role, Permission.QUEUE_MANAGE)
        ):
            raise PermissionDeniedError(
                message="You do not have permission to join the queue.",
            )

        target_farmer_id = await self.resolve_target_farmer_id(
            current_user,
            requested_farmer_id,
        )

        async def _attempt() -> TokenResponse:
            queue = await self.queue_repo.get_by_id_for_update(queue_id)
            if queue is None:
                raise NotFoundError(message="The requested queue was not found.")

            if current_user.role == Role.OFFICER:
                await self._verify_officer_centre(current_user, queue.centre_id)

            if queue.status != QueueStatus.OPEN:
                raise ConflictError(message="This queue is currently not open.")

            active_token = await self.token_repo.get_active_token_for_farmer(
                target_farmer_id,
                queue_id,
            )
            if active_token is not None:
                raise ConflictError(
                    message="Farmer already has an active token in this queue.",
                )

            next_seq, next_pos = await self.token_repo.get_next_sequence_and_position(
                queue_id
            )
            token_number = f"T-{next_seq:03d}"

            token = await self.token_repo.create_entry_and_token(
                queue_id=queue_id,
                farmer_id=target_farmer_id,
                position=next_pos,
                sequence_number=next_seq,
                token_number=token_number,
            )
            await self.session.commit()
            await self.session.refresh(token)
            return TokenResponse.model_validate(token)

        return await run_with_retry(self.session, _attempt)

    async def get_queue_status(
        self,
        queue_id: UUID,
        current_user: AuthenticatedUser,
    ) -> QueueStatusResponse:
        if not has_permission(current_user.role, Permission.QUEUE_READ):
            raise PermissionDeniedError(
                message="You do not have permission to view queue status.",
            )

        queue = await self.queue_repo.get_by_id(queue_id)
        if queue is None:
            raise NotFoundError(message="The requested queue was not found.")

        counts = await self.queue_repo.get_queue_counts(queue_id)
        current_called, last_issued = await self.queue_repo.get_latest_token_numbers(
            queue_id
        )

        return QueueStatusResponse(
            queue_id=queue.id,
            centre_id=queue.centre_id,
            date=queue.date,
            status=queue.status,
            total_waiting=counts.get(TokenStatus.WAITING.value, 0),
            total_called=counts.get(TokenStatus.CALLED.value, 0),
            total_processing=counts.get(TokenStatus.PROCESSING.value, 0),
            total_completed=counts.get(TokenStatus.COMPLETED.value, 0),
            total_cancelled=counts.get(TokenStatus.CANCELLED.value, 0),
            current_called_token=current_called,
            last_issued_token=last_issued,
        )

    async def get_token(
        self,
        token_id: UUID,
        current_user: AuthenticatedUser,
    ) -> TokenResponse:
        if not has_permission(current_user.role, Permission.QUEUE_READ):
            raise PermissionDeniedError(
                message="You do not have permission to view this token.",
            )

        token = await self.token_repo.get_by_id(token_id)
        if token is None:
            raise NotFoundError(message="The requested token was not found.")

        if current_user.role == Role.FARMER:
            user = await self.queue_repo.get_user_by_subject(current_user.subject)
            if user is None or user.farmer_id != token.farmer_id:
                raise PermissionDeniedError(
                    message=(
                        "You do not have permission to view another farmer's token."
                    ),
                )

        return TokenResponse.model_validate(token)

    async def call_next(
        self,
        queue_id: UUID,
        counter_id: UUID | None,
        current_user: AuthenticatedUser,
    ) -> TokenResponse:
        if not has_permission(current_user.role, Permission.QUEUE_MANAGE):
            raise PermissionDeniedError(
                message="You do not have permission to call tokens.",
            )

        async def _attempt() -> TokenResponse:
            # 1. Lock the target queues row with SELECT ... FOR UPDATE
            # (FIFO serialization)
            queue = await self.queue_repo.get_by_id_for_update(queue_id)
            if queue is None:
                raise NotFoundError(message="The requested queue was not found.")

            # 2. Officer centre isolation
            await self._verify_officer_centre(current_user, queue.centre_id)

            # 3. Counter centre validation
            if counter_id is not None:
                counter = await self.queue_repo.get_counter_by_id(counter_id)
                if counter is None:
                    raise NotFoundError(message="The requested counter was not found.")
                if counter.centre_id != queue.centre_id:
                    raise PermissionDeniedError(
                        message="Counter does not belong to this procurement centre.",
                    )

            # 4. Deterministic earliest WAITING token selection by sequence_number ASC
            token = await self.token_repo.get_next_waiting_token_for_update(queue_id)
            if token is None:
                raise NotFoundError(
                    message="No waiting tokens found in this queue.",
                )

            if token.status != TokenStatus.WAITING:
                raise ConflictError(
                    message=(
                        f"Only WAITING tokens can be CALLED; "
                        f"current status is {token.status.value}."
                    ),
                )

            token.status = TokenStatus.CALLED
            token.counter_id = counter_id
            token.called_at = datetime.now(UTC)

            saved = await self.token_repo.save(token)
            await self.session.commit()
            await self.session.refresh(saved)
            return TokenResponse.model_validate(saved)

        return await run_with_retry(self.session, _attempt)

    async def process_token(
        self,
        token_id: UUID,
        current_user: AuthenticatedUser,
    ) -> TokenResponse:
        if not has_permission(current_user.role, Permission.QUEUE_MANAGE):
            raise PermissionDeniedError(
                message="You do not have permission to process tokens.",
            )

        async def _attempt() -> TokenResponse:
            token = await self.token_repo.get_by_id_for_update(token_id)
            if token is None:
                raise NotFoundError(message="The requested token was not found.")

            queue = await self.queue_repo.get_by_id(token.queue_id)
            if queue is None:
                raise NotFoundError(message="The requested queue was not found.")

            await self._verify_officer_centre(current_user, queue.centre_id)

            if token.status != TokenStatus.CALLED:
                raise ConflictError(
                    message=(
                        f"Cannot move token to PROCESSING from status "
                        f"{token.status.value}; token must be CALLED."
                    ),
                )

            token.status = TokenStatus.PROCESSING
            token.processing_started_at = datetime.now(UTC)

            saved = await self.token_repo.save(token)
            await self.session.commit()
            await self.session.refresh(saved)
            return TokenResponse.model_validate(saved)

        return await run_with_retry(self.session, _attempt)

    async def complete_token(
        self,
        token_id: UUID,
        current_user: AuthenticatedUser,
    ) -> TokenResponse:
        if not has_permission(current_user.role, Permission.QUEUE_MANAGE):
            raise PermissionDeniedError(
                message="You do not have permission to complete tokens.",
            )

        async def _attempt() -> TokenResponse:
            token = await self.token_repo.get_by_id_for_update(token_id)
            if token is None:
                raise NotFoundError(message="The requested token was not found.")

            queue = await self.queue_repo.get_by_id(token.queue_id)
            if queue is None:
                raise NotFoundError(message="The requested queue was not found.")

            await self._verify_officer_centre(current_user, queue.centre_id)

            if token.status != TokenStatus.PROCESSING:
                raise ConflictError(
                    message=(
                        f"Cannot move token to COMPLETED from status "
                        f"{token.status.value}; token must be PROCESSING."
                    ),
                )

            token.status = TokenStatus.COMPLETED
            token.completed_at = datetime.now(UTC)

            saved = await self.token_repo.save(token)
            await self.session.commit()
            await self.session.refresh(saved)
            return TokenResponse.model_validate(saved)

        return await run_with_retry(self.session, _attempt)

    async def cancel_token(
        self,
        token_id: UUID,
        current_user: AuthenticatedUser,
    ) -> TokenResponse:
        async def _attempt() -> TokenResponse:
            token = await self.token_repo.get_by_id_for_update(token_id)
            if token is None:
                raise NotFoundError(message="The requested token was not found.")

            if current_user.role == Role.FARMER:
                user = await self.queue_repo.get_user_by_subject(current_user.subject)
                if user is None or user.farmer_id != token.farmer_id:
                    raise PermissionDeniedError(
                        message="You do not have permission to cancel this token.",
                    )
            elif has_permission(current_user.role, Permission.QUEUE_MANAGE):
                queue = await self.queue_repo.get_by_id(token.queue_id)
                if queue is None:
                    raise NotFoundError(message="The requested queue was not found.")
                await self._verify_officer_centre(current_user, queue.centre_id)
            else:
                raise PermissionDeniedError(
                    message="You do not have permission to cancel tokens.",
                )

            if token.status != TokenStatus.WAITING:
                raise ConflictError(
                    message=(
                        f"Cannot cancel token with status {token.status.value}; "
                        f"only WAITING tokens can be CANCELLED."
                    ),
                )

            token.status = TokenStatus.CANCELLED
            token.cancelled_at = datetime.now(UTC)

            saved = await self.token_repo.save(token)
            await self.session.commit()
            await self.session.refresh(saved)
            return TokenResponse.model_validate(saved)

        return await run_with_retry(self.session, _attempt)
