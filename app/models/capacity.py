from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.centre import ProcurementCentre
    from app.models.crop import Crop


class CapacityRecord(Base):
    __tablename__ = "capacity_records"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    centre_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_centres.id"),
        nullable=False,
    )
    crop_id: Mapped[UUID] = mapped_column(
        ForeignKey("crops.id"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    total_capacity_kg: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )
    allocated_quantity_kg: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
    )
    procured_quantity_kg: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
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

    centre: Mapped["ProcurementCentre"] = relationship(foreign_keys=[centre_id])
    crop: Mapped["Crop"] = relationship(foreign_keys=[crop_id])

    __table_args__ = (
        UniqueConstraint("centre_id", "crop_id", "date", name="uq_centre_crop_date"),
        CheckConstraint(
            "total_capacity_kg >= 0 AND "
            "allocated_quantity_kg >= 0 AND "
            "procured_quantity_kg >= 0",
            name="chk_capacity_non_negative",
        ),
        CheckConstraint(
            "allocated_quantity_kg <= total_capacity_kg AND "
            "procured_quantity_kg <= allocated_quantity_kg",
            name="chk_capacity_not_exceeded",
        ),
        Index("idx_capacity_records_centre_id", "centre_id"),
        Index("idx_capacity_records_crop_id", "crop_id"),
        Index("idx_capacity_records_date", "date"),
    )
