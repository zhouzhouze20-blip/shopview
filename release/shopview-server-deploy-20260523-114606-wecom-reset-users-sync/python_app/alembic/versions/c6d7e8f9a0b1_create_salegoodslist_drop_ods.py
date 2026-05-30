"""create salegoodslist and drop ods salegoodslist

Revision ID: c6d7e8f9a0b1
Revises: b9e1c2d3f4a5
Create Date: 2026-05-01

"""
from typing import Sequence, Union

from alembic import op


revision: str = "c6d7e8f9a0b1"
down_revision: Union[str, Sequence[str], None] = "b9e1c2d3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SALEGOODSLIST_SQL = r"""
DROP TABLE IF EXISTS ods_salegoodslist;

CREATE TABLE IF NOT EXISTS salegoodslist (
    sgldate DATE NOT NULL,
    sgltpid CHAR(2) NOT NULL,
    sglsummary VARCHAR(10) NOT NULL,
    sglmarket VARCHAR(20) NOT NULL,
    sglmfid VARCHAR(20) NOT NULL,
    sglgdid VARCHAR(20) NOT NULL,
    sglbarcode VARCHAR(20) NOT NULL,
    sglgdtype CHAR(1) NOT NULL,
    sglcatid VARCHAR(10) NOT NULL,
    sgltaxtype CHAR(1) NOT NULL,
    sglxstax NUMERIC(8, 4) NOT NULL,
    sglxftax NUMERIC(8, 4) NOT NULL,
    sglppcode VARCHAR(10) NOT NULL,
    sgluid VARCHAR(6) DEFAULT '00' NOT NULL,
    sglhsrq DATE NOT NULL,
    sglbatchno VARCHAR(20) DEFAULT '0' NOT NULL,
    sglsupid VARCHAR(20) NOT NULL,
    sglanalcode VARCHAR(20),
    sglsj NUMERIC(16, 4) NOT NULL,
    sglkl NUMERIC(5, 4) NOT NULL,
    sgljs NUMERIC(16, 4) NOT NULL,
    sglsl NUMERIC(16, 4) NOT NULL,
    sglsjje NUMERIC(16, 4) NOT NULL,
    sglxssr NUMERIC(16, 4) NOT NULL,
    sglxsse NUMERIC(16, 4) NOT NULL,
    sglxfse NUMERIC(16, 4) NOT NULL,
    sglqtsr NUMERIC(16, 4) NOT NULL,
    sglsysy NUMERIC(16, 4) NOT NULL,
    sglpopsr NUMERIC(16, 4) NOT NULL,
    sglcustsr NUMERIC(16, 4) NOT NULL,
    sglfcdsr NUMERIC(16, 4) NOT NULL,
    sglpfsr NUMERIC(16, 4) NOT NULL,
    sglyxssr NUMERIC(16, 4) NOT NULL,
    sgltotzk NUMERIC(16, 4) NOT NULL,
    sglsupzk NUMERIC(16, 4) NOT NULL,
    sglpopzk NUMERIC(16, 4) NOT NULL,
    sglcustzk NUMERIC(16, 4) NOT NULL,
    sglfcdzk NUMERIC(16, 4) NOT NULL,
    sglpfzk NUMERIC(16, 4) NOT NULL,
    sglgrantzk NUMERIC(16, 4) NOT NULL,
    sglyjhx NUMERIC(16, 4) NOT NULL,
    sglzszk NUMERIC(16, 4) NOT NULL,
    sglthss NUMERIC(16, 4) NOT NULL,
    sgladjustzk NUMERIC(16, 4) NOT NULL,
    sglcash NUMERIC(16, 4) NOT NULL,
    sglcheck NUMERIC(16, 4) NOT NULL,
    sglccard NUMERIC(16, 4) NOT NULL,
    sglfcard NUMERIC(16, 4) NOT NULL,
    sglgcert NUMERIC(16, 4) NOT NULL,
    sglgzje NUMERIC(16, 4) NOT NULL,
    sglopay NUMERIC(16, 4) NOT NULL,
    sgltimes NUMERIC(16, 4),
    sgln1 NUMERIC(16, 4),
    sgln2 NUMERIC(16, 4),
    sgln3 NUMERIC(16, 4),
    sgln4 NUMERIC(16, 4),
    sgln5 NUMERIC(16, 4),
    sglvc1 VARCHAR(20),
    sglvc2 VARCHAR(20),
    sglvc3 VARCHAR(64),
    sglwmid CHAR(1) DEFAULT '1' NOT NULL,
    sglfqje NUMERIC(16, 4) DEFAULT 0,
    sglsqje NUMERIC(16, 4) DEFAULT 0,
    sglqxssr NUMERIC(16, 4) DEFAULT 0,
    sgln6 NUMERIC(16, 4),
    sgln7 NUMERIC(16, 4),
    sgln8 NUMERIC(16, 4),
    sgln9 NUMERIC(16, 4),
    sgln10 NUMERIC(16, 4),
    sglxyksr1 NUMERIC(16, 4) DEFAULT 0,
    sglxyksr2 NUMERIC(16, 4) DEFAULT 0,
    sglxyksr3 NUMERIC(16, 4) DEFAULT 0,
    sglxyksr4 NUMERIC(16, 4) DEFAULT 0,
    sglxyksr5 NUMERIC(16, 4) DEFAULT 0,
    sglxyksr6 NUMERIC(16, 4) DEFAULT 0,
    sglxyksr7 NUMERIC(16, 4) DEFAULT 0,
    sglxyksr8 NUMERIC(16, 4) DEFAULT 0,
    sglxyksr9 NUMERIC(16, 4) DEFAULT 0,
    sglxyksr10 NUMERIC(16, 4) DEFAULT 0,
    sglbillno NUMERIC NOT NULL,
    sglrowno NUMERIC NOT NULL,
    sglbasekl NUMERIC(5, 4),
    sgln11 NUMERIC,
    sgln12 NUMERIC,
    sgln13 NUMERIC,
    sgln14 NUMERIC,
    sgln15 NUMERIC,
    sgln16 NUMERIC,
    sgln17 NUMERIC,
    sgln18 NUMERIC,
    sgln19 NUMERIC,
    sgln20 NUMERIC,
    sgln21 NUMERIC,
    sgln22 NUMERIC,
    sgln23 NUMERIC,
    sgln24 NUMERIC,
    sgln25 NUMERIC,
    sglvc4 VARCHAR(20),
    sglvc5 VARCHAR(20),
    sglvc6 VARCHAR(20),
    sglvc7 VARCHAR(20),
    sglvc8 VARCHAR(20),
    sglvc9 VARCHAR(20),
    sglvc10 VARCHAR(20),
    sglvc11 VARCHAR(20),
    sglvc12 VARCHAR(20),
    sglvc13 VARCHAR(20),
    sglvc14 VARCHAR(20),
    sglvc15 VARCHAR(20),
    sglsaledate DATE,
    sglnetml NUMERIC,
    sglcardtype VARCHAR(10),
    sglsyjid VARCHAR(20),
    sglinvno NUMERIC,
    sglchecker VARCHAR(20),
    sglposcls CHAR(1),
    sglshdate DATE,
    sgltmtype CHAR(1) DEFAULT '0',
    sglmd CHAR(1) DEFAULT '1',
    sglfysl NUMERIC(16, 4),
    sglvip1sr NUMERIC(16, 4),
    sglvip2sr NUMERIC(16, 4),
    sglvip3sr NUMERIC(16, 4),
    sglvip4sr NUMERIC(16, 4),
    sglvip5sr NUMERIC(16, 4),
    sglxykfy1 NUMERIC,
    sglxykfy2 NUMERIC,
    sglxykfy3 NUMERIC,
    sglxykfy4 NUMERIC,
    sglxykfy5 NUMERIC,
    sglxykfy6 NUMERIC,
    sglxykfy7 NUMERIC,
    sglxykfy8 NUMERIC,
    sglxykfy9 NUMERIC,
    sglxykfy10 NUMERIC,
    sglspsx VARCHAR(20) DEFAULT '0',
    sgljjtax NUMERIC(8, 4),
    sgln26 NUMERIC,
    sgln27 NUMERIC,
    sgln28 NUMERIC,
    sgln29 NUMERIC,
    CONSTRAINT pk_salegoodslist PRIMARY KEY (
        sgldate, sgltpid, sglsummary, sglmfid, sglgdid, sglbarcode,
        sglcatid, sgltaxtype, sglxstax, sglhsrq, sglsupid, sglwmid,
        sglbillno, sglrowno
    )
);

