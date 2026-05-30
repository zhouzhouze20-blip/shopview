"""create product payment coupon tables

Revision ID: d2f4a6b8c0e2
Revises: c6d7e8f9a0b1
Create Date: 2026-05-06

"""
from typing import Sequence, Union

from alembic import op


revision: str = "d2f4a6b8c0e2"
down_revision: Union[str, Sequence[str], None] = "c6d7e8f9a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PRODUCT_PAYMENT_COUPON_SQL = r"""
CREATE TABLE IF NOT EXISTS goodsbase (
    gbid VARCHAR(20) NOT NULL,
    gbbarcode VARCHAR(20) NOT NULL,
    gbanalcode VARCHAR(20) NOT NULL,
    gbtypeid CHAR(1) NOT NULL,
    gbmanamode CHAR(1) NOT NULL,
    gbisdj CHAR(1) NOT NULL,
    gbcostid CHAR(1) NOT NULL,
    gbstatus CHAR(1) NOT NULL,
    gbisweb CHAR(1) NOT NULL,
    gbcname VARCHAR(40) NOT NULL,
    gbename VARCHAR(64),
    gbskey VARCHAR(20),
    gbspec VARCHAR(40),
    gbunit VARCHAR(4),
    gbbzhl NUMERIC(10, 4) DEFAULT 1 NOT NULL,
    gbismform CHAR(1) DEFAULT 'N' NOT NULL,
    gbcatcode VARCHAR(10) NOT NULL,
    gbstatcat VARCHAR(10) NOT NULL,
    gbppcode VARCHAR(6) NOT NULL,
    gbcdcode VARCHAR(10),
    gbspcm VARCHAR(10),
    gbsphs VARCHAR(10),
    gbspks VARCHAR(10),
    gbspdj CHAR(1),
    gbspdc CHAR(1),
    gbspxb CHAR(1),
    gbsynl CHAR(1),
    gbsyjj CHAR(1),
    gbspxt VARCHAR(20),
    gbcpxz VARCHAR(60),
    gbzcff VARCHAR(20),
    gbzcsb VARCHAR(32),
    gbpzwh VARCHAR(20),
    gbzxbz VARCHAR(20),
    gbsccs VARCHAR(48),
    gbcshh VARCHAR(20),
    gbisbzq CHAR(1) NOT NULL,
    gbbzyjts NUMERIC(8) NOT NULL,
    gbjysj NUMERIC(12, 2),
    gbmaxsj NUMERIC(12, 2),
    gbminsj NUMERIC(12, 2),
    gbnewhsjj NUMERIC(14, 4),
    gbjxtax NUMERIC(8, 4) DEFAULT 0.17 NOT NULL,
    gbsupid VARCHAR(20),
    gbwmid CHAR(1) NOT NULL,
    gbmanacls CHAR(1) DEFAULT '1' NOT NULL,
    gbisdzcm CHAR(1) DEFAULT 'N' NOT NULL,
    gbdzcmlx CHAR(2),
    gbinputor VARCHAR(20) NOT NULL,
    gbinputdate TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    gbxgr VARCHAR(20),
    gbxgdate TIMESTAMP,
    gbmemo VARCHAR(100),
    gbnum1 NUMERIC,
    gbnum2 NUMERIC,
    gbnum3 NUMERIC,
    gbnum4 NUMERIC,
    gbnum5 NUMERIC,
    gbstr1 VARCHAR(48),
    gbstr2 VARCHAR(48),
    gbstr3 VARCHAR(48),
    gbstr4 VARCHAR(48),
    gbstr5 VARCHAR(48),
    gbfzunit VARCHAR(4),
    gbmanastatus CHAR(1) DEFAULT 'Y' NOT NULL,
    gbiskb CHAR(1) DEFAULT 'N' NOT NULL,
    gbisyj CHAR(1) DEFAULT 'N' NOT NULL,
    gbflag1 CHAR(1),
    gbflag2 CHAR(1),
    gbflag3 CHAR(1),
    gbjjfs CHAR(1),
    gbnum6 NUMERIC,
    gbnum7 NUMERIC,
    gbnum8 NUMERIC,
    gbnum9 NUMERIC,
    gbnum10 NUMERIC,
    gbstr6 VARCHAR(48),
    gbstr7 VARCHAR(48),
    gbstr8 VARCHAR(48),
    gbstr9 VARCHAR(48),
    gbstr10 VARCHAR(48),
    gbfirstjhdate TIMESTAMP,
    gblastjhdate TIMESTAMP,
    gbminjj NUMERIC(14, 4),
    gbmaxjj NUMERIC(14, 4),
    gblastjj NUMERIC(14, 4),
    CONSTRAINT pk_goodsbase PRIMARY KEY (gbid),
    CONSTRAINT chk_analcode CHECK ((gbtypeid <> '8') OR (gbanalcode IS NOT NULL)),
    CONSTRAINT chk_gbbzyjts CHECK (gbbzyjts >= 0),
    CONSTRAINT chk_gbisbzq CHECK (gbisbzq IN ('N', 'Y')),
    CONSTRAINT chk_gbisdj CHECK (gbisdj IN ('Y', 'N')),
    CONSTRAINT chk_gbismform CHECK (gbismform IN ('N', 'Y')),
    CONSTRAINT chk_gbisweb CHECK (gbisweb IN ('N', 'Y')),
    CONSTRAINT chk_gbjysj CHECK (gbjysj >= 0 OR gbjysj IS NULL),
    CONSTRAINT chk_gbmanamode CHECK (gbmanamode IN ('0', '1', '2', '3', '4')),
    CONSTRAINT chk_gbmaxsj CHECK (gbmaxsj >= 0 OR gbmaxsj IS NULL),
    CONSTRAINT chk_gbminsj CHECK (gbminsj >= 0 OR gbminsj IS NULL),
    CONSTRAINT chk_gbnewhsjj CHECK (gbnewhsjj >= 0 OR gbnewhsjj IS NULL),
    CONSTRAINT chk_gbstatus CHECK (gbstatus IN ('M', 'N', 'Y'))
);

