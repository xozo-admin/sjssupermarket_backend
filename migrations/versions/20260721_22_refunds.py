"""create refunds

Revision ID: 20260721_22
Revises: 20260721_21
"""

from alembic import op
import sqlalchemy as sa

revision = "20260721_22"
down_revision = "20260721_21"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "refund_configurations",
        sa.Column("allowed_days", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "refund_requests",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("order_item_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_item_id"),
    )
    op.create_index("ix_refund_requests_user_id", "refund_requests", ["user_id"])
    op.create_index("ix_refund_requests_order_id", "refund_requests", ["order_id"])
    op.create_index(
        "ix_refund_requests_order_item_id", "refund_requests", ["order_item_id"], unique=True
    )
    op.create_index("ix_refund_requests_status", "refund_requests", ["status"])


def downgrade():
    op.drop_table("refund_requests")
    op.drop_table("refund_configurations")
