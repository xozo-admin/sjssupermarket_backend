"""create users

Revision ID: 20260721_18
Revises: 20260720_17
"""

from alembic import op
import sqlalchemy as sa

revision = "20260721_18"
down_revision = "20260720_17"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("mobile", sa.String(20), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("mobile"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_mobile", "users", ["mobile"])
    op.create_index("ix_users_role", "users", ["role"])


def downgrade():
    op.drop_table("users")
