"""add unit revenue table comments

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-06-03

"""
from typing import Sequence, Union

from alembic import op


revision: str = "e8f9a0b1c2d3"
down_revision: Union[str, Sequence[str], None] = "d7e8f9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COMMENTS_SQL = r"""
COMMENT ON TABLE unit_revenue_sales_detail IS '经营单元销售毛利日明细，ETL 写入，金额按不含税口径';
COMMENT ON TABLE unit_revenue_fee_detail IS '经营单元收费日明细，ETL 写入，收益日期为实际收费日期，金额按不含税/去税口径';
COMMENT ON TABLE revenue_extra_receipts IS '财务补录其他收益，只有 CONFIRMED 状态进入收益汇总';
COMMENT ON TABLE unit_daily_revenue_summary IS '经营单元日收益汇总，月份展示由 revenue_date 聚合得到';
COMMENT ON TABLE unmatched_revenue_items IS '未匹配收益池，用于柜组无法唯一映射经营单元或暂未分摊的数据';

COMMENT ON COLUMN unit_revenue_sales_detail.id IS '销售毛利明细主键';
COMMENT ON COLUMN unit_revenue_sales_detail.store_id IS '门店ID，冗余字段，便于按门店筛选';
COMMENT ON COLUMN unit_revenue_sales_detail.floor_id IS '楼层ID，对应 floors.id';
COMMENT ON COLUMN unit_revenue_sales_detail.unit_id IS '经营单元ID，对应 business_units.id；ETL 匹配后写入';
COMMENT ON COLUMN unit_revenue_sales_detail.unit_code IS '经营单元编码/柜位号，对应 business_units.unit_code';
COMMENT ON COLUMN unit_revenue_sales_detail.revenue_date IS '收益日期，销售发生日期，由 ETL 补入';
COMMENT ON COLUMN unit_revenue_sales_detail.revenue_month IS '收益月份，格式 YYYY-MM，由 revenue_date 自动生成';
COMMENT ON COLUMN unit_revenue_sales_detail.source_group_code IS '来源系统柜组编码';
COMMENT ON COLUMN unit_revenue_sales_detail.source_group_name IS '来源系统柜组名称';
COMMENT ON COLUMN unit_revenue_sales_detail.department_code IS '来源系统部门编码';
COMMENT ON COLUMN unit_revenue_sales_detail.department_name IS '来源系统部门名称';
COMMENT ON COLUMN unit_revenue_sales_detail.area_name IS '来源系统区域名称';
COMMENT ON COLUMN unit_revenue_sales_detail.floor_name IS '来源系统楼层名称';
COMMENT ON COLUMN unit_revenue_sales_detail.operation_mode IS '经营方式，如联营、经销、租赁等';
COMMENT ON COLUMN unit_revenue_sales_detail.supplier_code IS '供应商编码';
COMMENT ON COLUMN unit_revenue_sales_detail.supplier_name IS '供应商名称';
COMMENT ON COLUMN unit_revenue_sales_detail.contract_code IS '合同号';
COMMENT ON COLUMN unit_revenue_sales_detail.sales_qty IS '销售数量';
COMMENT ON COLUMN unit_revenue_sales_detail.tax_excluded_sales_amount IS '不含税销售额';
COMMENT ON COLUMN unit_revenue_sales_detail.tax_excluded_profit_amount IS '不含税销售毛利，汇总时进入销售毛利收益';
COMMENT ON COLUMN unit_revenue_sales_detail.front_gross_profit_amount IS '前台毛利，明细展示和对账参考';
COMMENT ON COLUMN unit_revenue_sales_detail.tax_excl_profit_adjustment IS '不含税毛利调整金额';
COMMENT ON COLUMN unit_revenue_sales_detail.guaranteed_adjust_amount IS '保底调整金额';
COMMENT ON COLUMN unit_revenue_sales_detail.original_deduct_profit_amt IS '原扣率毛利金额';
COMMENT ON COLUMN unit_revenue_sales_detail.source_doc_no IS '来源单据号或报表编号';
COMMENT ON COLUMN unit_revenue_sales_detail.source_row_key IS '来源行唯一键，用于 ETL 去重或追溯';
COMMENT ON COLUMN unit_revenue_sales_detail.etl_batch_id IS 'ETL 批次号';
COMMENT ON COLUMN unit_revenue_sales_detail.raw_payload IS '来源原始数据 JSON，用于审计和排错';
COMMENT ON COLUMN unit_revenue_sales_detail.created_at IS '创建时间';
COMMENT ON COLUMN unit_revenue_sales_detail.updated_at IS '更新时间';