COMMENT ON TABLE goodsbase IS '[GB]商品基本信息';
COMMENT ON COLUMN goodsbase.gbid IS '商品代码';
COMMENT ON COLUMN goodsbase.gbbarcode IS '商品条码';
COMMENT ON COLUMN goodsbase.gbanalcode IS '分析码';
COMMENT ON COLUMN goodsbase.gbtypeid IS '编码类别';
COMMENT ON COLUMN goodsbase.gbmanamode IS '管理方法';
COMMENT ON COLUMN goodsbase.gbisdj IS '是否定价';
COMMENT ON COLUMN goodsbase.gbcostid IS '成本结转方法';
COMMENT ON COLUMN goodsbase.gbstatus IS '状态';
COMMENT ON COLUMN goodsbase.gbisweb IS '是否网上发布';
COMMENT ON COLUMN goodsbase.gbcname IS '中文品名';
COMMENT ON COLUMN goodsbase.gbename IS '英文名称';
COMMENT ON COLUMN goodsbase.gbskey IS '助记码';
COMMENT ON COLUMN goodsbase.gbspec IS '规格';
COMMENT ON COLUMN goodsbase.gbunit IS '计量单位';
COMMENT ON COLUMN goodsbase.gbbzhl IS '含量';
COMMENT ON COLUMN goodsbase.gbismform IS '是否多规格单位';
COMMENT ON COLUMN goodsbase.gbcatcode IS '企业内部分类';
COMMENT ON COLUMN goodsbase.gbstatcat IS '国家统计分类';
COMMENT ON COLUMN goodsbase.gbppcode IS '品牌';
COMMENT ON COLUMN goodsbase.gbcdcode IS '产地';
COMMENT ON COLUMN goodsbase.gbspcm IS '尺码';
COMMENT ON COLUMN goodsbase.gbsphs IS '花色';
COMMENT ON COLUMN goodsbase.gbspks IS '款式';
COMMENT ON COLUMN goodsbase.gbspdj IS '等级';
COMMENT ON COLUMN goodsbase.gbspdc IS '商品档次';
COMMENT ON COLUMN goodsbase.gbspxb IS '适用性别';
COMMENT ON COLUMN goodsbase.gbsynl IS '适用年龄';
COMMENT ON COLUMN goodsbase.gbsyjj IS '适用季节';
COMMENT ON COLUMN goodsbase.gbspxt IS '*经营柜组*';
COMMENT ON COLUMN goodsbase.gbcpxz IS '主要成分';
COMMENT ON COLUMN goodsbase.gbzcff IS '贮藏方法';
COMMENT ON COLUMN goodsbase.gbzcsb IS '注册商标';
COMMENT ON COLUMN goodsbase.gbpzwh IS '批准文号';
COMMENT ON COLUMN goodsbase.gbzxbz IS '执行标准';
COMMENT ON COLUMN goodsbase.gbsccs IS '生成厂商';
COMMENT ON COLUMN goodsbase.gbcshh IS '厂商货号';
COMMENT ON COLUMN goodsbase.gbisbzq IS '是否存在保质期';
COMMENT ON COLUMN goodsbase.gbbzyjts IS '预计保质天数';
COMMENT ON COLUMN goodsbase.gbjysj IS '建议售价';
COMMENT ON COLUMN goodsbase.gbmaxsj IS '最高售价';
COMMENT ON COLUMN goodsbase.gbminsj IS '最低售价';
COMMENT ON COLUMN goodsbase.gbnewhsjj IS '最新进价';
COMMENT ON COLUMN goodsbase.gbjxtax IS '进项税';
COMMENT ON COLUMN goodsbase.gbsupid IS '主营供应商';
COMMENT ON COLUMN goodsbase.gbwmid IS '主营经营方式';
COMMENT ON COLUMN goodsbase.gbmanacls IS '管理级别';
COMMENT ON COLUMN goodsbase.gbisdzcm IS '是否电子称';
COMMENT ON COLUMN goodsbase.gbdzcmlx IS '电子称码类型';
COMMENT ON COLUMN goodsbase.gbinputor IS '录入员';
COMMENT ON COLUMN goodsbase.gbinputdate IS '录入日期';
COMMENT ON COLUMN goodsbase.gbxgr IS '维护员';
COMMENT ON COLUMN goodsbase.gbxgdate IS '维护日期';
COMMENT ON COLUMN goodsbase.gbmemo IS '备注';
COMMENT ON COLUMN goodsbase.gbnum1 IS '长';
COMMENT ON COLUMN goodsbase.gbnum2 IS '宽';
COMMENT ON COLUMN goodsbase.gbnum3 IS '高';
COMMENT ON COLUMN goodsbase.gbnum4 IS '价格精度';
COMMENT ON COLUMN goodsbase.gbnum5 IS '保质期';
COMMENT ON COLUMN goodsbase.gbstr1 IS 'GBSTR1';
COMMENT ON COLUMN goodsbase.gbstr2 IS '配件(Y/N)';
COMMENT ON COLUMN goodsbase.gbstr3 IS '按销售数量提取费用的商品(Y/N)';
COMMENT ON COLUMN goodsbase.gbstr4 IS '岗组';
COMMENT ON COLUMN goodsbase.gbstr5 IS 'GBSTR5';
COMMENT ON COLUMN goodsbase.gbfzunit IS '辅助计量单位';
COMMENT ON COLUMN goodsbase.gbiskb IS '是否看板商品';
COMMENT ON COLUMN goodsbase.gbisyj IS '是否议价';
COMMENT ON COLUMN goodsbase.gbjjfs IS '计价方式';
COMMENT ON COLUMN goodsbase.gbfirstjhdate IS '初次进货日期';
COMMENT ON COLUMN goodsbase.gblastjhdate IS '最后进货日期';
COMMENT ON COLUMN goodsbase.gbminjj IS '最低进价';
COMMENT ON COLUMN goodsbase.gbmaxjj IS '最高进价';
COMMENT ON COLUMN goodsbase.gblastjj IS '最新进价';

