from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
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
    from app.models.counter import Counter
    from app.models.crop import Crop
    from app.models.farmer import Farmer
    from app.models.land_holding import FarmerLandHolding
    from app.models.user import User


class IntentStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class ProcurementTokenStatus(StrEnum):
    WAITING = "WAITING"
    CALLED = "CALLED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ProcurementIntent(Base):
    __tablename__ = "procurement_intents"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    farmer_id: Mapped[UUID] = mapped_column(
        ForeignKey("farmers.id"),
        nullable=False,
    )
    centre_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_centres.id"),
        nullable=False,
    )
    crop_id: Mapped[UUID] = mapped_column(
        ForeignKey("crops.id"),
        nullable=False,
    )
    land_holding_id: Mapped[UUID] = mapped_column(
        ForeignKey("farmer_land_holdings.id"),
        nullable=False,
    )
    expected_quantity_kg: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )
    ready_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    status: Mapped[IntentStatus] = mapped_column(
        Enum(
            IntentStatus,
            name="intent_status_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=IntentStatus.PENDING,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    farmer: Mapped["Farmer"] = relationship(foreign_keys=[farmer_id])
    centre: Mapped["ProcurementCentre"] = relationship(foreign_keys=[centre_id])
    crop: Mapped["Crop"] = relationship(foreign_keys=[crop_id])
    land_holding: Mapped["FarmerLandHolding"] = relationship(
        foreign_keys=[land_holding_id]
    )
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    tokens: Mapped[list["ProcurementToken"]] = relationship(
        back_populates="intent",
        cascade="all, delete-orphan",
    )
    records: Mapped[list["ProcurementRecord"]] = relationship(
        back_populates="intent",
        cascade="all, delete-orphan",
    )
    status_history: Mapped[list["ProcurementStatusHistory"]] = relationship(
        back_populates="intent",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_procurement_intents_farmer_id", "farmer_id"),
        Index("idx_procurement_intents_centre_id", "centre_id"),
        Index("idx_procurement_intents_crop_id", "crop_id"),
        Index(
            "uq_active_intent_slot",
            "farmer_id",
            "centre_id",
            "crop_id",
            "ready_date",
            unique=True,
            postgresql_where=text(
                "status NOT IN ('CANCELLED', 'REJECTED', 'COMPLETED')"
            ),
        ),
    )


class ProcurementToken(Base):
    __tablename__ = "procurement_tokens"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    intent_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_intents.id"),
        nullable=False,
    )
    centre_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_centres.id"),
        nullable=False,
    )
    token_number: Mapped[int] = mapped_column(
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[ProcurementTokenStatus] = mapped_column(
        Enum(
            ProcurementTokenStatus,
            name="token_status_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=ProcurementTokenStatus.WAITING,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    intent: Mapped["ProcurementIntent"] = relationship(back_populates="tokens")
    centre: Mapped["ProcurementCentre"] = relationship(foreign_keys=[centre_id])
    record: Mapped["ProcurementRecord | None"] = relationship(
        back_populates="token",
        uselist=False,
    )
    status_history: Mapped[list["ProcurementStatusHistory"]] = relationship(
        back_populates="token",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "centre_id",
            "scheduled_at",
            "token_number",
            name="uq_centre_schedule_token",
        ),
        Index("idx_procurement_tokens_intent_id", "intent_id"),
        Index("idx_procurement_tokens_centre_id", "centre_id"),
    )


class ProcurementRecord(Base):
    __tablename__ = "procurement_records"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    intent_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_intents.id"),
        nullable=False,
    )
    token_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_tokens.id"),
        nullable=False,
        unique=True,
    )
    counter_id: Mapped[UUID] = mapped_column(
        ForeignKey("counters.id"),
        nullable=False,
    )
    actual_quantity_kg: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )
    price_per_kg: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )
    total_amount: Mapped[Decimal | None] = mapped_column(
        Numeric,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    intent: Mapped["ProcurementIntent"] = relationship(back_populates="records")
    token: Mapped["ProcurementToken"] = relationship(back_populates="record")
    counter: Mapped["Counter"] = relationship(foreign_keys=[counter_id])

    __table_args__ = (
        Index("idx_procurement_records_intent_id", "intent_id"),
        Index("idx_procurement_records_counter_id", "counter_id"),
    )


class ProcurementStatusHistory(Base):
    __tablename__ = "procurement_status_history"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    intent_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_intents.id"),
        nullable=False,
    )
    token_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("procurement_tokens.id"),
        nullable=True,
    )
    from_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    to_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    changed_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    remarks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    intent: Mapped["ProcurementIntent"] = relationship(back_populates="status_history")
    token: Mapped["ProcurementToken | None"] = relationship(
        back_populates="status_history"
    )
    actor: Mapped["User"] = relationship(foreign_keys=[changed_by])

    __table_args__ = (
        CheckConstraint(
            "(token_id IS NOT NULL) OR (from_status = 'PENDING') OR "
            "(to_status IN ('APPROVED', 'REJECTED', 'CANCELLED'))",
            name="chk_status_history_condition",
        ),
        Index("idx_status_history_intent_id", "intent_id"),
    )
