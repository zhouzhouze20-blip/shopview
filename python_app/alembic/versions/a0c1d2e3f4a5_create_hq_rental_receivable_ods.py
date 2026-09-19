"""Create local ODS tables for headquarters rental receivables.

Revision ID: a0c1d2e3f4a5
Revises: f9b0c1d2e3f4
"""

from typing import Sequence, Union

from alembic import op


revision: str = "a0c1d2e3f4a5"
down_revision: Union[str, Sequence[str], None] = "f9b0c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ods")
    op.execute(
        """
        CREATE TABLE ods.hq_supsettlehead (
          sshbillno VARCHAR(20) PRIMARY KEY,
          sshdjlb CHAR(1) NOT NULL,
          sshflag CHAR(1) NOT NULL,
          sshsupid VARCHAR(20) NOT NULL,
          supplier_name TEXT,
          sshwmid CHAR(1) NOT NULL,
          sshmkt VARCHAR(20) NOT NULL,
          sshmfid VARCHAR(20),
          group_name TEXT,
          sshcontno VARCHAR(20),
          sshlastdate TIMESTAMP,
          sshthisdate TIMESTAMP NOT NULL,
          source_loaded_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_hq_supsettlehead_date_status "
        "ON ods.hq_supsettlehead (sshthisdate, sshflag)"
    )
    op.execute(
        "CREATE INDEX ix_hq_supsettlehead_scope "
        "ON ods.hq_supsettlehead (sshmkt, sshmfid, sshsupid)"
    )

    op.execute(
        """
        CREATE TABLE ods.hq_supsettledettot (
          sdtbillno VARCHAR(20) NOT NULL,
          sdtrowno BIGINT NOT NULL,
          sdtamount NUMERIC(20, 4),
          sdtye NUMERIC(20, 4),
          source_loaded_at TIMESTAMPTZ NOT NULL,
          PRIMARY KEY (sdtbillno, sdtrowno)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_hq_supsettledettot_billno "
        "ON ods.hq_supsettledettot (sdtbillno)"
    )

    op.execute(
        """
        CREATE TABLE ods.hq_supsettlepaydet (
          spdbillno VARCHAR(20) NOT NULL,
          spdrowno BIGINT NOT NULL,
          spdsetbillno VARCHAR(20) NOT NULL,
          source_loaded_at TIMESTAMPTZ NOT NULL,
          PRIMARY KEY (spdbillno, spdrowno)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_hq_supsettlepaydet_setbillno "
        "ON ods.hq_supsettlepaydet (spdsetbillno)"
    )
    op.execute(
        "CREATE INDEX ix_hq_supsettlepaydet_paybillno "
        "ON ods.hq_supsettlepaydet (spdbillno)"
    )

    op.execute(
        """
        CREATE TABLE ods.hq_mallsuppayhead (
          sphbillno VARCHAR(20) PRIMARY KEY,
          sphtype CHAR(1) NOT NULL,
          sphflag CHAR(1) NOT NULL,
          source_loaded_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_hq_mallsuppayhead_type_flag "
        "ON ods.hq_mallsuppayhead (sphtype, sphflag)"
    )

    op.execute(
        "COMMENT ON TABLE ods.hq_supsettlehead IS "
        "'PAPI source 9 headquarters rental settlement headers (WMID=5, DJLB=Z)'"
    )
    op.execute(
        "COMMENT ON TABLE ods.hq_supsettledettot IS "
        "'PAPI source 9 settlement total details for headquarters rental bills'"
    )
    op.execute(
        "COMMENT ON TABLE ods.hq_supsettlepaydet IS "
        "'PAPI source 9 payment links for headquarters rental settlement bills'"
    )
    op.execute(
        "COMMENT ON TABLE ods.hq_mallsuppayhead IS "
        "'PAPI source 9 payment headers linked to headquarters rental settlement bills'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ods.hq_mallsuppayhead")
    op.execute("DROP TABLE IF EXISTS ods.hq_supsettlepaydet")
    op.execute("DROP TABLE IF EXISTS ods.hq_supsettledettot")
    op.execute("DROP TABLE IF EXISTS ods.hq_supsettlehead")
