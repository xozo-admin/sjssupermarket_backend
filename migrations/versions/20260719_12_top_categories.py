"""Create homepage top category selection. Revision: 20260719_12."""

from alembic import op
import sqlalchemy as sa

revision = "20260719_12"
down_revision = "20260719_11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "homepage_top_categories",
        sa.Column("category_id", sa.Uuid(), nullable=False),
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
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_homepage_top_categories_category_id_categories"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_homepage_top_categories")),
        sa.UniqueConstraint("category_id", name=op.f("uq_homepage_top_categories_category_id")),
    )
    op.create_index(
        op.f("ix_homepage_top_categories_category_id"),
        "homepage_top_categories",
        ["category_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_homepage_top_categories_sort_order"),
        "homepage_top_categories",
        ["sort_order"],
        unique=False,
    )
    op.execute("""
        INSERT INTO homepage_top_categories (id, category_id, sort_order, created_at, updated_at)
        SELECT gen_random_uuid(), id, row_number() OVER (ORDER BY priority DESC, name) - 1, now(), now()
        FROM categories WHERE parent_id IS NULL
        ORDER BY priority DESC, name LIMIT 6
    """)


def downgrade() -> None:
    op.drop_index(
        op.f("ix_homepage_top_categories_sort_order"), table_name="homepage_top_categories"
    )
    op.drop_index(
        op.f("ix_homepage_top_categories_category_id"), table_name="homepage_top_categories"
    )
    op.drop_table("homepage_top_categories")
