"""Add Razorpay checkout sessions.

Revision ID: 20260724_28
Revises: 20260724_27
"""

from alembic import op
import sqlalchemy as sa

revision = "20260724_28"
down_revision = "20260724_27"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_checkout_sessions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("address_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("provider_order_id", sa.String(100), nullable=False),
        sa.Column("provider_payment_id", sa.String(100), nullable=True),
        sa.Column("provider_signature", sa.String(256), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["address_id"], ["customer_addresses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_order_id"),
        sa.UniqueConstraint("provider_payment_id"),
    )
    op.create_index(
        "ix_payment_checkout_sessions_user_id", "payment_checkout_sessions", ["user_id"]
    )
    op.create_index(
        "ix_payment_checkout_sessions_address_id", "payment_checkout_sessions", ["address_id"]
    )
    op.create_index(
        "ix_payment_checkout_sessions_order_id", "payment_checkout_sessions", ["order_id"]
    )
    op.create_index(
        "ix_payment_checkout_sessions_provider_order_id",
        "payment_checkout_sessions",
        ["provider_order_id"],
    )
    op.create_index("ix_payment_checkout_sessions_status", "payment_checkout_sessions", ["status"])


def downgrade():
    op.drop_table("payment_checkout_sessions")
