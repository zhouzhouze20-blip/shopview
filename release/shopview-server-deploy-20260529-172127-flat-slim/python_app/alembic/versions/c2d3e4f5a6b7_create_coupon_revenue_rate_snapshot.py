"""create coupon revenue rate daily snapshot table

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-05-19
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS activity_coupon_revenue_rate_snapshot (
    snapshot_date DATE NOT NULL,
    coupon_type VARCHAR(40) NOT NULL,
    market_code VARCHAR(20) NOT NULL,
    common_revenue_rate NUMERIC(18, 8),
    market_revenue_rate NUMERIC(18, 8),
    effective_revenue_rate NUMERIC(18, 8)
        GENERATED ALWAYS AS (COALESCE(market_revenue_rate, common_revenue_rate)) STORED,
    source_system VARCHAR(40) NOT NULL DEFAULT 'ERP',
    source_loaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_activity_coupon_revenue_rate_snapshot
        PRIMARY KEY (snapshot_date, coupon_type, market_code)
);

COMMENT ON TABLE activity_coupon_revenue_rate_snapshot IS '每日卡券销售收入占比快照，按券种和门店保存通用占比与门店例外占比';
COMMENT ON COLUMN activity_coupon_revenue_rate_snapshot.snapshot_date IS '快照日期，对应源系统 SYSDATE 日期';
COMMENT ON COLUMN activity_coupon_revenue_rate_snapshot.coupon_type IS '券种编码，对应 TKTQTYPE.TQCODE';
COMMENT ON COLUMN activity_coupon_revenue_rate_snapshot.market_code IS '门店编码：601/602/603/604';
COMMENT ON COLUMN activity_coupon_revenue_rate_snapshot.common_revenue_rate IS '通用销售收入占比，对应 TKTQTYPE.TQREVRATE';
COMMENT ON COLUMN activity_coupon_revenue_rate_snapshot.market_revenue_rate IS '门店例外销售收入占比，对应 TKTQTYPEMKT.TQMEVRATE；为空时使用通用占比';
COMMENT ON COLUMN activity_coupon_revenue_rate_snapshot.effective_revenue_rate IS '最终生效销售收入占比：优先门店例外占比，否则通用占比';
COMMENT ON COLUMN activity_coupon_revenue_rate_snapshot.source_system IS '来源系统';
COMMENT ON COLUMN activity_coupon_revenue_rate_snapshot.source_loaded_at IS '源数据抽取或同步时间';

CREATE INDEX IF NOT EXISTS idx_activity_coupon_revenue_rate_snapshot_coupon
    ON activity_coupon_revenue_rate_snapshot (coupon_type, snapshot_date);

CREATE INDEX IF NOT EXISTS idx_activity_coupon_revenue_rate_snapshot_market
    ON activity_coupon_revenue_rate_snapshot (market_code, snapshot_date);
"""


DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS activity_coupon_revenue_rate_snapshot;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
