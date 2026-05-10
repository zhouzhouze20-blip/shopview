"""create supplierbase table

Revision ID: c8f4b7a1d2e3
Revises: 4f6b2a1c9d08
Create Date: 2026-04-21 15:50:00

"""
from typing import Sequence, Union

from alembic import op


revision: str = "c8f4b7a1d2e3"
down_revision: Union[str, Sequence[str], None] = "4f6b2a1c9d08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SUPPLIERBASE_SQL = r"""
CREATE TABLE IF NOT EXISTS supplierbase (
    sbid VARCHAR(20) NOT NULL,
    sbpwd VARCHAR(10),
    sbcname VARCHAR(60) NOT NULL,
    sbename VARCHAR(60),
    sbsname VARCHAR(40),
    sbskey VARCHAR(20),
    sbstatus CHAR(1) NOT NULL,
    sbflag CHAR(1) NOT NULL,
    sbsubject VARCHAR(20),
    sbanalcode VARCHAR(20),
    sbregcode VARCHAR(10) NOT NULL,
    sbcatcode VARCHAR(6) NOT NULL,
    sbqydm VARCHAR(40),
    sbekindcode CHAR(1),
    sbtradecode CHAR(3),
    sbetypecode CHAR(1),
    sbyyzzno VARCHAR(40),
    sbzcrq TIMESTAMP,
    sbzcsb VARCHAR(600),
    sbzczb NUMERIC,
    sbjyfw VARCHAR(60),
    sbjygm NUMERIC,
    sbtaxpayer CHAR(1) NOT NULL,
    sbtaxrate NUMERIC(8, 4),
    sbtaxno VARCHAR(40),
    sbbank VARCHAR(60),
    sbaccntno VARCHAR(40),
    sbaddr VARCHAR(600),
    sbtel VARCHAR(200),
    sbfax VARCHAR(20),
    sbzip CHAR(60),
    sbcable VARCHAR(10),
    sbemail VARCHAR(40),
    sburl VARCHAR(40),
    sbfrdb VARCHAR(20),
    sbfrdbsfz VARCHAR(20),
    sbfrdblxfs VARCHAR(40),
    sblxr VARCHAR(20),
    sblxrzw VARCHAR(20),
    sblxrsfz VARCHAR(20),
    sblxfs VARCHAR(40),
    sbyjrq TIMESTAMP,
    sbwmid1 CHAR(1) NOT NULL,
    sbwmid2 CHAR(1) NOT NULL,
    sbwmid3 CHAR(1) NOT NULL,
    sbwmid4 CHAR(1) NOT NULL,
    sbwmid5 CHAR(1) NOT NULL,
    sbjszq NUMERIC(4, 1) NOT NULL,
    sbljsrq TIMESTAMP NOT NULL,
    sbdhzq NUMERIC(8) NOT NULL,
    sbdbsend CHAR(1) NOT NULL,
    sbyjcgy VARCHAR(20),
    sbcgyyj VARCHAR(80),
    sbzgjl VARCHAR(20),
    sbzgljyj VARCHAR(80),
    sbshr VARCHAR(20),
    sbshrq TIMESTAMP,
    sblry VARCHAR(20) NOT NULL,
    sblrrq TIMESTAMP NOT NULL,
    sbxgr VARCHAR(20),
    sbxgrq TIMESTAMP,
    sbjhsxq NUMERIC(8),
    sbsxksrq TIMESTAMP,
    sbsxjsrq TIMESTAMP,
    sbfjhrq TIMESTAMP,
    sbljhrq TIMESTAMP,
    sbzzrq TIMESTAMP,
    sbgqrq TIMESTAMP,
    sbtsrq TIMESTAMP,
    sbttrq TIMESTAMP,
    sbmemo VARCHAR(100),
    sbvc1 VARCHAR(20),
    sbvc2 VARCHAR(20),
    sbvc3 VARCHAR(20),
    sbvc4 VARCHAR(20),
    sbvc5 VARCHAR(20),
    sbvc6 VARCHAR(20),
    sbvc7 VARCHAR(20),
    sbvc8 VARCHAR(20),
    sbvc9 VARCHAR(40),
    sbvc10 VARCHAR(40),
    sbvc11 VARCHAR(40),
    sbvc12 VARCHAR(40),
    sbvc13 VARCHAR(60),
    sbvc14 VARCHAR(60),
    sbvc15 VARCHAR(60) DEFAULT 'S',
    sbvc16 VARCHAR(60),
    sbn1 NUMERIC,
    sbn2 NUMERIC,
    sbn3 NUMERIC,
    sbn4 NUMERIC,
    sbn5 NUMERIC,
    sbn6 NUMERIC,
    sbn7 NUMERIC,
    sbn8 NUMERIC,
    sbn9 NUMERIC,
    sbn10 NUMERIC,
    sbn11 NUMERIC,
    sbn12 NUMERIC,
    sbn13 NUMERIC,
    sbn14 NUMERIC,
    sbn15 NUMERIC,
    sbn16 NUMERIC,
    wmid5 CHAR(1),
    isgathering CHAR(20),
    gatfundcorp CHAR(60),
    gatfundbank CHAR(60),
    gataccntno CHAR(60),
    zzaddr CHAR(60),
    linkfax CHAR(20),
    linkemail CHAR(20),
    cwlinkman CHAR(20),
    cwlinkduty CHAR(60),
    cwlinktel CHAR(20),
    cwlinkfax CHAR(20),
    cwlinkemail CHAR(60),
    applydept CHAR(60),
    producerid CHAR(20),
    sbyjcgy2 VARCHAR(20),
    grade VARCHAR(20),
    sbnbtype CHAR(1),
    sbiftt CHAR(1),
    sbcomname VARCHAR(60),
    sbcomename VARCHAR(60),
    sbyt VARCHAR(10),
    sbxfdx VARCHAR(10),
    sbyxmf VARCHAR(30),
    sbyxrent NUMERIC,
    sbyxmon NUMERIC,
    sbyxmj NUMERIC,
    sbopendesc VARCHAR(200),
    sbppdesc VARCHAR(200),
    sbjfyq VARCHAR(200),
    CONSTRAINT pk_supplierbase PRIMARY KEY (sbid)
);

