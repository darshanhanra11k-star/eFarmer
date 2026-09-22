from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Table: allocation_runs
    op.create_table(
        "allocation_runs",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "centre_id",
            sa.UUID(),
            sa.ForeignKey(
                "procurement_centres.id",
                name="allocation_runs_centre_id_fkey",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "crop_id",
            sa.UUID(),
            sa.ForeignKey(
                "crops.id",
                name="allocation_runs_crop_id_fkey",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("allocation_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "centre_id",
            "crop_id",
            "allocation_date",
            name="uq_allocation_cycle",
        ),
    )
    op.create_index(
        "idx_allocation_runs_centre_id",
        "allocation_runs",
        ["centre_id"],
    )
    op.create_index(
        "idx_allocation_runs_crop_id",
        "allocation_runs",
        ["crop_id"],
    )
    op.create_index(
        "idx_allocation_runs_date",
        "allocation_runs",
        ["allocation_date"],
    )

    # 2. Table: allocation_decisions
    op.create_table(
        "allocation_decisions",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "allocation_run_id",
            sa.UUID(),
            sa.ForeignKey(
                "allocation_runs.id",
                name="allocation_decisions_run_id_fkey",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "intent_id",
            sa.UUID(),
            sa.ForeignKey(
                "procurement_intents.id",
                name="allocation_decisions_intent_id_fkey",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "farmer_id",
            sa.UUID(),
            sa.ForeignKey(
                "farmers.id",
                name="allocation_decisions_farmer_id_fkey",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("requested_quantity_kg", sa.Numeric(), nullable=False),
        sa.Column("allocated_quantity_kg", sa.Numeric(), nullable=False),
        sa.Column("remaining_capacity_kg", sa.Numeric(), nullable=False),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("ordering_reason", sa.Text(), nullable=False),
        sa.Column("tie_break_digest", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "allocation_run_id",
            "intent_id",
            name="uq_allocation_run_intent",
        ),
    )
    op.create_index(
        "idx_allocation_decisions_run_id",
        "allocation_decisions",
        ["allocation_run_id"],
    )
    op.create_index(
        "idx_allocation_decisions_intent_id",
        "allocation_decisions",
        ["intent_id"],
    )
    op.create_index(
        "idx_allocation_decisions_farmer_id",
        "allocation_decisions",
        ["farmer_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_allocation_decisions_farmer_id",
        table_name="allocation_decisions",
    )
    op.drop_index(
        "idx_allocation_decisions_intent_id",
        table_name="allocation_decisions",
    )
    op.drop_index(
        "idx_allocation_decisions_run_id",
        table_name="allocation_decisions",
    )
    op.drop_table("allocation_decisions")

    op.drop_index(
        "idx_allocation_runs_date",
        table_name="allocation_runs",
    )
    op.drop_index(
        "idx_allocation_runs_crop_id",
        table_name="allocation_runs",
    )
    op.drop_index(
        "idx_allocation_runs_centre_id",
        table_name="allocation_runs",
    )
    op.drop_table("allocation_runs")
