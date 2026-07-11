"""create coupon monthly balance tables

Revision ID: c3d4e5f6a7b8
Revises: 6f7a8b9c0d1e
Create Date: 2026-06-22
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "6f7a8b9c0d1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS activity_coupon_revenue_movement (
    id BIGSERIAL PRIMARY KEY,
    business_date DATE NOT NULL,
    period_month CHAR(7) NOT NULL,
    market_code VARCHAR(20) NOT NULL,
    business_store_code VARCHAR(20),
    coupon_type VARCHAR(40) NOT NULL,
    coupon_name VARCHAR(100),
    match_type VARCHAR(30) NOT NULL,
    voucher_match_id BIGINT NOT NULL REFERENCES activity_coupon_voucher_match(id) ON DELETE CASCADE,
    voucher_detail_id VARCHAR(32) NOT NULL,
    business_amount NUMERIC(28, 8) NOT NULL DEFAULT 0,
    revenue_rate NUMERIC(18, 8),
    actual_revenue_amount NUMERIC(28, 8) NOT NULL DEFAULT 0,
    rate_snapshot_date DATE,
    rate_status VARCHAR(30) NOT NULL DEFAULT 'MISSING_RATE',
    movement_direction VARCHAR(30) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ux_activity_coupon_revenue_movement_match UNIQUE (voucher_match_id),
    CONSTRAINT ck_activity_coupon_revenue_movement_match_type
        CHECK (match_type IN ('CREDIT_BUY', 'DEBIT_USE')),
    CONSTRAINT ck_activity_coupon_revenue_movement_rate_status
        CHECK (rate_status IN ('OK', 'MISSING_RATE')),
    CONSTRAINT ck_activity_coupon_revenue_movement_direction
        CHECK (movement_direction IN ('INCREASE', 'DECREASE'))
);

COMMENT ON TABLE activity_coupon_revenue_movement IS '卡券每日销售收入变动明细，由已确认凭证匹配行按收入占比折算生成';
COMMENT ON COLUMN activity_coupon_revenue_movement.period_month IS '归属月份，格式 YYYY-MM';
COMMENT ON COLUMN activity_coupon_revenue_movement.voucher_match_id IS '来源 activity_coupon_voucher_match.id';
COMMENT ON COLUMN activity_coupon_revenue_movement.actual_revenue_amount IS '卡券金额乘每日门店券种收入占比后的实际销售收入变动额';
COMMENT ON COLUMN activity_coupon_revenue_movement.rate_status IS '收入占比匹配状态：OK、MISSING_RATE';
COMMENT ON COLUMN activity_coupon_revenue_movement.movement_direction IS '余额方向：INCREASE、DECREASE';

CREATE INDEX IF NOT EXISTS idx_activity_coupon_revenue_movement_month_coupon
    ON activity_coupon_revenue_movement (period_month, market_code, coupon_type);

CREATE INDEX IF NOT EXISTS idx_activity_coupon_revenue_movement_rate_status
    ON activity_coupon_revenue_movement (rate_status);

CREATE TABLE IF NOT EXISTS activity_coupon_nc_carryover (
    id BIGSERIAL PRIMARY KEY,
    period_month CHAR(7) NOT NULL,
    market_code VARCHAR(20) NOT NULL,
    coupon_type VARCHAR(40) NOT NULL,
    coupon_name VARCHAR(100),
    nc_voucher_no VARCHAR(100) NOT NULL,
    carryover_amount NUMERIC(28, 8) NOT NULL DEFAULT 0,
    carryover_date DATE,
    remark VARCHAR(500),
    created_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE activity_coupon_nc_carryover IS '财务在 NC 手工结转后的 ShopView 登记记录';
COMMENT ON COLUMN activity_coupon_nc_carryover.period_month IS '归属月份，格式 YYYY-MM';
COMMENT ON COLUMN activity_coupon_nc_carryover.nc_voucher_no IS 'NC 手工结转凭证号';
COMMENT ON COLUMN activity_coupon_nc_carryover.carryover_amount IS '本次 NC 手工结转扣减金额';

CREATE INDEX IF NOT EXISTS idx_activity_coupon_nc_carryover_month_coupon
    ON activity_coupon_nc_carryover (period_month, market_code, coupon_type);

CREATE TABLE IF NOT EXISTS activity_coupon_monthly_balance (
    id BIGSERIAL PRIMARY KEY,
    period_month CHAR(7) NOT NULL,
    market_code VARCHAR(20) NOT NULL,
    coupon_type VARCHAR(40) NOT NULL,
    coupon_name VARCHAR(100),
    opening_balance NUMERIC(28, 8) NOT NULL DEFAULT 0,
    current_month_increase NUMERIC(28, 8) NOT NULL DEFAULT 0,
    current_month_decrease NUMERIC(28, 8) NOT NULL DEFAULT 0,
    nc_carryover_amount NUMERIC(28, 8) NOT NULL DEFAULT 0,
    ending_balance NUMERIC(28, 8) NOT NULL DEFAULT 0,
    missing_rate_count INTEGER NOT NULL DEFAULT 0,
    movement_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
    confirmed_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    confirmed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ux_activity_coupon_monthly_balance_month_coupon
        UNIQUE (period_month, market_code, coupon_type),
    CONSTRAINT ck_activity_coupon_monthly_balance_status
        CHECK (status IN ('DRAFT', 'CONFIRMED'))
);

COMMENT ON TABLE activity_coupon_monthly_balance IS '卡券月度销售收入余额快照';
COMMENT ON COLUMN activity_coupon_monthly_balance.period_month IS '归属月份，格式 YYYY-MM';
COMMENT ON COLUMN activity_coupon_monthly_balance.opening_balance IS '上月期末余额';
COMMENT ON COLUMN activity_coupon_monthly_balance.nc_carryover_amount IS '本月 NC 手工结转扣减金额';
COMMENT ON COLUMN activity_coupon_monthly_balance.ending_balance IS '月末余额';
COMMENT ON COLUMN activity_coupon_monthly_balance.missing_rate_count IS '缺收入占比的每日变动行数';

CREATE INDEX IF NOT EXISTS idx_activity_coupon_monthly_balance_status
    ON activity_coupon_monthly_balance (status);
"""


DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS activity_coupon_monthly_balance;
DROP TABLE IF EXISTS activity_coupon_nc_carryover;
DROP TABLE IF EXISTS activity_coupon_revenue_movement;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
