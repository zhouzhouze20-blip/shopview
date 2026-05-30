"""create ERP settlement-related tables (结算单)

Revision ID: f8e9d0c1b2a3
Revises: a3c9e1f7b2d4
Create Date: 2026-05-08

来源: 建表/结算单/*.txt（Oracle DDL）映射为 PostgreSQL。
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f8e9d0c1b2a3"
down_revision: Union[str, Sequence[str], None] = "a3c9e1f7b2d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SETTLEMENT_TABLES_SQL = r"""
CREATE TABLE IF NOT EXISTS mallsuppayhead (
    sphbillno VARCHAR(20) NOT NULL,
    sphdjbh VARCHAR(20),
    sphtype CHAR(1) NOT NULL,
    sphmkt VARCHAR(20) NOT NULL,
    sphflag CHAR(1) NOT NULL,
    sphsupid VARCHAR(20) NOT NULL,
    sphmoney NUMERIC(14, 4) NOT NULL,
    sphmoneyupper VARCHAR(100) NOT NULL,
    sphhl NUMERIC(12, 4),
    sphbz VARCHAR(10),
    sphbbje NUMERIC(14, 4),
    sphbank VARCHAR(60),
    sphaccntno VARCHAR(40),
    sphtaxno VARCHAR(40),
    sphmktbank VARCHAR(60),
    sphmktaccntno VARCHAR(40),
    sphmkttaxno VARCHAR(40),
    sphpaydate DATE NOT NULL,
    inputor VARCHAR(20) NOT NULL,
    inputdate DATE NOT NULL,
    auditor VARCHAR(20),
    auditdate DATE,
    sphn1 NUMERIC,
    sphn2 NUMERIC,
    sphn3 NUMERIC,
    sphvc1 VARCHAR(20),
    sphvc2 VARCHAR(200),
    sphvc3 VARCHAR(20),
    sphmemo VARCHAR(60),
    sphmfid VARCHAR(20),
    sphwmid CHAR(1),
    sphcontno VARCHAR(30),
    sphyckfs NUMERIC,
    CONSTRAINT pk_mallsuppayhead PRIMARY KEY (sphbillno)
);

COMMENT ON TABLE mallsuppayhead IS '[SPH]付款单头';
COMMENT ON COLUMN mallsuppayhead.sphbillno IS '单号';
COMMENT ON COLUMN mallsuppayhead.sphdjbh IS '手工号';
COMMENT ON COLUMN mallsuppayhead.sphtype IS '单据类型';
COMMENT ON COLUMN mallsuppayhead.sphmkt IS '门店';
COMMENT ON COLUMN mallsuppayhead.sphflag IS '状态';
COMMENT ON COLUMN mallsuppayhead.sphsupid IS '供应商';
COMMENT ON COLUMN mallsuppayhead.sphmoney IS '金额';
COMMENT ON COLUMN mallsuppayhead.sphmoneyupper IS '大写金额';
COMMENT ON COLUMN mallsuppayhead.sphhl IS '记帐汇率';
COMMENT ON COLUMN mallsuppayhead.sphbz IS '币种';
COMMENT ON COLUMN mallsuppayhead.sphbbje IS '本币金额';
COMMENT ON COLUMN mallsuppayhead.sphbank IS '开户银行';
COMMENT ON COLUMN mallsuppayhead.sphaccntno IS '银行帐号';
COMMENT ON COLUMN mallsuppayhead.sphtaxno IS '纳税号';
COMMENT ON COLUMN mallsuppayhead.sphmktbank IS '商场开户银行';
COMMENT ON COLUMN mallsuppayhead.sphmktaccntno IS '商场银行帐号';
COMMENT ON COLUMN mallsuppayhead.sphmkttaxno IS '商场纳税号';
COMMENT ON COLUMN mallsuppayhead.sphpaydate IS '付款日期';
COMMENT ON COLUMN mallsuppayhead.inputor IS '录入人';
COMMENT ON COLUMN mallsuppayhead.inputdate IS '录入日期';
COMMENT ON COLUMN mallsuppayhead.auditor IS '审核人';
COMMENT ON COLUMN mallsuppayhead.auditdate IS '审核日期';
COMMENT ON COLUMN mallsuppayhead.sphn1 IS '可抵扣金额';
COMMENT ON COLUMN mallsuppayhead.sphn2 IS '实际收款金额';
COMMENT ON COLUMN mallsuppayhead.sphn3 IS '预存款余额';
COMMENT ON COLUMN mallsuppayhead.sphvc1 IS '转帐标志(0/未处理1/自动转帐2/手工转帐) 抵扣项目';
COMMENT ON COLUMN mallsuppayhead.sphvc2 IS '转帐备注';
COMMENT ON COLUMN mallsuppayhead.sphmemo IS '备注';
COMMENT ON COLUMN mallsuppayhead.sphmfid IS '柜组';
COMMENT ON COLUMN mallsuppayhead.sphwmid IS '经营方式';
COMMENT ON COLUMN mallsuppayhead.sphcontno IS '合同号';
COMMENT ON COLUMN mallsuppayhead.sphyckfs IS '预存款发生额 正数为存入,负数为使用';

