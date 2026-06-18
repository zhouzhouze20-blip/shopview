"""change unit revenue sales detail id to varchar

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-06-04

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "e8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
ALTER TABLE unit_revenue_sales_detail
    ALTER COLUMN id DROP DEFAULT,
    ALTER COLUMN id TYPE VARCHAR(64) USING id::VARCHAR(64);

DROP SEQUENCE IF EXISTS unit_revenue_sales_detail_id_seq;
"""


DOWNGRADE_SQL = r"""
CREATE SEQUENCE IF NOT EXISTS unit_revenue_sales_detail_id_seq;

ALTER TABLE unit_revenue_sales_detail
    ALTER COLUMN id TYPE BIGINT USING id::BIGINT,
    ALTER COLUMN id SET DEFAULT nextval('unit_revenue_sales_detail_id_seq');

ALTER SEQUENCE unit_revenue_sales_detail_id_seq
    OWNED BY unit_revenue_sales_detail.id;

SELECT setval(
    'unit_revenue_sales_detail_id_seq',
    COALESCE((SELECT MAX(id) FROM unit_revenue_sales_detail), 1),
    (SELECT COUNT(*) > 0 FROM unit_revenue_sales_detail)
);
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
