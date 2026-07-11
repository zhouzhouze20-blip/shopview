"""create ERP point rule tables

Revision ID: f0a1b2c3d4e6
Revises: e2f3a4b5c6d7
Create Date: 2026-07-09
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f0a1b2c3d4e6"
down_revision: Union[str, Sequence[str], None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS card_paymoderule (
    jygs VARCHAR(10) NOT NULL,
    fkcode VARCHAR(10) NOT NULL,
    fkname VARCHAR(50) NOT NULL,
    chr1 VARCHAR(20),
    chr2 VARCHAR(20),
    chr3 VARCHAR(20),
    num1 NUMERIC,
    num2 NUMERIC,
    num3 NUMERIC,
    memo VARCHAR(200),
    CONSTRAINT pk_card_paymoderule PRIMARY KEY (jygs, fkcode)
);

COMMENT ON TABLE card_paymoderule IS '不参与积分的付款方式';
COMMENT ON COLUMN card_paymoderule.jygs IS '经营公司';
COMMENT ON COLUMN card_paymoderule.fkcode IS '付款代码';
COMMENT ON COLUMN card_paymoderule.fkname IS '付款名称';
COMMENT ON COLUMN card_paymoderule.chr1 IS 'CHR1';
COMMENT ON COLUMN card_paymoderule.chr2 IS 'CHR2';
COMMENT ON COLUMN card_paymoderule.chr3 IS 'CHR3';
COMMENT ON COLUMN card_paymoderule.num1 IS 'NUM1';
COMMENT ON COLUMN card_paymoderule.num2 IS 'NUM2';
COMMENT ON COLUMN card_paymoderule.num3 IS 'NUM3';
COMMENT ON COLUMN card_paymoderule.memo IS '备注';

CREATE TABLE IF NOT EXISTS rulejfrate (
    jfseq NUMERIC NOT NULL,
    jfjygs VARCHAR(20) NOT NULL,
    jfmkt VARCHAR(20) NOT NULL,
    jfcusttype VARCHAR(4) NOT NULL,
    jfbillno VARCHAR(20) NOT NULL,
    jfmode VARCHAR(20),
    jfgdid VARCHAR(20),
    jfmfid VARCHAR(20),
    jfcatcode VARCHAR(10),
    jfppcode VARCHAR(10),
    jfpropcode VARCHAR(20),
    jfrate NUMERIC(16, 4),
    jfchr1 VARCHAR(60),
    jfchr2 VARCHAR(50),
    jfchr3 VARCHAR(40),
    jfnum1 NUMERIC,
    jfnum2 NUMERIC,
    jfnum3 NUMERIC,
    jfcardmode CHAR(1) DEFAULT 'A' NOT NULL,
    jfbank VARCHAR(10),
    CONSTRAINT pk_rulejfrate PRIMARY KEY (jfseq)
);

COMMENT ON COLUMN rulejfrate.jfseq IS '序号';
COMMENT ON COLUMN rulejfrate.jfjygs IS '经营公司';
COMMENT ON COLUMN rulejfrate.jfmkt IS '门店';
COMMENT ON COLUMN rulejfrate.jfcusttype IS '会员类型';
COMMENT ON COLUMN rulejfrate.jfbillno IS '单据编号';
COMMENT ON COLUMN rulejfrate.jfmode IS '方式 1 商品 2 柜组 3 品牌 4 小类 5 中类 6 大类';
COMMENT ON COLUMN rulejfrate.jfgdid IS '商品';
COMMENT ON COLUMN rulejfrate.jfmfid IS '柜组';
COMMENT ON COLUMN rulejfrate.jfcatcode IS '类别';
COMMENT ON COLUMN rulejfrate.jfppcode IS '品牌';
COMMENT ON COLUMN rulejfrate.jfpropcode IS '属性码';
COMMENT ON COLUMN rulejfrate.jfrate IS '积分率';
COMMENT ON COLUMN rulejfrate.jfnum1 IS '特价积分率';
COMMENT ON COLUMN rulejfrate.jfcardmode IS '卡片类型(A/N/C,所有卡/普通卡/联名卡)';
COMMENT ON COLUMN rulejfrate.jfbank IS '发卡银行';

CREATE INDEX IF NOT EXISTS idx_rulejfrate_custtype ON rulejfrate (jfcusttype);
CREATE INDEX IF NOT EXISTS idx_rulejfrate_mkt ON rulejfrate (jfmkt);
CREATE INDEX IF NOT EXISTS idx_rulejfrate_mfid_seq ON rulejfrate (jfmfid, jfseq);

CREATE TABLE IF NOT EXISTS sellpaygoods (
    spgbillno NUMERIC NOT NULL,
    spgrowno NUMERIC NOT NULL,
    spgpmcode VARCHAR(20) NOT NULL,
    spgpayerid VARCHAR(100),
    spgpmtype CHAR(1),
    spgmoney NUMERIC,
    spgerate NUMERIC,
    spggdrow NUMERIC NOT NULL,
    spggdid VARCHAR(20) NOT NULL,
    spggdcjje NUMERIC NOT NULL,
    spggdmoney NUMERIC NOT NULL,
    spgno VARCHAR(255),
    spgispop CHAR(1),
    spgsysy NUMERIC,
    spgpmisjf CHAR(1),
    spgsrc CHAR(1) DEFAULT 'P',
    spgsqyy NUMERIC,
    sppmjfbs NUMERIC DEFAULT 0,
    sppmjfbno VARCHAR(20),
    CONSTRAINT pk_sellpaygoods PRIMARY KEY (spgbillno, spgrowno, spggdrow)
);

COMMENT ON TABLE sellpaygoods IS '销售付款商品分摊情况[SPG]';
COMMENT ON COLUMN sellpaygoods.spgbillno IS '单号';
COMMENT ON COLUMN sellpaygoods.spgrowno IS '付款行号';
COMMENT ON COLUMN sellpaygoods.spgpmcode IS '付款方式代码';
COMMENT ON COLUMN sellpaygoods.spgpayerid IS '证件号（第一个字符记录返券的类型）';
COMMENT ON COLUMN sellpaygoods.spgpmtype IS '付款方式类型';
COMMENT ON COLUMN sellpaygoods.spgmoney IS '付款方式金额';
COMMENT ON COLUMN sellpaygoods.spgerate IS '付款方式汇率';
COMMENT ON COLUMN sellpaygoods.spggdrow IS '商品行号';
COMMENT ON COLUMN sellpaygoods.spggdid IS '商品编码';
COMMENT ON COLUMN sellpaygoods.spggdcjje IS '商品成交金额';
COMMENT ON COLUMN sellpaygoods.spggdmoney IS '商品分摊金额';
COMMENT ON COLUMN sellpaygoods.spgno IS '原始单据号';
COMMENT ON COLUMN sellpaygoods.spgpmisjf IS '付款方式是否积分';
COMMENT ON COLUMN sellpaygoods.spgsrc IS 'P-POS,A-Auto';
COMMENT ON COLUMN sellpaygoods.spgsqyy IS '收券溢余';
COMMENT ON COLUMN sellpaygoods.sppmjfbs IS '付款方式积分倍数';
COMMENT ON COLUMN sellpaygoods.sppmjfbno IS '付款方式积分倍数促销单';

CREATE INDEX IF NOT EXISTS idx_sellpaygoods_billno ON sellpaygoods (spgbillno);
CREATE INDEX IF NOT EXISTS idx_sellpaygoods_gdid ON sellpaygoods (spggdid);
CREATE INDEX IF NOT EXISTS idx_sellpaygoods_pmcode ON sellpaygoods (spgpmcode);
"""


DOWNGRADE_SQL = r"""
DROP INDEX IF EXISTS idx_sellpaygoods_pmcode;
DROP INDEX IF EXISTS idx_sellpaygoods_gdid;
DROP INDEX IF EXISTS idx_sellpaygoods_billno;
DROP TABLE IF EXISTS sellpaygoods;

DROP INDEX IF EXISTS idx_rulejfrate_mfid_seq;
DROP INDEX IF EXISTS idx_rulejfrate_mkt;
DROP INDEX IF EXISTS idx_rulejfrate_custtype;
DROP TABLE IF EXISTS rulejfrate;

DROP TABLE IF EXISTS card_paymoderule;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
