"""Firebase push notification devices

Revision ID: 20260722_24
Revises: 20260721_23
"""

from alembic import op
import sqlalchemy as sa

revision = "20260722_24"
down_revision = "20260721_23"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "push_devices",
        sa.Column("token", sa.String(4096), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("app_kind", sa.String(20), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("delivery_man_id", sa.Uuid(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["delivery_man_id"], ["delivery_men.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    for column in ["token", "app_kind", "user_id", "delivery_man_id", "active"]:
        op.create_index(f"ix_push_devices_{column}", "push_devices", [column])


def downgrade():
    op.drop_table("push_devices")
