"""Create homepage weekly deals. Revision: 20260720_16."""

from alembic import op
import sqlalchemy as sa

revision = "20260720_16"
down_revision = "20260720_15"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "homepage_weekly_deals",
        sa.Column("product_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_homepage_weekly_deals_product_id_products"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_homepage_weekly_deals")),
        sa.UniqueConstraint("product_id", name=op.f("uq_homepage_weekly_deals_product_id")),
    )
    op.create_index(
        op.f("ix_homepage_weekly_deals_product_id"),
        "homepage_weekly_deals",
        ["product_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_homepage_weekly_deals_sort_order"),
        "homepage_weekly_deals",
        ["sort_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_homepage_weekly_deals_sort_order"), table_name="homepage_weekly_deals")
    op.drop_index(op.f("ix_homepage_weekly_deals_product_id"), table_name="homepage_weekly_deals")
    op.drop_table("homepage_weekly_deals")