CREATE INDEX IF NOT EXISTS idx_gb_analcode ON goodsbase (gbanalcode);
CREATE UNIQUE INDEX IF NOT EXISTS idx_gb_barcode ON goodsbase (gbbarcode);
CREATE INDEX IF NOT EXISTS idx_gb_catcode ON goodsbase (gbcatcode);
CREATE INDEX IF NOT EXISTS idx_gb_cname ON goodsbase (gbcname);
CREATE INDEX IF NOT EXISTS idx_gb_ppcode ON goodsbase (gbppcode);
CREATE UNIQUE INDEX IF NOT EXISTS idx_gb_skey ON goodsbase (gbskey);
CREATE INDEX IF NOT EXISTS idx_gb_str4 ON goodsbase (gbstr4);
CREATE INDEX IF NOT EXISTS idx_gb_supid ON goodsbase (gbsupid);
CREATE INDEX IF NOT EXISTS idx_gb_typeid ON goodsbase (gbtypeid);

CREATE TABLE IF NOT EXISTS goodsbarcode (
    gcgdid VARCHAR(20) NOT NULL,
    gcbarcode VARCHAR(20) NOT NULL,
    CONSTRAINT pk_goodsbarcode PRIMARY KEY (gcbarcode)
);

COMMENT ON TABLE goodsbarcode IS '[GC]商品多码';
COMMENT ON COLUMN goodsbarcode.gcgdid IS '商品代码';
COMMENT ON COLUMN goodsbarcode.gcbarcode IS '条码';

