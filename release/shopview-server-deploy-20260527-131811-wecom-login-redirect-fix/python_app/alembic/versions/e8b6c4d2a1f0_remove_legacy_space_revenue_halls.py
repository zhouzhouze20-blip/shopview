"""remove legacy space revenue and hall tables

Revision ID: e8b6c4d2a1f0
Revises: d2f4a6b8c0e2
Create Date: 2026-05-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8b6c4d2a1f0"
down_revision: Union[str, Sequence[str], None] = "d2f4a6b8c0e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM decoration_project_spaces WHERE space_type = 'HALL'")
    op.execute("ALTER TABLE decoration_project_spaces DROP CONSTRAINT IF EXISTS ck_decoration_project_spaces_target_ref")
    op.execute("ALTER TABLE decoration_project_spaces DROP CONSTRAINT IF EXISTS ck_decoration_project_spaces_space_type")
    op.execute("ALTER TABLE decoration_project_spaces DROP CONSTRAINT IF EXISTS decoration_project_spaces_hall_id_fkey")
    op.execute("DROP INDEX IF EXISTS ix_decoration_project_spaces_hall_id")
    op.execute("ALTER TABLE decoration_project_spaces DROP COLUMN IF EXISTS hall_id")
    op.create_check_constraint(
        "ck_decoration_project_spaces_space_type",
        "decoration_project_spaces",
        "space_type IN ('UNIT')",
    )
    op.create_check_constraint(
        "ck_decoration_project_spaces_target_ref",
        "decoration_project_spaces",
        "space_type = 'UNIT' AND business_unit_id IS NOT NULL",
    )

    op.execute("DROP TABLE IF EXISTS hall_group_bindings")
    op.execute("DROP TABLE IF EXISTS halls")

    op.execute("DROP TABLE IF EXISTS order_items")
    op.execute("DROP TABLE IF EXISTS orders")
    op.execute("DROP TABLE IF EXISTS sales_profits")
    op.execute("DROP TABLE IF EXISTS fees")
    op.execute("DROP TABLE IF EXISTS revenue_data")


def downgrade() -> None:
    op.execute("ALTER TABLE decoration_project_spaces DROP CONSTRAINT IF EXISTS ck_decoration_project_spaces_target_ref")
    op.execute("ALTER TABLE decoration_project_spaces DROP CONSTRAINT IF EXISTS ck_decoration_project_spaces_space_type")
    op.add_column("decoration_project_spaces", sa.Column("hall_id", sa.Integer(), nullable=True, comment="厅房ID"))
    op.create_index("ix_decoration_project_spaces_hall_id", "decoration_project_spaces", ["hall_id"])
    op.create_check_constraint(
        "ck_decoration_project_spaces_space_type",
        "decoration_project_spaces",
        "space_type IN ('HALL','UNIT')",
    )
    op.create_check_constraint(
        "ck_decoration_project_spaces_target_ref",
        "decoration_project_spaces",
        "(space_type = 'HALL' AND hall_id IS NOT NULL AND business_unit_id IS NULL) OR "
        "(space_type = 'UNIT' AND business_unit_id IS NOT NULL AND hall_id IS NULL)",
    )

    op.create_table(
        "halls",
        sa.Column("hall_id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("hall_code", sa.String(length=20), nullable=False),
        sa.Column("hall_name", sa.String(length=200), nullable=True),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("floor_id", sa.BigInteger(), nullable=False),
        sa.Column("counter_number", sa.String(length=20), nullable=False),
        sa.Column("area", sa.Numeric(10, 2), nullable=True),
        sa.Column("shape_type", sa.String(length=20), nullable=True),
        sa.Column("position_data", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["stores.store_id"]),
        sa.ForeignKeyConstraint(["floor_id"], ["floors.id"]),
        sa.UniqueConstraint("hall_code"),
    )
    op.create_index("ix_halls_hall_id", "halls", ["hall_id"])
    op.create_foreign_key(
        "decoration_project_spaces_hall_id_fkey",
        "decoration_project_spaces",
        "halls",
        ["hall_id"],
        ["hall_id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "hall_group_bindings",
        sa.Column("binding_id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("hall_id", sa.Integer(), nullable=False),
        sa.Column("group_code", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("bound_at", sa.DateTime(), nullable=True),
        sa.Column("bound_by", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["hall_id"], ["halls.hall_id"]),
    )
    op.create_index("ix_hall_group_bindings_binding_id", "hall_group_bindings", ["binding_id"])

    op.create_table(
        "revenue_data",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("counter_id", sa.Integer(), nullable=False),
        sa.Column("counter_code", sa.String(length=20), nullable=True),
        sa.Column("counter_name", sa.String(length=100), nullable=True),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("store_name", sa.String(length=100), nullable=True),
        sa.Column("floor_id", sa.Integer(), nullable=True),
        sa.Column("floor_name", sa.String(length=50), nullable=True),
        sa.Column("area", sa.Numeric(10, 2), nullable=True),
        sa.Column("monthly_revenue", sa.Numeric(10, 2), nullable=True),
        sa.Column("daily_revenue", sa.Numeric(10, 2), nullable=True),
        sa.Column("revenue_per_sqm", sa.Numeric(10, 2), nullable=True),
        sa.Column("report_date", sa.Date(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("month", sa.Integer(), nullable=True),
        sa.Column("day", sa.Integer(), nullable=True),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