COMMENT ON TABLE salegoodslist IS '[SGL]销售单品日汇总';
COMMENT ON COLUMN salegoodslist.sgldate IS '日期';
COMMENT ON COLUMN salegoodslist.sgltpid IS '时段ID';
COMMENT ON COLUMN salegoodslist.sglsummary IS '摘要';
COMMENT ON COLUMN salegoodslist.sglmarket IS '门店';
COMMENT ON COLUMN salegoodslist.sglmfid IS '柜组';
COMMENT ON COLUMN salegoodslist.sglgdid IS '商品代码';
COMMENT ON COLUMN salegoodslist.sglbarcode IS '商品条码';
COMMENT ON COLUMN salegoodslist.sglgdtype IS '编码类别';
COMMENT ON COLUMN salegoodslist.sglcatid IS '商品类别';
COMMENT ON COLUMN salegoodslist.sgltaxtype IS '税种';
COMMENT ON COLUMN salegoodslist.sglxstax IS '销售税率';
COMMENT ON COLUMN salegoodslist.sglxftax IS '消费税率';
COMMENT ON COLUMN salegoodslist.sglppcode IS '品牌';
COMMENT ON COLUMN salegoodslist.sgluid IS '单位代码';
COMMENT ON COLUMN salegoodslist.sglhsrq IS '核算日期';
COMMENT ON COLUMN salegoodslist.sglbatchno IS '批号';
COMMENT ON COLUMN salegoodslist.sglsupid IS '供应商';
COMMENT ON COLUMN salegoodslist.sglanalcode IS '分析码';
COMMENT ON COLUMN salegoodslist.sglsj IS '售价';
COMMENT ON COLUMN salegoodslist.sglkl IS '扣率';
COMMENT ON COLUMN salegoodslist.sgljs IS '件数';
COMMENT ON COLUMN salegoodslist.sglsl IS '数量';
COMMENT ON COLUMN salegoodslist.sglsjje IS '售价金额';
COMMENT ON COLUMN salegoodslist.sglxssr IS '销售收入';
COMMENT ON COLUMN salegoodslist.sglxsse IS '销售税额';
COMMENT ON COLUMN salegoodslist.sglxfse IS '消费税额';
COMMENT ON COLUMN salegoodslist.sglqtsr IS '其他收入';
COMMENT ON COLUMN salegoodslist.sglsysy IS '收银损益';
COMMENT ON COLUMN salegoodslist.sglpopsr IS '促销收入';
COMMENT ON COLUMN salegoodslist.sglcustsr IS '会员收入';
COMMENT ON COLUMN salegoodslist.sglfcdsr IS '储值卡收入';
COMMENT ON COLUMN salegoodslist.sglpfsr IS '批发收入';
COMMENT ON COLUMN salegoodslist.sglyxssr IS '预销售收入';
COMMENT ON COLUMN salegoodslist.sgltotzk IS '总折扣';
COMMENT ON COLUMN salegoodslist.sglsupzk IS '供应商折扣';
COMMENT ON COLUMN salegoodslist.sglpopzk IS '促销折扣';
COMMENT ON COLUMN salegoodslist.sglcustzk IS '会员折扣';
COMMENT ON COLUMN salegoodslist.sglfcdzk IS '储值卡折扣';
COMMENT ON COLUMN salegoodslist.sglpfzk IS '批发折扣';
COMMENT ON COLUMN salegoodslist.sglgrantzk IS '授权折扣';
COMMENT ON COLUMN salegoodslist.sglyjhx IS '以旧换新';
COMMENT ON COLUMN salegoodslist.sglzszk IS '赠送折扣';
COMMENT ON COLUMN salegoodslist.sglthss IS '退货损失';
COMMENT ON COLUMN salegoodslist.sgladjustzk IS '调整折扣(售价)';
COMMENT ON COLUMN salegoodslist.sglcash IS '现金';
COMMENT ON COLUMN salegoodslist.sglcheck IS '支票';
COMMENT ON COLUMN salegoodslist.sglccard IS '信用卡';
COMMENT ON COLUMN salegoodslist.sglfcard IS '面值卡';
COMMENT ON COLUMN salegoodslist.sglgcert IS '礼券';
COMMENT ON COLUMN salegoodslist.sglgzje IS '挂帐金额';
COMMENT ON COLUMN salegoodslist.sglopay IS '其他方式';
COMMENT ON COLUMN salegoodslist.sgltimes IS '券溢余';
COMMENT ON COLUMN salegoodslist.sgln1 IS '进价销售毛利（收入-成本+成本调整+供应商折扣）';
COMMENT ON COLUMN salegoodslist.sgln2 IS '核算价销售毛利（收入-成本+成本调整+供应商折扣）';
COMMENT ON COLUMN salegoodslist.sgln3 IS '信用卡内卡';
COMMENT ON COLUMN salegoodslist.sgln4 IS '信用卡外卡';
COMMENT ON COLUMN salegoodslist.sgln5 IS 'VIP1销售收入,VIP2销售收入＝SGLCUSTSR-SGLN5';
COMMENT ON COLUMN salegoodslist.sglvc1 IS 'SGLVC1';
COMMENT ON COLUMN salegoodslist.sglvc2 IS 'SGLVC2';
COMMENT ON COLUMN salegoodslist.sglvc3 IS 'SGLVC3';
COMMENT ON COLUMN salegoodslist.sglfqje IS '返券金额';
COMMENT ON COLUMN salegoodslist.sglsqje IS '收券金额';
COMMENT ON COLUMN salegoodslist.sglqxssr IS '用券销售收入(包括返和收)';
COMMENT ON COLUMN salegoodslist.sgln6 IS 'CRM消费积分额';
COMMENT ON COLUMN salegoodslist.sgln7 IS 'CRM促销积分额';
COMMENT ON COLUMN salegoodslist.sgln8 IS '会员毛利';
COMMENT ON COLUMN salegoodslist.sgln9 IS '返券毛利';
COMMENT ON COLUMN salegoodslist.sgln10 IS '收买券金额';
COMMENT ON COLUMN salegoodslist.sglxyksr1 IS '信用卡收入1';
COMMENT ON COLUMN salegoodslist.sglxyksr2 IS '信用卡收入2';
COMMENT ON COLUMN salegoodslist.sglxyksr3 IS '信用卡收入3';
COMMENT ON COLUMN salegoodslist.sglxyksr4 IS '信用卡收入4';
COMMENT ON COLUMN salegoodslist.sglxyksr5 IS '信用卡收入5';
COMMENT ON COLUMN salegoodslist.sglxyksr6 IS '信用卡收入6';
COMMENT ON COLUMN salegoodslist.sglxyksr7 IS '信用卡收入7';
COMMENT ON COLUMN salegoodslist.sglxyksr8 IS '信用卡收入8';
COMMENT ON COLUMN salegoodslist.sglxyksr9 IS '信用卡收入9';
COMMENT ON COLUMN salegoodslist.sglxyksr10 IS '信用卡收入10';
COMMENT ON COLUMN salegoodslist.sgln11 IS '折算买券付款金额';
COMMENT ON COLUMN salegoodslist.sgln13 IS '销售成本';
COMMENT ON COLUMN salegoodslist.sgln14 IS '销售成本调整';
COMMENT ON COLUMN salegoodslist.sgln15 IS 'CRM促销档期积分';
COMMENT ON COLUMN salegoodslist.sgln16 IS 'CRM分摊费用';
COMMENT ON COLUMN salegoodslist.sgln17 IS 'GPP分摊费用';
COMMENT ON COLUMN salegoodslist.sgln21 IS '返券折扣';
COMMENT ON COLUMN salegoodslist.sgln22 IS '返券折扣供应商承担';
COMMENT ON COLUMN salegoodslist.sgln23 IS '支付方式折扣供应商承担';
COMMENT ON COLUMN salegoodslist.sgln24 IS '支付方式折扣';
COMMENT ON COLUMN salegoodslist.sgln25 IS 'CRM身份积分额';
COMMENT ON COLUMN salegoodslist.sglvc4 IS '调整单据类型';
COMMENT ON COLUMN salegoodslist.sglvc5 IS '调整单号';
COMMENT ON COLUMN salegoodslist.sglvc6 IS '营业员';
COMMENT ON COLUMN salegoodslist.sglsaledate IS '销售发生时间';
COMMENT ON COLUMN salegoodslist.sglnetml IS '净毛利（销售收入-销售成本+成本调整+供应商折扣-收券额+折算买券付款金额+GPP分摊费用+CRM分摊费用）';
COMMENT ON COLUMN salegoodslist.sglcardtype IS '会员卡类别';
COMMENT ON COLUMN salegoodslist.sglsyjid IS '收银机id';
COMMENT ON COLUMN salegoodslist.sglinvno IS '小票号';
COMMENT ON COLUMN salegoodslist.sglchecker IS '收银员';
COMMENT ON COLUMN salegoodslist.sglposcls IS '班次';
COMMENT ON COLUMN salegoodslist.sglshdate IS '小票时间';
COMMENT ON COLUMN salegoodslist.sgltmtype IS '特卖类型-增加SALESUPDAY部分';
COMMENT ON COLUMN salegoodslist.sglmd IS '子库存';
COMMENT ON COLUMN salegoodslist.sglfysl IS '提取费用的数量-增加SALESUPDAY部分';
COMMENT ON COLUMN salegoodslist.sglvip1sr IS 'VIP1销售收入-增加SALESUPDAY部分';
COMMENT ON COLUMN salegoodslist.sglvip2sr IS 'VIP2销售收入-增加SALESUPDAY部分';
COMMENT ON COLUMN salegoodslist.sglvip3sr IS 'VIP3销售收入-增加SALESUPDAY部分';
COMMENT ON COLUMN salegoodslist.sglvip4sr IS 'VIP4销售收入-增加SALESUPDAY部分';
COMMENT ON COLUMN salegoodslist.sglvip5sr IS 'VIP5销售收入-增加SALESUPDAY部分';
COMMENT ON COLUMN salegoodslist.sglspsx IS '商品属性码';
COMMENT ON COLUMN salegoodslist.sgljjtax IS '进项税率';
COMMENT ON COLUMN salegoodslist.sgln26 IS '用券不计收入折扣';
COMMENT ON COLUMN salegoodslist.sgln27 IS '用券不计收入折扣供应商承担';
COMMENT ON COLUMN salegoodslist.sgln28 IS '用券不计收入折扣商场承担';
COMMENT ON COLUMN salegoodslist.sgln29 IS '支付方式折扣商场承担';

