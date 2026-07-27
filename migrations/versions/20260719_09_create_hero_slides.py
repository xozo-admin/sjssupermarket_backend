"""Create dynamic homepage hero slides. Revision: 20260719_09."""

from alembic import op
import sqlalchemy as sa

revision = "20260719_09"
down_revision = "20260718_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hero_slides",
        sa.Column("subtitle", sa.String(length=180), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("badge_text", sa.String(length=120), nullable=True),
        sa.Column("button_text", sa.String(length=80), nullable=False, server_default="Shop Now"),
        sa.Column("button_url", sa.String(length=500), nullable=False, server_default="#products"),
        sa.Column("delivery_text", sa.String(length=100), nullable=True),
        sa.Column("image_url", sa.String(length=1000), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hero_slides")),
    )
    op.create_index(op.f("ix_hero_slides_active"), "hero_slides", ["active"], unique=False)
    op.create_index(op.f("ix_hero_slides_sort_order"), "hero_slides", ["sort_order"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_hero_slides_sort_order"), table_name="hero_slides")
    op.drop_index(op.f("ix_hero_slides_active"), table_name="hero_slides")
    op.drop_table("hero_slides")