CREATE TABLE IF NOT EXISTS suppayhead (
    sphbillno VARCHAR(20) NOT NULL,
    sphdjbh VARCHAR(20),
    sphmkt VARCHAR(20) NOT NULL,
    sphflag CHAR(1) NOT NULL,
    sphsupid VARCHAR(20) NOT NULL,
    sphmoney NUMERIC(14, 4) NOT NULL,
    sphmoneyupper VARCHAR(100) NOT NULL,
    sphhl NUMERIC(12, 4),
    sphbz VARCHAR(10),
    sphbbje NUMERIC(14, 4),
    sphbank VARCHAR(60),
    sphaccntno VARCHAR(40),
    sphtaxno VARCHAR(40),
    sphmktbank VARCHAR(60),
    sphmktaccntno VARCHAR(40),
    sphmkttaxno VARCHAR(40),
    sphpaydate DATE NOT NULL,
    inputor VARCHAR(20) NOT NULL,
    inputdate DATE NOT NULL,
    auditor VARCHAR(20),
    auditdate DATE,
    sphn1 NUMERIC,
    sphn2 NUMERIC,
    sphn3 NUMERIC,
    sphvc1 VARCHAR(20),
    sphvc2 VARCHAR(200),
    sphvc3 VARCHAR(20),
    sphmemo VARCHAR(60),
    sphmfid VARCHAR(20),
    sphwmid CHAR(1),
    CONSTRAINT pk_suppayhead PRIMARY KEY (sphbillno)
);

COMMENT ON TABLE suppayhead IS '[SPH]付款单头';
COMMENT ON COLUMN suppayhead.sphbillno IS '单号';
COMMENT ON COLUMN suppayhead.sphdjbh IS '手工号';
COMMENT ON COLUMN suppayhead.sphmkt IS '门店';
COMMENT ON COLUMN suppayhead.sphflag IS '状态';
COMMENT ON COLUMN suppayhead.sphsupid IS '供应商';
COMMENT ON COLUMN suppayhead.sphmoney IS '金额';
COMMENT ON COLUMN suppayhead.sphmoneyupper IS '大写金额';
COMMENT ON COLUMN suppayhead.sphhl IS '记帐汇率';
COMMENT ON COLUMN suppayhead.sphbz IS '币种';
COMMENT ON COLUMN suppayhead.sphbbje IS '本币金额';
COMMENT ON COLUMN suppayhead.sphbank IS '开户银行';
COMMENT ON COLUMN suppayhead.sphaccntno IS '银行帐号';
COMMENT ON COLUMN suppayhead.sphtaxno IS '纳税号';
COMMENT ON COLUMN suppayhead.sphmktbank IS '商场开户银行';
COMMENT ON COLUMN suppayhead.sphmktaccntno IS '商场银行帐号';
COMMENT ON COLUMN suppayhead.sphmkttaxno IS '商场纳税号';
COMMENT ON COLUMN suppayhead.sphpaydate IS '付款日期';
COMMENT ON COLUMN suppayhead.inputor IS '录入人';
COMMENT ON COLUMN suppayhead.inputdate IS '录入日期';
COMMENT ON COLUMN suppayhead.auditor IS '审核人';
COMMENT ON COLUMN suppayhead.auditdate IS '审核日期';
COMMENT ON COLUMN suppayhead.sphvc2 IS '转帐备注';
COMMENT ON COLUMN suppayhead.sphmemo IS '备注';
COMMENT ON COLUMN suppayhead.sphmfid IS '柜组';
COMMENT ON COLUMN suppayhead.sphwmid IS '经营方式';

CREATE INDEX IF NOT EXISTS idx_sph_auditdate ON suppayhead (auditdate);

CREATE TABLE IF NOT EXISTS supsettlehead (
    sshbillno VARCHAR(20) NOT NULL,
    sshdjbh VARCHAR(20) NOT NULL,
    sshdjlb CHAR(1) NOT NULL,
    sshflag CHAR(1) NOT NULL,
    sshsupid VARCHAR(20) NOT NULL,
    sshwmid CHAR(1) NOT NULL,
    sshmkt VARCHAR(20) NOT NULL,
    sshmfid VARCHAR(20),
    sshcontno VARCHAR(20),
    sshbank VARCHAR(60),
    sshaccntno VARCHAR(40),
    sshtaxno VARCHAR(40),
    sshdate DATE NOT NULL,
    sshlastdate DATE,
    sshthisdate DATE NOT NULL,
    sshlastye NUMERIC(14, 2) NOT NULL,
    sshthisye NUMERIC(14, 2) NOT NULL,
    sshogdje NUMERIC(14, 2) NOT NULL,
    sshmgdje NUMERIC(14, 2) NOT NULL,
    sshaqdje NUMERIC(14, 2) NOT NULL,
    sshtotdje NUMERIC(14, 2) NOT NULL,
    sshtotyfje NUMERIC(14, 2) NOT NULL,
    sshtotkk NUMERIC(14, 2) NOT NULL,
    sshyfkje NUMERIC(14, 2) NOT NULL,
    sshadjustje NUMERIC(14, 2) NOT NULL,
    sshsjfkje NUMERIC(14, 2) NOT NULL,
    sshn1 NUMERIC,
    sshn2 NUMERIC,
    sshn3 NUMERIC,
    sshn4 NUMERIC,
    sshn5 NUMERIC,
    sshn6 NUMERIC,
    sshn7 NUMERIC,
    sshn8 NUMERIC,
    sshvc1 VARCHAR(20),
    sshvc2 VARCHAR(20),
    sshvc3 VARCHAR(600),
    sshvc4 VARCHAR(40),
    sshvc5 VARCHAR(80),
    sshd1 DATE,
    sshd2 DATE,
    sshsupsign VARCHAR(30),
    inputor VARCHAR(20) NOT NULL,
    inputdate DATE NOT NULL,
    auditor VARCHAR(20),
    auditdate DATE,
    buyer VARCHAR(20),
    person1 VARCHAR(20),
    person2 VARCHAR(20),
    person3 VARCHAR(20),
    person4 VARCHAR(20),
    person5 VARCHAR(20),
    sshn9 NUMERIC,
    sshn10 NUMERIC,
    sshsetadj NUMERIC,
    sshsetje NUMERIC,
    sshinvno VARCHAR(20),
    paydate DATE,
    sshpayno VARCHAR(20),
    sshpayflag CHAR(1) NOT NULL DEFAULT 'N',
    sshn11 NUMERIC,
    sshn12 NUMERIC,
    payer VARCHAR(20),
    sshplanpaydate DATE,
    sshenddate DATE,
    sshisadvance VARCHAR(20),
    sshlastbillno VARCHAR(20),
    sshn13 NUMERIC,
    sshn14 NUMERIC,
    sshn15 NUMERIC,
    sshn16 NUMERIC,
    sshn17 NUMERIC,
    sshn18 NUMERIC,
    sshn19 NUMERIC,
    sshn20 NUMERIC,
    sshn21 NUMERIC,
    sshn22 NUMERIC,
    sshn23 NUMERIC,
    sshn24 NUMERIC,
    sshn25 NUMERIC,
    sshn26 NUMERIC,
    sshn27 NUMERIC,
    sshn28 NUMERIC,
    sshn29 NUMERIC,
    sshn30 NUMERIC,
    CONSTRAINT pk_supsettlehead PRIMARY KEY (sshbillno)
);

