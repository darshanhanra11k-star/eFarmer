from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        user_role_enum = postgresql.ENUM("FARMER", "OFFICER", name="user_role")
        user_role_enum.create(bind, checkfirst=True)

    op.create_table(
        "crops",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("unit", sa.String(), nullable=False),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crops")),
        sa.UniqueConstraint("code", name=op.f("uq_crops_code")),
    )

    op.create_table(
        "procurement_centres",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("district", sa.String(), nullable=False),
        sa.Column("block", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("latitude", sa.Double(), nullable=True),
        sa.Column("longitude", sa.Double(), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_procurement_centres")),
    )

    op.create_table(
        "farmers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("farmer_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("village", sa.String(), nullable=True),
        sa.Column("block", sa.String(), nullable=True),
        sa.Column("district", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_farmers")),
        sa.UniqueConstraint("farmer_id", name=op.f("uq_farmers_farmer_id")),
    )

    role_type = (
        postgresql.ENUM("FARMER", "OFFICER", name="user_role", create_type=False)
        if bind.dialect.name == "postgresql"
        else sa.Enum("FARMER", "OFFICER", name="user_role")
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", role_type, nullable=False),
        sa.Column("centre_id", sa.Uuid(), nullable=True),
        sa.Column("farmer_id", sa.Uuid(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.ForeignKeyConstraint(
            ["centre_id"],
            ["procurement_centres.id"],
            name=op.f("fk_users_centre_id_procurement_centres"),
        ),
        sa.ForeignKeyConstraint(
            ["farmer_id"],
            ["farmers.id"],
            name=op.f("fk_users_farmer_id_farmers"),
        ),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
        sa.UniqueConstraint("farmer_id", name=op.f("uq_users_farmer_id")),
        sa.UniqueConstraint("phone", name=op.f("uq_users_phone")),
        sa.CheckConstraint(
            "(role = 'FARMER' AND farmer_id IS NOT NULL "
            "AND centre_id IS NULL AND username IS NULL) "
            "OR "
            "(role = 'OFFICER' AND centre_id IS NOT NULL "
            "AND farmer_id IS NULL AND username IS NOT NULL)",
            name=op.f("ck_users_role_consistency"),
        ),
    )
    op.create_index(op.f("ix_users_centre_id"), "users", ["centre_id"], unique=False)

    op.create_table(
        "farmer_land_holdings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("farmer_id", sa.Uuid(), nullable=False),
        sa.Column("survey_number", sa.String(), nullable=False),
        sa.Column("area_acres", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("village", sa.String(), nullable=True),
        sa.Column("block", sa.String(), nullable=True),
        sa.Column("district", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_farmer_land_holdings")),
        sa.ForeignKeyConstraint(
            ["farmer_id"],
            ["farmers.id"],
            name=op.f("fk_farmer_land_holdings_farmer_id_farmers"),
        ),
    )
    op.create_index(
        op.f("ix_farmer_land_holdings_farmer_id"),
        "farmer_land_holdings",
        ["farmer_id"],
        unique=False,
    )

    op.create_table(
        "counters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("centre_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_counters")),
        sa.ForeignKeyConstraint(
            ["centre_id"],
            ["procurement_centres.id"],
            name=op.f("fk_counters_centre_id_procurement_centres"),
        ),
    )
    op.create_index(
        op.f("ix_counters_centre_id"),
        "counters",
        ["centre_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_counters_centre_id"), table_name="counters")
    op.drop_table("counters")

    op.drop_index(
        op.f("ix_farmer_land_holdings_farmer_id"),
        table_name="farmer_land_holdings",
    )
    op.drop_table("farmer_land_holdings")

    op.drop_index(op.f("ix_users_centre_id"), table_name="users")
    op.drop_table("users")

    op.drop_table("farmers")
    op.drop_table("procurement_centres")
    op.drop_table("crops")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        user_role_enum = postgresql.ENUM("FARMER", "OFFICER", name="user_role")
        user_role_enum.drop(bind, checkfirst=True)
