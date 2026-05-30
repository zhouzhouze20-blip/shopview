"""create finance voucher detail sync table

Revision ID: a0b1c2d3e4f5
Revises: 9d0e1f2a3b4c
Create Date: 2026-05-18
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, Sequence[str], None] = "9d0e1f2a3b4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS bh_dw_gl_detail_fact2 (
    pk_detail VARCHAR(20),
    pk_voucher VARCHAR(20),
    pk_accsubj VARCHAR(20),
    subject_code VARCHAR(40),
    pk_currtype VARCHAR(20),
    pk_sob VARCHAR(20),
    pk_corp VARCHAR(4),
    price NUMERIC(20, 8),
    excrate1 NUMERIC(15, 8),
    explanation VARCHAR(300),
    excrate2 NUMERIC(15, 8),
    debitquantity NUMERIC(28, 8),
    debitamount NUMERIC(28, 8),
    fracdebitamount NUMERIC(28, 8),
    localdebitamount NUMERIC(28, 8),
    creditquantity NUMERIC(28, 8),
    creditamount NUMERIC(28, 8),
    fraccreditamount NUMERIC(28, 8),
    localcreditamount NUMERIC(28, 8),
    checkcount INTEGER,
    valuecode VARCHAR(100),
    valuename VARCHAR(100),
    account_year VARCHAR(6),
    account_period VARCHAR(2),
    load_date TIMESTAMP,
    subject_classify VARCHAR(40)
);

COMMENT ON TABLE bh_dw_gl_detail_fact2 IS '财务凭证明细ETL原始同步表';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.pk_detail IS '源系统凭证明细标识，可能重复';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.pk_voucher IS '凭证主键';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.pk_accsubj IS '会计科目主键';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.subject_code IS '会计科目编码';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.pk_currtype IS '币种主键';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.pk_sob IS '账簿主键';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.pk_corp IS '公司编码';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.price IS '单价';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.excrate1 IS '汇率1';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.explanation IS '摘要';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.excrate2 IS '汇率2';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.debitquantity IS '借方数量';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.debitamount IS '借方金额';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.fracdebitamount IS '原币借方金额';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.localdebitamount IS '本币借方金额';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.creditquantity IS '贷方数量';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.creditamount IS '贷方金额';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.fraccreditamount IS '原币贷方金额';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.localcreditamount IS '本币贷方金额';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.checkcount IS '核算项数量';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.valuecode IS '辅助核算编码';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.valuename IS '辅助核算名称';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.account_year IS '会计年度';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.account_period IS '会计期间';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.load_date IS 'ETL加载时间';
COMMENT ON COLUMN bh_dw_gl_detail_fact2.subject_classify IS '科目分类';

CREATE INDEX IF NOT EXISTS idx_bh_gl_detail_voucher
    ON bh_dw_gl_detail_fact2 (pk_voucher);

CREATE INDEX IF NOT EXISTS idx_bh_gl_detail_pk_detail
    ON bh_dw_gl_detail_fact2 (pk_detail);

CREATE INDEX IF NOT EXISTS idx_bh_gl_detail_period
    ON bh_dw_gl_detail_fact2 (account_year, account_period);

CREATE INDEX IF NOT EXISTS idx_bh_gl_detail_subject
    ON bh_dw_gl_detail_fact2 (subject_code);

CREATE INDEX IF NOT EXISTS idx_bh_gl_detail_assist
    ON bh_dw_gl_detail_fact2 (valuecode, valuename);

CREATE INDEX IF NOT EXISTS idx_bh_gl_detail_load_date
    ON bh_dw_gl_detail_fact2 (load_date);

CREATE INDEX IF NOT EXISTS idx_bh_gl_detail_period_subject
    ON bh_dw_gl_detail_fact2 (account_year, account_period, subject_code);
"""


DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS bh_dw_gl_detail_fact2;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
