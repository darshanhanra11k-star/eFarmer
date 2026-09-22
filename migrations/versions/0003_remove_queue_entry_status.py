from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("queue_entries", "status")


def downgrade() -> None:
    op.add_column(
        "queue_entries",
        sa.Column(
            "status",
            sa.String(),
            server_default="WAITING",
            nullable=False,
        ),
    )
    op.alter_column("queue_entries", "status", server_default=None)