COMMENT ON TABLE supsettlehead IS '[SSH]供应商结算单';
COMMENT ON COLUMN supsettlehead.sshbillno IS '结算单号';
COMMENT ON COLUMN supsettlehead.sshdjlb IS '单据类别';
COMMENT ON COLUMN supsettlehead.sshflag IS '标志';
COMMENT ON COLUMN supsettlehead.sshsupid IS '供应商';
COMMENT ON COLUMN supsettlehead.sshwmid IS '经营方式';
COMMENT ON COLUMN supsettlehead.sshcontno IS '合同编号';
COMMENT ON COLUMN supsettlehead.sshbank IS '开户银行';
COMMENT ON COLUMN supsettlehead.sshaccntno IS '银行帐号';
COMMENT ON COLUMN supsettlehead.sshtaxno IS '纳税号';
COMMENT ON COLUMN supsettlehead.sshdate IS '制单日期';
COMMENT ON COLUMN supsettlehead.sshlastdate IS '上次结算日期';
COMMENT ON COLUMN supsettlehead.sshthisdate IS '本次结算日期';
COMMENT ON COLUMN supsettlehead.sshlastye IS '上次计算余额';
COMMENT ON COLUMN supsettlehead.sshthisye IS '本次计算余额';
COMMENT ON COLUMN supsettlehead.sshogdje IS '应提成金额';
COMMENT ON COLUMN supsettlehead.sshmgdje IS '保底提成额';
COMMENT ON COLUMN supsettlehead.sshaqdje IS '超额提成额';
COMMENT ON COLUMN supsettlehead.sshtotdje IS '实际提成额合计';
COMMENT ON COLUMN supsettlehead.sshtotyfje IS '应付金额合计';
COMMENT ON COLUMN supsettlehead.sshtotkk IS '扣款合计';
COMMENT ON COLUMN supsettlehead.sshyfkje IS '预付款金额';
COMMENT ON COLUMN supsettlehead.sshadjustje IS '调整金额';
COMMENT ON COLUMN supsettlehead.sshsjfkje IS '实际付款';
COMMENT ON COLUMN supsettlehead.sshsupsign IS '供应商签字';
COMMENT ON COLUMN supsettlehead.inputor IS 'INPUTOR';
COMMENT ON COLUMN supsettlehead.inputdate IS 'INPUTDATE';
COMMENT ON COLUMN supsettlehead.auditor IS 'AUDITOR';
COMMENT ON COLUMN supsettlehead.auditdate IS 'AUDITDATE';
COMMENT ON COLUMN supsettlehead.buyer IS 'BUYER';
COMMENT ON COLUMN supsettlehead.person1 IS 'PERSON1';
COMMENT ON COLUMN supsettlehead.person2 IS 'PERSON2';
COMMENT ON COLUMN supsettlehead.person3 IS 'PERSON3';
COMMENT ON COLUMN supsettlehead.person4 IS 'PERSON4';
COMMENT ON COLUMN supsettlehead.person5 IS 'PERSON5';
COMMENT ON COLUMN supsettlehead.sshn9 IS '累计提成金额（清算时用）';
COMMENT ON COLUMN supsettlehead.sshsetadj IS '结算调整';
COMMENT ON COLUMN supsettlehead.sshsetje IS '结算金额';
COMMENT ON COLUMN supsettlehead.paydate IS '付款审核日期';
COMMENT ON COLUMN supsettlehead.sshpayno IS '付款单号';
COMMENT ON COLUMN supsettlehead.sshpayflag IS '付款标志';
COMMENT ON COLUMN supsettlehead.sshn11 IS '清算应结金额';
COMMENT ON COLUMN supsettlehead.sshn12 IS '清算已结金额';
COMMENT ON COLUMN supsettlehead.payer IS '付款审核人';
COMMENT ON COLUMN supsettlehead.sshplanpaydate IS '计划付款日期';
COMMENT ON COLUMN supsettlehead.sshenddate IS '到期日期';
COMMENT ON COLUMN supsettlehead.sshisadvance IS 'null';
COMMENT ON COLUMN supsettlehead.sshlastbillno IS '上次结算单';
COMMENT ON COLUMN supsettlehead.sshn13 IS '本期入库';
COMMENT ON COLUMN supsettlehead.sshn14 IS '本期退货';
COMMENT ON COLUMN supsettlehead.sshn15 IS '本期调整';
COMMENT ON COLUMN supsettlehead.sshn16 IS '上期未结余款';
COMMENT ON COLUMN supsettlehead.sshn17 IS '本自然年本合同的累计付款';
COMMENT ON COLUMN supsettlehead.sshn18 IS '本自然年本合同的累计销售金额';
COMMENT ON COLUMN supsettlehead.sshn19 IS '本结算单截至日的库存金额';
COMMENT ON COLUMN supsettlehead.sshn20 IS '本年累计入库：本自然年累计入库金额';

