"""Shipping zone configuration.

Revision ID: 20260727_32
Revises: 20260724_31
"""

from alembic import op
import sqlalchemy as sa

revision = "20260727_32"
down_revision = "20260724_31"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "shipping_zone_configurations",
        sa.Column("store_name", sa.String(160), nullable=False),
        sa.Column("store_address", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("radius_km", sa.Float(), nullable=False),
        sa.Column("delivery_fee", sa.Numeric(10, 2), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade():
    op.drop_table("shipping_zone_configurations")
