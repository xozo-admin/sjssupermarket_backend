"""Staff RBAC and supplier procurement.
Revision ID: 20260724_31
Revises: 20260724_30
"""

from alembic import op
import sqlalchemy as sa

revision = "20260724_31"
down_revision = "20260724_30"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("designation", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("permissions", sa.JSON(), server_default="[]", nullable=False))
    op.create_table(
        "suppliers",
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("contact_person", sa.String(120)),
        sa.Column("email", sa.String(255)),
        sa.Column("mobile", sa.String(30), nullable=False),
        sa.Column("gst_number", sa.String(40)),
        sa.Column("address", sa.Text()),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_suppliers_name", "suppliers", ["name"])
    op.create_index("ix_suppliers_mobile", "suppliers", ["mobile"])
    op.create_index("ix_suppliers_active", "suppliers", ["active"])
    op.create_table(
        "purchase_orders",
        sa.Column("po_number", sa.String(40), nullable=False, unique=True),
        sa.Column(
            "supplier_id",
            sa.Uuid(),
            sa.ForeignKey("suppliers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("payment_status", sa.String(20), nullable=False),
        sa.Column("expected_date", sa.String(10)),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_purchase_orders_po_number", "purchase_orders", ["po_number"])
    op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])
    op.create_index("ix_purchase_orders_status", "purchase_orders", ["status"])
    op.create_index("ix_purchase_orders_payment_status", "purchase_orders", ["payment_status"])
    op.create_table(
        "purchase_order_items",
        sa.Column(
            "purchase_order_id",
            sa.Uuid(),
            sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Uuid(),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("received_quantity", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_percent", sa.Numeric(6, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_purchase_order_items_purchase_order_id", "purchase_order_items", ["purchase_order_id"]
    )
    op.create_index("ix_purchase_order_items_product_id", "purchase_order_items", ["product_id"])


def downgrade():
    op.drop_table("purchase_order_items")
    op.drop_table("purchase_orders")
    op.drop_table("suppliers")
    op.drop_column("users", "permissions")
    op.drop_column("users", "designation")
