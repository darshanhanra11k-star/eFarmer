from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Double, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.counter import Counter
    from app.models.user import User


class ProcurementCentre(Base):
    __tablename__ = "procurement_centres"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    district: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    block: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    state: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    latitude: Mapped[float | None] = mapped_column(
        Double,
        nullable=True,
    )
    longitude: Mapped[float | None] = mapped_column(
        Double,
        nullable=True,
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

    counters: Mapped[list["Counter"]] = relationship(
        "Counter",
        back_populates="centre",
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="centre",
    )
