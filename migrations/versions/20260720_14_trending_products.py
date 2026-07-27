"""Create homepage trending product selection. Revision: 20260720_14."""

from alembic import op
import sqlalchemy as sa

revision = "20260720_14"
down_revision = "20260720_13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "homepage_trending_products",
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
            name=op.f("fk_homepage_trending_products_product_id_products"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_homepage_trending_products")),
        sa.UniqueConstraint("product_id", name=op.f("uq_homepage_trending_products_product_id")),
    )
    op.create_index(
        op.f("ix_homepage_trending_products_product_id"),
        "homepage_trending_products",
        ["product_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_homepage_trending_products_sort_order"),
        "homepage_trending_products",
        ["sort_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_homepage_trending_products_sort_order"), table_name="homepage_trending_products"
    )
    op.drop_index(
        op.f("ix_homepage_trending_products_product_id"), table_name="homepage_trending_products"
    )
    op.drop_table("homepage_trending_products")
