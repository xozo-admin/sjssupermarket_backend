"""Store only R2 image filenames. Revision: 20260718_08."""

from alembic import op

revision = "20260718_08"
down_revision = "20260718_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """UPDATE products SET image_url = CASE WHEN image_url IS NULL OR btrim(image_url) = '' THEN canonical_slug || '.webp' ELSE regexp_replace(split_part(image_url, '?', 1), '^.*/', '') END"""
    )


def downgrade() -> None:
    pass