CREATE INDEX IF NOT EXISTS idx_gc_gdid ON goodsbarcode (gcgdid);

CREATE TABLE IF NOT EXISTS goodsmframe (
    gmfgdid VARCHAR(20) NOT NULL,
    gmfmfid VARCHAR(20) NOT NULL,
    gmfmarket VARCHAR(20) NOT NULL,
    gmfstatus CHAR(1) NOT NULL,
    gmfmanacls CHAR(1),
    gmfmscode VARCHAR(20),
    gmfsupid VARCHAR(20) NOT NULL,
    gmfwmid CHAR(1) NOT NULL,
    gmfisxj CHAR(1) DEFAULT 'N',
    gmfxjj NUMERIC,
    gmfisdzcm CHAR(1),
    gmfdzcmlx CHAR(1),
    gmfmaintor VARCHAR(20),
    gmfmaintdate TIMESTAMP,
    gmfcgrq TIMESTAMP,
    gmfxszq NUMERIC,
    gmfdhzq NUMERIC,
    gmfmaxkcsl NUMERIC,
    gmfminkcsl NUMERIC,
    gmfbhmode CHAR(1) DEFAULT '3',
    gmfpsmode VARCHAR(20),
    gmfstr1 VARCHAR(20),
    gmfstr2 VARCHAR(20),
    gmfstr3 VARCHAR(100),
    gmffirstsale TIMESTAMP,
    gmflastsale TIMESTAMP,
    gmffirstinstr TIMESTAMP,
    gmflastinstr TIMESTAMP,
    CONSTRAINT pk_goodsmframe PRIMARY KEY (gmfgdid, gmfmfid)
);

COMMENT ON TABLE goodsmframe IS '[GMF]商品的经营管理结构';
COMMENT ON COLUMN goodsmframe.gmfgdid IS '商品代码';
COMMENT ON COLUMN goodsmframe.gmfmfid IS '存放位置';
COMMENT ON COLUMN goodsmframe.gmfmarket IS '管理架构第一级';
COMMENT ON COLUMN goodsmframe.gmfstatus IS '状态';
COMMENT ON COLUMN goodsmframe.gmfmanacls IS '经营级别';
COMMENT ON COLUMN goodsmframe.gmfmscode IS '货位';
COMMENT ON COLUMN goodsmframe.gmfsupid IS '主营供应商';
COMMENT ON COLUMN goodsmframe.gmfwmid IS '主营经营方式';
COMMENT ON COLUMN goodsmframe.gmfisxj IS 'GMFISXJ';
COMMENT ON COLUMN goodsmframe.gmfxjj IS 'GMFXJJ';
COMMENT ON COLUMN goodsmframe.gmfisdzcm IS '是否电子称码';
COMMENT ON COLUMN goodsmframe.gmfdzcmlx IS '电子称码类型';
COMMENT ON COLUMN goodsmframe.gmfmaintor IS '维护员';
COMMENT ON COLUMN goodsmframe.gmfmaintdate IS '维护日期';
COMMENT ON COLUMN goodsmframe.gmfcgrq IS '撤柜日期';
COMMENT ON COLUMN goodsmframe.gmfxszq IS '销售周期';
COMMENT ON COLUMN goodsmframe.gmfdhzq IS '订货周期';
COMMENT ON COLUMN goodsmframe.gmfmaxkcsl IS '最大库存数量';
COMMENT ON COLUMN goodsmframe.gmfminkcsl IS '最小库存数量';
COMMENT ON COLUMN goodsmframe.gmfbhmode IS '补货方式(配送 1 ,直供  2,自采 3)';
COMMENT ON COLUMN goodsmframe.gmfstr1 IS '停售标识(H:手工停售,A:自动停售)';

