from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

intent_status_enum = postgresql.ENUM(
    "PENDING",
    "APPROVED",
    "REJECTED",
    "CANCELLED",
    "COMPLETED",
    name="intent_status_enum",
    create_type=False,
)

token_status_enum = postgresql.ENUM(
    "WAITING",
    "CALLED",
    "PROCESSING",
    "COMPLETED",
    "CANCELLED",
    name="token_status_enum",
    create_type=False,
)


def upgrade() -> None:
    # 1. Create Enums explicitly
    sa.Enum(
        "PENDING",
        "APPROVED",
        "REJECTED",
        "CANCELLED",
        "COMPLETED",
        name="intent_status_enum",
    ).create(op.get_bind(), checkfirst=True)

    sa.Enum(
        "WAITING",
        "CALLED",
        "PROCESSING",
        "COMPLETED",
        "CANCELLED",
        name="token_status_enum",
    ).create(op.get_bind(), checkfirst=True)

    # 2. Table: procurement_intents
    op.create_table(
        "procurement_intents",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "farmer_id",
            sa.UUID(),
            sa.ForeignKey("farmers.id", name="procurement_intents_farmer_id_fkey"),
            nullable=False,
        ),
        sa.Column(
            "centre_id",
            sa.UUID(),
            sa.ForeignKey(
                "procurement_centres.id", name="procurement_intents_centre_id_fkey"
            ),
            nullable=False,
        ),
        sa.Column(
            "crop_id",
            sa.UUID(),
            sa.ForeignKey("crops.id", name="procurement_intents_crop_id_fkey"),
            nullable=False,
        ),
        sa.Column(
            "land_holding_id",
            sa.UUID(),
            sa.ForeignKey(
                "farmer_land_holdings.id",
                name="procurement_intents_land_holding_id_fkey",
            ),
            nullable=False,
        ),
        sa.Column("expected_quantity_kg", sa.Numeric(), nullable=False),
        sa.Column("ready_date", sa.Date(), nullable=False),
        sa.Column("status", intent_status_enum, nullable=False),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            sa.UUID(),
            sa.ForeignKey("users.id", name="procurement_intents_created_by_fkey"),
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
        sa.UniqueConstraint(
            "farmer_id",
            "centre_id",
            "crop_id",
            "ready_date",
            name="uq_intent_slot",
        ),
    )
    op.create_index(
        "idx_procurement_intents_farmer_id",
        "procurement_intents",
        ["farmer_id"],
    )
    op.create_index(
        "idx_procurement_intents_centre_id",
        "procurement_intents",
        ["centre_id"],
    )
    op.create_index(
        "idx_procurement_intents_crop_id",
        "procurement_intents",
        ["crop_id"],
    )
    op.create_index(
        "uq_active_intent_slot",
        "procurement_intents",
        ["farmer_id", "centre_id", "crop_id", "ready_date"],
        unique=True,
        postgresql_where=sa.text(
            "status <> ALL (ARRAY["
            "'CANCELLED'::intent_status_enum, "
            "'REJECTED'::intent_status_enum, "
            "'COMPLETED'::intent_status_enum"
            "])"
        ),
    )

    # 3. Table: procurement_tokens
    op.create_table(
        "procurement_tokens",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "intent_id",
            sa.UUID(),
            sa.ForeignKey(
                "procurement_intents.id", name="procurement_tokens_intent_id_fkey"
            ),
            nullable=False,
        ),
        sa.Column(
            "centre_id",
            sa.UUID(),
            sa.ForeignKey(
                "procurement_centres.id", name="procurement_tokens_centre_id_fkey"
            ),
            nullable=False,
        ),
        sa.Column("token_number", sa.Integer(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", token_status_enum, nullable=False),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
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
        sa.UniqueConstraint(
            "centre_id",
            "scheduled_at",
            "token_number",
            name="uq_centre_schedule_token",
        ),
    )
    op.create_index(
        "idx_procurement_tokens_intent_id",
        "procurement_tokens",
        ["intent_id"],
    )
    op.create_index(
        "idx_procurement_tokens_centre_id",
        "procurement_tokens",
        ["centre_id"],
    )

    # 4. Table: procurement_records
    op.create_table(
        "procurement_records",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "intent_id",
            sa.UUID(),
            sa.ForeignKey(
                "procurement_intents.id", name="procurement_records_intent_id_fkey"
            ),
            nullable=False,
        ),
        sa.Column(
            "token_id",
            sa.UUID(),
            sa.ForeignKey(
                "procurement_tokens.id", name="procurement_records_token_id_fkey"
            ),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "counter_id",
            sa.UUID(),
            sa.ForeignKey("counters.id", name="procurement_records_counter_id_fkey"),
            nullable=False,
        ),
        sa.Column("actual_quantity_kg", sa.Numeric(), nullable=False),
        sa.Column("price_per_kg", sa.Numeric(), nullable=False),
        sa.Column("total_amount", sa.Numeric(), nullable=True),
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
    )
    op.create_index(
        "idx_procurement_records_intent_id",
        "procurement_records",
        ["intent_id"],
    )
    op.create_index(
        "idx_procurement_records_counter_id",
        "procurement_records",
        ["counter_id"],
    )

    # 5. Table: procurement_status_history
    op.create_table(
        "procurement_status_history",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "intent_id",
            sa.UUID(),
            sa.ForeignKey(
                "procurement_intents.id",
                name="procurement_status_history_intent_id_fkey",
            ),
            nullable=False,
        ),
        sa.Column(
            "token_id",
            sa.UUID(),
            sa.ForeignKey(
                "procurement_tokens.id", name="procurement_status_history_token_id_fkey"
            ),
            nullable=True,
        ),
        sa.Column("from_status", sa.Text(), nullable=False),
        sa.Column("to_status", sa.Text(), nullable=False),
        sa.Column(
            "changed_by",
            sa.UUID(),
            sa.ForeignKey(
                "users.id", name="procurement_status_history_changed_by_fkey"
            ),
            nullable=False,
        ),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "(token_id IS NOT NULL) OR (from_status = 'PENDING'::text) OR "
            "(to_status = ANY (ARRAY["
            "'APPROVED'::text, 'REJECTED'::text, 'CANCELLED'::text"
            "]))",
            name="chk_status_history_condition",
        ),
    )
    op.create_index(
        "idx_status_history_intent_id",
        "procurement_status_history",
        ["intent_id"],
    )


def downgrade() -> None:
    op.drop_table("procurement_status_history")
    op.drop_table("procurement_records")
    op.drop_table("procurement_tokens")
    op.drop_table("procurement_intents")
    sa.Enum(name="token_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="intent_status_enum").drop(op.get_bind(), checkfirst=True)
