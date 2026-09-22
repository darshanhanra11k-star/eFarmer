from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_intent_slot", "procurement_intents", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_intent_slot",
        "procurement_intents",
        ["farmer_id", "centre_id", "crop_id", "ready_date"],
    )
