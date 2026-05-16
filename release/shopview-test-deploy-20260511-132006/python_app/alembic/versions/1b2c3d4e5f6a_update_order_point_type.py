"""update order_point point type

Revision ID: 1b2c3d4e5f6a
Revises: 0a1b2c3d4e5f
Create Date: 2026-05-09

"""
from typing import Sequence, Union

from alembic import op


revision: str = "1b2c3d4e5f6a"
down_revision: Union[str, Sequence[str], None] = "0a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
ALTER TABLE order_point DROP COLUMN IF EXISTS remark;
ALTER TABLE order_point ADD COLUMN IF NOT EXISTS point_type VARCHAR(50);

ALTER TABLE order_point DROP CONSTRAINT IF EXISTS ck_order_point_point_type;
ALTER TABLE order_point
    ADD CONSTRAINT ck_order_point_point_type
    CHECK (point_type IS NULL OR point_type IN ('消费加积分', '生日月多倍积分'));

COMMENT ON COLUMN order_point.order_id IS '序号/小票号';
COMMENT ON COLUMN order_point.point IS '积分';
COMMENT ON COLUMN order_point.point_type IS '积分类型：消费加积分、生日月多倍积分';
"""


DOWNGRADE_SQL = r"""
ALTER TABLE order_point DROP CONSTRAINT IF EXISTS ck_order_point_point_type;
ALTER TABLE order_point DROP COLUMN IF EXISTS point_type;
ALTER TABLE order_point ADD COLUMN IF NOT EXISTS remark VARCHAR(250);
COMMENT ON COLUMN order_point.remark IS '备注';
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
