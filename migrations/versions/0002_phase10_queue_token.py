from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "queues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("centre_id", sa.Uuid(), nullable=False),
        sa.Column("crop_id", sa.Uuid(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.String(),
            server_default="OPEN",
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_queues")),
        sa.ForeignKeyConstraint(
            ["centre_id"],
            ["procurement_centres.id"],
            name=op.f("fk_queues_centre_id_procurement_centres"),
        ),
        sa.ForeignKeyConstraint(
            ["crop_id"],
            ["crops.id"],
            name=op.f("fk_queues_crop_id_crops"),
        ),
        sa.UniqueConstraint(
            "centre_id",
            "date",
            "crop_id",
            name="uq_queues_centre_date_crop",
        ),
    )
    op.create_index(
        op.f("ix_queues_centre_id"),
        "queues",
        ["centre_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_queues_crop_id"),
        "queues",
        ["crop_id"],
        unique=False,
    )

    op.create_table(
        "queue_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("queue_id", sa.Uuid(), nullable=False),
        sa.Column("farmer_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(),
            server_default="CHECK_IN",
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_queue_entries")),
        sa.ForeignKeyConstraint(
            ["queue_id"],
            ["queues.id"],
            name=op.f("fk_queue_entries_queue_id_queues"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["farmer_id"],
            ["farmers.id"],
            name=op.f("fk_queue_entries_farmer_id_farmers"),
        ),
        sa.UniqueConstraint(
            "queue_id",
            "position",
            name="uq_queue_entries_queue_position",
        ),
    )
    op.create_index(
        op.f("ix_queue_entries_queue_id"),
        "queue_entries",
        ["queue_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_queue_entries_farmer_id"),
        "queue_entries",
        ["farmer_id"],
        unique=False,
    )

    op.create_table(
        "tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token_number", sa.String(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("queue_id", sa.Uuid(), nullable=False),
        sa.Column("queue_entry_id", sa.Uuid(), nullable=False),
        sa.Column("farmer_id", sa.Uuid(), nullable=False),
        sa.Column("counter_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.String(),
            server_default="WAITING",
            nullable=False,
        ),
        sa.Column("called_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "processing_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tokens")),
        sa.ForeignKeyConstraint(
            ["queue_id"],
            ["queues.id"],
            name=op.f("fk_tokens_queue_id_queues"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["queue_entry_id"],
            ["queue_entries.id"],
            name=op.f("fk_tokens_queue_entry_id_queue_entries"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["farmer_id"],
            ["farmers.id"],
            name=op.f("fk_tokens_farmer_id_farmers"),
        ),
        sa.ForeignKeyConstraint(
            ["counter_id"],
            ["counters.id"],
            name=op.f("fk_tokens_counter_id_counters"),
        ),
        sa.UniqueConstraint(
            "queue_entry_id",
            name=op.f("uq_tokens_queue_entry_id"),
        ),
        sa.UniqueConstraint(
            "queue_id",
            "sequence_number",
            name="uq_tokens_queue_sequence",
        ),
        sa.UniqueConstraint(
            "queue_id",
            "token_number",
            name="uq_tokens_queue_token_number",
        ),
    )
    op.create_index(
        op.f("ix_tokens_queue_id"),
        "tokens",
        ["queue_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tokens_queue_entry_id"),
        "tokens",
        ["queue_entry_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_tokens_farmer_id"),
        "tokens",
        ["farmer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tokens_counter_id"),
        "tokens",
        ["counter_id"],
        unique=False,
    )
    op.create_index(
        "uq_active_farmer_token",
        "tokens",
        ["farmer_id", "queue_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('CHECK_IN', 'TOKEN', 'WAITING', 'CALLED', 'PROCESSING')"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_active_farmer_token", table_name="tokens")
    op.drop_index(op.f("ix_tokens_counter_id"), table_name="tokens")
    op.drop_index(op.f("ix_tokens_farmer_id"), table_name="tokens")
    op.drop_index(op.f("ix_tokens_queue_entry_id"), table_name="tokens")
    op.drop_index(op.f("ix_tokens_queue_id"), table_name="tokens")
    op.drop_table("tokens")

    op.drop_index(op.f("ix_queue_entries_farmer_id"), table_name="queue_entries")
    op.drop_index(op.f("ix_queue_entries_queue_id"), table_name="queue_entries")
    op.drop_table("queue_entries")

    op.drop_index(op.f("ix_queues_crop_id"), table_name="queues")
    op.drop_index(op.f("ix_queues_centre_id"), table_name="queues")
    op.drop_table("queues")
