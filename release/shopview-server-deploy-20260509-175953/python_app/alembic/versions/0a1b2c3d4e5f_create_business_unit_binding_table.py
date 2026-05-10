"""create business_unit_binding table (经营单元绑定表)

Revision ID: 0a1b2c3d4e5f
Revises: 9c1d2e3f4a5b
Create Date: 2026-05-09

"""
from typing import Sequence, Union

from alembic import op


revision: str = "0a1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "9c1d2e3f4a5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BUSINESS_UNIT_BINDING_SQL = r"""
CREATE TABLE IF NOT EXISTS business_unit_binding (
    id BIGSERIAL NOT NULL,
    shop_unit_id BIGINT NOT NULL,
    counter_group_id INTEGER,
    supplier_id VARCHAR(50),
    brand_id VARCHAR(50),
    contract_id VARCHAR(100) NOT NULL,
    business_type VARCHAR(50),
    start_date DATE,
    end_date DATE,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    remark TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_business_unit_binding PRIMARY KEY (id),
    CONSTRAINT fk_bub_shop_unit FOREIGN KEY (shop_unit_id) REFERENCES business_units(id) ON DELETE RESTRICT,
    CONSTRAINT fk_bub_counter_group FOREIGN KEY (counter_group_id) REFERENCES counter_groups(group_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_bub_shop_unit_id ON business_unit_binding(shop_unit_id);
CREATE INDEX IF NOT EXISTS idx_bub_counter_group_id ON business_unit_binding(counter_group_id);
CREATE INDEX IF NOT EXISTS idx_bub_supplier_id ON business_unit_binding(supplier_id);
CREATE INDEX IF NOT EXISTS idx_bub_brand_id ON business_unit_binding(brand_id);
CREATE INDEX IF NOT EXISTS idx_bub_contract_id ON business_unit_binding(contract_id);
CREATE INDEX IF NOT EXISTS idx_bub_effective_dates ON business_unit_binding(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_bub_status ON business_unit_binding(status);

COMMENT ON TABLE business_unit_binding IS '经营单元绑定表/铺位-柜组-合同关系表';
COMMENT ON COLUMN business_unit_binding.id IS '系统主键';
COMMENT ON COLUMN business_unit_binding.shop_unit_id IS '铺位ID，对应 business_units.id';
COMMENT ON COLUMN business_unit_binding.counter_group_id IS '柜组ID，对应 counter_groups.group_id，可为空';
COMMENT ON COLUMN business_unit_binding.supplier_id IS '供应商ID/编码，可为空';
COMMENT ON COLUMN business_unit_binding.brand_id IS '品牌ID/编码，可为空';
COMMENT ON COLUMN business_unit_binding.contract_id IS '合同ID/合同号';
COMMENT ON COLUMN business_unit_binding.business_type IS '经营类型：普通商铺、超市联营、租赁、临时经营等';
COMMENT ON COLUMN business_unit_binding.start_date IS '绑定关系开始日期';
COMMENT ON COLUMN business_unit_binding.end_date IS '绑定关系结束日期';
COMMENT ON COLUMN business_unit_binding.is_primary IS '是否主关系';
COMMENT ON COLUMN business_unit_binding.status IS '状态：ACTIVE/INACTIVE/HISTORY 等';
COMMENT ON COLUMN business_unit_binding.remark IS '备注';
COMMENT ON COLUMN business_unit_binding.created_at IS '创建时间';
COMMENT ON COLUMN business_unit_binding.updated_at IS '更新时间';
"""


def upgrade() -> None:
    op.execute(BUSINESS_UNIT_BINDING_SQL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS business_unit_binding;")
