"""create area category table

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-07-10
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
CREATE TABLE area_category (
    area_code VARCHAR(100),
    area_name VARCHAR(100),
    category_code VARCHAR(100),
    category_name VARCHAR(100)
);

COMMENT ON TABLE area_category IS '区域与品类关系';
COMMENT ON COLUMN area_category.area_code IS '区域编码';
COMMENT ON COLUMN area_category.area_name IS '区域名称';
COMMENT ON COLUMN area_category.category_code IS '品类编码';
COMMENT ON COLUMN area_category.category_name IS '品类名称';
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.drop_table("area_category")