CREATE INDEX IF NOT EXISTS idx_ssh_sshdate ON supsettlehead (sshdate);
CREATE INDEX IF NOT EXISTS idx_ssh_supid_date ON supsettlehead (sshsupid, sshwmid, sshmkt, sshthisdate);

CREATE TABLE IF NOT EXISTS supsettledettot (
    sdtbillno VARCHAR(20) NOT NULL,
    sdtrowno NUMERIC NOT NULL,
    sdtflag CHAR(1) NOT NULL,
    sdtitemcode VARCHAR(20) NOT NULL,
    sdtstartdate DATE NOT NULL,
    sdtenddate DATE NOT NULL,
    sdtdep VARCHAR(20) NOT NULL,
    sdtamount NUMERIC NOT NULL DEFAULT 0,
    sdtckamount NUMERIC NOT NULL DEFAULT 0,
    sdtyfamount NUMERIC NOT NULL DEFAULT 0,
    sdtmemo VARCHAR(500),
    sdtdkamount NUMERIC NOT NULL DEFAULT 0,
    sdtye NUMERIC NOT NULL DEFAULT 0,
    sdttype CHAR(1) NOT NULL DEFAULT 'Y',
    sdtisadv CHAR(1) NOT NULL DEFAULT 'N',
    sdtfl CHAR(1),
    sdtcontno VARCHAR(30),
    sdtsupid VARCHAR(30),
    sdtwmid CHAR(1),
    sdtmkt VARCHAR(30),
    sdtmfid VARCHAR(30),
    sdtadjamount NUMERIC NOT NULL DEFAULT 0,
    sdtxssr NUMERIC NOT NULL DEFAULT 0,
    sdthsy VARCHAR(10) NOT NULL DEFAULT '#',
    sdtcalcplace VARCHAR(30) DEFAULT '#',
    sdtcalcrowno NUMERIC DEFAULT 0,
    sdtmfjzmj NUMERIC DEFAULT 0,
    sdtmfzjmj NUMERIC DEFAULT 0,
    sdtareatype CHAR(1) DEFAULT 'Z',
    sdttaxrate NUMERIC DEFAULT 0,
    sdtnotaxamount NUMERIC DEFAULT 0,
    CONSTRAINT pk_supsettledettot PRIMARY KEY (sdtbillno, sdtrowno)
);

COMMENT ON TABLE supsettledettot IS '结算单明细汇总';
COMMENT ON COLUMN supsettledettot.sdtbillno IS '单号';
COMMENT ON COLUMN supsettledettot.sdtrowno IS '行号';
COMMENT ON COLUMN supsettledettot.sdtflag IS '状态 M-生成 Y-审核 E-收款完成';
COMMENT ON COLUMN supsettledettot.sdtitemcode IS '项目编码';
COMMENT ON COLUMN supsettledettot.sdtstartdate IS '开始日期';
COMMENT ON COLUMN supsettledettot.sdtenddate IS '结束日期';
COMMENT ON COLUMN supsettledettot.sdtdep IS '结算部门';
COMMENT ON COLUMN supsettledettot.sdtamount IS '结算金额';
COMMENT ON COLUMN supsettledettot.sdtckamount IS '参考金额';
COMMENT ON COLUMN supsettledettot.sdtyfamount IS '已付金额';
COMMENT ON COLUMN supsettledettot.sdtmemo IS '说明';
COMMENT ON COLUMN supsettledettot.sdtdkamount IS '已抵扣金额';
COMMENT ON COLUMN supsettledettot.sdtye IS '余额';
COMMENT ON COLUMN supsettledettot.sdttype IS 'Y-租金明细 N-费用明细';
COMMENT ON COLUMN supsettledettot.sdtisadv IS 'Y-预收 N-应收 P-应付';
COMMENT ON COLUMN supsettledettot.sdtfl IS '0-销售收入 1-中央收银款 2-租金管理费 3-预收租金 4- 费用';
COMMENT ON COLUMN supsettledettot.sdtcontno IS '合同';
COMMENT ON COLUMN supsettledettot.sdtsupid IS '供应商';
COMMENT ON COLUMN supsettledettot.sdtwmid IS '经营方式';
COMMENT ON COLUMN supsettledettot.sdtmkt IS '门店';
COMMENT ON COLUMN supsettledettot.sdtmfid IS '柜组';
COMMENT ON COLUMN supsettledettot.sdtadjamount IS '调整金额';
COMMENT ON COLUMN supsettledettot.sdtxssr IS '销售收入[计算提成、清算或销售返款时的销售收入]';
COMMENT ON COLUMN supsettledettot.sdtcalcplace IS '计算位置(内部使用,见结算包说明)';
COMMENT ON COLUMN supsettledettot.sdtcalcrowno IS '计算行号(内部使用,见结算包说明)';
COMMENT ON COLUMN supsettledettot.sdtmfjzmj IS '商位面积-建筑面积';
COMMENT ON COLUMN supsettledettot.sdtmfzjmj IS '商位面积-租金面积';
COMMENT ON COLUMN supsettledettot.sdtareatype IS '面积计算基数 Z-使用租金面积 J-使用建筑面积';
COMMENT ON COLUMN supsettledettot.sdttaxrate IS '税率';
COMMENT ON COLUMN supsettledettot.sdtnotaxamount IS '不含税金额';

