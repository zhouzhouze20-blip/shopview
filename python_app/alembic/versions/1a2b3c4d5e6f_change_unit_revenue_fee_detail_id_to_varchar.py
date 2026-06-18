"""change unit revenue fee detail id to varchar

Revision ID: 1a2b3c4d5e6f
Revises: f9a0b1c2d3e4
Create Date: 2026-06-05

"""
from typing import Sequence, Union

from alembic import op


revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, Sequence[str], None] = "f9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
ALTER TABLE unit_revenue_fee_detail
    ALTER COLUMN id DROP DEFAULT,
    ALTER COLUMN id TYPE VARCHAR(50) USING id::varchar;

DROP SEQUENCE IF EXISTS unit_revenue_fee_detail_id_seq;
"""


DOWNGRADE_SQL = r"""
CREATE SEQUENCE IF NOT EXISTS unit_revenue_fee_detail_id_seq;

ALTER TABLE unit_revenue_fee_detail
    ALTER COLUMN id TYPE BIGINT USING id::bigint,
    ALTER COLUMN id SET DEFAULT nextval('unit_revenue_fee_detail_id_seq');

ALTER SEQUENCE unit_revenue_fee_detail_id_seq
    OWNED BY unit_revenue_fee_detail.id;

SELECT setval(
    'unit_revenue_fee_detail_id_seq',
    COALESCE((SELECT MAX(id) FROM unit_revenue_fee_detail), 1),
    (SELECT COUNT(*) > 0 FROM unit_revenue_fee_detail)
);
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
