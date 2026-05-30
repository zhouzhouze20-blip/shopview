"""create pos sale tables

Revision ID: b9e1c2d3f4a5
Revises: a1b2c3d4e5f6
Create Date: 2026-05-01

"""
from typing import Sequence, Union

from alembic import op


revision: str = "b9e1c2d3f4a5"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


POS_SALE_TABLES_SQL = r"""
CREATE TABLE IF NOT EXISTS salehead (
    billno NUMERIC(20) NOT NULL,
    mkt VARCHAR(20) NOT NULL,
    syjh VARCHAR(8) NOT NULL,
    fphm NUMERIC NOT NULL,
    djlb VARCHAR(20),
    bc CHAR(1),
    rqsj TIMESTAMP,
    syyh VARCHAR(10),
    hykh VARCHAR(20),
    jfkh VARCHAR(20),
    thsq VARCHAR(20),
    ghsq VARCHAR(20),
    hysq VARCHAR(20),
    sqkh VARCHAR(20),
    sqktype CHAR(1),
    sqkzkfd NUMERIC(10, 4),
    ysje NUMERIC(12, 2),
    sjfk NUMERIC(12, 2),
    zl NUMERIC(12, 2),
    sswr_sysy NUMERIC(12, 2),
    fk_sysy NUMERIC(12, 2),
    hjzje NUMERIC(12, 2),
    hjzsl INTEGER,
    hjzke NUMERIC(12, 2),
    hyzke NUMERIC(12, 2),
    yhzke NUMERIC(12, 2),
    lszke NUMERIC(12, 2),
    buyerinfo VARCHAR(20),
    jdfhdd VARCHAR(20),
    salefphm VARCHAR(20),
    ljjf NUMERIC(12, 2),
    bcjf NUMERIC(12, 2),
    memo VARCHAR(100),
    str1 VARCHAR(100),
    str2 VARCHAR(100),
    str3 VARCHAR(100),
    str4 VARCHAR(100),
    str5 VARCHAR(100),
    num1 NUMERIC(12, 2),
    num2 NUMERIC(12, 2),
    num3 NUMERIC(12, 2),
    num4 NUMERIC(12, 2),
    num5 NUMERIC(12, 2),
    sendrqsj TIMESTAMP,
    status CHAR(1),
    custtype VARCHAR(20),
    hhflag CHAR(1),
    manaunit VARCHAR(20),
    fqflag CHAR(1),
    jfflag CHAR(1),
    saflag CHAR(1),
    fqje NUMERIC(12, 2),
    yhzszk NUMERIC(12, 2),
    ybillno NUMERIC(18),
    ysyjh VARCHAR(8),
    yfphm INTEGER,
    crmbillno NUMERIC,
    str8 VARCHAR(100),
    channel VARCHAR(20),
    hycid VARCHAR(20),
    hytype VARCHAR(20),
    CONSTRAINT pk_salehead PRIMARY KEY (billno)
);

COMMENT ON TABLE salehead IS '小票主单';
COMMENT ON COLUMN salehead.billno IS '小票单据号 (对应POSSEQCENCE)';
COMMENT ON COLUMN salehead.mkt IS '门店号';
COMMENT ON COLUMN salehead.syjh IS '收银机';
COMMENT ON COLUMN salehead.fphm IS '小票号';
COMMENT ON COLUMN salehead.djlb IS '小票类别';
COMMENT ON COLUMN salehead.bc IS '班次代码';
COMMENT ON COLUMN salehead.rqsj IS '交易时间';
COMMENT ON COLUMN salehead.syyh IS '收银员号';
COMMENT ON COLUMN salehead.hykh IS '会员卡号';
COMMENT ON COLUMN salehead.jfkh IS '积分卡号';
COMMENT ON COLUMN salehead.thsq IS '退货授权卡号';
COMMENT ON COLUMN salehead.ghsq IS '员工授权卡号';
COMMENT ON COLUMN salehead.hysq IS '顾客授权卡号';
COMMENT ON COLUMN salehead.sqkh IS '总折扣授权卡号';
COMMENT ON COLUMN salehead.sqktype IS '总折扣授权方式 (1-员工卡/2-顾客卡)';
COMMENT ON COLUMN salehead.sqkzkfd IS '总折扣授权分担';
COMMENT ON COLUMN salehead.ysje IS '应收金额';
COMMENT ON COLUMN salehead.sjfk IS '实际付款';
COMMENT ON COLUMN salehead.zl IS '找零金额';
COMMENT ON COLUMN salehead.sswr_sysy IS '四舍五入收银损溢';
COMMENT ON COLUMN salehead.fk_sysy IS '付款方式收银损溢';
COMMENT ON COLUMN salehead.hjzje IS '合计总金额';
COMMENT ON COLUMN salehead.hjzsl IS '合计商品数';
COMMENT ON COLUMN salehead.hjzke IS '合计总折扣';
COMMENT ON COLUMN salehead.hyzke IS '会员折扣额';
COMMENT ON COLUMN salehead.yhzke IS '促销折扣额';
COMMENT ON COLUMN salehead.lszke IS '手工折扣额';
COMMENT ON COLUMN salehead.buyerinfo IS '顾客采集信息';
COMMENT ON COLUMN salehead.jdfhdd IS '家电发货地点';
COMMENT ON COLUMN salehead.salefphm IS '手工发票号码';
COMMENT ON COLUMN salehead.ljjf IS '累计积分';
COMMENT ON COLUMN salehead.bcjf IS '本次积分';
COMMENT ON COLUMN salehead.memo IS '备用';
COMMENT ON COLUMN salehead.str1 IS '备用';
COMMENT ON COLUMN salehead.str2 IS '备用';
COMMENT ON COLUMN salehead.str3 IS '备用';
COMMENT ON COLUMN salehead.str4 IS '备用';
COMMENT ON COLUMN salehead.str5 IS '备用';
COMMENT ON COLUMN salehead.num1 IS '备用';
COMMENT ON COLUMN salehead.num2 IS '备用';
COMMENT ON COLUMN salehead.num3 IS '备用';
COMMENT ON COLUMN salehead.num4 IS '备用';
COMMENT ON COLUMN salehead.num5 IS '备用';
COMMENT ON COLUMN salehead.sendrqsj IS '送网日期时间';
COMMENT ON COLUMN salehead.status IS '处理标志';
COMMENT ON COLUMN salehead.custtype IS '会员卡类型';
COMMENT ON COLUMN salehead.hhflag IS '换货标志';
COMMENT ON COLUMN salehead.manaunit IS '经营公司';
COMMENT ON COLUMN salehead.fqflag IS '返券标志 n未处理 c已计算 y已处理_打印 2不返券,';
COMMENT ON COLUMN salehead.jfflag IS '积分标志';
COMMENT ON COLUMN salehead.saflag IS '是否追送n未处理 c已计算 y已处理_打印 2不返券';
COMMENT ON COLUMN salehead.fqje IS '小票返券/买券 金额';
COMMENT ON COLUMN salehead.yhzszk IS '银行追送折扣额';
COMMENT ON COLUMN salehead.ybillno IS '原小票序号';
COMMENT ON COLUMN salehead.ysyjh IS '原收银机号';
COMMENT ON COLUMN salehead.yfphm IS '原小票号';
COMMENT ON COLUMN salehead.crmbillno IS 'crmbillno';
COMMENT ON COLUMN salehead.str8 IS '备用';
COMMENT ON COLUMN salehead.channel IS '渠道';
COMMENT ON COLUMN salehead.hycid IS '会员cid';
COMMENT ON COLUMN salehead.hytype IS '会员类型';

CREATE INDEX IF NOT EXISTS idx_salehead_rqsj ON salehead (rqsj);
CREATE INDEX IF NOT EXISTS idx_salehead_mkt_ysyjh_yfphm ON salehead (mkt, ysyjh, yfphm);
CREATE INDEX IF NOT EXISTS idx_salehead_ybillno ON salehead (ybillno);
CREATE UNIQUE INDEX IF NOT EXISTS unq_salehead_mkt_syjh_fphm ON salehead (mkt, syjh, fphm);

CREATE TABLE IF NOT EXISTS salegoods (
    billno NUMERIC(18) NOT NULL,
    rowno INTEGER NOT NULL,
    mkt VARCHAR(20),
    yyyh VARCHAR(10),
    barcode VARCHAR(20),
    code VARCHAR(20),
    sptype CHAR(1),
    gz VARCHAR(20),
    catid VARCHAR(10),
    ppcode VARCHAR(10),
    unitid VARCHAR(2),
    batch VARCHAR(20),
    yhdjbh VARCHAR(20),
    name VARCHAR(60),
    unit VARCHAR(4),
    bzhl NUMERIC(12, 2),
    sl NUMERIC(10, 4),
    lsj NUMERIC(12, 2),
    jg NUMERIC(12, 2),
    hjje NUMERIC(12, 2),
    hjzk NUMERIC(12, 2),
    hyzke NUMERIC(12, 2),
    hyzkfd NUMERIC(10, 4),
    yhzke NUMERIC(12, 2),
    yhzkfd NUMERIC(10, 4),
    lszke NUMERIC(12, 2),
    lszre NUMERIC(12, 2),
    lszzk NUMERIC(12, 2),
    lszzr NUMERIC(12, 2),
    lszkfd NUMERIC(10, 4),
    plzke NUMERIC(12, 2),
    plzkfd NUMERIC(10, 4),
    zsdjbh VARCHAR(20),
    zszke NUMERIC(12, 2),
    zszkfd NUMERIC(10, 4),
    sqkh VARCHAR(20),
    sqktype CHAR(1),
    sqkzkfd NUMERIC(10, 4),
    hyzklje NUMERIC(12, 2),
    cjzke NUMERIC(12, 2),
    ltzke NUMERIC(12, 2),
    qtzke NUMERIC(12, 2),
    qtzre NUMERIC(12, 2),
    sswr_sysy NUMERIC(12, 2),
    fk_sysy NUMERIC(12, 2),
    isvipzk CHAR(1),
    xxtax NUMERIC(12, 2),
    flag CHAR(1),
    yjhxcode VARCHAR(20),
    ysyjh VARCHAR(8),
    yfphm INTEGER,
    fhdd VARCHAR(20),
    hydjbh VARCHAR(20),
    memo VARCHAR(100),
    str1 VARCHAR(100),
    str2 VARCHAR(100),
    str3 VARCHAR(100),
    str4 VARCHAR(100),
    str5 VARCHAR(100),
    num1 NUMERIC(12, 2),
    num2 NUMERIC(12, 2),
    num3 NUMERIC(12, 2),
    num4 NUMERIC(12, 2),
    num5 NUMERIC(12, 2),
    rqsj TIMESTAMP,
    str6 VARCHAR(100),
    str7 VARCHAR(100),
    str8 VARCHAR(100),
    str9 VARCHAR(100),
    str10 VARCHAR(100),
    num6 NUMERIC,
    num7 NUMERIC,
    num8 NUMERIC,
    num9 NUMERIC,
    num10 NUMERIC,
    sdjfbs NUMERIC(14, 4),
    sdpopisjf NUMERIC(5, 4),
    sdpopjfbs NUMERIC(14, 4),
    sdmjrule VARCHAR(20),
    sdfqrule VARCHAR(20),
    sdflrule VARCHAR(20),
    sdsarule NUMERIC,
    sdsazk NUMERIC,
    sdpoprule VARCHAR(10),
    sdspsx VARCHAR(20),
    sdpoppayje VARCHAR(2000),
    sgfph VARCHAR(20),
    sdrulezke NUMERIC,
    sdrulezkfd NUMERIC(10, 4),
    sdruledjbh VARCHAR(20),
    sdmjzke NUMERIC,
    sdmjzkfd NUMERIC(10, 4),
    sdmjdjbh VARCHAR(20),
    sdspzkfd NUMERIC(10, 4),
    sdypopzke NUMERIC(10, 4),
    inputbarcode VARCHAR(100),
    iszt CHAR(1),
    custname VARCHAR(20),
    custtel VARCHAR(50),
    addr1 VARCHAR(300),
    isinstall CHAR(1),
    sjcm VARCHAR(50),
    dkqje NUMERIC(12, 2),
    cjqno VARCHAR(20),
    cdqje NUMERIC(12, 2),
    cjqzkfd VARCHAR(20),
    sjqno VARCHAR(30),
    sdqje NUMERIC(12, 2),
    dyqno VARCHAR(20),
    dyqje NUMERIC(12, 2),
    dyqzkfd NUMERIC(12, 2),
    ycf NUMERIC(12, 2),
    iscyhd CHAR(1),
    psrq VARCHAR(20),
    yrowno INTEGER,
    CONSTRAINT pk_salegoods PRIMARY KEY (billno, rowno)
);

COMMENT ON TABLE salegoods IS '小票商品明细';
COMMENT ON COLUMN salegoods.billno IS '小票单据号 (对应SALEHEAD)';
COMMENT ON COLUMN salegoods.rowno IS '商品行号';
COMMENT ON COLUMN salegoods.yyyh IS '营业员';
COMMENT ON COLUMN salegoods.barcode IS '商品条码';
COMMENT ON COLUMN salegoods.code IS '商品编码';
COMMENT ON COLUMN salegoods.sptype IS '商品编码类型';
COMMENT ON COLUMN salegoods.gz IS '商品柜组';
COMMENT ON COLUMN salegoods.catid IS '商品品类';
COMMENT ON COLUMN salegoods.ppcode IS '商品品牌';
COMMENT ON COLUMN salegoods.batch IS '商品批号';
COMMENT ON COLUMN salegoods.yhdjbh IS '促销单据编号';
COMMENT ON COLUMN salegoods.name IS '商品名称';
COMMENT ON COLUMN salegoods.unit IS '商品单位';
COMMENT ON COLUMN salegoods.bzhl IS '包装含量';
COMMENT ON COLUMN salegoods.sl IS '销售数量';
COMMENT ON COLUMN salegoods.lsj IS '商品零售价';
COMMENT ON COLUMN salegoods.jg IS '销售价格';
COMMENT ON COLUMN salegoods.hjje IS '合计总金额';
COMMENT ON COLUMN salegoods.hjzk IS '合计总折扣';
COMMENT ON COLUMN salegoods.hyzke IS '会员折扣额';
COMMENT ON COLUMN salegoods.hyzkfd IS '会员折扣分担';
COMMENT ON COLUMN salegoods.yhzke IS '促销折扣额';
COMMENT ON COLUMN salegoods.yhzkfd IS '促销折扣分担';
COMMENT ON COLUMN salegoods.lszke IS '手工折扣额';
COMMENT ON COLUMN salegoods.lszre IS '手工折让额';
COMMENT ON COLUMN salegoods.lszzk IS '手工总品折扣';
COMMENT ON COLUMN salegoods.lszzr IS '手工总品折让';
COMMENT ON COLUMN salegoods.lszkfd IS '手工折扣分担';
COMMENT ON COLUMN salegoods.plzke IS '批量折扣';
COMMENT ON COLUMN salegoods.plzkfd IS '批量折扣分担';
COMMENT ON COLUMN salegoods.zsdjbh IS '规则促销单据号';
COMMENT ON COLUMN salegoods.zszke IS '规则促销折扣额';
COMMENT ON COLUMN salegoods.zszkfd IS '规则促销折扣分担';
COMMENT ON COLUMN salegoods.sqkh IS '单品授权卡号';
COMMENT ON COLUMN salegoods.sqktype IS '单品授权类别';
COMMENT ON COLUMN salegoods.sqkzkfd IS '单品授权折扣分担';
COMMENT ON COLUMN salegoods.hyzklje IS '会员折扣率折扣';
COMMENT ON COLUMN salegoods.cjzke IS '厂家折扣额';
COMMENT ON COLUMN salegoods.ltzke IS '零头折扣额';
COMMENT ON COLUMN salegoods.qtzke IS '其他折扣额';
COMMENT ON COLUMN salegoods.qtzre IS '其他折让额';
COMMENT ON COLUMN salegoods.sswr_sysy IS '四舍五入收银损溢';
COMMENT ON COLUMN salegoods.fk_sysy IS '付款方式收银损溢';
COMMENT ON COLUMN salegoods.isvipzk IS '是否允许VIP折扣';
COMMENT ON COLUMN salegoods.xxtax IS '商品税率';
COMMENT ON COLUMN salegoods.flag IS '商品标志 (1-赠送商品/2-电子秤商品/ 3-削价商品/4-普通商品)';
COMMENT ON COLUMN salegoods.yjhxcode IS '以旧换新条码';
COMMENT ON COLUMN salegoods.ysyjh IS '原收银机号';
COMMENT ON COLUMN salegoods.yfphm IS '原小票号';
COMMENT ON COLUMN salegoods.fhdd IS '发货地点';
COMMENT ON COLUMN salegoods.hydjbh IS '会员折扣单号';
COMMENT ON COLUMN salegoods.memo IS '备注';
COMMENT ON COLUMN salegoods.str1 IS '备用';
COMMENT ON COLUMN salegoods.str2 IS '备用';
COMMENT ON COLUMN salegoods.str3 IS '备用';
COMMENT ON COLUMN salegoods.str4 IS '备用';
COMMENT ON COLUMN salegoods.str5 IS '备用';
COMMENT ON COLUMN salegoods.num1 IS '备用';
COMMENT ON COLUMN salegoods.num2 IS '备用';
COMMENT ON COLUMN salegoods.num3 IS '备用';
COMMENT ON COLUMN salegoods.num4 IS '备用';
COMMENT ON COLUMN salegoods.num5 IS '备用';
COMMENT ON COLUMN salegoods.rqsj IS '交易时间';
COMMENT ON COLUMN salegoods.num6 IS '已退货数量';
COMMENT ON COLUMN salegoods.num7 IS '1:已红冲';
COMMENT ON COLUMN salegoods.sdjfbs IS '业务系统积分倍数';
COMMENT ON COLUMN salegoods.sdpopisjf IS '忽略其他积分优惠(1是,0否)';
COMMENT ON COLUMN salegoods.sdpopjfbs IS '促销积分倍率';
COMMENT ON COLUMN salegoods.sdmjrule IS '满减规则(买券时记录档期)';
COMMENT ON COLUMN salegoods.sdfqrule IS '返券规则';
COMMENT ON COLUMN salegoods.sdflrule IS '满赠规则_返礼品';
COMMENT ON COLUMN salegoods.sdsarule IS '追送规则序号';
COMMENT ON COLUMN salegoods.sdsazk IS '追送折扣额';
COMMENT ON COLUMN salegoods.sdpoprule IS '促销类型 1010,打折,满减,返券,返礼';
COMMENT ON COLUMN salegoods.sdspsx IS '商品属性码';
COMMENT ON COLUMN salegoods.sdpoppayje IS '记录分摊金额 付款行号:付款代码:分摊金额,付款行号:付款代码:分摊金额.......';
COMMENT ON COLUMN salegoods.sdrulezke IS '规则促销折扣额';
COMMENT ON COLUMN salegoods.sdrulezkfd IS '规则促销折扣分担';
COMMENT ON COLUMN salegoods.sdruledjbh IS '规则促销折扣单据编号';
COMMENT ON COLUMN salegoods.sdmjzke IS '满减促销折扣额';
COMMENT ON COLUMN salegoods.sdmjzkfd IS '满减促销折扣分担';
COMMENT ON COLUMN salegoods.sdspzkfd IS '规则促销折扣单据编号';
COMMENT ON COLUMN salegoods.sdypopzke IS '营促销折扣额';
COMMENT ON COLUMN salegoods.inputbarcode IS '编码';
COMMENT ON COLUMN salegoods.iszt IS '是否自提';
COMMENT ON COLUMN salegoods.custname IS '会员姓名';
COMMENT ON COLUMN salegoods.custtel IS '会员手机号';
COMMENT ON COLUMN salegoods.addr1 IS '配送地址';
COMMENT ON COLUMN salegoods.isinstall IS '是否安装';
COMMENT ON COLUMN salegoods.sjcm IS '串码';
COMMENT ON COLUMN salegoods.dkqje IS '抵扣券金额';
COMMENT ON COLUMN salegoods.cjqno IS '厂家券号';
COMMENT ON COLUMN salegoods.cdqje IS '厂担券金额';
COMMENT ON COLUMN salegoods.cjqzkfd IS '厂家折扣分担';
COMMENT ON COLUMN salegoods.sjqno IS '商家券号';
COMMENT ON COLUMN salegoods.sdqje IS '商担券金额';
COMMENT ON COLUMN salegoods.dyqno IS '店长优惠券号';
COMMENT ON COLUMN salegoods.dyqje IS '店长优惠券金额';
COMMENT ON COLUMN salegoods.dyqzkfd IS '店长优惠券折扣分担';
COMMENT ON COLUMN salegoods.ycf IS '远程费';
COMMENT ON COLUMN salegoods.iscyhd IS '是否参与赠品活动';
COMMENT ON COLUMN salegoods.psrq IS '配送日期';
COMMENT ON COLUMN salegoods.yrowno IS '原行号';

CREATE INDEX IF NOT EXISTS idx_salegoods_rqsj ON salegoods (rqsj);
CREATE INDEX IF NOT EXISTS idx_salegoods_mkt_ysyjh_yfphm ON salegoods (mkt, ysyjh, yfphm);

CREATE TABLE IF NOT EXISTS salepay (
    billno NUMERIC(18) NOT NULL,
    rowno INTEGER NOT NULL,
    paycode VARCHAR(4) NOT NULL,
    payname VARCHAR(20),
    flag CHAR(1),
    ybje NUMERIC(12, 2),
    hl NUMERIC(12, 2),
    je NUMERIC(12, 2),
    payno VARCHAR(255),
    batch VARCHAR(20),
    kye NUMERIC(12, 2),
    idno VARCHAR(255),
    memo VARCHAR(100),
    str1 VARCHAR(100),
    str2 VARCHAR(100),
    str3 VARCHAR(100),
    str4 VARCHAR(100),
    str5 VARCHAR(100),
    num1 NUMERIC(12, 2),
    num2 NUMERIC(12, 2),
    num3 NUMERIC(12, 2),
    num4 NUMERIC(12, 2),
    num5 NUMERIC(12, 2),
    mkt VARCHAR(20),
    rqsj TIMESTAMP,
    ispop CHAR(1),
    str6 VARCHAR(100),
    coptype VARCHAR(20),
    paytype VARCHAR(20),
    paymemo VARCHAR(200),
    overage NUMERIC(12, 6),
    consumers_id VARCHAR(20),
    coupon_group VARCHAR(20),
    coupon_event_scd VARCHAR(20),
    coupon_event_id INTEGER,
    coupon_policy_id INTEGER,
    coupon_mutex VARCHAR(300),
    coupon_trace_seqno INTEGER,
    overpay NUMERIC(12, 6),
    coupon_is_cash VARCHAR(20),
    CONSTRAINT pk_salepay PRIMARY KEY (billno, rowno)
);

COMMENT ON TABLE salepay IS '小票付款明细';
COMMENT ON COLUMN salepay.billno IS '小票单据号';
COMMENT ON COLUMN salepay.rowno IS '付款行号';
COMMENT ON COLUMN salepay.paycode IS '付款方式代码';
COMMENT ON COLUMN salepay.payname IS '付款方式名称';
COMMENT ON COLUMN salepay.flag IS '标志 (1-付款/2-找零/3-扣回)';
COMMENT ON COLUMN salepay.ybje IS '原币金额';
COMMENT ON COLUMN salepay.hl IS '付款汇率';
COMMENT ON COLUMN salepay.je IS '付款金额,原币金额*汇率';
COMMENT ON COLUMN salepay.payno IS '付款卡号';
COMMENT ON COLUMN salepay.batch IS '面值卡交易流水/金卡工程交易流水';
COMMENT ON COLUMN salepay.kye IS '卡上余额';
COMMENT ON COLUMN salepay.idno IS '证件号码';
COMMENT ON COLUMN salepay.memo IS '备注';
COMMENT ON COLUMN salepay.str1 IS '备用';
COMMENT ON COLUMN salepay.str2 IS '备用';
COMMENT ON COLUMN salepay.str3 IS '备用';
COMMENT ON COLUMN salepay.str4 IS '备用';
COMMENT ON COLUMN salepay.str5 IS '备用';
COMMENT ON COLUMN salepay.num1 IS '备用';
COMMENT ON COLUMN salepay.num2 IS '备用';
COMMENT ON COLUMN salepay.num3 IS '备用';
COMMENT ON COLUMN salepay.num4 IS '备用';
COMMENT ON COLUMN salepay.num5 IS '备用';
COMMENT ON COLUMN salepay.str6 IS '是否补现paytype in(YQKH,YJKH,DKKH)';
COMMENT ON COLUMN salepay.coptype IS '付款券种/积分种类';
COMMENT ON COLUMN salepay.paytype IS '付款大类';
COMMENT ON COLUMN salepay.paymemo IS '付款备注';
COMMENT ON COLUMN salepay.overage IS '溢余';
COMMENT ON COLUMN salepay.consumers_id IS '券付款所属会员账号';
COMMENT ON COLUMN salepay.coupon_group IS '券账户分组';
COMMENT ON COLUMN salepay.coupon_event_scd IS '券付款用券档期';
COMMENT ON COLUMN salepay.coupon_event_id IS '券付款用券活动';
COMMENT ON COLUMN salepay.coupon_policy_id IS '券付款用券策略';
COMMENT ON COLUMN salepay.coupon_mutex IS '券互斥规则';
COMMENT ON COLUMN salepay.coupon_trace_seqno IS '券交易流水号';
COMMENT ON COLUMN salepay.overpay IS '支付结余';
COMMENT ON COLUMN salepay.coupon_is_cash IS '-券种是否现金券（填入couponuse.get返回的coupon_is_cash）';

CREATE INDEX IF NOT EXISTS idx_salepay_billno ON salepay (billno);

"""


def upgrade() -> None:
    op.execute(POS_SALE_TABLES_SQL)


def downgrade() -> None:
    op.drop_index("idx_salepay_billno", table_name="salepay")
    op.drop_table("salepay")
    op.drop_index("idx_salegoods_mkt_ysyjh_yfphm", table_name="salegoods")
    op.drop_index("idx_salegoods_rqsj", table_name="salegoods")
    op.drop_table("salegoods")
    op.drop_index("unq_salehead_mkt_syjh_fphm", table_name="salehead")
    op.drop_index("idx_salehead_ybillno", table_name="salehead")
    op.drop_index("idx_salehead_mkt_ysyjh_yfphm", table_name="salehead")
    op.drop_index("idx_salehead_rqsj", table_name="salehead")
    op.drop_table("salehead")

