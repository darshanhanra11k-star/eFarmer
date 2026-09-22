from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.farmer import Farmer


class FarmerLandHolding(Base):
    __tablename__ = "farmer_land_holdings"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    farmer_id: Mapped[UUID] = mapped_column(
        ForeignKey("farmers.id"),
        nullable=False,
        index=True,
    )
    survey_number: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    area_acres: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
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

    farmer: Mapped["Farmer"] = relationship(
        "Farmer",
        back_populates="land_holdings",
    )
