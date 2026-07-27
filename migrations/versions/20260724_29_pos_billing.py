"""Add POS billing ledger.

Revision ID: 20260724_29
Revises: 20260724_28
"""

from alembic import op
import sqlalchemy as sa

revision = "20260724_29"
down_revision = "20260724_28"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pos_sales",
        sa.Column("invoice_number", sa.String(40), nullable=False),
        sa.Column("cashier_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("customer_name", sa.String(150), nullable=True),
        sa.Column("customer_mobile", sa.String(30), nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_method", sa.String(20), nullable=False),
        sa.Column("amount_tendered", sa.Numeric(12, 2), nullable=False),
        sa.Column("change_due", sa.Numeric(12, 2), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["cashier_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_number"),
    )
    op.create_index("ix_pos_sales_invoice_number", "pos_sales", ["invoice_number"])
    op.create_index("ix_pos_sales_cashier_id", "pos_sales", ["cashier_id"])
    op.create_index("ix_pos_sales_status", "pos_sales", ["status"])
    op.create_index("ix_pos_sales_customer_mobile", "pos_sales", ["customer_mobile"])
    op.create_table(
        "pos_sale_items",
        sa.Column("sale_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("barcode", sa.String(100), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_percent", sa.Numeric(6, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["sale_id"], ["pos_sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pos_sale_items_sale_id", "pos_sale_items", ["sale_id"])
    op.create_index("ix_pos_sale_items_product_id", "pos_sale_items", ["product_id"])


def downgrade():
    op.drop_table("pos_sale_items")
    op.drop_table("pos_sales")