CREATE INDEX IF NOT EXISTS index_gmf_gdid ON goodsmframe (gmfgdid);
CREATE INDEX IF NOT EXISTS index_gmf_market ON goodsmframe (gmfmarket);
CREATE INDEX IF NOT EXISTS index_gmf_mfcode ON goodsmframe (gmfmfid);
CREATE INDEX IF NOT EXISTS index_gmf_mktgdid ON goodsmframe (gmfmarket, gmfgdid);
CREATE INDEX IF NOT EXISTS index_gmf_shelf ON goodsmframe (gmfmscode);

CREATE TABLE IF NOT EXISTS goodsmfprice (
    gmpmfid VARCHAR(20) NOT NULL,
    gmpgdid VARCHAR(20) NOT NULL,
    gmpuid CHAR(2) DEFAULT '00' NOT NULL,
    gmpmarket VARCHAR(20) NOT NULL,
    gmptaxtype CHAR(1) DEFAULT '1' NOT NULL,
    gmpxstax NUMERIC(8, 4) NOT NULL,
    gmpxftax NUMERIC(8, 4),
    gmphsjj NUMERIC(14, 4),
    gmppsjtype CHAR(1),
    gmppsj NUMERIC(14, 4),
    gmppsjjl NUMERIC(5, 4),
    gmpsj NUMERIC(12, 2),
    gmpjjffid CHAR(1),
    gmpkl NUMERIC(5, 4),
    gmpke NUMERIC(14, 4),
    gmphyj NUMERIC(12, 2),
    gmppfj NUMERIC(12, 2),
    gmpzkfd NUMERIC(5, 4),
    gmpzkbz CHAR(1) DEFAULT 'Y' NOT NULL,
    gmpvipbz CHAR(1) DEFAULT 'Y' NOT NULL,
    gmpmaxzkl NUMERIC(5, 4) DEFAULT 1 NOT NULL,
    gmpmaxzke NUMERIC(12, 2) DEFAULT 0 NOT NULL,
    gmpismftj CHAR(1) DEFAULT 'N' NOT NULL,
    gmpminsj NUMERIC(12, 2),
    gmpmaxsj NUMERIC(12, 2),
    gmpminrq TIMESTAMP,
    gmpmaxrq TIMESTAMP,
    gmppfzkfd NUMERIC(5, 4),
    gmpsubco VARCHAR(20) DEFAULT '0',
    gmpjxtax NUMERIC(8, 4),
    gmpminjj NUMERIC(14, 4),
    gmpmaxjj NUMERIC(14, 4),
    gmplastjj NUMERIC(14, 4),
    CONSTRAINT pk_goodsmfprice PRIMARY KEY (gmpmfid, gmpgdid, gmpuid)
);

