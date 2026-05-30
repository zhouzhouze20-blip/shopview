"""update order_point primary key

Revision ID: 2c3d4e5f6a7b
Revises: 1b2c3d4e5f6a
Create Date: 2026-05-09

"""
from typing import Sequence, Union

from alembic import op


revision: str = "2c3d4e5f6a7b"
down_revision: Union[str, Sequence[str], None] = "1b2c3d4e5f6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
ALTER TABLE order_point DROP CONSTRAINT IF EXISTS ck_order_point_point_type;
ALTER TABLE order_point DROP CONSTRAINT IF EXISTS pk_order_point;

ALTER TABLE order_point ALTER COLUMN point_type TYPE VARCHAR(250);
UPDATE order_point SET point_type = '' WHERE point_type IS NULL;
ALTER TABLE order_point ALTER COLUMN point_type SET NOT NULL;

ALTER TABLE order_point
    ADD CONSTRAINT pk_order_point PRIMARY KEY (order_id, point_type);

COMMENT ON COLUMN order_point.point_type IS '积分类型';
"""


DOWNGRADE_SQL = r"""
ALTER TABLE order_point DROP CONSTRAINT IF EXISTS pk_order_point;

ALTER TABLE order_point ALTER COLUMN point_type TYPE VARCHAR(50);
ALTER TABLE order_point ALTER COLUMN point_type DROP NOT NULL;
ALTER TABLE order_point
    ADD CONSTRAINT ck_order_point_point_type
    CHECK (point_type IS NULL OR point_type IN ('消费加积分', '生日月多倍积分'));

ALTER TABLE order_point
    ADD CONSTRAINT pk_order_point PRIMARY KEY (order_id);
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
