"""remove category themes"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260717_02"
down_revision: str | None = "20260717_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("categories", "themes")


def downgrade() -> None:
    op.add_column(
        "categories",
        sa.Column("themes", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