COMMENT ON TABLE goodsmfprice IS '[GMP]商品的经营物价信息';
COMMENT ON COLUMN goodsmfprice.gmpmfid IS '存放位置';
COMMENT ON COLUMN goodsmfprice.gmpgdid IS '商品代码';
COMMENT ON COLUMN goodsmfprice.gmpuid IS '单位';
COMMENT ON COLUMN goodsmfprice.gmpmarket IS '管理架构第一级';
COMMENT ON COLUMN goodsmfprice.gmptaxtype IS '销售税种';
COMMENT ON COLUMN goodsmfprice.gmpxstax IS '销售税率';
COMMENT ON COLUMN goodsmfprice.gmpxftax IS '消费税率';
COMMENT ON COLUMN goodsmfprice.gmphsjj IS '进价';
COMMENT ON COLUMN goodsmfprice.gmppsjtype IS '配送计价方式';
COMMENT ON COLUMN goodsmfprice.gmppsj IS '配送价';
COMMENT ON COLUMN goodsmfprice.gmppsjjl IS '配送比率';
COMMENT ON COLUMN goodsmfprice.gmpsj IS '售价';
COMMENT ON COLUMN goodsmfprice.gmpjjffid IS '计价方式';
COMMENT ON COLUMN goodsmfprice.gmpkl IS '扣率';
COMMENT ON COLUMN goodsmfprice.gmpke IS '扣额';
COMMENT ON COLUMN goodsmfprice.gmphyj IS '会员价';
COMMENT ON COLUMN goodsmfprice.gmppfj IS '批发价';
COMMENT ON COLUMN goodsmfprice.gmpzkfd IS '折扣分担';
COMMENT ON COLUMN goodsmfprice.gmpzkbz IS '是否允许打折';
COMMENT ON COLUMN goodsmfprice.gmpvipbz IS '是否允许VIP打折';
COMMENT ON COLUMN goodsmfprice.gmpmaxzkl IS '最大折扣率';
COMMENT ON COLUMN goodsmfprice.gmpmaxzke IS '最大折扣额';
COMMENT ON COLUMN goodsmfprice.gmpismftj IS 'GMPISMFTJ';
COMMENT ON COLUMN goodsmfprice.gmpminsj IS 'GMPMINSJ';
COMMENT ON COLUMN goodsmfprice.gmpmaxsj IS 'GMPMAXSJ';
COMMENT ON COLUMN goodsmfprice.gmpminrq IS 'GMPMINRQ';
COMMENT ON COLUMN goodsmfprice.gmpmaxrq IS 'GMPMAXRQ';
COMMENT ON COLUMN goodsmfprice.gmppfzkfd IS '折扣分担';
COMMENT ON COLUMN goodsmfprice.gmpsubco IS '经营公司';
COMMENT ON COLUMN goodsmfprice.gmpjxtax IS '进项税率';
COMMENT ON COLUMN goodsmfprice.gmpminjj IS '最低进价';
COMMENT ON COLUMN goodsmfprice.gmpmaxjj IS '最高进价';
COMMENT ON COLUMN goodsmfprice.gmplastjj IS '最新进价';

CREATE INDEX IF NOT EXISTS index_gmp_gdid ON goodsmfprice (gmpgdid);
CREATE INDEX IF NOT EXISTS index_gmp_market ON goodsmfprice (gmpmarket);
CREATE INDEX IF NOT EXISTS index_gmp_mfid ON goodsmfprice (gmpmfid);
CREATE INDEX IF NOT EXISTS index_gmp_mfidgdid ON goodsmfprice (gmpmfid, gmpgdid);
CREATE INDEX IF NOT EXISTS index_gmp_mktgdid ON goodsmfprice (gmpmarket, gmpgdid);

CREATE TABLE IF NOT EXISTS suppliergoods (
    sgssupid VARCHAR(20) NOT NULL,
    sgsgdid VARCHAR(20) NOT NULL,
    sgsstatus CHAR(1) NOT NULL,
    sgsflag CHAR(1) NOT NULL,
    sgsdhunit VARCHAR(6),
    sgssupcode VARCHAR(20),
    sgscdcode VARCHAR(10),
    sgsdesc VARCHAR(60),
    sgsjxtax NUMERIC(8, 4) NOT NULL,
    sgshsjj NUMERIC(14, 4) NOT NULL,
    sgsbhsjj NUMERIC(14, 4) NOT NULL,
    sgsjysj NUMERIC(12, 2),
    sgsjyhyj NUMERIC(12, 2),
    sgsjypfj NUMERIC(12, 2),
    sgsjypsj NUMERIC(14, 4),
    sgsminzk NUMERIC,
    sgsfjhrq TIMESTAMP,
    sgsljhrq TIMESTAMP,
    sgsttrq TIMESTAMP,
    sgsmaint VARCHAR(20),
    sgsmaintrq TIMESTAMP,
    sgssxksrq TIMESTAMP,
    sgssxjsrq TIMESTAMP,
    CONSTRAINT pk_suppliergoods PRIMARY KEY (sgssupid, sgsgdid)
);

