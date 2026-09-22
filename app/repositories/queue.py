from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.models.counter import Counter
from app.models.queue import Queue
from app.models.token import Token, TokenStatus
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


class QueueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, queue_id: UUID) -> Queue | None:
        stmt = select(Queue).where(Queue.id == queue_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, queue_id: UUID) -> Queue | None:
        stmt = select(Queue).where(Queue.id == queue_id).with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_centre_and_date(
        self,
        centre_id: UUID,
        queue_date: date,
        crop_id: UUID | None = None,
    ) -> Queue | None:
        stmt = select(Queue).where(
            Queue.centre_id == centre_id,
            Queue.date == queue_date,
            Queue.crop_id == crop_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, queue: Queue) -> Queue:
        self.session.add(queue)
        try:
            await self.session.flush()
            return queue
        except IntegrityError as exc:
            await self.session.rollback()
            if _is_unique_violation(exc):
                raise ConflictError(
                    message="A queue for this centre, date, and crop already exists.",
                ) from None
            raise

    async def get_queue_counts(self, queue_id: UUID) -> dict[str, int]:
        stmt = (
            select(Token.status, func.count(Token.id))
            .where(Token.queue_id == queue_id)
            .group_by(Token.status)
        )
        result = await self.session.execute(stmt)
        counts: dict[str, int] = {status.value: 0 for status in TokenStatus}
        for status, count in result.all():
            counts[str(status)] = int(count)
        return counts

    async def get_latest_token_numbers(
        self,
        queue_id: UUID,
    ) -> tuple[str | None, str | None]:
        called_stmt = (
            select(Token.token_number)
            .where(
                Token.queue_id == queue_id,
                Token.status.in_([TokenStatus.CALLED, TokenStatus.PROCESSING]),
            )
            .order_by(Token.called_at.desc().nullslast())
            .limit(1)
        )
        called_result = await self.session.execute(called_stmt)
        current_called = called_result.scalar_one_or_none()

        issued_stmt = (
            select(Token.token_number)
            .where(Token.queue_id == queue_id)
            .order_by(Token.sequence_number.desc())
            .limit(1)
        )
        issued_result = await self.session.execute(issued_stmt)
        last_issued = issued_result.scalar_one_or_none()

        return current_called, last_issued

    async def get_user_by_subject(self, subject: str) -> User | None:
        try:
            user_id = UUID(subject)
            stmt = select(User).where(User.id == user_id)
        except ValueError:
            stmt = select(User).where(User.username == subject)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_counter_by_id(self, counter_id: UUID) -> Counter | None:
        stmt = select(Counter).where(Counter.id == counter_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
