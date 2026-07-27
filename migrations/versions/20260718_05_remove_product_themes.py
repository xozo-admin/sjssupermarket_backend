"""remove product themes"""

from collections.abc import Sequence
from alembic import op

revision: str = "20260718_05"
down_revision: str | None = "20260718_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("products", "themes")


def downgrade() -> None:
    import sqlalchemy as sa

    op.add_column(
        "products",
        sa.Column("themes", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
