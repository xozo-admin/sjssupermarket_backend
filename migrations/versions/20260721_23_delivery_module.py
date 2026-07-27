"""delivery management module

Revision ID: 20260721_23
Revises: 20260721_22
"""

from alembic import op
import sqlalchemy as sa

revision = "20260721_23"
down_revision = "20260721_22"
branch_labels = None
depends_on = None


def common():
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade():
    op.create_table(
        "delivery_men",
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("mobile", sa.String(20), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("zone", sa.String(120), nullable=False),
        sa.Column("vehicle_type", sa.String(80), nullable=False),
        sa.Column("vehicle_number", sa.String(80), nullable=False),
        sa.Column("documents", sa.JSON(), nullable=False),
        sa.Column("bank_details", sa.JSON(), nullable=False),
        sa.Column("verification_status", sa.String(30), nullable=False),
        sa.Column("delivery_status", sa.String(30), nullable=False),
        sa.Column("online", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("blocked", sa.Boolean(), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("total_deliveries", sa.Integer(), nullable=False),
        sa.Column("completed_orders", sa.Integer(), nullable=False),
        sa.Column("cancelled_orders", sa.Integer(), nullable=False),
        sa.Column("failed_orders", sa.Integer(), nullable=False),
        sa.Column("average_delivery_minutes", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        *common(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mobile"),
        sa.UniqueConstraint("email"),
    )
    for name in [
        "mobile",
        "email",
        "zone",
        "vehicle_type",
        "verification_status",
        "delivery_status",
        "online",
        "active",
        "blocked",
    ]:
        op.create_index(f"ix_delivery_men_{name}", "delivery_men", [name])
    op.add_column("orders", sa.Column("delivery_man_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_orders_delivery_man_id",
        "orders",
        "delivery_men",
        ["delivery_man_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_orders_delivery_man_id", "orders", ["delivery_man_id"])
    op.create_table(
        "delivery_attendance",
        sa.Column("delivery_man_id", sa.Uuid(), nullable=False),
        sa.Column("login_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("logout_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("online_minutes", sa.Integer(), nullable=False),
        *common(),
        sa.ForeignKeyConstraint(["delivery_man_id"], ["delivery_men.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_delivery_attendance_delivery_man_id", "delivery_attendance", ["delivery_man_id"]
    )
    op.create_table(
        "delivery_earnings",
        sa.Column("delivery_man_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("cash_collected", sa.Numeric(12, 2), nullable=False),
        sa.Column("online_payment", sa.Numeric(12, 2), nullable=False),
        sa.Column("settlement_status", sa.String(30), nullable=False),
        *common(),
        sa.ForeignKeyConstraint(["delivery_man_id"], ["delivery_men.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_delivery_earnings_delivery_man_id", "delivery_earnings", ["delivery_man_id"]
    )
    op.create_table(
        "delivery_leaves",
        sa.Column("delivery_man_id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("admin_note", sa.Text(), nullable=True),
        *common(),
        sa.ForeignKeyConstraint(["delivery_man_id"], ["delivery_men.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_delivery_leaves_delivery_man_id", "delivery_leaves", ["delivery_man_id"])
    op.create_table(
        "delivery_notifications",
        sa.Column("delivery_man_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        *common(),
        sa.ForeignKeyConstraint(["delivery_man_id"], ["delivery_men.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "delivery_activity_logs",
        sa.Column("delivery_man_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        *common(),
        sa.ForeignKeyConstraint(["delivery_man_id"], ["delivery_men.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_delivery_activity_logs_delivery_man_id", "delivery_activity_logs", ["delivery_man_id"]
    )


def downgrade():
    op.drop_constraint("fk_orders_delivery_man_id", "orders", type_="foreignkey")
    op.drop_column("orders", "delivery_man_id")
    for t in [
        "delivery_activity_logs",
        "delivery_notifications",
        "delivery_leaves",
        "delivery_earnings",
        "delivery_attendance",
        "delivery_men",
    ]:
        op.drop_table(t)
