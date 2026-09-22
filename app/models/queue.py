from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.centre import ProcurementCentre
    from app.models.crop import Crop
    from app.models.queue_entry import QueueEntry
    from app.models.token import Token


class QueueStatus(StrEnum):
    OPEN = "OPEN"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


class Queue(Base):
    __tablename__ = "queues"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    centre_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_centres.id"),
        nullable=False,
        index=True,
    )
    crop_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("crops.id"),
        nullable=True,
        index=True,
    )
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=date.today,
    )
    status: Mapped[QueueStatus] = mapped_column(
        String,
        nullable=False,
        default=QueueStatus.OPEN,
        server_default=text("'OPEN'"),
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

    centre: Mapped["ProcurementCentre"] = relationship(
        "ProcurementCentre",
    )
    crop: Mapped["Crop | None"] = relationship(
        "Crop",
    )
    entries: Mapped[list["QueueEntry"]] = relationship(
        "QueueEntry",
        back_populates="queue",
        cascade="all, delete-orphan",
    )
    tokens: Mapped[list["Token"]] = relationship(
        "Token",
        back_populates="queue",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "centre_id",
            "date",
            "crop_id",
            name="uq_queues_centre_date_crop",
        ),
    )