COMMENT ON TABLE supplierbase IS '[SB]供应商基本资料';
COMMENT ON COLUMN supplierbase.sbid IS '代码';
COMMENT ON COLUMN supplierbase.sbpwd IS '密码';
COMMENT ON COLUMN supplierbase.sbcname IS '名称';
COMMENT ON COLUMN supplierbase.sbename IS '英文名称';
COMMENT ON COLUMN supplierbase.sbsname IS '简称';
COMMENT ON COLUMN supplierbase.sbskey IS '间码';
COMMENT ON COLUMN supplierbase.sbstatus IS '状态';
COMMENT ON COLUMN supplierbase.sbflag IS '可用标志';
COMMENT ON COLUMN supplierbase.sbsubject IS '核算代码';
COMMENT ON COLUMN supplierbase.sbanalcode IS '分析编码';
COMMENT ON COLUMN supplierbase.sbregcode IS '地区';
COMMENT ON COLUMN supplierbase.sbcatcode IS '供应商分类Sbnbtype';
COMMENT ON COLUMN supplierbase.sbqydm IS '企业代码';
COMMENT ON COLUMN supplierbase.sbekindcode IS '企业性质';
COMMENT ON COLUMN supplierbase.sbtradecode IS '所属行业';
COMMENT ON COLUMN supplierbase.sbetypecode IS '企业类别';
COMMENT ON COLUMN supplierbase.sbyyzzno IS '营业执照代码';
COMMENT ON COLUMN supplierbase.sbzcrq IS '注册日期';
COMMENT ON COLUMN supplierbase.sbzcsb IS '注册商标';
COMMENT ON COLUMN supplierbase.sbzczb IS '注册资本';
COMMENT ON COLUMN supplierbase.sbjyfw IS '经营范围(品种)';
COMMENT ON COLUMN supplierbase.sbjygm IS '经营规模(营业额)';
COMMENT ON COLUMN supplierbase.sbtaxpayer IS '纳税人类型';
COMMENT ON COLUMN supplierbase.sbtaxrate IS '适用税率';
COMMENT ON COLUMN supplierbase.sbtaxno IS '纳税号';
COMMENT ON COLUMN supplierbase.sbbank IS '开户银行';
COMMENT ON COLUMN supplierbase.sbaccntno IS '银行帐号';
COMMENT ON COLUMN supplierbase.sbaddr IS '注册地址';
COMMENT ON COLUMN supplierbase.sbtel IS '公司电话';
COMMENT ON COLUMN supplierbase.sbfax IS '公司传真';
COMMENT ON COLUMN supplierbase.sbzip IS '邮政编码';
COMMENT ON COLUMN supplierbase.sbcable IS '电报';
COMMENT ON COLUMN supplierbase.sbemail IS 'EMAIL地址';
COMMENT ON COLUMN supplierbase.sburl IS '主页';
COMMENT ON COLUMN supplierbase.sbfrdb IS '法人代表';
COMMENT ON COLUMN supplierbase.sbfrdbsfz IS '法人代表身份证';
COMMENT ON COLUMN supplierbase.sbfrdblxfs IS '法人联系方式';
COMMENT ON COLUMN supplierbase.sblxr IS '联系人';
COMMENT ON COLUMN supplierbase.sblxrzw IS '联系人职务';
COMMENT ON COLUMN supplierbase.sblxrsfz IS '联系人身份证';
COMMENT ON COLUMN supplierbase.sblxfs IS '联系方式';
COMMENT ON COLUMN supplierbase.sbyjrq IS '引进日期';
COMMENT ON COLUMN supplierbase.sbwmid1 IS '经销';
COMMENT ON COLUMN supplierbase.sbwmid2 IS '成本代销';
COMMENT ON COLUMN supplierbase.sbwmid3 IS '扣率代销';
COMMENT ON COLUMN supplierbase.sbwmid4 IS '联营';
COMMENT ON COLUMN supplierbase.sbwmid5 IS '租赁';
COMMENT ON COLUMN supplierbase.sbjszq IS '结算周期';
COMMENT ON COLUMN supplierbase.sbljsrq IS '最后结算日期';
COMMENT ON COLUMN supplierbase.sbdhzq IS '到货周期';
COMMENT ON COLUMN supplierbase.sbdbsend IS '订单传递方式';
COMMENT ON COLUMN supplierbase.sbyjcgy IS '引进买手';
COMMENT ON COLUMN supplierbase.sbcgyyj IS '买手意见';
COMMENT ON COLUMN supplierbase.sbzgjl IS '主管人员';
COMMENT ON COLUMN supplierbase.sbzgljyj IS '主管人员意见';
COMMENT ON COLUMN supplierbase.sbshr IS '复核人';
COMMENT ON COLUMN supplierbase.sbshrq IS '复核日期';
COMMENT ON COLUMN supplierbase.sblry IS '录入员';
COMMENT ON COLUMN supplierbase.sblrrq IS '录入日期';
COMMENT ON COLUMN supplierbase.sbxgr IS '最后修改人员';
COMMENT ON COLUMN supplierbase.sbxgrq IS '最后修改日期';
COMMENT ON COLUMN supplierbase.sbjhsxq IS '计划试销期';
COMMENT ON COLUMN supplierbase.sbsxksrq IS '试销开始日期';
COMMENT ON COLUMN supplierbase.sbsxjsrq IS '试销结束日期';
COMMENT ON COLUMN supplierbase.sbfjhrq IS '第一次进货时间';
COMMENT ON COLUMN supplierbase.sbljhrq IS '最近进货时间';
COMMENT ON COLUMN supplierbase.sbzzrq IS '转正日期';
COMMENT ON COLUMN supplierbase.sbgqrq IS '挂起时间';
COMMENT ON COLUMN supplierbase.sbtsrq IS '停售时间';
COMMENT ON COLUMN supplierbase.sbttrq IS '淘汰时间';
COMMENT ON COLUMN supplierbase.sbmemo IS '备注';
COMMENT ON COLUMN supplierbase.sbvc1 IS 'SBVC1';
COMMENT ON COLUMN supplierbase.sbvc2 IS 'SBVC2';
COMMENT ON COLUMN supplierbase.sbvc3 IS 'SBVC3';
COMMENT ON COLUMN supplierbase.sbvc4 IS 'SBVC4';
COMMENT ON COLUMN supplierbase.sbvc5 IS 'SBVC5';
COMMENT ON COLUMN supplierbase.sbvc6 IS 'SBVC6';
COMMENT ON COLUMN supplierbase.sbvc7 IS 'SBVC7';
COMMENT ON COLUMN supplierbase.sbvc8 IS '结算日';
COMMENT ON COLUMN supplierbase.sbvc9 IS 'SBVC9';
COMMENT ON COLUMN supplierbase.sbvc10 IS 'SBVC10';
COMMENT ON COLUMN supplierbase.sbvc11 IS 'SBVC11';
COMMENT ON COLUMN supplierbase.sbvc12 IS 'SBVC12';
COMMENT ON COLUMN supplierbase.sbvc13 IS 'SBVC13';
COMMENT ON COLUMN supplierbase.sbvc14 IS '使用门店';
COMMENT ON COLUMN supplierbase.sbvc15 IS 'M商户/供应商S';
COMMENT ON COLUMN supplierbase.sbvc16 IS 'SBVC16 / 综合评分';
COMMENT ON COLUMN supplierbase.sbn1 IS 'SBN1';
COMMENT ON COLUMN supplierbase.sbn2 IS 'SBN2';
COMMENT ON COLUMN supplierbase.sbn3 IS 'SBN3';
COMMENT ON COLUMN supplierbase.sbn4 IS 'SBN4';
COMMENT ON COLUMN supplierbase.sbn5 IS 'SBN5';
COMMENT ON COLUMN supplierbase.sbn6 IS 'SBN6';
COMMENT ON COLUMN supplierbase.sbn7 IS 'SBN7';
COMMENT ON COLUMN supplierbase.sbn8 IS 'SBN8';
COMMENT ON COLUMN supplierbase.sbn9 IS 'SBN9';
COMMENT ON COLUMN supplierbase.sbn10 IS '付款日期';
COMMENT ON COLUMN supplierbase.sbn11 IS 'SBN11';
COMMENT ON COLUMN supplierbase.sbn12 IS 'SBN12';
COMMENT ON COLUMN supplierbase.sbn13 IS 'SBN13';
COMMENT ON COLUMN supplierbase.sbn14 IS 'SBN14';
COMMENT ON COLUMN supplierbase.sbn15 IS 'SBN15';
COMMENT ON COLUMN supplierbase.sbn16 IS 'SBN16';
COMMENT ON COLUMN supplierbase.wmid5 IS '是否代销';
COMMENT ON COLUMN supplierbase.isgathering IS '是否指定收款';
COMMENT ON COLUMN supplierbase.gatfundcorp IS '收款单位';
COMMENT ON COLUMN supplierbase.gatfundbank IS '收款银行';
COMMENT ON COLUMN supplierbase.gataccntno IS '收款账号';
COMMENT ON COLUMN supplierbase.zzaddr IS '转账地址';
COMMENT ON COLUMN supplierbase.linkfax IS '业务联系传真';
COMMENT ON COLUMN supplierbase.linkemail IS '业务联系EMAIL';
COMMENT ON COLUMN supplierbase.cwlinkman IS '财务联系人';
COMMENT ON COLUMN supplierbase.cwlinkduty IS '财务联系人职务';
COMMENT ON COLUMN supplierbase.cwlinktel IS '财务联系人电话';
COMMENT ON COLUMN supplierbase.cwlinkfax IS '财务联系人传真';
COMMENT ON COLUMN supplierbase.cwlinkemail IS '财务联系人EMAIL';
COMMENT ON COLUMN supplierbase.applydept IS '引进部门';
COMMENT ON COLUMN supplierbase.producerid IS '主要厂商';
COMMENT ON COLUMN supplierbase.sbyjcgy2 IS '引进买手2  交接备份';
COMMENT ON COLUMN supplierbase.grade IS '等级';
COMMENT ON COLUMN supplierbase.sbnbtype IS '供应商内部分类';
COMMENT ON COLUMN supplierbase.sbiftt IS '是否参与淘汰预警报表排名（Y=参加，N=不参加）';
COMMENT ON COLUMN supplierbase.sbcomname IS '公司名称';
COMMENT ON COLUMN supplierbase.sbcomename IS '公司英文名称';
COMMENT ON COLUMN supplierbase.sbyt IS '业态';
COMMENT ON COLUMN supplierbase.sbxfdx IS '消费对象';
COMMENT ON COLUMN supplierbase.sbyxmf IS '意向商位';
COMMENT ON COLUMN supplierbase.sbyxrent IS '意向租金';
COMMENT ON COLUMN supplierbase.sbyxmon IS '意向租期';
COMMENT ON COLUMN supplierbase.sbyxmj IS '意向面积';
COMMENT ON COLUMN supplierbase.sbopendesc IS '开店描述';
COMMENT ON COLUMN supplierbase.sbppdesc IS '品牌描述';
COMMENT ON COLUMN supplierbase.sbjfyq IS '交房要求';

CREATE INDEX IF NOT EXISTS idx_supplierbase_vc15 ON supplierbase (sbvc15);
CREATE INDEX IF NOT EXISTS idx_supplierbase_cat ON supplierbase (sbcatcode);
CREATE INDEX IF NOT EXISTS idx_supplierbase_cname ON supplierbase (sbcname);
CREATE INDEX IF NOT EXISTS idx_supplierbase_region ON supplierbase (sbregcode);
CREATE INDEX IF NOT EXISTS idx_supplierbase_skey ON supplierbase (sbskey);
"""


def upgrade() -> None:
    op.get_bind().exec_driver_sql(SUPPLIERBASE_SQL)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_supplierbase_skey")
    op.execute("DROP INDEX IF EXISTS idx_supplierbase_region")
    op.execute("DROP INDEX IF EXISTS idx_supplierbase_cname")
    op.execute("DROP INDEX IF EXISTS idx_supplierbase_cat")
    op.execute("DROP INDEX IF EXISTS idx_supplierbase_vc15")
    op.execute("DROP TABLE IF EXISTS supplierbase")
