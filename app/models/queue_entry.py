from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.farmer import Farmer
    from app.models.queue import Queue
    from app.models.token import Token


class QueueEntry(Base):
    __tablename__ = "queue_entries"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    queue_id: Mapped[UUID] = mapped_column(
        ForeignKey("queues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    farmer_id: Mapped[UUID] = mapped_column(
        ForeignKey("farmers.id"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
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
        back_populates="entries",
    )
    farmer: Mapped["Farmer"] = relationship(
        "Farmer",
    )
    token: Mapped["Token | None"] = relationship(
        "Token",
        back_populates="queue_entry",
        uselist=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "queue_id",
            "position",
            name="uq_queue_entries_queue_position",
        ),
    )
