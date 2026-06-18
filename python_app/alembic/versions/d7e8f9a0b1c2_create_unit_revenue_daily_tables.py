"""create unit revenue daily tables

Revision ID: d7e8f9a0b1c2
Revises: c9d0e1f2a3b4, b6d4e8f0a2c1
Create Date: 2026-06-03

"""
from typing import Sequence, Union

from alembic import op


revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = ("c9d0e1f2a3b4", "b6d4e8f0a2c1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS unit_revenue_sales_detail (
    id VARCHAR(64) PRIMARY KEY,
    store_id INTEGER,
    floor_id BIGINT,
    unit_id BIGINT REFERENCES business_units(id) ON DELETE SET NULL,
    unit_code TEXT,
    revenue_date DATE NOT NULL,
    revenue_month VARCHAR(7),
    source_group_code VARCHAR(50),
    source_group_name VARCHAR(200),
    department_code VARCHAR(50),
    department_name VARCHAR(200),
    area_name VARCHAR(100),
    floor_name VARCHAR(50),
    operation_mode VARCHAR(50),
    supplier_code VARCHAR(50),
    supplier_name VARCHAR(200),
    contract_code VARCHAR(100),
    sales_qty NUMERIC(18, 4) NOT NULL DEFAULT 0,
    tax_excluded_sales_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    tax_excluded_profit_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    front_gross_profit_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    tax_excl_profit_adjustment NUMERIC(18, 2) NOT NULL DEFAULT 0,
    guaranteed_adjust_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    original_deduct_profit_amt NUMERIC(18, 2) NOT NULL DEFAULT 0,
    source_doc_no VARCHAR(100),
    source_row_key VARCHAR(200),
    etl_batch_id VARCHAR(100),
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS unit_revenue_fee_detail (
    id VARCHAR(50) PRIMARY KEY,
    store_id INTEGER,
    floor_id BIGINT,
    unit_id BIGINT REFERENCES business_units(id) ON DELETE SET NULL,
    unit_code TEXT,
    revenue_date DATE NOT NULL,
    revenue_month VARCHAR(7),
    source_group_code VARCHAR(50),
    source_group_name VARCHAR(200),
    department_code VARCHAR(50),
    department_name VARCHAR(200),
    area_name VARCHAR(100),
    floor_name VARCHAR(50),
    contract_code VARCHAR(100),
    contract_name VARCHAR(300),
    fee_type_code VARCHAR(50),
    fee_type_name VARCHAR(200),
    source_type VARCHAR(30) NOT NULL DEFAULT 'ETL',
    tax_included_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    tax_excluded_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    source_doc_no VARCHAR(100),
    source_row_key VARCHAR(200),
    etl_batch_id VARCHAR(100),
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS revenue_extra_receipts (
    id BIGSERIAL PRIMARY KEY,
    store_id INTEGER,
    floor_id BIGINT,
    unit_id BIGINT REFERENCES business_units(id) ON DELETE SET NULL,
    unit_code TEXT,
    revenue_date DATE NOT NULL,
    revenue_month VARCHAR(7),
    extra_type VARCHAR(100) NOT NULL DEFAULT '其他收益',
    amount NUMERIC(18, 2) NOT NULL,
    receipt_date DATE,
    voucher_no VARCHAR(100),
    contract_code VARCHAR(100),
    supplier_code VARCHAR(50),
    supplier_name VARCHAR(200),
    source_group_code VARCHAR(50),
    source_group_name VARCHAR(200),
    remark TEXT,
    attachment_url TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    created_by INTEGER,
    confirmed_by INTEGER,
    voided_by INTEGER,
    confirmed_at TIMESTAMPTZ,
    voided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_revenue_extra_receipts_status CHECK (status IN ('DRAFT', 'CONFIRMED', 'VOID')),
    CONSTRAINT ck_revenue_extra_receipts_amount_nonzero CHECK (amount <> 0)
);

CREATE TABLE IF NOT EXISTS unit_daily_revenue_summary (
    id BIGSERIAL PRIMARY KEY,
    store_id INTEGER,
    floor_id BIGINT,
    unit_id BIGINT REFERENCES business_units(id) ON DELETE CASCADE,
    unit_code TEXT NOT NULL,
    revenue_date DATE NOT NULL,
    revenue_month VARCHAR(7),
    sales_gross_profit_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    fee_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    extra_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(18, 2) GENERATED ALWAYS AS (
        sales_gross_profit_amount + fee_amount + extra_amount
    ) STORED,
    sales_detail_count INTEGER NOT NULL DEFAULT 0,
    fee_detail_count INTEGER NOT NULL DEFAULT 0,
    extra_detail_count INTEGER NOT NULL DEFAULT 0,
    etl_batch_id VARCHAR(100),
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_unit_daily_revenue_summary_unit_date UNIQUE (unit_id, revenue_date)
);

CREATE TABLE IF NOT EXISTS unmatched_revenue_items (
    id BIGSERIAL PRIMARY KEY,
    store_id INTEGER,
    revenue_date DATE NOT NULL,
    revenue_month VARCHAR(7),
    source_category VARCHAR(20) NOT NULL,
    source_group_code VARCHAR(50),
    source_group_name VARCHAR(200),
    contract_code VARCHAR(100),
    supplier_code VARCHAR(50),
    supplier_name VARCHAR(200),
    amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    reason VARCHAR(100) NOT NULL DEFAULT 'UNMATCHED_UNIT',
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    etl_batch_id VARCHAR(100),
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_unmatched_revenue_items_source_category CHECK (source_category IN ('SALES', 'FEE', 'EXTRA')),
    CONSTRAINT ck_unmatched_revenue_items_status CHECK (status IN ('PENDING', 'RESOLVED', 'IGNORED'))
);

CREATE OR REPLACE FUNCTION set_revenue_month_from_date()
RETURNS TRIGGER AS $$
BEGIN
    NEW.revenue_month := to_char(NEW.revenue_date, 'YYYY-MM');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_unit_revenue_sales_detail_month ON unit_revenue_sales_detail;
CREATE TRIGGER trg_unit_revenue_sales_detail_month
    BEFORE INSERT OR UPDATE OF revenue_date ON unit_revenue_sales_detail
    FOR EACH ROW EXECUTE FUNCTION set_revenue_month_from_date();

DROP TRIGGER IF EXISTS trg_unit_revenue_fee_detail_month ON unit_revenue_fee_detail;
CREATE TRIGGER trg_unit_revenue_fee_detail_month
    BEFORE INSERT OR UPDATE OF revenue_date ON unit_revenue_fee_detail
    FOR EACH ROW EXECUTE FUNCTION set_revenue_month_from_date();

DROP TRIGGER IF EXISTS trg_revenue_extra_receipts_month ON revenue_extra_receipts;
CREATE TRIGGER trg_revenue_extra_receipts_month
    BEFORE INSERT OR UPDATE OF revenue_date ON revenue_extra_receipts
    FOR EACH ROW EXECUTE FUNCTION set_revenue_month_from_date();

DROP TRIGGER IF EXISTS trg_unit_daily_revenue_summary_month ON unit_daily_revenue_summary;
CREATE TRIGGER trg_unit_daily_revenue_summary_month
    BEFORE INSERT OR UPDATE OF revenue_date ON unit_daily_revenue_summary
    FOR EACH ROW EXECUTE FUNCTION set_revenue_month_from_date();

DROP TRIGGER IF EXISTS trg_unmatched_revenue_items_month ON unmatched_revenue_items;
CREATE TRIGGER trg_unmatched_revenue_items_month
    BEFORE INSERT OR UPDATE OF revenue_date ON unmatched_revenue_items
    FOR EACH ROW EXECUTE FUNCTION set_revenue_month_from_date();

CREATE INDEX IF NOT EXISTS ix_unit_revenue_sales_detail_date_unit
    ON unit_revenue_sales_detail(revenue_date, unit_id);
CREATE INDEX IF NOT EXISTS ix_unit_revenue_sales_detail_month_unit
    ON unit_revenue_sales_detail(revenue_month, unit_id);
CREATE INDEX IF NOT EXISTS ix_unit_revenue_sales_detail_group
    ON unit_revenue_sales_detail(source_group_code);
CREATE INDEX IF NOT EXISTS ix_unit_revenue_sales_detail_batch
    ON unit_revenue_sales_detail(etl_batch_id);

CREATE INDEX IF NOT EXISTS ix_unit_revenue_fee_detail_date_unit
    ON unit_revenue_fee_detail(revenue_date, unit_id);
CREATE INDEX IF NOT EXISTS ix_unit_revenue_fee_detail_month_unit
    ON unit_revenue_fee_detail(revenue_month, unit_id);
CREATE INDEX IF NOT EXISTS ix_unit_revenue_fee_detail_group
    ON unit_revenue_fee_detail(source_group_code);
CREATE INDEX IF NOT EXISTS ix_unit_revenue_fee_detail_batch
    ON unit_revenue_fee_detail(etl_batch_id);

CREATE INDEX IF NOT EXISTS ix_revenue_extra_receipts_date_unit
    ON revenue_extra_receipts(revenue_date, unit_id);
CREATE INDEX IF NOT EXISTS ix_revenue_extra_receipts_month_unit
    ON revenue_extra_receipts(revenue_month, unit_id);
CREATE INDEX IF NOT EXISTS ix_revenue_extra_receipts_status
    ON revenue_extra_receipts(status);

CREATE INDEX IF NOT EXISTS ix_unit_daily_revenue_summary_month_floor
    ON unit_daily_revenue_summary(revenue_month, floor_id);
CREATE INDEX IF NOT EXISTS ix_unit_daily_revenue_summary_date_unit
    ON unit_daily_revenue_summary(revenue_date, unit_id);

CREATE INDEX IF NOT EXISTS ix_unmatched_revenue_items_month_status
    ON unmatched_revenue_items(revenue_month, status);
CREATE INDEX IF NOT EXISTS ix_unmatched_revenue_items_group
    ON unmatched_revenue_items(source_group_code);

COMMENT ON TABLE unit_revenue_sales_detail IS '经营单元销售毛利日明细，ETL 写入，金额按不含税口径';
COMMENT ON TABLE unit_revenue_fee_detail IS '经营单元收费日明细，ETL 写入，收益日期为实际收费日期，金额按不含税/去税口径';
COMMENT ON TABLE revenue_extra_receipts IS '财务补录其他收益，只有 CONFIRMED 状态进入收益汇总';
COMMENT ON TABLE unit_daily_revenue_summary IS '经营单元日收益汇总，月份展示由 revenue_date 聚合得到';
COMMENT ON TABLE unmatched_revenue_items IS '未匹配收益池，用于柜组无法唯一映射经营单元或暂未分摊的数据';
"""


DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS unmatched_revenue_items;
DROP TABLE IF EXISTS unit_daily_revenue_summary;
DROP TABLE IF EXISTS revenue_extra_receipts;
DROP TABLE IF EXISTS unit_revenue_fee_detail;
DROP TABLE IF EXISTS unit_revenue_sales_detail;
DROP FUNCTION IF EXISTS set_revenue_month_from_date();
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
