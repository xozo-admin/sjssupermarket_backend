"""Add Razorpay references to POS sales.

Revision ID: 20260724_30
Revises: 20260724_29
"""

from alembic import op
import sqlalchemy as sa

revision = "20260724_30"
down_revision = "20260724_29"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "pos_sales",
        sa.Column("payment_status", sa.String(20), server_default="pending", nullable=False),
    )
    op.add_column("pos_sales", sa.Column("provider_order_id", sa.String(100), nullable=True))
    op.add_column("pos_sales", sa.Column("provider_payment_id", sa.String(100), nullable=True))
    op.add_column("pos_sales", sa.Column("provider_signature", sa.String(256), nullable=True))
    op.create_index("ix_pos_sales_payment_status", "pos_sales", ["payment_status"])
    op.create_index(
        "ix_pos_sales_provider_order_id", "pos_sales", ["provider_order_id"], unique=True
    )
    op.create_unique_constraint(
        "uq_pos_sales_provider_payment_id", "pos_sales", ["provider_payment_id"]
    )


def downgrade():
    op.drop_constraint("uq_pos_sales_provider_payment_id", "pos_sales", type_="unique")
    op.drop_index("ix_pos_sales_provider_order_id", table_name="pos_sales")
    op.drop_index("ix_pos_sales_payment_status", table_name="pos_sales")
    op.drop_column("pos_sales", "provider_signature")
    op.drop_column("pos_sales", "provider_payment_id")
    op.drop_column("pos_sales", "provider_order_id")
    op.drop_column("pos_sales", "payment_status")
