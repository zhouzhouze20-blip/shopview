"""Expand headquarters rental settlement detail lines for drill-down.

Revision ID: c2e3f4a5b6c7
Revises: b1d2e3f4a5b6
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "b1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DETAIL_COLUMNS = (
    ("sdtflag", "CHAR(1)"),
    ("sdtitemcode", "VARCHAR(20)"),
    ("item_name_raw", "TEXT"),
    ("sdtstartdate", "TIMESTAMP"),
    ("sdtenddate", "TIMESTAMP"),
    ("sdtdep", "VARCHAR(20)"),
    ("sdtckamount", "NUMERIC(20, 4)"),
    ("sdtyfamount", "NUMERIC(20, 4)"),
    ("sdtmemo", "TEXT"),
    ("sdtdkamount", "NUMERIC(20, 4)"),
    ("sdttype", "CHAR(1)"),
    ("sdtisadv", "CHAR(1)"),
    ("sdtadjamount", "NUMERIC(20, 4)"),
    ("sdtxssr", "NUMERIC(20, 4)"),
    ("sdthsy", "VARCHAR(10)"),
    ("sdtcalcplace", "VARCHAR(30)"),
    ("sdtmfjzmj", "NUMERIC(20, 4)"),
    ("sdtmfzjmj", "NUMERIC(20, 4)"),
    ("sdttaxrate", "NUMERIC(12, 6)"),
    ("sdtnotaxamount", "NUMERIC(20, 4)"),
)


def upgrade() -> None:
    for name, data_type in DETAIL_COLUMNS:
        op.execute(f"ALTER TABLE ods.hq_supsettledettot ADD COLUMN {name} {data_type}")
    op.execute(
        "CREATE INDEX ix_hq_supsettledettot_itemcode "
        "ON ods.hq_supsettledettot (sdtitemcode)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ods.ix_hq_supsettledettot_itemcode")
    for name, _data_type in reversed(DETAIL_COLUMNS):
        op.execute(
            f"ALTER TABLE ods.hq_supsettledettot DROP COLUMN IF EXISTS {name}"
        )