CREATE TABLE IF NOT EXISTS supsetcharge (
    sscbillno VARCHAR(20) NOT NULL,
    sscrowno NUMERIC(6, 0) NOT NULL,
    sscdjbh VARCHAR(20) NOT NULL,
    ssctype CHAR(1) NOT NULL,
    sscflag CHAR(1) NOT NULL,
    sscsupid VARCHAR(20) NOT NULL,
    sscwmid CHAR(1),
    sscmarket VARCHAR(20),
    sscmfid VARCHAR(20),
    sscdate DATE NOT NULL,
    sscfsdate DATE NOT NULL,
    sscfsmon CHAR(6) NOT NULL,
    sscid CHAR(2) NOT NULL,
    sscname VARCHAR(32),
    sscmoney NUMERIC(12, 2) NOT NULL,
    sscjsno VARCHAR(20),
    ssccontno VARCHAR(20),
    inputor VARCHAR(20) NOT NULL,
    inputdate DATE NOT NULL,
    auditor VARCHAR(20),
    auditdate DATE,
    person1 VARCHAR(20),
    person2 VARCHAR(20),
    person3 VARCHAR(20),
    person4 VARCHAR(20),
    person5 VARCHAR(20),
    sscmemo VARCHAR(2000),
    sscsetpl VARCHAR(20),
    sscgdmoney NUMERIC(12, 2),
    sscmoneyupper VARCHAR(100),
    sscret CHAR(1) DEFAULT 'N',
    sscretdate DATE,
    sscretstatus CHAR(1) DEFAULT 'N',
    sscretmoney NUMERIC,
    sscrecretdate DATE,
    sscyretbillno VARCHAR(20),
    sscrettype CHAR(1) DEFAULT '1',
    sscpaymkt VARCHAR(20),
    sscsyjid VARCHAR(20),
    sscinvno VARCHAR(20),
    sscchecker VARCHAR(20),
    sscvc1 VARCHAR(20),
    sscvc2 VARCHAR(20),
    sscvc3 VARCHAR(20),
    sscfsstartdate DATE,
    sscfsenddate DATE,
    sscpayer VARCHAR(20),
    sscpaydate DATE,
    sscdate1 DATE,
    sscdate2 DATE,
    sscdate3 DATE,
    sscnum1 NUMERIC,
    sscnum2 NUMERIC,
    sscnum3 NUMERIC,
    sscisqs CHAR(1),
    sscqssettleno VARCHAR(20),
    sscpaybillno VARCHAR(20),
    CONSTRAINT pk_supsetcharge PRIMARY KEY (sscbillno, sscrowno)
);

