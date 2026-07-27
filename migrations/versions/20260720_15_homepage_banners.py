"""Create homepage banners. Revision: 20260720_15."""

from alembic import op
import sqlalchemy as sa

revision = "20260720_15"
down_revision = "20260720_14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "homepage_banners",
        sa.Column("section_key", sa.String(50), nullable=False),
        sa.Column("eyebrow", sa.String(120), nullable=True),
        sa.Column("title", sa.String(240), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("button_text", sa.String(80), nullable=True),
        sa.Column("button_url", sa.String(500), nullable=True),
        sa.Column("image_url", sa.String(1000), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_homepage_banners")),
        sa.UniqueConstraint("section_key", name=op.f("uq_homepage_banners_section_key")),
    )
    op.create_index(
        op.f("ix_homepage_banners_section_key"), "homepage_banners", ["section_key"], unique=True
    )
    op.create_index(
        op.f("ix_homepage_banners_active"), "homepage_banners", ["active"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_homepage_banners_active"), table_name="homepage_banners")
    op.drop_index(op.f("ix_homepage_banners_section_key"), table_name="homepage_banners")
    op.drop_table("homepage_banners")
