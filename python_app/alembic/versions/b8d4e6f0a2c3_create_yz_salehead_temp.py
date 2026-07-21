"""create yz_salehead_temp table

Revision ID: b8d4e6f0a2c3
Revises: a7c9e1f3b5d7
Create Date: 2026-07-20
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b8d4e6f0a2c3"
down_revision: Union[str, Sequence[str], None] = "a7c9e1f3b5d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CREATE_YZ_SALEHEAD_TEMP_SQL = r"""
CREATE TABLE IF NOT EXISTS public.yz_salehead_temp (
    l_tid VARCHAR(100),
    l_ytid VARCHAR(100),
    l_store_id VARCHAR(5),
    l_lx VARCHAR(1),
    l_created_time TIMESTAMP WITHOUT TIME ZONE,
    l_access_time TIMESTAMP WITHOUT TIME ZONE,
    l_order_phone VARCHAR(20),
    l_price NUMERIC(18, 4),
    l_total_fee NUMERIC(18, 4),
    l_sysdate VARCHAR(100),
    l_status VARCHAR(1),
    l_by1 VARCHAR(100),
    l_by2 VARCHAR(100),
    l_by3 VARCHAR(100),
    l_by4 NUMERIC(18, 4)
);

ALTER TABLE public.yz_salehead_temp
    ALTER COLUMN l_price TYPE NUMERIC(18, 4) USING l_price::NUMERIC(18, 4),
    ALTER COLUMN l_total_fee TYPE NUMERIC(18, 4) USING l_total_fee::NUMERIC(18, 4),
    ALTER COLUMN l_by4 TYPE NUMERIC(18, 4) USING l_by4::NUMERIC(18, 4);

COMMENT ON COLUMN public.yz_salehead_temp.l_tid IS '有赞订单编码';
COMMENT ON COLUMN public.yz_salehead_temp.l_ytid IS '有赞原单编码';
COMMENT ON COLUMN public.yz_salehead_temp.l_store_id IS '门店编码';
COMMENT ON COLUMN public.yz_salehead_temp.l_lx IS '销售类型';
COMMENT ON COLUMN public.yz_salehead_temp.l_created_time IS '订单创建时间';
COMMENT ON COLUMN public.yz_salehead_temp.l_access_time IS '订单成功时间';
COMMENT ON COLUMN public.yz_salehead_temp.l_order_phone IS '订单手机号';
COMMENT ON COLUMN public.yz_salehead_temp.l_price IS '订单零售价';
COMMENT ON COLUMN public.yz_salehead_temp.l_total_fee IS '订单实际付款金额（不含邮费）';
COMMENT ON COLUMN public.yz_salehead_temp.l_sysdate IS '传入时间';
COMMENT ON COLUMN public.yz_salehead_temp.l_status IS '数据状态（0未处理，1处理成功）';
"""


def upgrade() -> None:
    # The table was initially created out of band. IF NOT EXISTS reconciles
    # that database safely while still creating it on every fresh deployment.
    op.execute(CREATE_YZ_SALEHEAD_TEMP_SQL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.yz_salehead_temp")
