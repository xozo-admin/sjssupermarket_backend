"""create customer addresses

Revision ID: 20260721_19
Revises: 20260721_18
"""

from alembic import op
import sqlalchemy as sa

revision = "20260721_19"
down_revision = "20260721_18"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "customer_addresses",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("mobile", sa.String(20), nullable=False),
        sa.Column("street", sa.String(300), nullable=False),
        sa.Column("locality", sa.String(180), nullable=True),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("state", sa.String(120), nullable=False),
        sa.Column("pincode", sa.String(20), nullable=False),
        sa.Column("landmark", sa.String(180), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_addresses_user_id", "customer_addresses", ["user_id"])
    op.create_index("ix_customer_addresses_is_default", "customer_addresses", ["is_default"])


def downgrade():
    op.drop_table("customer_addresses")