COMMENT ON COLUMN unit_revenue_fee_detail.id IS '收费明细主键';
COMMENT ON COLUMN unit_revenue_fee_detail.store_id IS '门店ID，冗余字段，便于按门店筛选';
COMMENT ON COLUMN unit_revenue_fee_detail.floor_id IS '楼层ID，对应 floors.id';
COMMENT ON COLUMN unit_revenue_fee_detail.unit_id IS '经营单元ID，对应 business_units.id；ETL 匹配后写入';
COMMENT ON COLUMN unit_revenue_fee_detail.unit_code IS '经营单元编码/柜位号，对应 business_units.unit_code';
COMMENT ON COLUMN unit_revenue_fee_detail.revenue_date IS '收益日期，实际收费日期；哪天收费算哪天收益';
COMMENT ON COLUMN unit_revenue_fee_detail.revenue_month IS '收益月份，格式 YYYY-MM，由 revenue_date 自动生成';
COMMENT ON COLUMN unit_revenue_fee_detail.source_group_code IS '来源系统柜组编码';
COMMENT ON COLUMN unit_revenue_fee_detail.source_group_name IS '来源系统柜组名称';
COMMENT ON COLUMN unit_revenue_fee_detail.department_code IS '来源系统部门编码';
COMMENT ON COLUMN unit_revenue_fee_detail.department_name IS '来源系统部门名称';
COMMENT ON COLUMN unit_revenue_fee_detail.area_name IS '来源系统区域名称';
COMMENT ON COLUMN unit_revenue_fee_detail.floor_name IS '来源系统楼层名称';
COMMENT ON COLUMN unit_revenue_fee_detail.contract_code IS '合同号';
COMMENT ON COLUMN unit_revenue_fee_detail.contract_name IS '合同名称';
COMMENT ON COLUMN unit_revenue_fee_detail.fee_type_code IS '费用类型编码';
COMMENT ON COLUMN unit_revenue_fee_detail.fee_type_name IS '费用类型名称，如租金、管理费、电费等';
COMMENT ON COLUMN unit_revenue_fee_detail.source_type IS '来源类型，默认 ETL';
COMMENT ON COLUMN unit_revenue_fee_detail.tax_included_amount IS '含税收费金额，仅用于展示和对账参考';
COMMENT ON COLUMN unit_revenue_fee_detail.tax_excluded_amount IS '不含税/去税收费金额，汇总时进入收费收益';
COMMENT ON COLUMN unit_revenue_fee_detail.source_doc_no IS '来源单据号或付款单号';
COMMENT ON COLUMN unit_revenue_fee_detail.source_row_key IS '来源行唯一键，用于 ETL 去重或追溯';
COMMENT ON COLUMN unit_revenue_fee_detail.etl_batch_id IS 'ETL 批次号';
COMMENT ON COLUMN unit_revenue_fee_detail.raw_payload IS '来源原始数据 JSON，用于审计和排错';
COMMENT ON COLUMN unit_revenue_fee_detail.created_at IS '创建时间';
COMMENT ON COLUMN unit_revenue_fee_detail.updated_at IS '更新时间';

COMMENT ON COLUMN revenue_extra_receipts.id IS '补收记录主键';
COMMENT ON COLUMN revenue_extra_receipts.store_id IS '门店ID，冗余字段，便于按门店筛选';
COMMENT ON COLUMN revenue_extra_receipts.floor_id IS '楼层ID，对应 floors.id';
COMMENT ON COLUMN revenue_extra_receipts.unit_id IS '经营单元ID，对应 business_units.id';
COMMENT ON COLUMN revenue_extra_receipts.unit_code IS '经营单元编码/柜位号，对应 business_units.unit_code';
COMMENT ON COLUMN revenue_extra_receipts.revenue_date IS '收益日期，补收金额归属日期';
COMMENT ON COLUMN revenue_extra_receipts.revenue_month IS '收益月份，格式 YYYY-MM，由 revenue_date 自动生成';
COMMENT ON COLUMN revenue_extra_receipts.extra_type IS '补收类型/其他收益类型';
COMMENT ON COLUMN revenue_extra_receipts.amount IS '补收金额，确认后进入其他收益';
COMMENT ON COLUMN revenue_extra_receipts.receipt_date IS '到账日期或收款日期';
COMMENT ON COLUMN revenue_extra_receipts.voucher_no IS '凭证号';
COMMENT ON COLUMN revenue_extra_receipts.contract_code IS '合同号';
COMMENT ON COLUMN revenue_extra_receipts.supplier_code IS '供应商编码';
COMMENT ON COLUMN revenue_extra_receipts.supplier_name IS '供应商名称';
COMMENT ON COLUMN revenue_extra_receipts.source_group_code IS '来源系统柜组编码';
COMMENT ON COLUMN revenue_extra_receipts.source_group_name IS '来源系统柜组名称';
COMMENT ON COLUMN revenue_extra_receipts.remark IS '备注';
COMMENT ON COLUMN revenue_extra_receipts.attachment_url IS '附件地址';
COMMENT ON COLUMN revenue_extra_receipts.status IS '补收状态：DRAFT 草稿，CONFIRMED 已确认，VOID 作废';
COMMENT ON COLUMN revenue_extra_receipts.created_by IS '创建人用户ID';
COMMENT ON COLUMN revenue_extra_receipts.confirmed_by IS '确认人用户ID';
COMMENT ON COLUMN revenue_extra_receipts.voided_by IS '作废人用户ID';
COMMENT ON COLUMN revenue_extra_receipts.confirmed_at IS '确认时间';
COMMENT ON COLUMN revenue_extra_receipts.voided_at IS '作废时间';
COMMENT ON COLUMN revenue_extra_receipts.created_at IS '创建时间';
COMMENT ON COLUMN revenue_extra_receipts.updated_at IS '更新时间';