COMMENT ON TABLE supsetcharge IS '[SSC]供应商结算费用明细';
COMMENT ON COLUMN supsetcharge.sscbillno IS '费用单号';
COMMENT ON COLUMN supsetcharge.sscrowno IS '行号';
COMMENT ON COLUMN supsetcharge.sscdjbh IS 'SSCDJBH';
COMMENT ON COLUMN supsetcharge.ssctype IS '单据类型';
COMMENT ON COLUMN supsetcharge.sscflag IS '标志(录入	N/已生成结算单	M/结算审核	Y/费用审核	S/已收款	G)';
COMMENT ON COLUMN supsetcharge.sscsupid IS '供应商';
COMMENT ON COLUMN supsetcharge.sscwmid IS '经营方式';
COMMENT ON COLUMN supsetcharge.sscmarket IS '门店';
COMMENT ON COLUMN supsetcharge.sscmfid IS '柜组';
COMMENT ON COLUMN supsetcharge.sscdate IS '制单日期';
COMMENT ON COLUMN supsetcharge.sscfsdate IS '发生日期';
COMMENT ON COLUMN supsetcharge.sscfsmon IS '发生月';
COMMENT ON COLUMN supsetcharge.sscid IS '费用代码';
COMMENT ON COLUMN supsetcharge.sscname IS '费用名称';
COMMENT ON COLUMN supsetcharge.sscmoney IS '费用金额';
COMMENT ON COLUMN supsetcharge.sscjsno IS '结算单号';
COMMENT ON COLUMN supsetcharge.ssccontno IS 'SSCCONTNO';
COMMENT ON COLUMN supsetcharge.inputor IS 'INPUTOR';
COMMENT ON COLUMN supsetcharge.inputdate IS 'INPUTDATE';
COMMENT ON COLUMN supsetcharge.auditor IS 'AUDITOR';
COMMENT ON COLUMN supsetcharge.auditdate IS 'AUDITDATE';
COMMENT ON COLUMN supsetcharge.person1 IS 'PERSON1';
COMMENT ON COLUMN supsetcharge.person2 IS 'PERSON2';
COMMENT ON COLUMN supsetcharge.person4 IS '能源区间读数';
COMMENT ON COLUMN supsetcharge.sscmemo IS 'SSCMEMO';
COMMENT ON COLUMN supsetcharge.sscgdmoney IS '商品费用金额';
COMMENT ON COLUMN supsetcharge.sscmoneyupper IS '大写金额';
COMMENT ON COLUMN supsetcharge.sscret IS '是否返还';
COMMENT ON COLUMN supsetcharge.sscretdate IS '返还日期';
COMMENT ON COLUMN supsetcharge.sscretstatus IS '是否终止返回';
COMMENT ON COLUMN supsetcharge.sscretmoney IS '返还金额';
COMMENT ON COLUMN supsetcharge.sscrecretdate IS '最近返还日期';
COMMENT ON COLUMN supsetcharge.sscyretbillno IS '原返还单号';
COMMENT ON COLUMN supsetcharge.sscvc2 IS '付款方式';
COMMENT ON COLUMN supsetcharge.sscfsstartdate IS '发生开始日期';
COMMENT ON COLUMN supsetcharge.sscfsenddate IS '发生结算日期';
COMMENT ON COLUMN supsetcharge.sscpayer IS '付款人';
COMMENT ON COLUMN supsetcharge.sscpaydate IS '付款日期';
COMMENT ON COLUMN supsetcharge.sscdate1 IS '实际付款日期';
COMMENT ON COLUMN supsetcharge.sscpaybillno IS '付款单号';

CREATE INDEX IF NOT EXISTS idx_ssc_date_mkt ON supsetcharge (auditdate, sscmarket);
CREATE INDEX IF NOT EXISTS idx_ssc_djbh ON supsetcharge (sscdjbh);
CREATE INDEX IF NOT EXISTS idx_ssc_jsno ON supsetcharge (sscjsno);
CREATE INDEX IF NOT EXISTS idx_ssc_fsdate ON supsetcharge (sscfsdate);
CREATE INDEX IF NOT EXISTS idx_ssc_supid ON supsetcharge (sscsupid);

CREATE TABLE IF NOT EXISTS supsettlepaydet (
    spdbillno VARCHAR(20) NOT NULL,
    spdrowno NUMERIC NOT NULL,
    spdsetbillno VARCHAR(20) NOT NULL,
    spdsetrowno NUMERIC NOT NULL,
    spditemcode VARCHAR(20) NOT NULL,
    spdstartdate DATE NOT NULL,
    spdenddate DATE NOT NULL,
    spddep VARCHAR(20) NOT NULL,
    spdamount NUMERIC NOT NULL,
    spdckamount NUMERIC NOT NULL,
    spdyfamount NUMERIC NOT NULL,
    spdbcpay NUMERIC NOT NULL,
    spdbcdk NUMERIC NOT NULL DEFAULT 0,
    spdmemo VARCHAR(500),
    spdtype CHAR(1) NOT NULL DEFAULT 'Y',
    spdisadv CHAR(1) NOT NULL DEFAULT 'N',
    spdmfid VARCHAR(30),
    spdzntype CHAR(1),
    spdtaxrate NUMERIC DEFAULT 0,
    spdnotaxamount NUMERIC DEFAULT 0,
    CONSTRAINT pk_supsettlepaydet PRIMARY KEY (spdbillno, spdrowno)
);

COMMENT ON TABLE supsettlepaydet IS '结算单明细汇总';
COMMENT ON COLUMN supsettlepaydet.spdbillno IS '单号';
COMMENT ON COLUMN supsettlepaydet.spdrowno IS '行号';
COMMENT ON COLUMN supsettlepaydet.spdsetbillno IS '结算单号';
COMMENT ON COLUMN supsettlepaydet.spdsetrowno IS '结算明细行号';
COMMENT ON COLUMN supsettlepaydet.spditemcode IS '项目编码';
COMMENT ON COLUMN supsettlepaydet.spdstartdate IS '开始日期';
COMMENT ON COLUMN supsettlepaydet.spdenddate IS '结束日期';
COMMENT ON COLUMN supsettlepaydet.spddep IS '结算部门';
COMMENT ON COLUMN supsettlepaydet.spdamount IS '结算金额';
COMMENT ON COLUMN supsettlepaydet.spdckamount IS '参考金额';
COMMENT ON COLUMN supsettlepaydet.spdyfamount IS '已付金额';
COMMENT ON COLUMN supsettlepaydet.spdbcpay IS '本次收款金额';
COMMENT ON COLUMN supsettlepaydet.spdbcdk IS '已抵扣金额';
COMMENT ON COLUMN supsettlepaydet.spdmemo IS '说明';
COMMENT ON COLUMN supsettlepaydet.spdtype IS 'Y-租金明细 N-费用明细';
COMMENT ON COLUMN supsettlepaydet.spdisadv IS '是否预收 收款时使用 Y/N';
COMMENT ON COLUMN supsettlepaydet.spdmfid IS '商位';
COMMENT ON COLUMN supsettlepaydet.spdzntype IS '滞纳金处理方式，Y-收取,N-免除';
COMMENT ON COLUMN supsettlepaydet.spdtaxrate IS '税率';
COMMENT ON COLUMN supsettlepaydet.spdnotaxamount IS '不含税金额';

