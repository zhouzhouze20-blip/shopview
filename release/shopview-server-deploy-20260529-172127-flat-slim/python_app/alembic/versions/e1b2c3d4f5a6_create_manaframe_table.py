"""create manaframe table

Revision ID: e1b2c3d4f5a6
Revises: c8f4b7a1d2e3
Create Date: 2026-04-22 14:40:00

"""
from typing import Sequence, Union

from alembic import op


revision: str = "e1b2c3d4f5a6"
down_revision: Union[str, Sequence[str], None] = "c8f4b7a1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MANAFRAME_SQL = r"""
CREATE TABLE IF NOT EXISTS manaframe (
    mfcode VARCHAR(20) NOT NULL,
    mfcname VARCHAR(40) NOT NULL,
    mfename VARCHAR(60),
    mfcatcode VARCHAR(20),
    mfsubject VARCHAR(20),
    mfclass NUMERIC(2) DEFAULT 1 NOT NULL,
    mffcode VARCHAR(20) NOT NULL,
    mfpcode VARCHAR(20) DEFAULT '0' NOT NULL,
    mfflag CHAR(1) DEFAULT 'N' NOT NULL,
    mfstatus CHAR(1) DEFAULT 'Y' NOT NULL,
    mftypecode CHAR(1) NOT NULL,
    mfisweb CHAR(1) DEFAULT 'N' NOT NULL,
    mfcglx CHAR(1) DEFAULT '0' NOT NULL,
    mflsfs CHAR(1) DEFAULT '1' NOT NULL,
    mfisjjps CHAR(1) DEFAULT 'N' NOT NULL,
    mfisjjbl NUMERIC(5, 4),
    mfdefjsyj CHAR(1) DEFAULT '0',
    mfisxh CHAR(1) DEFAULT 'N' NOT NULL,
    mfismgys CHAR(1) DEFAULT 'Y' NOT NULL,
    mfswfzr VARCHAR(20),
    mftel VARCHAR(20),
    mffax VARCHAR(20),
    mfemail VARCHAR(40),
    mfplanmll NUMERIC(5, 4),
    mfplangdfl NUMERIC(5, 4),
    mfplanbdfl NUMERIC(5, 4),
    mfyymj NUMERIC(12, 2),
    mfmemo VARCHAR(80),
    mfisareacenter CHAR(1),
    mfareacenter VARCHAR(20),
    mfsubco VARCHAR(20),
    mfcatgroup VARCHAR(10),
    mfinitflag CHAR(1) DEFAULT 'N',
    mfmanaunit VARCHAR(20),
    mfdsbu CHAR(1),
    mfyt VARCHAR(2),
    mfcattype VARCHAR(20),
    mfgtmj NUMERIC,
    mfgtl NUMERIC,
    mfpmkcmin NUMERIC,
    mfpmkcmax NUMERIC,
    mfjhzq NUMERIC,
    mfasicode VARCHAR(20),
    mfmallsat CHAR(1),
    mflocation VARCHAR(4),
    mfshape VARCHAR(4),
    mflength VARCHAR(4),
    mfeasy CHAR(1),
    mfspxz VARCHAR(10),
    mfzqjh VARCHAR(10),
    mfhygh VARCHAR(10),
    mfytgh VARCHAR(10),
    mfzlgh VARCHAR(10),
    mfkind VARCHAR(2),
    mfjzarea NUMERIC,
    mfzjarea NUMERIC,
    mfarealx CHAR(1),
    mfexprent NUMERIC,
    mfexpsj NUMERIC,
    mfcentertype VARCHAR(10),
    mfsupplywh VARCHAR(20),
    mfis_xssy CHAR(1),
    mfhth VARCHAR(20),
    mfoprid VARCHAR(20),
    mfadtid VARCHAR(20),
    mflast_modified TIMESTAMP DEFAULT NOW(),
    mflast_billid VARCHAR(6),
    mflast_billno VARCHAR(20),
    mflast_operid VARCHAR(20),
    mfoprdate TIMESTAMP,
    mfadtdate TIMESTAMP,
    mfsource CHAR(1),
    mfld VARCHAR(20),
    mflc VARCHAR(20),
    mfjyfs VARCHAR(20),
    mfjywz VARCHAR(20),
    mfjyqy VARCHAR(20),
    mfchr1 VARCHAR(40),
    mfchr2 VARCHAR(40),
    mfchr3 VARCHAR(40),
    mfnum1 NUMERIC,
    mfnum2 NUMERIC,
    mfnum3 NUMERIC,
    CONSTRAINT pk_manaframe PRIMARY KEY (mfcode)
);

COMMENT ON TABLE manaframe IS '[MF]管理架构';
COMMENT ON COLUMN manaframe.mfcode IS '编码';
COMMENT ON COLUMN manaframe.mfcname IS '中文名称';
COMMENT ON COLUMN manaframe.mfcatcode IS '经营区域';
COMMENT ON COLUMN manaframe.mfstatus IS '状态';
COMMENT ON COLUMN manaframe.mfjyfs IS '经营方式   (燕莎需求)';
COMMENT ON COLUMN manaframe.mfjywz IS '经营位置   (燕莎需求)';
COMMENT ON COLUMN manaframe.mfjyqy IS '区域   (燕莎需求)';

CREATE INDEX IF NOT EXISTS idx_manaframe_cat ON manaframe (mfcatcode);
CREATE INDEX IF NOT EXISTS idx_manaframe_class ON manaframe (mfclass);
CREATE INDEX IF NOT EXISTS idx_manaframe_fcode ON manaframe (mffcode);
CREATE INDEX IF NOT EXISTS idx_manaframe_pcode ON manaframe (mfpcode);
CREATE INDEX IF NOT EXISTS idx_manaframe_type ON manaframe (mftypecode);
CREATE INDEX IF NOT EXISTS idx_manaframe_name ON manaframe (mfcname);
"""


def upgrade() -> None:
    op.get_bind().exec_driver_sql(MANAFRAME_SQL)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_manaframe_name")
    op.execute("DROP INDEX IF EXISTS idx_manaframe_type")
    op.execute("DROP INDEX IF EXISTS idx_manaframe_pcode")
    op.execute("DROP INDEX IF EXISTS idx_manaframe_fcode")
    op.execute("DROP INDEX IF EXISTS idx_manaframe_class")
    op.execute("DROP INDEX IF EXISTS idx_manaframe_cat")
    op.execute("DROP TABLE IF EXISTS manaframe")