COMMENT ON COLUMN unit_daily_revenue_summary.id IS '日收益汇总主键';
COMMENT ON COLUMN unit_daily_revenue_summary.store_id IS '门店ID，冗余字段，便于按门店筛选';
COMMENT ON COLUMN unit_daily_revenue_summary.floor_id IS '楼层ID，对应 floors.id';
COMMENT ON COLUMN unit_daily_revenue_summary.unit_id IS '经营单元ID，对应 business_units.id';
COMMENT ON COLUMN unit_daily_revenue_summary.unit_code IS '经营单元编码/柜位号，对应 business_units.unit_code';
COMMENT ON COLUMN unit_daily_revenue_summary.revenue_date IS '收益日期，日汇总粒度';
COMMENT ON COLUMN unit_daily_revenue_summary.revenue_month IS '收益月份，格式 YYYY-MM，由 revenue_date 自动生成';
COMMENT ON COLUMN unit_daily_revenue_summary.sales_gross_profit_amount IS '销售毛利收益合计，不含税口径';
COMMENT ON COLUMN unit_daily_revenue_summary.fee_amount IS '收费收益合计，不含税/去税口径';
COMMENT ON COLUMN unit_daily_revenue_summary.extra_amount IS '其他补收收益合计，仅统计已确认补收';
COMMENT ON COLUMN unit_daily_revenue_summary.total_amount IS '总收益，销售毛利 + 收费 + 其他补收';
COMMENT ON COLUMN unit_daily_revenue_summary.sales_detail_count IS '参与汇总的销售明细条数';
COMMENT ON COLUMN unit_daily_revenue_summary.fee_detail_count IS '参与汇总的收费明细条数';
COMMENT ON COLUMN unit_daily_revenue_summary.extra_detail_count IS '参与汇总的已确认补收条数';
COMMENT ON COLUMN unit_daily_revenue_summary.etl_batch_id IS '最近参与汇总的 ETL 批次号';
COMMENT ON COLUMN unit_daily_revenue_summary.calculated_at IS '汇总计算时间';
COMMENT ON COLUMN unit_daily_revenue_summary.created_at IS '创建时间';
COMMENT ON COLUMN unit_daily_revenue_summary.updated_at IS '更新时间';

COMMENT ON COLUMN unmatched_revenue_items.id IS '未匹配收益主键';
COMMENT ON COLUMN unmatched_revenue_items.store_id IS '门店ID，冗余字段，便于按门店筛选';
COMMENT ON COLUMN unmatched_revenue_items.revenue_date IS '收益日期';
COMMENT ON COLUMN unmatched_revenue_items.revenue_month IS '收益月份，格式 YYYY-MM，由 revenue_date 自动生成';
COMMENT ON COLUMN unmatched_revenue_items.source_category IS '来源类别：SALES 销售，FEE 收费，EXTRA 其他';
COMMENT ON COLUMN unmatched_revenue_items.source_group_code IS '来源系统柜组编码';
COMMENT ON COLUMN unmatched_revenue_items.source_group_name IS '来源系统柜组名称';
COMMENT ON COLUMN unmatched_revenue_items.contract_code IS '合同号';
COMMENT ON COLUMN unmatched_revenue_items.supplier_code IS '供应商编码';
COMMENT ON COLUMN unmatched_revenue_items.supplier_name IS '供应商名称';
COMMENT ON COLUMN unmatched_revenue_items.amount IS '未匹配金额，不含税口径';
COMMENT ON COLUMN unmatched_revenue_items.reason IS '未匹配原因，如 UNMATCHED_UNIT 或 MULTI_UNIT_PENDING_SPLIT';
COMMENT ON COLUMN unmatched_revenue_items.status IS '处理状态：PENDING 待处理，RESOLVED 已处理，IGNORED 已忽略';
COMMENT ON COLUMN unmatched_revenue_items.etl_batch_id IS 'ETL 批次号';
COMMENT ON COLUMN unmatched_revenue_items.raw_payload IS '来源原始数据 JSON，用于审计和排错';
COMMENT ON COLUMN unmatched_revenue_items.created_at IS '创建时间';
COMMENT ON COLUMN unmatched_revenue_items.updated_at IS '更新时间';
"""


def upgrade() -> None:
    op.execute(COMMENTS_SQL)


def downgrade() -> None:
    # Downgrade keeps comments in place; removing them has no runtime benefit.
    pass