CREATE INDEX IF NOT EXISTS idx_supsettlepaydet_lookup ON supsettlepaydet (
    spdsetbillno, spditemcode, spdstartdate, spdenddate, spddep, spdtype
);

CREATE TABLE IF NOT EXISTS paybatch (
    pbseq NUMERIC NOT NULL,
    pbsupid VARCHAR(20) NOT NULL,
    pbwmid CHAR(1) NOT NULL,
    pbmkt VARCHAR(20) NOT NULL,
    pbmfid VARCHAR(20) NOT NULL,
    pbmcontno VARCHAR(20) NOT NULL,
    pbcontno VARCHAR(20) NOT NULL,
    pbjsno VARCHAR(20) NOT NULL,
    pbbillno VARCHAR(20) NOT NULL,
    pbdjlb CHAR(1) NOT NULL,
    pbfeetype CHAR(1),
    pbbilltype CHAR(1) NOT NULL,
    pbjssdate DATE,
    pbjsedate DATE,
    pbxssr NUMERIC,
    pbtc NUMERIC NOT NULL,
    pbyf NUMERIC NOT NULL,
    pbpay NUMERIC NOT NULL DEFAULT 0,
    pbsf NUMERIC NOT NULL DEFAULT 0,
    pbdate DATE NOT NULL,
    pbisgen CHAR(1) NOT NULL DEFAULT 'N',
    pbpaybillno VARCHAR(20),
    pbpaystatus CHAR(1),
    pbselected CHAR(1) DEFAULT 'Y',
    pbkp NUMERIC(14, 2),
    pbbckp NUMERIC(14, 2),
    pbykp NUMERIC(14, 2),
    pbjh NUMERIC(14, 2),
    pbzkfd NUMERIC(14, 2),
    pbyfk NUMERIC(14, 2),
    pbsy NUMERIC(14, 2),
    pbzj NUMERIC(14, 2),
    pbfy1 NUMERIC(14, 2),
    pbfy2 NUMERIC(14, 2),
    pbn1 NUMERIC(14, 2),
    pbn2 NUMERIC(14, 2),
    pbn3 NUMERIC(14, 2),
    pbn4 NUMERIC(14, 2),
    CONSTRAINT pk_paybatch PRIMARY KEY (
        pbseq, pbsupid, pbwmid, pbmkt, pbmfid, pbmcontno,
        pbjsno, pbbillno, pbdjlb, pbbilltype, pbcontno
    )
);

COMMENT ON TABLE paybatch IS '付款批次临时表';
COMMENT ON COLUMN paybatch.pbseq IS '结算批次号';
COMMENT ON COLUMN paybatch.pbsupid IS '供应商';
COMMENT ON COLUMN paybatch.pbwmid IS '经营方式';
COMMENT ON COLUMN paybatch.pbmkt IS '付款位置';
COMMENT ON COLUMN paybatch.pbmfid IS '柜组';
COMMENT ON COLUMN paybatch.pbmcontno IS '主合同号';
COMMENT ON COLUMN paybatch.pbcontno IS '子合同号';
COMMENT ON COLUMN paybatch.pbjsno IS '结算单号';
COMMENT ON COLUMN paybatch.pbbillno IS '单据号';
COMMENT ON COLUMN paybatch.pbdjlb IS '单据类别';
COMMENT ON COLUMN paybatch.pbfeetype IS '费用类型[账扣,非账扣]';
COMMENT ON COLUMN paybatch.pbbilltype IS 'J-结算 F-费用 P-联营预付款';
COMMENT ON COLUMN paybatch.pbjssdate IS '结算开始日期';
COMMENT ON COLUMN paybatch.pbjsedate IS '结算截止日期';
COMMENT ON COLUMN paybatch.pbxssr IS '销售收入';
COMMENT ON COLUMN paybatch.pbtc IS '提成或费用或预付款金额';
COMMENT ON COLUMN paybatch.pbyf IS '应付金额';
COMMENT ON COLUMN paybatch.pbpay IS '已付';
COMMENT ON COLUMN paybatch.pbsf IS '本次付款';
COMMENT ON COLUMN paybatch.pbdate IS '生成日期';
COMMENT ON COLUMN paybatch.pbisgen IS '是否生成付款单';
COMMENT ON COLUMN paybatch.pbpaybillno IS '付款单号';
COMMENT ON COLUMN paybatch.pbpaystatus IS '付款状态';

CREATE INDEX IF NOT EXISTS idx_pb_date ON paybatch (pbdate);
CREATE INDEX IF NOT EXISTS idx_pb_paybillno_jsno_mfid ON paybatch (pbpaybillno, pbjsno, pbmfid);

