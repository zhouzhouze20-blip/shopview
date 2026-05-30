"""create contbd_xs table (合同保底区间销售收入)

Revision ID: a3c9e1f7b2d4
Revises: e8b6c4d2a1f0
Create Date: 2026-05-07

"""
from typing import Sequence, Union

from alembic import op


revision: str = "a3c9e1f7b2d4"
down_revision: Union[str, Sequence[str], None] = "e8b6c4d2a1f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONTBD_XS_SQL = r"""
CREATE TABLE IF NOT EXISTS contbd_xs (
    cbcontno VARCHAR(20) NOT NULL,
    cbmkt VARCHAR(20) NOT NULL,
    cbmfid VARCHAR(20) NOT NULL,
    cbeffdate DATE NOT NULL,
    cblapdate DATE NOT NULL,
    cbsum NUMERIC(14, 2),
    xssr NUMERIC(16, 4),
    CONSTRAINT pk_contbd_xs PRIMARY KEY (cbcontno, cbmkt, cbmfid, cbeffdate, cblapdate)
);

COMMENT ON TABLE contbd_xs IS '[CONTBD_XS]合同保底区间销售收入';
COMMENT ON COLUMN contbd_xs.cbcontno IS '合同单号';
COMMENT ON COLUMN contbd_xs.cbmkt IS '门店';
COMMENT ON COLUMN contbd_xs.cbmfid IS '柜组';
COMMENT ON COLUMN contbd_xs.cbeffdate IS '生效日期';
COMMENT ON COLUMN contbd_xs.cblapdate IS '失效日期';
COMMENT ON COLUMN contbd_xs.cbsum IS '保底额';
COMMENT ON COLUMN contbd_xs.xssr IS '销售收入';
"""


def upgrade() -> None:
    op.execute(CONTBD_XS_SQL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS contbd_xs")
