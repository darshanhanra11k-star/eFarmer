from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.models.queue_entry import QueueEntry
from app.models.token import Token, TokenStatus


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


class TokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, token_id: UUID) -> Token | None:
        stmt = select(Token).where(Token.id == token_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, token_id: UUID) -> Token | None:
        stmt = select(Token).where(Token.id == token_id).with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_token_for_farmer(
        self,
        farmer_id: UUID,
        queue_id: UUID,
    ) -> Token | None:
        active_statuses = [
            TokenStatus.CHECK_IN,
            TokenStatus.TOKEN,
            TokenStatus.WAITING,
            TokenStatus.CALLED,
            TokenStatus.PROCESSING,
        ]
        stmt = select(Token).where(
            Token.farmer_id == farmer_id,
            Token.queue_id == queue_id,
            Token.status.in_(active_statuses),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_next_sequence_and_position(
        self,
        queue_id: UUID,
    ) -> tuple[int, int]:
        seq_stmt = select(func.coalesce(func.max(Token.sequence_number), 0) + 1).where(
            Token.queue_id == queue_id
        )
        seq_res = await self.session.execute(seq_stmt)
        next_seq = int(seq_res.scalar_one())

        pos_stmt = select(func.coalesce(func.max(QueueEntry.position), 0) + 1).where(
            QueueEntry.queue_id == queue_id
        )
        pos_res = await self.session.execute(pos_stmt)
        next_pos = int(pos_res.scalar_one())

        return next_seq, next_pos

    async def create_entry_and_token(
        self,
        queue_id: UUID,
        farmer_id: UUID,
        position: int,
        sequence_number: int,
        token_number: str,
    ) -> Token:
        entry = QueueEntry(
            queue_id=queue_id,
            farmer_id=farmer_id,
            position=position,
        )
        self.session.add(entry)
        await self.session.flush()

        token = Token(
            token_number=token_number,
            sequence_number=sequence_number,
            queue_id=queue_id,
            queue_entry_id=entry.id,
            farmer_id=farmer_id,
            counter_id=None,
            status=TokenStatus.WAITING,
        )
        self.session.add(token)

        try:
            await self.session.flush()
            return token
        except IntegrityError as exc:
            await self.session.rollback()
            if _is_unique_violation(exc):
                raise ConflictError(
                    message=(
                        "An active token already exists for this farmer "
                        "or sequence collision occurred."
                    ),
                ) from None
            raise

    async def get_next_waiting_token_for_update(
        self,
        queue_id: UUID,
    ) -> Token | None:
        stmt = (
            select(Token)
            .where(
                Token.queue_id == queue_id,
                Token.status == TokenStatus.WAITING,
            )
            .order_by(Token.sequence_number.asc())
            .limit(1)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def save(self, token: Token) -> Token:
        self.session.add(token)
        try:
            await self.session.flush()
            return token
        except IntegrityError as exc:
            await self.session.rollback()
            if _is_unique_violation(exc):
                raise ConflictError(
                    message="A token conflict occurred.",
                ) from None
            raise