COMMENT ON TABLE suppliergoods IS '[SGS]供应商商品';
COMMENT ON COLUMN suppliergoods.sgssupid IS '供应商';
COMMENT ON COLUMN suppliergoods.sgsgdid IS '商品代码';
COMMENT ON COLUMN suppliergoods.sgsstatus IS '状态';
COMMENT ON COLUMN suppliergoods.sgsflag IS '标志';
COMMENT ON COLUMN suppliergoods.sgsdhunit IS '订货单位';
COMMENT ON COLUMN suppliergoods.sgssupcode IS '供应商商品代码';
COMMENT ON COLUMN suppliergoods.sgscdcode IS '产地';
COMMENT ON COLUMN suppliergoods.sgsdesc IS '来源描述';
COMMENT ON COLUMN suppliergoods.sgsjxtax IS '进项税率';
COMMENT ON COLUMN suppliergoods.sgshsjj IS '含税进价';
COMMENT ON COLUMN suppliergoods.sgsbhsjj IS '不含税进价';
COMMENT ON COLUMN suppliergoods.sgsjysj IS '建议售价';
COMMENT ON COLUMN suppliergoods.sgsjyhyj IS '建议会员价';
COMMENT ON COLUMN suppliergoods.sgsjypfj IS '建议批发价';
COMMENT ON COLUMN suppliergoods.sgsjypsj IS '建议配送价';
COMMENT ON COLUMN suppliergoods.sgsminzk IS '最底折扣';
COMMENT ON COLUMN suppliergoods.sgsfjhrq IS '首次进货日期';
COMMENT ON COLUMN suppliergoods.sgsljhrq IS '最后进货日期';
COMMENT ON COLUMN suppliergoods.sgsttrq IS '淘汰日期';
COMMENT ON COLUMN suppliergoods.sgsmaint IS '维护员';
COMMENT ON COLUMN suppliergoods.sgsmaintrq IS '维护日期';
COMMENT ON COLUMN suppliergoods.sgssxksrq IS 'SGSSXKSRQ';
COMMENT ON COLUMN suppliergoods.sgssxjsrq IS 'SGSSXJSRQ';

CREATE INDEX IF NOT EXISTS index_sgs_gdid ON suppliergoods (sgsgdid);
CREATE INDEX IF NOT EXISTS index_sgs_supid ON suppliergoods (sgssupid);

CREATE TABLE IF NOT EXISTS paymode (
    pmcode VARCHAR(4) NOT NULL,
    pmtype CHAR(1) NOT NULL,
    pmname VARCHAR(20) NOT NULL,
    pmscode CHAR(3) NOT NULL,
    pmpcode VARCHAR(4) NOT NULL,
    pmclass CHAR(1) NOT NULL,
    pmflag CHAR(1) NOT NULL,
    pmrange CHAR(1) DEFAULT '1' NOT NULL,
    pmiswb CHAR(1) NOT NULL,
    pmhl NUMERIC NOT NULL,
    pmiszl CHAR(1) NOT NULL,
    pmisyy CHAR(1) NOT NULL,
    pmminje NUMERIC NOT NULL,
    pmmaxje NUMERIC NOT NULL,
    pmstatus CHAR(1) NOT NULL,
    pmisjkgc CHAR(1) DEFAULT 'N' NOT NULL,
    pmxyktype VARCHAR(2),
    pmrevrate NUMERIC DEFAULT 1,
    pmsupzkfd NUMERIC DEFAULT 0,
    CONSTRAINT pk_paymode PRIMARY KEY (pmcode)
);

COMMENT ON TABLE paymode IS '[PM]付款方式';
COMMENT ON COLUMN paymode.pmcode IS '代码';
COMMENT ON COLUMN paymode.pmtype IS '类别';
COMMENT ON COLUMN paymode.pmname IS '名称';
COMMENT ON COLUMN paymode.pmscode IS '间码';
COMMENT ON COLUMN paymode.pmpcode IS '上级代码';
COMMENT ON COLUMN paymode.pmclass IS '级次';
COMMENT ON COLUMN paymode.pmflag IS '末级标志';
COMMENT ON COLUMN paymode.pmrange IS '使用范围';
COMMENT ON COLUMN paymode.pmiswb IS '是否外币';
COMMENT ON COLUMN paymode.pmhl IS '汇率';
COMMENT ON COLUMN paymode.pmiszl IS '是否找零';
COMMENT ON COLUMN paymode.pmisyy IS '是否溢余';
COMMENT ON COLUMN paymode.pmminje IS '最小金额';
COMMENT ON COLUMN paymode.pmmaxje IS '最大金额';
COMMENT ON COLUMN paymode.pmstatus IS '状态';
COMMENT ON COLUMN paymode.pmisjkgc IS '是否金卡工程';
COMMENT ON COLUMN paymode.pmxyktype IS '信用卡费率代码';
COMMENT ON COLUMN paymode.pmrevrate IS '折算收入比例';
COMMENT ON COLUMN paymode.pmsupzkfd IS '不计收入付款方式金额供应商承担比例';

