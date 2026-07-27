"""COD delivery confirmation and proof

Revision ID: 20260722_25
Revises: 20260722_24
"""

from alembic import op
import sqlalchemy as sa

revision = "20260722_25"
down_revision = "20260722_24"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("delivery_otp", sa.String(6), nullable=True))
    op.add_column(
        "orders",
        sa.Column("cod_collected", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("orders", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("delivery_proof_url", sa.String(500), nullable=True))


def downgrade():
    for column in ["delivery_proof_url", "delivered_at", "cod_collected", "delivery_otp"]:
        op.drop_column("orders", column)
