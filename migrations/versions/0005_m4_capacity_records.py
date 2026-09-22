from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "capacity_records",
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
                name="capacity_records_centre_id_fkey",
            ),
            nullable=False,
        ),
        sa.Column(
            "crop_id",
            sa.UUID(),
            sa.ForeignKey(
                "crops.id",
                name="capacity_records_crop_id_fkey",
            ),
            nullable=False,
        ),
        sa.Column(
            "date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "total_capacity_kg",
            sa.Numeric(),
            nullable=False,
        ),
        sa.Column(
            "allocated_quantity_kg",
            sa.Numeric(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "procured_quantity_kg",
            sa.Numeric(),
            server_default=sa.text("0"),
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
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "centre_id",
            "crop_id",
            "date",
            name="uq_centre_crop_date",
        ),
        sa.CheckConstraint(
            "total_capacity_kg >= 0 AND "
            "allocated_quantity_kg >= 0 AND "
            "procured_quantity_kg >= 0",
            name="chk_capacity_non_negative",
        ),
        sa.CheckConstraint(
            "allocated_quantity_kg <= total_capacity_kg AND "
            "procured_quantity_kg <= allocated_quantity_kg",
            name="chk_capacity_not_exceeded",
        ),
    )
    op.create_index(
        "idx_capacity_records_centre_id",
        "capacity_records",
        ["centre_id"],
    )
    op.create_index(
        "idx_capacity_records_crop_id",
        "capacity_records",
        ["crop_id"],
    )
    op.create_index(
        "idx_capacity_records_date",
        "capacity_records",
        ["date"],
    )


def downgrade() -> None:
    op.drop_index("idx_capacity_records_date", table_name="capacity_records")
    op.drop_index("idx_capacity_records_crop_id", table_name="capacity_records")
    op.drop_index("idx_capacity_records_centre_id", table_name="capacity_records")
    op.drop_table("capacity_records")