CREATE INDEX IF NOT EXISTS idx_sgl_billnorowno ON salegoodslist (sglbillno, sglrowno);
CREATE INDEX IF NOT EXISTS idx_sgl_datecatid ON salegoodslist (sgldate, sglcatid);
CREATE INDEX IF NOT EXISTS idx_sgl_dategdid ON salegoodslist (sgldate, sglgdid);
CREATE INDEX IF NOT EXISTS idx_sgl_datemfid ON salegoodslist (sgldate, sglmfid);
CREATE INDEX IF NOT EXISTS idx_sgl_hsrqmfid ON salegoodslist (sglhsrq, sglmfid, sglmarket);
CREATE INDEX IF NOT EXISTS idx_sgl_sgldatemfid ON salegoodslist (sglgdid, sglmfid, sglmarket, sgldate);
CREATE INDEX IF NOT EXISTS inx_sgl_cat_pid ON salegoodslist (sglcatid, sgltpid, sglhsrq, sgldate, sglmarket);
CREATE INDEX IF NOT EXISTS inx_sgl_gdidmfid ON salegoodslist (sglgdid, sglmfid, sglmarket, sglsummary);
CREATE INDEX IF NOT EXISTS inx_sgl_sglsaledate ON salegoodslist (sglsaledate);
"""


RESTORE_ODS_SALEGOODSLIST_SQL = r"""
CREATE TABLE IF NOT EXISTS ods_salegoodslist (LIKE salegoodslist INCLUDING DEFAULTS INCLUDING CONSTRAINTS);
ALTER TABLE ods_salegoodslist ADD COLUMN IF NOT EXISTS sglgdname VARCHAR(255);
COMMENT ON TABLE ods_salegoodslist IS '销售商品清单表';
COMMENT ON COLUMN ods_salegoodslist.sglgdname IS '商品名称';
"""


def upgrade() -> None:
    op.execute(SALEGOODSLIST_SQL)


def downgrade() -> None:
    op.drop_index("inx_sgl_sglsaledate", table_name="salegoodslist")
    op.drop_index("inx_sgl_gdidmfid", table_name="salegoodslist")
    op.drop_index("inx_sgl_cat_pid", table_name="salegoodslist")
    op.drop_index("idx_sgl_sgldatemfid", table_name="salegoodslist")
    op.drop_index("idx_sgl_hsrqmfid", table_name="salegoodslist")
    op.drop_index("idx_sgl_datemfid", table_name="salegoodslist")
    op.drop_index("idx_sgl_dategdid", table_name="salegoodslist")
    op.drop_index("idx_sgl_datecatid", table_name="salegoodslist")
    op.drop_index("idx_sgl_billnorowno", table_name="salegoodslist")
    op.execute(RESTORE_ODS_SALEGOODSLIST_SQL)
    op.drop_table("salegoodslist")
