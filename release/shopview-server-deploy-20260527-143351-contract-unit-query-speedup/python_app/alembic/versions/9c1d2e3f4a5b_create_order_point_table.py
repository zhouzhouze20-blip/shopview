"""create order_point table (小票积分表)

Revision ID: 9c1d2e3f4a5b
Revises: a7b8c9d0e1f2
Create Date: 2026-05-09

"""
from typing import Sequence, Union

from alembic import op


revision: str = "9c1d2e3f4a5b"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ORDER_POINT_SQL = r"""
CREATE TABLE IF NOT EXISTS order_point (
    order_id VARCHAR(50) NOT NULL,
    point NUMERIC(10, 2),
    remark VARCHAR(250),
    CONSTRAINT pk_order_point PRIMARY KEY (order_id)
);

COMMENT ON TABLE order_point IS '小票积分表';
COMMENT ON COLUMN order_point.order_id IS '小票号/订单号';
COMMENT ON COLUMN order_point.point IS '积分，整数8位 + 小数2位';
COMMENT ON COLUMN order_point.remark IS '备注';
"""


def upgrade() -> None:
    op.execute(ORDER_POINT_SQL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS order_point;")
