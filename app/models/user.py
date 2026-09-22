from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.rbac import Role
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.centre import ProcurementCentre
    from app.models.farmer import Farmer


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "(role = 'FARMER' AND farmer_id IS NOT NULL "
            "AND centre_id IS NULL AND username IS NULL) "
            "OR "
            "(role = 'OFFICER' AND centre_id IS NOT NULL "
            "AND farmer_id IS NULL AND username IS NOT NULL)",
            name="ck_users_role_consistency",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    username: Mapped[str | None] = mapped_column(
        String,
        unique=True,
        nullable=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    role: Mapped[Role] = mapped_column(
        Enum(
            Role,
            name="user_role",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    centre_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("procurement_centres.id"),
        nullable=True,
        index=True,
    )
    farmer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("farmers.id"),
        unique=True,
        nullable=True,
    )
    phone: Mapped[str | None] = mapped_column(
        String,
        unique=True,
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

    farmer: Mapped["Farmer | None"] = relationship(
        "Farmer",
        back_populates="user",
    )
    centre: Mapped["ProcurementCentre | None"] = relationship(
        "ProcurementCentre",
        back_populates="users",
    )
