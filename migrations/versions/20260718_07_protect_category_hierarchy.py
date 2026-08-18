"""Protect L1 categories that still contain L2 categories.

Revision ID: 20260718_07
Revises: 20260718_06
"""

from alembic import op

revision = "20260718_07"
down_revision = "20260718_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("fk_categories_parent_id_categories", "categories", type_="foreignkey")
    op.create_foreign_key(
        "fk_categories_parent_id_categories",
        "categories",
        "categories",
        ["parent_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_categories_parent_id_categories", "categories", type_="foreignkey")
    op.create_foreign_key(
        "fk_categories_parent_id_categories",
        "categories",
        "categories",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )


