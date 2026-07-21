"""create JXCGOODSLIST incremental-sync target

Revision ID: d1b3c5e7f9a2
Revises: c1a4e7b9d2f6
Create Date: 2026-07-20

The column names and types mirror the PAPI task named
"JXCGOODSLIST 2026增量同步".  IF NOT EXISTS keeps this migration safe for the
already-provisioned sales_db target while making fresh deployments repeatable.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "d1b3c5e7f9a2"
down_revision: Union[str, Sequence[str], None] = "c1a4e7b9d2f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS jxcgoodslist (
    jglseq NUMERIC NOT NULL,
    jgldate TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    jgltran CHAR(1) NOT NULL,
    jglbatchseq NUMERIC NOT NULL,
    jglbillno VARCHAR(20) NOT NULL,
    jglfsdate TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    jglbap CHAR(1) NOT NULL,
    jglmarket VARCHAR(20) NOT NULL,
    jglmfid VARCHAR(20) NOT NULL,
    jglmmkt VARCHAR(20) NOT NULL,
    jglmmfid VARCHAR(20) NOT NULL,
    jglsupid VARCHAR(20) NOT NULL,
    jglwmid CHAR(1) NOT NULL,
    jglgdid VARCHAR(20) NOT NULL,
    jglgdtype CHAR(1) NOT NULL,
    jglmanamode CHAR(1) NOT NULL,
    jglcatid VARCHAR(10) NOT NULL,
    jglppcode VARCHAR(6) NOT NULL,
    jgldac CHAR(1) NOT NULL,
    jglsl NUMERIC(16, 4) NOT NULL,
    jgljjtax NUMERIC(8, 4) NOT NULL,
    jglhsjj NUMERIC(14, 4) NOT NULL,
    jglbhsjj NUMERIC(14, 4) NOT NULL,
    jglhsjjje NUMERIC(16, 4) NOT NULL,
    jglbhsjjje NUMERIC(16, 4) NOT NULL,
    jglcbtax NUMERIC(8, 4) NOT NULL,
    jglhscbj NUMERIC(14, 4) NOT NULL,
    jglbhscbj NUMERIC(14, 4) NOT NULL,
    jglhscbje NUMERIC(16, 4) NOT NULL,
    jglbhscbje NUMERIC(16, 4) NOT NULL,
    jglsj NUMERIC(12, 2) NOT NULL,
    jglsjje NUMERIC(16, 4) NOT NULL,
    jglqcsl NUMERIC(16, 4) NOT NULL,
    jglqchsjjje NUMERIC(16, 4) NOT NULL,
    jglqcbhsjjje NUMERIC(16, 4) NOT NULL,
    jglqchscbje NUMERIC(16, 4) NOT NULL,
    jglqcbhscbje NUMERIC(16, 4) NOT NULL,
    jglqcsjje NUMERIC(16, 4) NOT NULL,
    jglqmsl NUMERIC(16, 4) NOT NULL,
    jglqmhsjjje NUMERIC(16, 4) NOT NULL,
    jglqmbhsjjje NUMERIC(16, 4) NOT NULL,
    jglqmhscbje NUMERIC(16, 4) NOT NULL,
    jglqmbhscbje NUMERIC(16, 4) NOT NULL,
    jglqmsjje NUMERIC(16, 4) NOT NULL,
    jglintjsyj CHAR(1) NOT NULL,
    jglintjsbz CHAR(1) NOT NULL,
    jglintjsdate TIMESTAMP WITHOUT TIME ZONE,
    jglintjsdh VARCHAR(20),
    jglsupjsyj CHAR(1) NOT NULL,
    jglsupjsbz CHAR(1) NOT NULL,
    jglsupjsdate TIMESTAMP WITHOUT TIME ZONE,
    jglsupjsdh VARCHAR(20),
    jgln1 NUMERIC(16, 4) NOT NULL,
    jgln2 NUMERIC(16, 4) NOT NULL,
    jgln3 NUMERIC(16, 4) NOT NULL,
    jgln4 NUMERIC(16, 4) NOT NULL,
    jgln5 NUMERIC(16, 4) NOT NULL,
    jgln6 NUMERIC(16, 4) NOT NULL,
    jgln7 NUMERIC(16, 4) NOT NULL,
    jgln8 NUMERIC(16, 4) NOT NULL,
    jgln9 NUMERIC(16, 4) NOT NULL,
    jgln10 NUMERIC(16, 4) NOT NULL,
    jgln11 NUMERIC(16, 4) NOT NULL,
    jgln12 NUMERIC(16, 4) NOT NULL,
    jgln13 NUMERIC(16, 4) NOT NULL,
    jgln14 NUMERIC(16, 4) NOT NULL,
    jgln15 NUMERIC(16, 4) NOT NULL,
    jglvc1 VARCHAR(20),
    jglvc2 VARCHAR(20),
    jglvc3 VARCHAR(48),
    jglvc4 VARCHAR(48),
    jglvc5 VARCHAR(64),
    jglmd CHAR(1) NOT NULL,
    jglshelf VARCHAR(20),
    jgljs NUMERIC,
    jglsample CHAR(1),
    jglzk1 NUMERIC(16, 4) NOT NULL,
    jglzk2 NUMERIC(16, 4) NOT NULL,
    jglzk3 NUMERIC(16, 4) NOT NULL,
    jglzk4 NUMERIC(16, 4) NOT NULL,
    jglsupzk1 NUMERIC(16, 4) NOT NULL,
    jglsupzk2 NUMERIC(16, 4) NOT NULL,
    jglsupzk3 NUMERIC(16, 4) NOT NULL,
    jglsupzk4 NUMERIC(16, 4) NOT NULL,
    jglfhmfid VARCHAR(20),
    jglshmfid VARCHAR(20),
    jglxstzhsjjje NUMERIC(16, 4) NOT NULL,
    jglxstzbhsjjje NUMERIC(16, 4) NOT NULL,
    jglxstzhscbje NUMERIC(16, 4) NOT NULL,
    jglxstzbhscbje NUMERIC(16, 4) NOT NULL,
    jglxstzn5 NUMERIC(16, 4),
    jglxstzsupzk1 NUMERIC(16, 4),
    jglxstzsupzk2 NUMERIC(16, 4),
    jglxstzsupzk3 NUMERIC(16, 4),
    jglxstzsupzk4 NUMERIC(16, 4),
    jglkl NUMERIC(5, 4),
    jglbasekl NUMERIC(5, 4),
    jglbillid VARCHAR(3),
    jgln16 NUMERIC,
    jgln17 NUMERIC,
    jgln18 NUMERIC,
    jgln19 NUMERIC,
    jgln20 NUMERIC,
    jgln21 NUMERIC,
    jgln22 NUMERIC,
    jgln23 NUMERIC,
    jgln24 NUMERIC,
    jgln25 NUMERIC,
    jglvc6 VARCHAR(20),
    jglvc7 VARCHAR(20),
    jglvc8 VARCHAR(20),
    jglvc9 VARCHAR(20),
    jglvc10 VARCHAR(20),
    jglvc11 VARCHAR(20),
    jglvc12 VARCHAR(20),
    jglvc13 VARCHAR(20),
    jglvc14 VARCHAR(20),
    jglvc15 VARCHAR(20),
    jgltpid CHAR(2),
    jglspsx VARCHAR(20),
    jgln26 NUMERIC,
    jgln27 NUMERIC,
    jgln28 NUMERIC,
    jgln29 NUMERIC,
    CONSTRAINT pk_jxcgoodslist PRIMARY KEY (jglseq)
);

COMMENT ON TABLE jxcgoodslist IS 'JXCGOODSLIST 2026增量同步目标；商品进销存流水';
CREATE INDEX IF NOT EXISTS idx_jxcgoodslist_jgldate ON jxcgoodslist (jgldate);
CREATE INDEX IF NOT EXISTS idx_jxcgoodslist_jglfsdate ON jxcgoodslist (jglfsdate);
CREATE INDEX IF NOT EXISTS idx_jxcgoodslist_market_fsdate ON jxcgoodslist (jglmarket, jglfsdate);
CREATE INDEX IF NOT EXISTS idx_jxcgoodslist_mfid_fsdate ON jxcgoodslist (jglmfid, jglfsdate);
CREATE INDEX IF NOT EXISTS idx_jxcgoodslist_supid_fsdate ON jxcgoodslist (jglsupid, jglfsdate);
CREATE INDEX IF NOT EXISTS idx_jxcgoodslist_gdid_fsdate ON jxcgoodslist (jglgdid, jglfsdate);
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS jxcgoodslist CASCADE")
