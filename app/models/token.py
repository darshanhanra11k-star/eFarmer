from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.counter import Counter
    from app.models.farmer import Farmer
    from app.models.queue import Queue
    from app.models.queue_entry import QueueEntry


class TokenStatus(StrEnum):
    CHECK_IN = "CHECK_IN"
    TOKEN = "TOKEN"
    WAITING = "WAITING"
    CALLED = "CALLED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Token(Base):
    __tablename__ = "tokens"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    token_number: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    queue_id: Mapped[UUID] = mapped_column(
        ForeignKey("queues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    queue_entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("queue_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    farmer_id: Mapped[UUID] = mapped_column(
        ForeignKey("farmers.id"),
        nullable=False,
        index=True,
    )
    counter_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("counters.id"),
        nullable=True,
        index=True,
    )
    status: Mapped[TokenStatus] = mapped_column(
        String,
        nullable=False,
        default=TokenStatus.WAITING,
        server_default=text("'WAITING'"),
    )
    called_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    queue: Mapped["Queue"] = relationship(
        "Queue",
        back_populates="tokens",
    )
    queue_entry: Mapped["QueueEntry"] = relationship(
        "QueueEntry",
        back_populates="token",
    )
    farmer: Mapped["Farmer"] = relationship(
        "Farmer",
    )
    counter: Mapped["Counter | None"] = relationship(
        "Counter",
    )

    __table_args__ = (
        UniqueConstraint(
            "queue_entry_id",
            name="uq_tokens_queue_entry_id",
        ),
        Index(
            "ix_tokens_queue_entry_id",
            "queue_entry_id",
            unique=True,
        ),
        UniqueConstraint(
            "queue_id",
            "sequence_number",
            name="uq_tokens_queue_sequence",
        ),
        UniqueConstraint(
            "queue_id",
            "token_number",
            name="uq_tokens_queue_token_number",
        ),
        Index(
            "uq_active_farmer_token",
            "farmer_id",
            "queue_id",
            unique=True,
            postgresql_where=(
                status.in_(
                    [
                        TokenStatus.CHECK_IN,
                        TokenStatus.TOKEN,
                        TokenStatus.WAITING,
                        TokenStatus.CALLED,
                        TokenStatus.PROCESSING,
                    ]
                )
            ),
        ),
    )
