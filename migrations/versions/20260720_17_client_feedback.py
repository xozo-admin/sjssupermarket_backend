"""Create client feedback. Revision: 20260720_17."""

from alembic import op
import sqlalchemy as sa

revision = "20260720_17"
down_revision = "20260720_16"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_feedback",
        sa.Column("client_name", sa.String(120), nullable=False),
        sa.Column("client_role", sa.String(120), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("avatar_url", sa.String(1000), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_client_feedback")),
    )
    op.create_index(op.f("ix_client_feedback_active"), "client_feedback", ["active"], unique=False)
    op.create_index(
        op.f("ix_client_feedback_sort_order"), "client_feedback", ["sort_order"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_client_feedback_sort_order"), table_name="client_feedback")
    op.drop_index(op.f("ix_client_feedback_active"), table_name="client_feedback")
    op.drop_table("client_feedback")
