"""rebuild products for platform catalog"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260718_06"
down_revision: str | None = "20260718_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("product_categories")
    op.drop_table("products")
    op.create_table(
        "products",
        sa.Column("platform_product_id", sa.String(100), nullable=False),
        sa.Column("canonical_slug", sa.String(220), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("short_description", sa.Text()),
        sa.Column("description_long", sa.Text()),
        sa.Column("category_l1", sa.String(150), nullable=False),
        sa.Column("category_l2", sa.String(150)),
        sa.Column("brand", sa.String(150)),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("tax_percent", sa.Numeric(6, 2), nullable=False),
        sa.Column("selling_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("mrp", sa.Numeric(12, 2), nullable=False),
        sa.Column("rating", sa.Numeric(3, 2), nullable=False),
        sa.Column("inventory_qty", sa.Integer(), nullable=False),
        sa.Column("stock_status", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("unit_value", sa.Numeric(12, 3), nullable=False),
        sa.Column("barcode", sa.String(100)),
        sa.Column("featured_score", sa.Numeric(8, 2), nullable=False),
        sa.Column("color_hex", sa.String(7)),
        sa.Column("supplier_user_id", sa.String(100)),
        sa.Column("image_url", sa.String(1000)),
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
        sa.UniqueConstraint("platform_product_id"),
        sa.UniqueConstraint("canonical_slug"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("barcode"),
    )
    for col in (
        "platform_product_id",
        "canonical_slug",
        "name",
        "category_l1",
        "category_l2",
        "brand",
        "stock_status",
        "is_active",
        "barcode",
        "featured_score",
        "supplier_user_id",
    ):
        op.create_index(f"ix_products_{col}", "products", [col])


def downgrade() -> None:
    op.drop_table("products")
