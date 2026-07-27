"""Archive products referenced by order history.

Revision ID: 20260724_27
Revises: 20260722_26
"""

from alembic import op
import sqlalchemy as sa

revision = "20260724_27"
down_revision = "20260722_26"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "products",
        sa.Column("archived", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index("ix_products_archived", "products", ["archived"])


def downgrade():
    op.drop_index("ix_products_archived", table_name="products")
    op.drop_column("products", "archived")
