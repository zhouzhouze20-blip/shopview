"""create erp contract tables

Revision ID: 4f6b2a1c9d08
Revises: 7d4b8a2c6f10, add_store_id_to_floors
Create Date: 2026-04-20 17:04:29

"""
from typing import Sequence, Union

from alembic import op


revision: str = "4f6b2a1c9d08"
down_revision: Union[str, Sequence[str], None] = ("7d4b8a2c6f10", "add_store_id_to_floors")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ERP_CONTRACT_TABLES_SQL = r"""
CREATE TABLE IF NOT EXISTS contmain (
    cmcontno VARCHAR(20) NOT NULL,
    cmstatus CHAR(1) NOT NULL,
    cmtype CHAR(1) NOT NULL,
    cmmfid VARCHAR(20),
    cmsupid VARCHAR(20) NOT NULL,
    cmwmid CHAR(1) NOT NULL,
    cmtitle VARCHAR(60) NOT NULL,
    cmobject VARCHAR(60) NOT NULL,
    cmppname VARCHAR(400),
    cmcatname VARCHAR(60),
    cmcatnum NUMERIC(6),
    cmeffdate TIMESTAMP NOT NULL,
    cmlapdate TIMESTAMP NOT NULL,
    cmmoney NUMERIC(16, 4),
    cmpaycode CHAR(4) NOT NULL,
    cmrefermode CHAR(1),
    cmreferplace VARCHAR(30),
    cmbysettle CHAR(1) NOT NULL,
    cmyfkmode CHAR(1) NOT NULL,
    cmyfk NUMERIC(14, 4),
    cmsetmode CHAR(1) NOT NULL,
    cmzqts1 NUMERIC(4),
    cmzqts2 NUMERIC(8, 2),
    cmzqts3 NUMERIC(4),
    cmzqts4 NUMERIC(4),
    cmzqts5 NUMERIC(4),
    cmzqrate1 NUMERIC(5, 4),
    cmzqrate2 NUMERIC(5, 4),
    cmzqrate3 NUMERIC(5, 4),
    cmzqrate4 NUMERIC(5, 4),
    cmzqrate5 NUMERIC(5, 4),
    cmdhfs CHAR(1),
    cmweek0 CHAR(1),
    cmweek1 CHAR(1),
    cmweek2 CHAR(1),
    cmweek3 CHAR(1),
    cmweek4 CHAR(1),
    cmweek5 CHAR(1),
    cmweek6 CHAR(1),
    cmpasign CHAR(1) DEFAULT 'N' NOT NULL,
    cmpasignper VARCHAR(30),
    cmpasigndate TIMESTAMP,
    cmpbsign CHAR(1) DEFAULT 'N' NOT NULL,
    cmpbsignper VARCHAR(30),
    cmpbsigndate TIMESTAMP,
    cminputor VARCHAR(20) NOT NULL,
    cminputdate TIMESTAMP NOT NULL,
    cmauditor VARCHAR(20),
    cmauditdate TIMESTAMP,
    cmannulor VARCHAR(20),
    cmannuldate TIMESTAMP,
    cmfreezer VARCHAR(20),
    cmfreezedate TIMESTAMP,
    cmmemo VARCHAR(1000),
    cmjsmkt VARCHAR(20),
    cmkl NUMERIC(16, 4),
    cmlastsetdate TIMESTAMP,
    cmsettletype CHAR(1),
    cmlastqsdate TIMESTAMP,
    cmchr1 VARCHAR(40),
    cmchr2 VARCHAR(40),
    cmchr3 VARCHAR(40),
    cmchr4 VARCHAR(40),
    cmchr5 VARCHAR(40),
    cmchr6 VARCHAR(40),
    cmchr7 VARCHAR(40),
    cmchr8 VARCHAR(40),
    cmchr9 VARCHAR(40),
    cmchr10 VARCHAR(40),
    cmpostype VARCHAR(1) DEFAULT 'Y',
    cmbanktype VARCHAR(1) DEFAULT 'Y',
    cmqzyq VARCHAR(1),
    cmtqmon NUMERIC,
    cmjmon NUMERIC,
    cmzljl NUMERIC(16, 4),
    cmzcfkr NUMERIC,
    cmzjtype VARCHAR(2) DEFAULT 'S',
    cmdqcl VARCHAR(1) DEFAULT 'S',
    cmyqmon NUMERIC,
    cmtqzz VARCHAR(1) DEFAULT 'N',
    cmtqzzmon NUMERIC,
    cmmzts NUMERIC,
    cmzj CHAR(1),
    cmwgf CHAR(1),
    cmpos CHAR(1),
    cmygf CHAR(1),
    cmyxs VARCHAR(40),
    cmsqk CHAR(1) DEFAULT 'N',
    cmsqkoper VARCHAR(40),
    cmsptype CHAR(1) DEFAULT 'B',
    cmjsr VARCHAR(20),
    cmyt VARCHAR(40),
    cmkyrq TIMESTAMP,
    cmzsy VARCHAR(20),
    cmzjbz VARCHAR(30),
    cmzjbzdj VARCHAR(30),
    cmzjbzbz VARCHAR(30),
    cmzczdrts VARCHAR(30),
    cmhtbh VARCHAR(30),
    cmnum1 NUMERIC(16, 4),
    cmnum2 NUMERIC(16, 4),
    cmnum3 NUMERIC(16, 4),
    cmjhqd CHAR(1),
    cmmasterno VARCHAR(20),
    cmseqno VARCHAR(2),
    cmcontact VARCHAR(20),
    cmadd VARCHAR(100),
    cmtel VARCHAR(100),
    cmfax VARCHAR(100),
    cmqq VARCHAR(100),
    cmemail VARCHAR(100),
    cmsuptype VARCHAR(2),
    cmhhtype VARCHAR(2),
    cmhhterm VARCHAR(2),
    cmjkcond VARCHAR(2),
    cmchar1 VARCHAR(100),
    cmchar2 VARCHAR(100),
    cmchar3 VARCHAR(100),
    cmchar4 VARCHAR(100),
    cmchar5 VARCHAR(100),
    cmchar6 VARCHAR(100),
    cmchar7 VARCHAR(100),
    cmchar8 VARCHAR(100),
    cmchar9 VARCHAR(100),
    cmchar0 VARCHAR(100),
    signdate TIMESTAMP,
    deliverydate TIMESTAMP,
    tackbackdate TIMESTAMP,
    sjcgdate TIMESTAMP,
    effectdate TIMESTAMP,
    zxqsrq TIMESTAMP,
    zxjzrq TIMESTAMP,
    yszq1 NUMERIC DEFAULT 0 NOT NULL,
    yszq2 NUMERIC DEFAULT 0 NOT NULL,
    yszq3 NUMERIC DEFAULT 0 NOT NULL,
    settlegroup VARCHAR(10),
    cmttr VARCHAR(20),
    cmttdate TIMESTAMP,
    cmdate1 TIMESTAMP,
    cmdate2 TIMESTAMP,
    cmdate3 TIMESTAMP,
    cmkhfs CHAR(1),
    cmznjfs CHAR(1) DEFAULT '1',
    CONSTRAINT pk_contmain PRIMARY KEY (cmcontno)
);
COMMENT ON TABLE contmain IS '[CM]合同主体信息';
COMMENT ON COLUMN contmain.cmcontno IS '合同编号(子合同号)';
COMMENT ON COLUMN contmain.cmstatus IS '状态未生效	B/已生效	Y/停用	S/终止	N/已审批	A/过期	Q/';
COMMENT ON COLUMN contmain.cmtype IS '类型';
COMMENT ON COLUMN contmain.cmmfid IS '签订部门';
COMMENT ON COLUMN contmain.cmsupid IS '供应商代码';
COMMENT ON COLUMN contmain.cmwmid IS '经营方式';
COMMENT ON COLUMN contmain.cmtitle IS '主题';
COMMENT ON COLUMN contmain.cmobject IS '合同标的';
COMMENT ON COLUMN contmain.cmppname IS '品牌';
COMMENT ON COLUMN contmain.cmcatname IS '品种';
COMMENT ON COLUMN contmain.cmcatnum IS '品种数量';
COMMENT ON COLUMN contmain.cmeffdate IS '生效日期';
COMMENT ON COLUMN contmain.cmlapdate IS '失效日期';
COMMENT ON COLUMN contmain.cmmoney IS '月目标销售额';
COMMENT ON COLUMN contmain.cmpaycode IS '付款方式';
COMMENT ON COLUMN contmain.cmrefermode IS '提货方式';
COMMENT ON COLUMN contmain.cmreferplace IS '提货地点';
COMMENT ON COLUMN contmain.cmbysettle IS '结算依据';
COMMENT ON COLUMN contmain.cmyfkmode IS '超额方式';
COMMENT ON COLUMN contmain.cmsetmode IS '结算方式';
COMMENT ON COLUMN contmain.cmzqts1 IS '店长人数';
COMMENT ON COLUMN contmain.cmdhfs IS '到货方式';
COMMENT ON COLUMN contmain.cmweek0 IS '售价形式';
COMMENT ON COLUMN contmain.cmweek1 IS '购物袋形式';
COMMENT ON COLUMN contmain.cmweek2 IS '是否提供增值税发票';
COMMENT ON COLUMN contmain.cmweek3 IS '促销人员工装';
COMMENT ON COLUMN contmain.cmweek4 IS '店长工装';
COMMENT ON COLUMN contmain.cmweek5 IS '保底方式';
COMMENT ON COLUMN contmain.cmpasign IS '甲方是否签字';
COMMENT ON COLUMN contmain.cmpasignper IS '甲方签字人';
COMMENT ON COLUMN contmain.cmpasigndate IS '甲方签字日期';
COMMENT ON COLUMN contmain.cmpbsign IS '乙方是否签字';
COMMENT ON COLUMN contmain.cmpbsignper IS '乙方签字人';
COMMENT ON COLUMN contmain.cmpbsigndate IS '乙方签字日期';
COMMENT ON COLUMN contmain.cminputor IS '录入员';
COMMENT ON COLUMN contmain.cminputdate IS '录入日期';
COMMENT ON COLUMN contmain.cmauditor IS '审核人';
COMMENT ON COLUMN contmain.cmauditdate IS '审核日期';
COMMENT ON COLUMN contmain.cmannulor IS '解除/终止人';
COMMENT ON COLUMN contmain.cmannuldate IS '解除/终止日期';
COMMENT ON COLUMN contmain.cmfreezer IS '挂起人';
COMMENT ON COLUMN contmain.cmfreezedate IS '挂起日期';
COMMENT ON COLUMN contmain.cmmemo IS 'MEMO';
COMMENT ON COLUMN contmain.cmlastsetdate IS '上次结算日期';
COMMENT ON COLUMN contmain.cmsettletype IS '是否清算';
COMMENT ON COLUMN contmain.cmlastqsdate IS '上次清算日期';
COMMENT ON COLUMN contmain.cmchr1 IS '合同分类';
COMMENT ON COLUMN contmain.cmchr2 IS '是否卓展独有品牌';
COMMENT ON COLUMN contmain.cmchr3 IS '业种';
COMMENT ON COLUMN contmain.cmchr4 IS '是否标准合作条件';
COMMENT ON COLUMN contmain.cmchr5 IS '电费承担';
COMMENT ON COLUMN contmain.cmchr6 IS '电力增容费承担';
COMMENT ON COLUMN contmain.cmchr7 IS '供应商参加活动方式';
COMMENT ON COLUMN contmain.cmchr8 IS '合同所处阶段 [租赁-XDJLX]';
COMMENT ON COLUMN contmain.cmchr9 IS '撤场原因[租赁-ENDREASON]';
COMMENT ON COLUMN contmain.cmchr10 IS '招商原合同编号';
COMMENT ON COLUMN contmain.cmpostype IS '收款方式 代收银Y/自收银N';
COMMENT ON COLUMN contmain.cmbanktype IS '银行刷卡 进商场银行帐户Y/进商户自开帐户N';
COMMENT ON COLUMN contmain.cmqzyq IS '缴租要求 月结Y/提前交租N';
COMMENT ON COLUMN contmain.cmtqmon IS '提前几月 -1不提前 0-提前 1- 提前一个月';
COMMENT ON COLUMN contmain.cmjmon IS '计费周期';
COMMENT ON COLUMN contmain.cmzljl IS '滞纳金率';
COMMENT ON COLUMN contmain.cmzcfkr IS '缴款期限(天) 最迟付款日为帐单后几日';
COMMENT ON COLUMN contmain.cmzjtype IS '合同租金计算模式：月租金+抽成租金(抽成、保底)S/月租金、抽成租金(抽成)两者取高';
COMMENT ON COLUMN contmain.cmdqcl IS '到期处理 自动延续Y/自动终止S ';
COMMENT ON COLUMN contmain.cmyqmon IS '自动延续期限几月';
COMMENT ON COLUMN contmain.cmtqzz IS '提前终止 处罚Y/不处罚N';
COMMENT ON COLUMN contmain.cmtqzzmon IS '提前终止期限 几月';
COMMENT ON COLUMN contmain.cmmzts IS '合同期内装修免租天数';
COMMENT ON COLUMN contmain.cmyxs IS '原意向书编号';
COMMENT ON COLUMN contmain.cmsqk IS '首期缴款单生成标志(Y),(E)合同清退';
COMMENT ON COLUMN contmain.cmsqkoper IS '首期缴款单生成人';
COMMENT ON COLUMN contmain.cmsptype IS '租赁合同类型S=商位 G=广告位 Z=展位 B=百货';
COMMENT ON COLUMN contmain.cmjsr IS '接手人';
COMMENT ON COLUMN contmain.cmyt IS '业态';
COMMENT ON COLUMN contmain.cmkyrq IS '开业日期';
COMMENT ON COLUMN contmain.cmzsy IS '招商员';
COMMENT ON COLUMN contmain.cmzczdrts IS '滞纳金计算方式';
COMMENT ON COLUMN contmain.cmhtbh IS '合同档案号';
COMMENT ON COLUMN contmain.cmjhqd IS '进货渠道';
COMMENT ON COLUMN contmain.cmmasterno IS '主合同号';
COMMENT ON COLUMN contmain.cmseqno IS '序号(00为主合同,固定为两位)';
COMMENT ON COLUMN contmain.cmcontact IS '联系人';
COMMENT ON COLUMN contmain.cmadd IS '联系地址';
COMMENT ON COLUMN contmain.cmtel IS '联系电话';
COMMENT ON COLUMN contmain.cmfax IS '传真号';
COMMENT ON COLUMN contmain.cmqq IS 'QQ号';
COMMENT ON COLUMN contmain.cmemail IS 'EMAIL地址';
COMMENT ON COLUMN contmain.cmsuptype IS '供应商类型';
COMMENT ON COLUMN contmain.cmhhtype IS '换货方式';
COMMENT ON COLUMN contmain.cmhhterm IS '换货期限';
COMMENT ON COLUMN contmain.cmjkcond IS '结款条件';
COMMENT ON COLUMN contmain.cmchar1 IS '开户行';
COMMENT ON COLUMN contmain.cmchar2 IS '银行帐号';
COMMENT ON COLUMN contmain.cmchar4 IS '店招';
COMMENT ON COLUMN contmain.signdate IS '签约日期';
COMMENT ON COLUMN contmain.deliverydate IS '交付日期';
COMMENT ON COLUMN contmain.tackbackdate IS '收回日期';
COMMENT ON COLUMN contmain.sjcgdate IS '离场日期 ';
COMMENT ON COLUMN contmain.effectdate IS '生效日期';
COMMENT ON COLUMN contmain.zxqsrq IS '装修起始日';
COMMENT ON COLUMN contmain.zxjzrq IS '装修截止日';
COMMENT ON COLUMN contmain.yszq1 IS '预收周期 租金';
COMMENT ON COLUMN contmain.yszq2 IS '预收周期 管理费';
COMMENT ON COLUMN contmain.yszq3 IS '预收周期 推广费';
COMMENT ON COLUMN contmain.settlegroup IS '结算组';
COMMENT ON COLUMN contmain.cmttr IS '淘汰员';
COMMENT ON COLUMN contmain.cmttdate IS '淘汰日期';
COMMENT ON COLUMN contmain.cmkhfs IS '保底中销售考核方式1按销售收入2未达标差额3按考核指标';
COMMENT ON COLUMN contmain.cmznjfs IS '1按缴款日期算2按指定日期算';
CREATE INDEX IF NOT EXISTS idx_cm_supid ON contmain (cmsupid);
CREATE INDEX IF NOT EXISTS idx_comatin_cmfeffdate ON contmain (cmeffdate);

CREATE TABLE IF NOT EXISTS contbd (
    cbcontno VARCHAR(20) NOT NULL,
    cbseqno NUMERIC NOT NULL,
    cbmkt VARCHAR(20) NOT NULL,
    cbmfid VARCHAR(20) NOT NULL,
    cbeffdate TIMESTAMP NOT NULL,
    cblapdate TIMESTAMP NOT NULL,
    cbflag CHAR(1) NOT NULL,
    cbsum NUMERIC(14, 2),
    cbrate NUMERIC(5, 4),
    cbsum1 NUMERIC(14, 2),
    cbrate1 NUMERIC(5, 4),
    cbsum2 NUMERIC(14, 2),
    cbrate2 NUMERIC(5, 4),
    cbsum3 NUMERIC(14, 2),
    cbrate3 NUMERIC(5, 4),
    cbsum4 NUMERIC(14, 2),
    cbrate4 NUMERIC(5, 4),
    cbsum5 NUMERIC(14, 2),
    cbrate5 NUMERIC(5, 4),
    cbsum6 NUMERIC(14, 2),
    cbrate6 NUMERIC(5, 4),
    cbprofit NUMERIC(14, 2),
    cbisrunbd CHAR(1),
    cbisrunqs CHAR(1),
    cbisbd CHAR(1),
    cbisqs CHAR(1),
    cbsettype VARCHAR(10),
    cbrentunit VARCHAR(3),
    cbmanaunit VARCHAR(3),
    cbpopunit VARCHAR(3),
    cbrentprice NUMERIC,
    cbnamaprice NUMERIC,
    cbpopprice NUMERIC,
    cbiscalcrent CHAR(1),
    cbmode1 CHAR(1),
    cbmode2 CHAR(1),
    cbmode3 CHAR(1),
    cbmode4 CHAR(1),
    cbmode5 CHAR(1),
    cbmode6 CHAR(1),
    cbsalekh NUMERIC(14, 2),
    cbsalerate NUMERIC(5, 4),
    CONSTRAINT pk_contbd PRIMARY KEY (cbcontno, cbseqno)
);
COMMENT ON TABLE contbd IS '合同保底超额';
COMMENT ON COLUMN contbd.cbcontno IS '合同单号';
COMMENT ON COLUMN contbd.cbseqno IS '序号';
COMMENT ON COLUMN contbd.cbmkt IS '门店';
COMMENT ON COLUMN contbd.cbmfid IS '柜组';
COMMENT ON COLUMN contbd.cbeffdate IS '生效日期';
COMMENT ON COLUMN contbd.cblapdate IS '失效日期';
COMMENT ON COLUMN contbd.cbsum IS '保底额';
COMMENT ON COLUMN contbd.cbrate IS '比率';
COMMENT ON COLUMN contbd.cbsum1 IS '超额1';
COMMENT ON COLUMN contbd.cbrate1 IS '比率1';
COMMENT ON COLUMN contbd.cbsum2 IS '超额2';
COMMENT ON COLUMN contbd.cbrate2 IS '比率2';
COMMENT ON COLUMN contbd.cbsum3 IS '超额3';
COMMENT ON COLUMN contbd.cbrate3 IS '比率3';
COMMENT ON COLUMN contbd.cbsum4 IS '超额4';
COMMENT ON COLUMN contbd.cbrate4 IS '比率4';
COMMENT ON COLUMN contbd.cbsum5 IS '超额5';
COMMENT ON COLUMN contbd.cbrate5 IS '比率5';
COMMENT ON COLUMN contbd.cbsum6 IS '特卖超额';
COMMENT ON COLUMN contbd.cbrate6 IS '特卖比率';
COMMENT ON COLUMN contbd.cbprofit IS '保底毛利';
COMMENT ON COLUMN contbd.cbisrunbd IS '是否计算保底';
COMMENT ON COLUMN contbd.cbisrunqs IS '是否计算清算';
COMMENT ON COLUMN contbd.cbisbd IS '是否计算过保底';
COMMENT ON COLUMN contbd.cbisqs IS '是否计算过清算';
COMMENT ON COLUMN contbd.cbsettype IS '结算方式(购物中心)';
COMMENT ON COLUMN contbd.cbrentunit IS '租金单位';
COMMENT ON COLUMN contbd.cbmanaunit IS '管理费单位';
COMMENT ON COLUMN contbd.cbpopunit IS '推广费岗位';
COMMENT ON COLUMN contbd.cbrentprice IS '租金单价';
COMMENT ON COLUMN contbd.cbnamaprice IS '管理费单价';
COMMENT ON COLUMN contbd.cbpopprice IS '推广费单价';
COMMENT ON COLUMN contbd.cbiscalcrent IS '是否计算租金';
COMMENT ON COLUMN contbd.cbmode1 IS '超额方式1,1:全额2:差额';
COMMENT ON COLUMN contbd.cbmode2 IS '超额方式2';
COMMENT ON COLUMN contbd.cbmode3 IS '超额方式3';
COMMENT ON COLUMN contbd.cbmode4 IS '超额方式4';
COMMENT ON COLUMN contbd.cbmode5 IS '超额方式5';
COMMENT ON COLUMN contbd.cbmode6 IS '超额方式6';
COMMENT ON COLUMN contbd.cbsalekh IS '销售考核指标';

CREATE TABLE IF NOT EXISTS contmanaframe (
    cmfcontno VARCHAR(20) NOT NULL,
    cmfmfid VARCHAR(20) NOT NULL,
    cmfmarket VARCHAR(20) NOT NULL,
    cmfeffdate TIMESTAMP NOT NULL,
    cmflapdate TIMESTAMP NOT NULL,
    cmfjzmj NUMERIC(10, 2),
    cmfsymj NUMERIC(10, 2),
    cmfavgsyf NUMERIC(14, 4),
    cmftotsyf NUMERIC(12, 2),
    cmfcharter NUMERIC(14, 4),
    cmfmemo VARCHAR(100),
    cmfbrand VARCHAR(6) DEFAULT '0' NOT NULL,
    cmfzkfd1 NUMERIC(5, 4) DEFAULT 0 NOT NULL,
    cmfzkfd2 NUMERIC(5, 4) DEFAULT 0 NOT NULL,
    cmfaddr VARCHAR(20),
    cmfarea CHAR(1),
    cmfnum1 NUMERIC,
    cmfnum2 NUMERIC,
    cmfnum3 NUMERIC,
    cmfnum4 NUMERIC,
    cmfnum5 NUMERIC,
    cmfnum6 NUMERIC,
    cmfnum7 NUMERIC,
    cmfnum8 NUMERIC,
    cmfzkfd3 NUMERIC(5, 4),
    cmfzkfd4 NUMERIC(5, 4),
    cmfzkfd5 NUMERIC(5, 4),
    cmfdiscont6 NUMERIC,
    cmfdiscont7 NUMERIC,
    cmfdiscont8 NUMERIC,
    cmfdiscont9 NUMERIC,
    cmfdiscont10 NUMERIC,
    cmfismaster CHAR(1) DEFAULT '1',
    cmflastoper VARCHAR(20),
    cmflastdate TIMESTAMP,
    cmfregmen VARCHAR(20),
    cmfregdate TIMESTAMP,
    cmfzjmj NUMERIC(10, 2),
    CONSTRAINT pk_contmanaframe PRIMARY KEY (cmfcontno, cmfmfid, cmfbrand)
);
COMMENT ON TABLE contmanaframe IS '[CMF]合同经营地点';
COMMENT ON COLUMN contmanaframe.cmfcontno IS '合同编号';
COMMENT ON COLUMN contmanaframe.cmfmfid IS '柜组';
COMMENT ON COLUMN contmanaframe.cmfmarket IS '门店';
COMMENT ON COLUMN contmanaframe.cmfeffdate IS '生效日期';
COMMENT ON COLUMN contmanaframe.cmflapdate IS '失效日期';
COMMENT ON COLUMN contmanaframe.cmfjzmj IS '契约面积';
COMMENT ON COLUMN contmanaframe.cmfsymj IS '实际面积';
COMMENT ON COLUMN contmanaframe.cmfmemo IS '备注';
COMMENT ON COLUMN contmanaframe.cmfbrand IS '品牌';
COMMENT ON COLUMN contmanaframe.cmfzkfd1 IS 'VIP折扣分担1';
COMMENT ON COLUMN contmanaframe.cmfzkfd2 IS 'VIP折扣分担2';
COMMENT ON COLUMN contmanaframe.cmfaddr IS '_座_层_号';
COMMENT ON COLUMN contmanaframe.cmfarea IS '区（A/B/C）';
COMMENT ON COLUMN contmanaframe.cmfnum1 IS '促销人员总数';
COMMENT ON COLUMN contmanaframe.cmfnum2 IS '甲方人数';
COMMENT ON COLUMN contmanaframe.cmfnum3 IS '乙方人数';
COMMENT ON COLUMN contmanaframe.cmfnum4 IS '甲方促销人员工资（每人）';
COMMENT ON COLUMN contmanaframe.cmfnum5 IS '乙方促销人员培训费（每人）';
COMMENT ON COLUMN contmanaframe.cmfnum6 IS '契约平效';
COMMENT ON COLUMN contmanaframe.cmfnum7 IS '实际平效';
COMMENT ON COLUMN contmanaframe.cmfnum8 IS '月目标获利额';
COMMENT ON COLUMN contmanaframe.cmfzkfd3 IS 'VIP折扣分担3';
COMMENT ON COLUMN contmanaframe.cmfzkfd4 IS 'VIP折扣分担4';
COMMENT ON COLUMN contmanaframe.cmfzkfd5 IS 'VIP折扣分担5';
COMMENT ON COLUMN contmanaframe.cmfdiscont6 IS '扣率6';
COMMENT ON COLUMN contmanaframe.cmfdiscont7 IS '扣率7';
COMMENT ON COLUMN contmanaframe.cmfdiscont8 IS '扣率8';
COMMENT ON COLUMN contmanaframe.cmfdiscont9 IS '扣率9';
COMMENT ON COLUMN contmanaframe.cmfdiscont10 IS '扣率10';
COMMENT ON COLUMN contmanaframe.cmfismaster IS '是否主商位 1主商位 0次商位(购物中心)';
COMMENT ON COLUMN contmanaframe.cmflastoper IS '最后修改人';
COMMENT ON COLUMN contmanaframe.cmflastdate IS '最后修改日期';
COMMENT ON COLUMN contmanaframe.cmfregmen IS '登记人';
COMMENT ON COLUMN contmanaframe.cmfregdate IS '登记日期';
COMMENT ON COLUMN contmanaframe.cmfzjmj IS '租金面积';
CREATE INDEX IF NOT EXISTS idx_cmfeffdate ON contmanaframe (cmfeffdate);

CREATE TABLE IF NOT EXISTS contcyclist (
    cclcontno VARCHAR(20) NOT NULL,
    cclseqno NUMERIC NOT NULL,
    cclmkt VARCHAR(20),
    cclmfid VARCHAR(20),
    ccleffdate TIMESTAMP,
    ccllapdate TIMESTAMP,
    cclitemid VARCHAR(20),
    cclitemunit CHAR(1),
    cclitemprice NUMERIC,
    cclsumamount NUMERIC,
    cclystype NUMERIC,
    cclysnum NUMERIC,
    cclisfree CHAR(1),
    cclflag CHAR(1) DEFAULT 'Y',
    cclpchflag CHAR(1) DEFAULT 'N',
    CONSTRAINT pk_contcyclist PRIMARY KEY (cclcontno, cclseqno)
);
COMMENT ON COLUMN contcyclist.cclcontno IS '合同号';
COMMENT ON COLUMN contcyclist.cclseqno IS '序号';
COMMENT ON COLUMN contcyclist.cclmkt IS '门店';
COMMENT ON COLUMN contcyclist.cclmfid IS '柜组';
COMMENT ON COLUMN contcyclist.ccleffdate IS '开始日期';
COMMENT ON COLUMN contcyclist.ccllapdate IS '结束日期';
COMMENT ON COLUMN contcyclist.cclitemid IS '项目编号';
COMMENT ON COLUMN contcyclist.cclitemunit IS '项目单位';
COMMENT ON COLUMN contcyclist.cclitemprice IS '价格';
COMMENT ON COLUMN contcyclist.cclsumamount IS '总金额';
COMMENT ON COLUMN contcyclist.cclystype IS '预收类型';
COMMENT ON COLUMN contcyclist.cclysnum IS '一次收取月数';
COMMENT ON COLUMN contcyclist.cclisfree IS '是否免除';
COMMENT ON COLUMN contcyclist.cclflag IS '费用状态';
COMMENT ON COLUMN contcyclist.cclpchflag IS '是否参与提成比高';

CREATE TABLE IF NOT EXISTS contsupcharge (
    csccontno VARCHAR(20) NOT NULL,
    cscrowno NUMERIC NOT NULL,
    cscispub CHAR(1) DEFAULT 'Y' NOT NULL,
    cscmfid VARCHAR(20),
    cscmarket VARCHAR(20),
    cscchargecode CHAR(2) NOT NULL,
    cscchargename VARCHAR(32),
    csceffdate TIMESTAMP NOT NULL,
    csclapdate TIMESTAMP NOT NULL,
    cscsetmon CHAR(6) NOT NULL,
    cscismcjs CHAR(1) DEFAULT '0' NOT NULL,
    cscvalue NUMERIC(14, 4) NOT NULL,
    csctotal NUMERIC(14, 4),
    cscisdeduct CHAR(1) DEFAULT 'Y' NOT NULL,
    cscflag CHAR(1) DEFAULT 'N' NOT NULL,
    cscjsbillno VARCHAR(20),
    cscmemo VARCHAR(60),
    cscoldrowno NUMERIC,
    cscnum1 NUMERIC,
    cscnum2 NUMERIC,
    cscnum3 NUMERIC,
    cscnum4 NUMERIC,
    cscnum5 NUMERIC,
    cscisret CHAR(1) DEFAULT 'N',
    cscretdate TIMESTAMP,
    cscbottomvalues NUMERIC(14, 4) DEFAULT 0,
    cscpeakvalues NUMERIC(14, 4) DEFAULT 0,
    CONSTRAINT pk_contsupcharge PRIMARY KEY (csccontno, cscrowno)
);
COMMENT ON TABLE contsupcharge IS '[CSC]合同供应商结算费用';
COMMENT ON COLUMN contsupcharge.csccontno IS '合同编号';
COMMENT ON COLUMN contsupcharge.cscrowno IS '行号';
COMMENT ON COLUMN contsupcharge.cscispub IS '范围';
COMMENT ON COLUMN contsupcharge.cscmfid IS '部门';
COMMENT ON COLUMN contsupcharge.cscmarket IS '地点';
COMMENT ON COLUMN contsupcharge.cscchargecode IS '费用编码';
COMMENT ON COLUMN contsupcharge.cscchargename IS '费用名称';
COMMENT ON COLUMN contsupcharge.csceffdate IS '生效日期';
COMMENT ON COLUMN contsupcharge.csclapdate IS '失效日期';
COMMENT ON COLUMN contsupcharge.cscsetmon IS '结算月';
COMMENT ON COLUMN contsupcharge.cscismcjs IS '结算方式';
COMMENT ON COLUMN contsupcharge.cscvalue IS '指标';
COMMENT ON COLUMN contsupcharge.csctotal IS '总金额';
COMMENT ON COLUMN contsupcharge.cscisdeduct IS '是否帐扣';
COMMENT ON COLUMN contsupcharge.cscflag IS '标志';
COMMENT ON COLUMN contsupcharge.cscjsbillno IS '结算单号';
COMMENT ON COLUMN contsupcharge.cscmemo IS '备注';
COMMENT ON COLUMN contsupcharge.cscoldrowno IS '原行号';
COMMENT ON COLUMN contsupcharge.cscnum1 IS '单位数量';
COMMENT ON COLUMN contsupcharge.cscnum2 IS '单位金额';
COMMENT ON COLUMN contsupcharge.cscnum3 IS '每月扣除日';
COMMENT ON COLUMN contsupcharge.cscisret IS '是否返还型费用';
COMMENT ON COLUMN contsupcharge.cscretdate IS '返还日期';
COMMENT ON COLUMN contsupcharge.cscbottomvalues IS '保底值';
COMMENT ON COLUMN contsupcharge.cscpeakvalues IS '封顶值';
CREATE INDEX IF NOT EXISTS idx_csc_date ON contsupcharge (csceffdate, csclapdate);
"""


def upgrade() -> None:
    op.get_bind().exec_driver_sql(ERP_CONTRACT_TABLES_SQL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS contsupcharge")
    op.execute("DROP TABLE IF EXISTS contcyclist")
    op.execute("DROP TABLE IF EXISTS contmanaframe")
    op.execute("DROP TABLE IF EXISTS contbd")
    op.execute("DROP TABLE IF EXISTS contmain")
