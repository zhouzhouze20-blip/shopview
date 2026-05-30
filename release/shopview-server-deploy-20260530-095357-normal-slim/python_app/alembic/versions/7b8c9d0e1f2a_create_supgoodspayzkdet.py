"""create supplier goods payment discount allocation table

Revision ID: 7b8c9d0e1f2a
Revises: 6a7b8c9d0e1f
Create Date: 2026-05-12
"""
from typing import Sequence, Union

from alembic import op


revision: str = "7b8c9d0e1f2a"
down_revision: Union[str, Sequence[str], None] = "6a7b8c9d0e1f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SUPGOODSPAYZKDET_SQL = r"""
CREATE TABLE IF NOT EXISTS supgoodspayzkdet (
    sgpbillno NUMERIC NOT NULL,
    sgprowno NUMERIC NOT NULL,
    sgppmcode VARCHAR(4) NOT NULL,
    sgpqtype VARCHAR(100),
    sgppmtype CHAR(1) NOT NULL,
    sgpgdrow NUMERIC NOT NULL,
    sgpgdid VARCHAR(20) NOT NULL,
    sgpjglseq NUMERIC NOT NULL,
    sgpmfid VARCHAR(20),
    sgpsupid VARCHAR(20),
    sgpwmid CHAR(1),
    sgpmoney NUMERIC(18, 4),
    sgperate NUMERIC(18, 6),
    sgpgdcjje NUMERIC(18, 4) NOT NULL,
    sgpgdmoney NUMERIC(18, 4) NOT NULL,
    sgpgspayzk NUMERIC(18, 4),
    sgpjglmoney NUMERIC(18, 4),
    sgpjglpayzk NUMERIC(18, 4) DEFAULT 0,
    sgpjglsupzkfd NUMERIC(18, 6) DEFAULT 0,
    sgpjglsupzk NUMERIC(18, 4) DEFAULT 0,
    sgpfttype NUMERIC,
    sgpjglshopzk NUMERIC(18, 4) DEFAULT 0,
    CONSTRAINT pk_supgoodspayzkdet PRIMARY KEY (sgpbillno, sgprowno, sgpgdrow, sgpjglseq)
);

COMMENT ON TABLE supgoodspayzkdet IS '供应商付款方式折扣分摊明细[SGP]';
COMMENT ON COLUMN supgoodspayzkdet.sgpbillno IS '小票单号';
COMMENT ON COLUMN supgoodspayzkdet.sgprowno IS '付款行号';
COMMENT ON COLUMN supgoodspayzkdet.sgppmcode IS '付款方式代码';
COMMENT ON COLUMN supgoodspayzkdet.sgpqtype IS '券类型';
COMMENT ON COLUMN supgoodspayzkdet.sgppmtype IS '付款方式类型';
COMMENT ON COLUMN supgoodspayzkdet.sgpgdrow IS '商品行号';
COMMENT ON COLUMN supgoodspayzkdet.sgpgdid IS '商品编码';
COMMENT ON COLUMN supgoodspayzkdet.sgpjglseq IS 'JXCGOODSLIST.JGLSEQ';
COMMENT ON COLUMN supgoodspayzkdet.sgpmfid IS '柜组';
COMMENT ON COLUMN supgoodspayzkdet.sgpsupid IS '供应商';
COMMENT ON COLUMN supgoodspayzkdet.sgpwmid IS '经营方式';
COMMENT ON COLUMN supgoodspayzkdet.sgpmoney IS '付款方式金额';
COMMENT ON COLUMN supgoodspayzkdet.sgperate IS '付款方式汇率';
COMMENT ON COLUMN supgoodspayzkdet.sgpgdcjje IS '商品成交金额';
COMMENT ON COLUMN supgoodspayzkdet.sgpgdmoney IS '商品行分摊金额';
COMMENT ON COLUMN supgoodspayzkdet.sgpgspayzk IS '商品行分摊不计收入金额';
COMMENT ON COLUMN supgoodspayzkdet.sgpjglmoney IS 'jgl行分摊金额';
COMMENT ON COLUMN supgoodspayzkdet.sgpjglpayzk IS 'jgl行分摊不计收入金额';
COMMENT ON COLUMN supgoodspayzkdet.sgpjglsupzkfd IS 'jgl供应商折扣分摊比例';
COMMENT ON COLUMN supgoodspayzkdet.sgpjglsupzk IS 'jgl供应商折扣分摊金额';
COMMENT ON COLUMN supgoodspayzkdet.sgpfttype IS '折扣分摊类型';
COMMENT ON COLUMN supgoodspayzkdet.sgpjglshopzk IS 'jgl商场折扣分摊金额';

CREATE INDEX IF NOT EXISTS idx_supgoodspayzkdet_bill_pay
    ON supgoodspayzkdet (sgpbillno, sgppmcode, sgppmtype);
CREATE INDEX IF NOT EXISTS idx_supgoodspayzkdet_bill_row
    ON supgoodspayzkdet (sgpbillno, sgprowno);
CREATE INDEX IF NOT EXISTS idx_supgoodspayzkdet_mf
    ON supgoodspayzkdet (sgpmfid);
CREATE INDEX IF NOT EXISTS idx_supgoodspayzkdet_sup
    ON supgoodspayzkdet (sgpsupid);
"""


def upgrade() -> None:
    op.execute(SUPGOODSPAYZKDET_SQL)


def downgrade() -> None:
    op.drop_index("idx_supgoodspayzkdet_sup", table_name="supgoodspayzkdet")
    op.drop_index("idx_supgoodspayzkdet_mf", table_name="supgoodspayzkdet")
    op.drop_index("idx_supgoodspayzkdet_bill_row", table_name="supgoodspayzkdet")
    op.drop_index("idx_supgoodspayzkdet_bill_pay", table_name="supgoodspayzkdet")
    op.drop_table("supgoodspayzkdet")
