"""create rpt_goods_sales_detail (商品销售明细报表 / ERP 633)

Revision ID: a7b8c9d0e1f2
Revises: f8e9d0c1b2a3
Create Date: 2026-05-08

字段对齐 建表/数据报表/商品销售明细报表条件窗口.txt 外层查询结果列。
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f8e9d0c1b2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RPT_GOODS_SALES_DETAIL_SQL = r"""
CREATE TABLE IF NOT EXISTS rpt_goods_sales_detail (
    id BIGSERIAL NOT NULL,
    stat_start_date DATE NOT NULL,
    stat_end_date DATE NOT NULL,
    floor_display VARCHAR(200),
    storage_area VARCHAR(200),
    counter_display VARCHAR(200),
    supplier_display VARCHAR(200),
    goods_code VARCHAR(40) NOT NULL,
    barcode VARCHAR(64),
    goods_name VARCHAR(400),
    base_discount_rate NUMERIC(18, 8),
    sales_discount_rate NUMERIC(18, 8),
    preferential_discount_rate NUMERIC(18, 8),
    concession_amount NUMERIC(18, 4),
    sales_qty NUMERIC(18, 4),
    priced_sales_amount NUMERIC(18, 4),
    sales_revenue NUMERIC(18, 4),
    gross_profit NUMERIC(18, 4),
    gross_margin_rate NUMERIC(18, 8),
    net_sales_amount NUMERIC(18, 4),
    net_gross_profit NUMERIC(18, 4),
    net_gross_margin_rate NUMERIC(18, 8),
    sales_cost NUMERIC(18, 4),
    net_sales_cost NUMERIC(18, 4),
    total_discount NUMERIC(18, 4),
    member_discount_amt NUMERIC(18, 4),
    promo_discount_amt NUMERIC(18, 4),
    auth_discount_amt NUMERIC(18, 4),
    other_discount_amt NUMERIC(18, 4),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_rpt_goods_sales_detail PRIMARY KEY (id)
);

COMMENT ON TABLE rpt_goods_sales_detail IS '商品销售明细报表(633)汇总行：对应 ERP 报表列，取值口径见数据报表 SQL';
COMMENT ON COLUMN rpt_goods_sales_detail.stat_start_date IS '统计区间起（发生日期）';
COMMENT ON COLUMN rpt_goods_sales_detail.stat_end_date IS '统计区间止';
COMMENT ON COLUMN rpt_goods_sales_detail.floor_display IS '楼层 class2';
COMMENT ON COLUMN rpt_goods_sales_detail.storage_area IS '库区 spbm';
COMMENT ON COLUMN rpt_goods_sales_detail.counter_display IS '柜组 SGLMFID';
COMMENT ON COLUMN rpt_goods_sales_detail.supplier_display IS '供应商 SGLSUPID';
COMMENT ON COLUMN rpt_goods_sales_detail.goods_code IS '商品编码 SGLGDID';
COMMENT ON COLUMN rpt_goods_sales_detail.barcode IS '商品条码 SGLBARCODE';
COMMENT ON COLUMN rpt_goods_sales_detail.goods_name IS '商品名称 GBCNAME';
COMMENT ON COLUMN rpt_goods_sales_detail.base_discount_rate IS '原扣率 SGLBASEKL（比例 0–1）';
COMMENT ON COLUMN rpt_goods_sales_detail.sales_discount_rate IS '销售扣率 SGLKL（比例 0–1）';
COMMENT ON COLUMN rpt_goods_sales_detail.preferential_discount_rate IS '优惠扣率（比例 0–1）';
COMMENT ON COLUMN rpt_goods_sales_detail.concession_amount IS '让扣金额 sum(rkje)';
COMMENT ON COLUMN rpt_goods_sales_detail.sales_qty IS '销售数量 sum(JGLSL)';
COMMENT ON COLUMN rpt_goods_sales_detail.priced_sales_amount IS '售价金额 sum(sjje)';
COMMENT ON COLUMN rpt_goods_sales_detail.sales_revenue IS '销售收入 sum(JGLN3)';
COMMENT ON COLUMN rpt_goods_sales_detail.gross_profit IS '毛利 sum(ML)';
COMMENT ON COLUMN rpt_goods_sales_detail.gross_margin_rate IS '毛利率（比例 0–1）';
COMMENT ON COLUMN rpt_goods_sales_detail.net_sales_amount IS '销售净额 sum(XSJEJE)';
COMMENT ON COLUMN rpt_goods_sales_detail.net_gross_profit IS '净毛利 sum(NETML)';
COMMENT ON COLUMN rpt_goods_sales_detail.net_gross_margin_rate IS '净毛利率（比例 0–1）';
COMMENT ON COLUMN rpt_goods_sales_detail.sales_cost IS '销售成本 sum(xscb)';
COMMENT ON COLUMN rpt_goods_sales_detail.net_sales_cost IS '净销售成本 sum(jxscb)';
COMMENT ON COLUMN rpt_goods_sales_detail.total_discount IS '总折扣 sum(JGLN4)';
COMMENT ON COLUMN rpt_goods_sales_detail.member_discount_amt IS '会员折扣 sum(JGLZK1)';
COMMENT ON COLUMN rpt_goods_sales_detail.promo_discount_amt IS '促销折扣 sum(JGLZK2)';
COMMENT ON COLUMN rpt_goods_sales_detail.auth_discount_amt IS '授权折扣 sum(JGLZK3)';
COMMENT ON COLUMN rpt_goods_sales_detail.other_discount_amt IS '其他折扣 sum(JGLZK4)';

CREATE INDEX IF NOT EXISTS idx_rpt_gsd_stat ON rpt_goods_sales_detail (stat_start_date, stat_end_date);
CREATE INDEX IF NOT EXISTS idx_rpt_gsd_goods ON rpt_goods_sales_detail (goods_code);
CREATE INDEX IF NOT EXISTS idx_rpt_gsd_barcode ON rpt_goods_sales_detail (barcode);
"""


def upgrade() -> None:
    op.execute(RPT_GOODS_SALES_DETAIL_SQL)


def downgrade() -> None:
    op.drop_index("idx_rpt_gsd_barcode", table_name="rpt_goods_sales_detail")
    op.drop_index("idx_rpt_gsd_goods", table_name="rpt_goods_sales_detail")
    op.drop_index("idx_rpt_gsd_stat", table_name="rpt_goods_sales_detail")
    op.drop_table("rpt_goods_sales_detail")
