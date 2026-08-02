"""create category manager performance tables

Revision ID: h6c7d8e9f0a1
Revises: g5b6c7d8e9f0
Create Date: 2026-07-24
"""
from typing import Sequence, Union

from alembic import op


revision: str = "h6c7d8e9f0a1"
down_revision: Union[str, Sequence[str], None] = "g5b6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS category_manager_brand_assignments (
            id BIGSERIAL PRIMARY KEY,
            store_id INTEGER NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
            group_code VARCHAR(50) NOT NULL,
            manager_user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
            manager_name VARCHAR(100) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
            updated_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_category_manager_brand_store_group UNIQUE (store_id, group_code)
        );

        CREATE TABLE IF NOT EXISTS category_key_brand_targets (
            id BIGSERIAL PRIMARY KEY,
            store_id INTEGER NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
            group_code VARCHAR(50) NOT NULL,
            period_month DATE NOT NULL,
            manager_user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
            manager_name VARCHAR(100) NOT NULL,
            sales_target NUMERIC(18, 4) NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
            updated_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_category_key_brand_period_first_day
                CHECK (period_month = date_trunc('month', period_month)::date),
            CONSTRAINT ck_category_key_brand_sales_target_nonnegative
                CHECK (sales_target >= 0),
            CONSTRAINT uq_category_key_brand_store_group_period
                UNIQUE (store_id, group_code, period_month)
        );

        CREATE TABLE IF NOT EXISTS category_manager_performance_targets (
            id BIGSERIAL PRIMARY KEY,
            store_id INTEGER NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
            period_month DATE NOT NULL,
            manager_user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
            manager_name VARCHAR(100) NOT NULL,
            area_revenue_target NUMERIC(18, 4) NOT NULL DEFAULT 0,
            area_weight NUMERIC(8, 4) NOT NULL DEFAULT 40,
            key_brand_weight NUMERIC(8, 4) NOT NULL DEFAULT 40,
            self_weight NUMERIC(8, 4) NOT NULL DEFAULT 20,
            self_score NUMERIC(8, 4),
            assessment_content TEXT,
            created_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
            updated_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_category_manager_period_first_day
                CHECK (period_month = date_trunc('month', period_month)::date),
            CONSTRAINT ck_category_manager_area_target_nonnegative
                CHECK (area_revenue_target >= 0),
            CONSTRAINT ck_category_manager_weights_nonnegative
                CHECK (area_weight >= 0 AND key_brand_weight >= 0 AND self_weight >= 0),
            CONSTRAINT ck_category_manager_weights_total
                CHECK (area_weight + key_brand_weight + self_weight = 100),
            CONSTRAINT ck_category_manager_self_score
                CHECK (self_score IS NULL OR (self_score >= 0 AND self_score <= self_weight)),
            CONSTRAINT uq_category_manager_store_user_period
                UNIQUE (store_id, manager_user_id, period_month)
        );

        CREATE INDEX IF NOT EXISTS ix_category_manager_brand_manager
            ON category_manager_brand_assignments(store_id, manager_user_id)
            WHERE is_active;
        CREATE INDEX IF NOT EXISTS ix_category_key_brand_period_manager
            ON category_key_brand_targets(store_id, period_month, manager_user_id)
            WHERE is_active;
        CREATE INDEX IF NOT EXISTS ix_category_manager_target_period
            ON category_manager_performance_targets(store_id, period_month);

        COMMENT ON TABLE category_manager_brand_assignments
            IS '品牌柜组对应品类主管维护表，以ERP柜组编码为稳定键';
        COMMENT ON TABLE category_key_brand_targets
            IS '重点品牌对应品类主管及月度销售目标维护表，目标单位为万元';
        COMMENT ON TABLE category_manager_performance_targets
            IS '品类主管月度绩效参数，分管区域收益目标单位为万元';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS category_manager_performance_targets;
        DROP TABLE IF EXISTS category_key_brand_targets;
        DROP TABLE IF EXISTS category_manager_brand_assignments;
        """
    )
