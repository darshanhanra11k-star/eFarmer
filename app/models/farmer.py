from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.land_holding import FarmerLandHolding
    from app.models.user import User


class Farmer(Base):
    __tablename__ = "farmers"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    farmer_id: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    phone: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    village: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    block: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    district: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    state: Mapped[str | None] = mapped_column(
        String,
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

    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="farmer",
        uselist=False,
    )
    land_holdings: Mapped[list["FarmerLandHolding"]] = relationship(
        "FarmerLandHolding",
        back_populates="farmer",
    )
