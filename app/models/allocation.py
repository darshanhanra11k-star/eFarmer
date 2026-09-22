from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.centre import ProcurementCentre
    from app.models.crop import Crop
    from app.models.farmer import Farmer
    from app.models.procurement import ProcurementIntent


class AllocationRun(Base):
    __tablename__ = "allocation_runs"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    centre_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_centres.id", ondelete="CASCADE"),
        nullable=False,
    )
    crop_id: Mapped[UUID] = mapped_column(
        ForeignKey("crops.id", ondelete="CASCADE"),
        nullable=False,
    )
    allocation_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    centre: Mapped["ProcurementCentre"] = relationship(foreign_keys=[centre_id])
    crop: Mapped["Crop"] = relationship(foreign_keys=[crop_id])
    decisions: Mapped[list["AllocationDecision"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "centre_id",
            "crop_id",
            "allocation_date",
            name="uq_allocation_cycle",
        ),
        Index("idx_allocation_runs_centre_id", "centre_id"),
        Index("idx_allocation_runs_crop_id", "crop_id"),
        Index("idx_allocation_runs_date", "allocation_date"),
    )


class AllocationDecision(Base):
    __tablename__ = "allocation_decisions"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    allocation_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("allocation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    intent_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_intents.id", ondelete="CASCADE"),
        nullable=False,
    )
    farmer_id: Mapped[UUID] = mapped_column(
        ForeignKey("farmers.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_quantity_kg: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )
    allocated_quantity_kg: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )
    remaining_capacity_kg: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )
    selected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    ordering_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    tie_break_digest: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    run: Mapped["AllocationRun"] = relationship(back_populates="decisions")
    intent: Mapped["ProcurementIntent"] = relationship(foreign_keys=[intent_id])
    farmer: Mapped["Farmer"] = relationship(foreign_keys=[farmer_id])

    __table_args__ = (
        UniqueConstraint(
            "allocation_run_id",
            "intent_id",
            name="uq_allocation_run_intent",
        ),
        Index("idx_allocation_decisions_run_id", "allocation_run_id"),
        Index("idx_allocation_decisions_intent_id", "intent_id"),
        Index("idx_allocation_decisions_farmer_id", "farmer_id"),
    )
