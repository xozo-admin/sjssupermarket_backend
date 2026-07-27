"""Make remaining hero content fields optional. Revision: 20260719_11."""

from alembic import op

revision = "20260719_11"
down_revision = "20260719_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("hero_slides", "button_text", nullable=True, server_default=None)
    op.alter_column("hero_slides", "button_url", nullable=True, server_default=None)


def downgrade() -> None:
    op.execute("UPDATE hero_slides SET button_text = 'Shop Now' WHERE button_text IS NULL")
    op.execute("UPDATE hero_slides SET button_url = '#products' WHERE button_url IS NULL")
    op.alter_column("hero_slides", "button_text", nullable=False, server_default="Shop Now")
    op.alter_column("hero_slides", "button_url", nullable=False, server_default="#products")
