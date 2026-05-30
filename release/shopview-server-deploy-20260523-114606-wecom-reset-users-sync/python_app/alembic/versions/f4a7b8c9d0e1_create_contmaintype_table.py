"""create contmaintype table

Revision ID: f4a7b8c9d0e1
Revises: d4c9e8f1a2b3
Create Date: 2026-04-30

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f4a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "d4c9e8f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONTMAINTYPE_SQL = r"""
CREATE TABLE IF NOT EXISTS contmaintype (
    cmtypecode CHAR(1) NOT NULL,
    cmtypename VARCHAR(20) NOT NULL,
    CONSTRAINT pk_contmaintype PRIMARY KEY (cmtypecode)
);

COMMENT ON TABLE contmaintype IS '[CMTYPE]合同类型';
COMMENT ON COLUMN contmaintype.cmtypecode IS '编码';
COMMENT ON COLUMN contmaintype.cmtypename IS '名称';
"""


def upgrade() -> None:
    op.execute(CONTMAINTYPE_SQL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS contmaintype")
