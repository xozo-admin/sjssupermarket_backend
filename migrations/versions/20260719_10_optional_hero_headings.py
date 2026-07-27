"""Make hero title and subtitle optional. Revision: 20260719_10."""

from alembic import op

revision = "20260719_10"
down_revision = "20260719_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("hero_slides", "subtitle", nullable=True)
    op.alter_column("hero_slides", "title", nullable=True)


def downgrade() -> None:
    op.execute("UPDATE hero_slides SET subtitle = '' WHERE subtitle IS NULL")
    op.execute("UPDATE hero_slides SET title = '' WHERE title IS NULL")
    op.alter_column("hero_slides", "subtitle", nullable=False)
    op.alter_column("hero_slides", "title", nullable=False)
