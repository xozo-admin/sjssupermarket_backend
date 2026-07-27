"""catalog management and products"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260718_03"
down_revision: str | None = "20260717_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def named_table(name: str) -> None:
    op.create_table(
        name,
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(f"ix_{name}_name", name, ["name"])
    op.create_index(f"ix_{name}_active", name, ["active"])


def upgrade() -> None:
    for name in ("variations", "units", "taxes"):
        named_table(name)
    op.create_table(
        "brands",
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("image_url", sa.String(500)),
        sa.Column("meta_title", sa.String(170)),
        sa.Column("meta_description", sa.Text()),
        sa.Column("meta_image_url", sa.String(500)),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_brands_name", "brands", ["name"])
    op.create_index("ix_brands_active", "brands", ["active"])
    op.create_table(
        "products",
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(220), nullable=False),
        sa.Column("short_description", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("thumbnail_url", sa.String(500)),
        sa.Column("gallery_urls", sa.JSON(), nullable=False),
        sa.Column("youtube_url", sa.String(500)),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("brand_id", sa.Uuid()),
        sa.Column("unit_id", sa.Uuid()),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("has_variations", sa.Boolean(), nullable=False),
        sa.Column("variations", sa.JSON(), nullable=False),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_type", sa.String(20), nullable=False),
        sa.Column("discount_start", sa.String(30)),
        sa.Column("discount_end", sa.String(30)),
        sa.Column("minimum_purchase", sa.Integer(), nullable=False),
        sa.Column("maximum_purchase", sa.Integer(), nullable=False),
        sa.Column("tax_configuration", sa.JSON(), nullable=False),
        sa.Column("sell_target", sa.Integer()),
        sa.Column("published", sa.Boolean(), nullable=False),
        sa.Column("featured", sa.Boolean(), nullable=False),
        sa.Column("meta_title", sa.String(170)),
        sa.Column("meta_description", sa.Text()),
        sa.Column("meta_image_url", sa.String(500)),
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
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("sku"),
        sa.UniqueConstraint("code"),
    )
    for column in ("name", "slug", "sku", "code", "published", "featured"):
        op.create_index(f"ix_products_{column}", "products", [column])
    op.create_table(
        "product_categories",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("product_id", "category_id"),
    )


def downgrade() -> None:
    op.drop_table("product_categories")
    op.drop_table("products")
    op.drop_table("brands")
    for name in ("taxes", "units", "variations"):
        op.drop_table(name)
