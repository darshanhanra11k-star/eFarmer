from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.centre import ProcurementCentre


class Counter(Base):
    __tablename__ = "counters"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    centre_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_centres.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
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

    centre: Mapped["ProcurementCentre"] = relationship(
        "ProcurementCentre",
        back_populates="counters",
    )
