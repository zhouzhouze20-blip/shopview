"""create merchant planning tables

Revision ID: 6f7a8b9c0d1e
Revises: c9d0e1f2a3b4
Create Date: 2026-06-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6f7a8b9c0d1e"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "merchant_planning_projects",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("store_id", sa.String(20), nullable=True),
        sa.Column("floor_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("scope_type", sa.String(30), nullable=False, server_default="FLOOR"),
        sa.Column("target_description", sa.Text(), nullable=True),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("current_annual_revenue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estimated_annual_revenue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estimated_lift_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estimated_lift_rate", sa.Numeric(8, 4), nullable=True),
        sa.Column("total_area", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("scope_type IN ('FLOOR','MULTI_FLOOR','AREA')", name="ck_mpp_scope_type"),
        sa.CheckConstraint("status IN ('DRAFT','ACTIVE','COMPLETED','CANCELLED')", name="ck_mpp_status"),
    )
    op.create_index("idx_mpp_store_status", "merchant_planning_projects", ["store_id", "status"])

    op.create_table(
        "merchant_opportunities",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.BigInteger(), sa.ForeignKey("merchant_planning_projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_type", sa.String(30), nullable=False, server_default="MANUAL"),
        sa.Column("store_id", sa.String(20), nullable=True),
        sa.Column("floor_id", sa.BigInteger(), nullable=True),
        sa.Column("unit_id", sa.BigInteger(), nullable=True),
        sa.Column("unit_code", sa.String(100), nullable=True),
        sa.Column("unit_area", sa.Numeric(12, 2), nullable=True),
        sa.Column("current_brand", sa.String(200), nullable=True),
        sa.Column("current_contract_id", sa.String(100), nullable=True),
        sa.Column("current_annual_revenue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("target_category", sa.String(100), nullable=True),
        sa.Column("target_brand", sa.String(200), nullable=True),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="TODO"),
        sa.Column("expected_sign_date", sa.Date(), nullable=True),
        sa.Column("priority", sa.String(10), nullable=False, server_default="P2"),
        sa.Column("estimated_annual_revenue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estimated_lift_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("source_type IN ('REVENUE_MAP','MANUAL','PROJECT')", name="ck_mo_source_type"),
        sa.CheckConstraint("status IN ('TODO','NEGOTIATING','SIGNED','ABANDONED')", name="ck_mo_status"),
        sa.CheckConstraint("priority IN ('P0','P1','P2')", name="ck_mo_priority"),
    )
    op.create_index("idx_mo_project", "merchant_opportunities", ["project_id"])
    op.create_index("idx_mo_unit", "merchant_opportunities", ["unit_id"])
    op.create_index("idx_mo_store_floor_status", "merchant_opportunities", ["store_id", "floor_id", "status"])

    op.create_table(
        "merchant_calculation_scenarios",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("opportunity_id", sa.BigInteger(), sa.ForeignKey("merchant_opportunities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cooperation_mode", sa.String(30), nullable=False),
        sa.Column("monthly_rent", sa.Numeric(14, 2), nullable=True),
        sa.Column("rent_unit_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("commission_rate", sa.Numeric(8, 4), nullable=True),
        sa.Column("guaranteed_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("expected_monthly_sales", sa.Numeric(14, 2), nullable=True),
        sa.Column("manual_monthly_revenue", sa.Numeric(14, 2), nullable=True),
        sa.Column("decoration_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vacancy_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contract_start_date", sa.Date(), nullable=True),
        sa.Column("contract_end_date", sa.Date(), nullable=True),
        sa.Column("estimated_monthly_revenue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estimated_annual_revenue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estimated_lift_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("calculation_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("cooperation_mode IN ('LEASE','JOINT_OPERATION','OTHER')", name="ck_mcs_cooperation_mode"),
    )
    op.create_index("idx_mcs_opportunity", "merchant_calculation_scenarios", ["opportunity_id"])

    op.create_table(
        "merchant_follow_ups",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("opportunity_id", sa.BigInteger(), sa.ForeignKey("merchant_opportunities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("follow_up_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("follow_up_type", sa.String(50), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_mfu_opportunity", "merchant_follow_ups", ["opportunity_id"])


def downgrade() -> None:
    op.drop_table("merchant_follow_ups")
    op.drop_table("merchant_calculation_scenarios")
    op.drop_table("merchant_opportunities")
    op.drop_table("merchant_planning_projects")