CREATE TABLE IF NOT EXISTS tktqtype (
    tqcode CHAR(1) NOT NULL,
    tqname VARCHAR(60) NOT NULL,
    tqisfq CHAR(1) DEFAULT '0' NOT NULL,
    tqzxbl NUMERIC DEFAULT 1 NOT NULL,
    tqstatus CHAR(1) DEFAULT '1' NOT NULL,
    tqmemo VARCHAR(100),
    tqisjf CHAR(1) DEFAULT '0',
    tqrevrate NUMERIC DEFAULT 1,
    tqsupzkfd NUMERIC DEFAULT 0,
    CONSTRAINT pk_tktqtype PRIMARY KEY (tqcode)
);

COMMENT ON TABLE tktqtype IS '[TQ]券种字典';
COMMENT ON COLUMN tktqtype.tqcode IS '券种编码（A～Z）';
COMMENT ON COLUMN tktqtype.tqname IS '券名称';
COMMENT ON COLUMN tktqtype.tqisfq IS '1参与返券满赠/0不参与返券满赠';
COMMENT ON COLUMN tktqtype.tqzxbl IS '券退货折现比率';
COMMENT ON COLUMN tktqtype.tqstatus IS '1启用/0禁用';
COMMENT ON COLUMN tktqtype.tqmemo IS '备注';
COMMENT ON COLUMN tktqtype.tqisjf IS '1允许积分/0允许积分';
COMMENT ON COLUMN tktqtype.tqrevrate IS '折算收入比例';
COMMENT ON COLUMN tktqtype.tqsupzkfd IS '不计收入券金额供应商承担比例';

CREATE TABLE IF NOT EXISTS tktqtypemkt (
    tqmcode CHAR(1) NOT NULL,
    tqmmkt VARCHAR(20) NOT NULL,
    tqmisfq CHAR(1) DEFAULT '0' NOT NULL,
    tqmzxbl NUMERIC DEFAULT 1 NOT NULL,
    tqmstatus CHAR(1) DEFAULT '1' NOT NULL,
    tqmmemo VARCHAR(100),
    tqmisjf CHAR(1) DEFAULT '0',
    tqmevrate NUMERIC DEFAULT 1,
    tqmsupzkfd NUMERIC DEFAULT 0,
    CONSTRAINT pk_tktqtypemkt PRIMARY KEY (tqmcode, tqmmkt)
);

COMMENT ON TABLE tktqtypemkt IS '[TQ]券种字典';
COMMENT ON COLUMN tktqtypemkt.tqmcode IS '券种编码（A～Z）';
COMMENT ON COLUMN tktqtypemkt.tqmisfq IS '1参与返券满赠/0不参与返券满赠';
COMMENT ON COLUMN tktqtypemkt.tqmzxbl IS '券退货折现比率';
COMMENT ON COLUMN tktqtypemkt.tqmstatus IS '1启用/0禁用';
COMMENT ON COLUMN tktqtypemkt.tqmmemo IS '备注';
COMMENT ON COLUMN tktqtypemkt.tqmisjf IS '1允许积分/0允许积分';
COMMENT ON COLUMN tktqtypemkt.tqmevrate IS '1计算收入/0不计算收入';
COMMENT ON COLUMN tktqtypemkt.tqmsupzkfd IS '不计收入券金额供应商承担比例';
"""


def upgrade() -> None:
    op.execute(PRODUCT_PAYMENT_COUPON_SQL)


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS tktqtypemkt;
        DROP TABLE IF EXISTS tktqtype;
        DROP TABLE IF EXISTS paymode;
        DROP TABLE IF EXISTS suppliergoods;
        DROP TABLE IF EXISTS goodsmfprice;
        DROP TABLE IF EXISTS goodsmframe;
        DROP TABLE IF EXISTS goodsbarcode;
        DROP TABLE IF EXISTS goodsbase;
        """
    )