CREATE TABLE IF NOT EXISTS mallsupadvances (
    advseq NUMERIC NOT NULL,
    supid VARCHAR(30) NOT NULL,
    mkt VARCHAR(30) NOT NULL,
    contno VARCHAR(30) NOT NULL,
    mfid VARCHAR(30) NOT NULL,
    feeid VARCHAR(2) NOT NULL,
    feename VARCHAR(60) NOT NULL,
    feetype VARCHAR(4) NOT NULL,
    balance NUMERIC NOT NULL,
    ysamount NUMERIC NOT NULL DEFAULT 0,
    chargeamount NUMERIC NOT NULL DEFAULT 0,
    returnamount NUMERIC NOT NULL DEFAULT 0,
    yssdate DATE NOT NULL,
    ysedate DATE NOT NULL,
    adjamount NUMERIC NOT NULL DEFAULT 0,
    jsbillno VARCHAR(30) NOT NULL,
    jsbillid VARCHAR(10),
    jsbillstatus CHAR(1),
    isconfirm CHAR(1),
    confirmbillno VARCHAR(30),
    confirmbillid VARCHAR(10),
    confirmbillstatus CHAR(1),
    acre NUMERIC,
    jzacre NUMERIC,
    acretype CHAR(1),
    unit CHAR(1),
    price NUMERIC NOT NULL DEFAULT 0,
    zshamount NUMERIC NOT NULL DEFAULT 0,
    calcplace VARCHAR(30),
    calcrowno NUMERIC,
    isadv CHAR(1) NOT NULL DEFAULT 'Y',
    CONSTRAINT pk_mallsupadvances PRIMARY KEY (advseq)
);

COMMENT ON TABLE mallsupadvances IS '商户押金余额表';
COMMENT ON COLUMN mallsupadvances.advseq IS '序列';
COMMENT ON COLUMN mallsupadvances.supid IS '供应商编号';
COMMENT ON COLUMN mallsupadvances.contno IS '租约编号';
COMMENT ON COLUMN mallsupadvances.mfid IS '柜组';
COMMENT ON COLUMN mallsupadvances.feeid IS '费用代码';
COMMENT ON COLUMN mallsupadvances.feename IS '费用名称';
COMMENT ON COLUMN mallsupadvances.feetype IS '费用类型';
COMMENT ON COLUMN mallsupadvances.balance IS '预收余额';
COMMENT ON COLUMN mallsupadvances.ysamount IS '应收金额';
COMMENT ON COLUMN mallsupadvances.chargeamount IS '已收';
COMMENT ON COLUMN mallsupadvances.returnamount IS '已退';
COMMENT ON COLUMN mallsupadvances.yssdate IS '开始日期';
COMMENT ON COLUMN mallsupadvances.ysedate IS '结束日期';
COMMENT ON COLUMN mallsupadvances.adjamount IS '调整金额';
COMMENT ON COLUMN mallsupadvances.jsbillno IS '结算单据编号';
COMMENT ON COLUMN mallsupadvances.jsbillid IS '结算单类型';
COMMENT ON COLUMN mallsupadvances.jsbillstatus IS '结算单状态';
COMMENT ON COLUMN mallsupadvances.isconfirm IS '是否已确认';
COMMENT ON COLUMN mallsupadvances.confirmbillno IS '确认结算单编号';
COMMENT ON COLUMN mallsupadvances.confirmbillid IS '确认结算单类型';
COMMENT ON COLUMN mallsupadvances.confirmbillstatus IS '确认结算单状态';
COMMENT ON COLUMN mallsupadvances.acre IS '租金面积';
COMMENT ON COLUMN mallsupadvances.jzacre IS '建筑面积';
COMMENT ON COLUMN mallsupadvances.acretype IS '面积类型';
COMMENT ON COLUMN mallsupadvances.unit IS '单位';
COMMENT ON COLUMN mallsupadvances.price IS '单价';
COMMENT ON COLUMN mallsupadvances.zshamount IS '已结转实收金额';
COMMENT ON COLUMN mallsupadvances.calcplace IS '计算位置(内部使用)';
COMMENT ON COLUMN mallsupadvances.calcrowno IS '计算行号';
COMMENT ON COLUMN mallsupadvances.isadv IS '是否是预收费用';

CREATE INDEX IF NOT EXISTS idx_mallsupadvances_lookup ON mallsupadvances (
    supid, mkt, contno, mfid, feeid, yssdate, ysedate
);
"""


def upgrade() -> None:
    op.execute(SETTLEMENT_TABLES_SQL)


def downgrade() -> None:
    op.drop_index("idx_mallsupadvances_lookup", table_name="mallsupadvances")
    op.drop_table("mallsupadvances")
    op.drop_index("idx_pb_paybillno_jsno_mfid", table_name="paybatch")
    op.drop_index("idx_pb_date", table_name="paybatch")
    op.drop_table("paybatch")
    op.drop_index("idx_supsettlepaydet_lookup", table_name="supsettlepaydet")
    op.drop_table("supsettlepaydet")
    op.drop_index("idx_ssc_supid", table_name="supsetcharge")
    op.drop_index("idx_ssc_fsdate", table_name="supsetcharge")
    op.drop_index("idx_ssc_jsno", table_name="supsetcharge")
    op.drop_index("idx_ssc_djbh", table_name="supsetcharge")
    op.drop_index("idx_ssc_date_mkt", table_name="supsetcharge")
    op.drop_table("supsetcharge")
    op.drop_table("supsettledettot")
    op.drop_index("idx_ssh_supid_date", table_name="supsettlehead")
    op.drop_index("idx_ssh_sshdate", table_name="supsettlehead")
    op.drop_table("supsettlehead")
    op.drop_index("idx_sph_auditdate", table_name="suppayhead")
    op.drop_table("suppayhead")
    op.drop_table("mallsuppayhead")
