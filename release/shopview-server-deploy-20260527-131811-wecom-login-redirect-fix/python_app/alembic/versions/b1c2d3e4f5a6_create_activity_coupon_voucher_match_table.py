"""create activity coupon voucher match table

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-05-18
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS activity_coupon_voucher_match (
    id BIGSERIAL PRIMARY KEY,
    business_date DATE NOT NULL,
    market_code VARCHAR(20),
    business_store_code VARCHAR(20),
    coupon_type VARCHAR(40) NOT NULL,
    coupon_name VARCHAR(100),
    match_type VARCHAR(30) NOT NULL,
    match_type_name VARCHAR(30),
    business_amount NUMERIC(28, 8) NOT NULL DEFAULT 0,
    flow_count INTEGER NOT NULL DEFAULT 0,
    member_count INTEGER NOT NULL DEFAULT 0,
    voucher_detail_id VARCHAR(32) NOT NULL,
    voucher_amount NUMERIC(28, 8) NOT NULL DEFAULT 0,
    amount_diff NUMERIC(28, 8) NOT NULL DEFAULT 0,
    match_score INTEGER NOT NULL DEFAULT 0,
    match_status VARCHAR(30) NOT NULL,
    confirm_status VARCHAR(30) NOT NULL DEFAULT 'AUTO_CONFIRMED',
    confirmed_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    confirmed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    rejected_reason VARCHAR(300),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ux_activity_coupon_voucher_match_business_voucher
        UNIQUE (business_date, business_store_code, coupon_type, match_type, voucher_detail_id)
);

COMMENT ON TABLE activity_coupon_voucher_match IS '活动卡券业务汇总与财务凭证明细确认匹配表';
COMMENT ON COLUMN activity_coupon_voucher_match.voucher_detail_id IS '按 bh_dw_gl_detail_fact2 凭证明细业务字段拼接后 md5 生成的稳定匹配键';
COMMENT ON COLUMN activity_coupon_voucher_match.confirm_status IS '确认状态：AUTO_CONFIRMED、MANUAL_CONFIRMED、REJECTED';

CREATE INDEX IF NOT EXISTS idx_activity_coupon_voucher_match_business
    ON activity_coupon_voucher_match (business_date, business_store_code, coupon_type, match_type);

CREATE INDEX IF NOT EXISTS idx_activity_coupon_voucher_match_voucher
    ON activity_coupon_voucher_match (voucher_detail_id);

CREATE INDEX IF NOT EXISTS idx_activity_coupon_voucher_match_status
    ON activity_coupon_voucher_match (confirm_status, confirmed_at);
"""


DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS activity_coupon_voucher_match;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
