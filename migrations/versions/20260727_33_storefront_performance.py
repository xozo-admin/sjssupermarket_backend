"""Add indexes for public storefront queries.

Revision ID: 20260727_33
Revises: 20260727_32
"""

from alembic import op

revision = "20260727_33"
down_revision = "20260727_32"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_hero_slides_active_sort_created",
        "hero_slides",
        ["active", "sort_order", "created_at"],
    )
    op.create_index(
        "ix_client_feedback_active_sort_created",
        "client_feedback",
        ["active", "sort_order", "created_at"],
    )
    op.create_index(
        "ix_categories_priority_name",
        "categories",
        ["priority", "name"],
    )
    op.create_index(
        "ix_products_archived_category_l1",
        "products",
        ["archived", "category_l1"],
    )
    op.create_index(
        "ix_products_archived_category_l2",
        "products",
        ["archived", "category_l2"],
    )


def downgrade() -> None:
    op.drop_index("ix_products_archived_category_l2", table_name="products")
    op.drop_index("ix_products_archived_category_l1", table_name="products")
    op.drop_index("ix_categories_priority_name", table_name="categories")
    op.drop_index("ix_client_feedback_active_sort_created", table_name="client_feedback")
    op.drop_index("ix_hero_slides_active_sort_created", table_name="hero_slides")
