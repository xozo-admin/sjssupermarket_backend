"""add product themes"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260718_04"
down_revision: str | None = "20260718_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("themes", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )


def downgrade() -> None:
    op.drop_column("products", "themes")
