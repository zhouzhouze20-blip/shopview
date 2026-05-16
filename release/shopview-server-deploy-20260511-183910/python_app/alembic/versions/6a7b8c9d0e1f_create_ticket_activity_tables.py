"""create ticket card log and promotion period tables

Revision ID: 6a7b8c9d0e1f
Revises: 5f6a7b8c9d0e
Create Date: 2026-05-11
"""
from typing import Sequence, Union

from alembic import op


revision: str = "6a7b8c9d0e1f"
down_revision: Union[str, Sequence[str], None] = "5f6a7b8c9d0e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TICKET_ACTIVITY_TABLES_SQL = r"""
CREATE TABLE IF NOT EXISTS tktcardfqlog (
    tcflseqno NUMERIC NOT NULL,
    tcflvipno VARCHAR(20) NOT NULL,
    tcflstartdate DATE NOT NULL,
    tcflenddate DATE NOT NULL,
    tcfldate DATE NOT NULL,
    tcflzy CHAR(1) NOT NULL,
    tcflpopid VARCHAR(20),
    tcflpoprule VARCHAR(20),
    tcflmoney NUMERIC(12, 2),
    tcflye NUMERIC(12, 2),
    tcfloper VARCHAR(20),
    tcflsyjid VARCHAR(20),
    tcflinvno VARCHAR(20),
    tcflmemo VARCHAR(100),
    tcflsyjtrace NUMERIC,
    tcfljetype CHAR(1),
    tcflvipseq NUMERIC NOT NULL,
    tcflmkt VARCHAR(20),
    tcfljygs VARCHAR(20),
    tcflsource CHAR(1) DEFAULT '1',
    tcfltransno NUMERIC,
    tcfltype CHAR(1),
    tcflqchg CHAR(1) DEFAULT 'N',
    tcflchr1 VARCHAR(20),
    tcflchr2 VARCHAR(20),
    tcflchr3 VARCHAR(20),
    tcflnum1 NUMERIC,
    tcflnum2 NUMERIC,
    tcflnum3 NUMERIC,
    tcflywdh VARCHAR(20),
    tcflismzq CHAR(1),
    tcflqmz NUMERIC,
    tcflqno VARCHAR(20),
    CONSTRAINT pk_tktcardfqlog PRIMARY KEY (tcflseqno)
);

COMMENT ON TABLE tktcardfqlog IS '[TCFL]VIP卡返券日志';
COMMENT ON COLUMN tktcardfqlog.tcflseqno IS '序号';
COMMENT ON COLUMN tktcardfqlog.tcflvipno IS 'VIP卡号';
COMMENT ON COLUMN tktcardfqlog.tcflstartdate IS '返券有效期';
COMMENT ON COLUMN tktcardfqlog.tcflenddate IS '返券有效期';
COMMENT ON COLUMN tktcardfqlog.tcfldate IS '发生日期';
COMMENT ON COLUMN tktcardfqlog.tcflzy IS '摘要';
COMMENT ON COLUMN tktcardfqlog.tcflpopid IS '返券促销活动编码';
COMMENT ON COLUMN tktcardfqlog.tcflpoprule IS '返券规则';
COMMENT ON COLUMN tktcardfqlog.tcflmoney IS '发生金额';
COMMENT ON COLUMN tktcardfqlog.tcflye IS '余额';
COMMENT ON COLUMN tktcardfqlog.tcfloper IS '操作员';
COMMENT ON COLUMN tktcardfqlog.tcflsyjid IS '收银机号';
COMMENT ON COLUMN tktcardfqlog.tcflinvno IS '小票号';
COMMENT ON COLUMN tktcardfqlog.tcflmemo IS '备注(冲正日期)';
COMMENT ON COLUMN tktcardfqlog.tcflsyjtrace IS '收银机消费序号';
COMMENT ON COLUMN tktcardfqlog.tcfljetype IS '券种A～Z';
COMMENT ON COLUMN tktcardfqlog.tcflvipseq IS 'VIP序号(tktcardfqtotal.TCFTSEQNO)';
COMMENT ON COLUMN tktcardfqlog.tcflmkt IS '发生门店号';
COMMENT ON COLUMN tktcardfqlog.tcfljygs IS '经营公司';
COMMENT ON COLUMN tktcardfqlog.tcflsource IS '券来源1:销售返券 2:前台买券,8:后天买券, 3:银行追送 4:退货返券5券转入7后台手工新增';
COMMENT ON COLUMN tktcardfqlog.tcfltransno IS '事务号';
COMMENT ON COLUMN tktcardfqlog.tcfltype IS '1:vip电子券,2:手工券';
COMMENT ON COLUMN tktcardfqlog.tcflqchg IS '手工券号是否已指定';
COMMENT ON COLUMN tktcardfqlog.tcflchr1 IS '银行代码（追送）';
COMMENT ON COLUMN tktcardfqlog.tcflchr2 IS '追送付款卡号';
COMMENT ON COLUMN tktcardfqlog.tcflchr3 IS '打券位置 0 前台,1后台 ,2 不用打券';
COMMENT ON COLUMN tktcardfqlog.tcflnum1 IS '打券次数';
COMMENT ON COLUMN tktcardfqlog.tcflywdh IS '业务单号';
COMMENT ON COLUMN tktcardfqlog.tcflismzq IS '是否面值券';
COMMENT ON COLUMN tktcardfqlog.tcflqmz IS '券面值';
COMMENT ON COLUMN tktcardfqlog.tcflqno IS '券号';

CREATE INDEX IF NOT EXISTS idx_tcflsyjinv ON tktcardfqlog (tcflsyjid, tcflinvno, tcflmkt);
CREATE INDEX IF NOT EXISTS idx_tktcardfqlog_date ON tktcardfqlog (tcfldate);
CREATE INDEX IF NOT EXISTS idx_tktcardfqlog_syj ON tktcardfqlog (tcflmkt, tcflsyjid, tcflsyjtrace, tcflmemo);
CREATE INDEX IF NOT EXISTS idx_tktcardfqlog_tcflenddate ON tktcardfqlog (tcflenddate);
CREATE INDEX IF NOT EXISTS idx_tktcardfqlog_tcflsource ON tktcardfqlog (tcflsource);
CREATE INDEX IF NOT EXISTS idx_tktcardfqlog_trace ON tktcardfqlog (tcflsyjtrace);
CREATE INDEX IF NOT EXISTS idx_tktcardfqlog_trans ON tktcardfqlog (tcfltransno, tcfltype);
CREATE INDEX IF NOT EXISTS idx_tktcardfqlog_vipno ON tktcardfqlog (tcflvipno, tcflzy);
CREATE INDEX IF NOT EXISTS idx_tktcardfqlog_vipseq ON tktcardfqlog (tcflvipseq);

CREATE TABLE IF NOT EXISTS tktpopinfo (
    tpiid VARCHAR(10) NOT NULL,
    tpiname VARCHAR(60) NOT NULL,
    tpistartdate DATE NOT NULL,
    tpienddate DATE NOT NULL,
    tpiyqstartdate DATE,
    tpiyqenddate DATE,
    tpbingonum NUMERIC DEFAULT 0,
    tpmemo VARCHAR(200),
    tpisoneday CHAR(1),
    tptime VARCHAR(10),
    tpendtime VARCHAR(10),
    tphyfqmode CHAR(1),
    tpfhyfqmode CHAR(1),
    tpmzmode CHAR(1),
    tpmanaunit VARCHAR(20),
    tpprintplace CHAR(1),
    tprulepj CHAR(1),
    tpiszk CHAR(1),
    tpcertarea VARCHAR(20),
    tpstr1 VARCHAR(10),
    tpstr2 VARCHAR(60),
    tpstr3 VARCHAR(60),
    tpnum1 NUMERIC,
    tpnum2 NUMERIC,
    tpzkfd NUMERIC,
    tpjfbs NUMERIC,
    tpmaxzkl NUMERIC,
    tpispopprn CHAR(1),
    tpprnrate NUMERIC,
    tpstr4 VARCHAR(20),
    tpstr5 VARCHAR(20),
    tpflag CHAR(1) DEFAULT 'N',
    CONSTRAINT pk_tktpopinfo PRIMARY KEY (tpiid)
);

COMMENT ON TABLE tktpopinfo IS '[TPI]促销活动档期表';
COMMENT ON COLUMN tktpopinfo.tpiid IS '活动档期编码';
COMMENT ON COLUMN tktpopinfo.tpiname IS '活动主题';
COMMENT ON COLUMN tktpopinfo.tpistartdate IS '活动开始日期';
COMMENT ON COLUMN tktpopinfo.tpienddate IS '活动结束日期';
COMMENT ON COLUMN tktpopinfo.tpiyqstartdate IS '活动所返券的开始使用日期(取消)';
COMMENT ON COLUMN tktpopinfo.tpiyqenddate IS '活动所返券的结束使用日期(取消)';
COMMENT ON COLUMN tktpopinfo.tpmemo IS '备注';
COMMENT ON COLUMN tktpopinfo.tpisoneday IS '券只能用一天';
COMMENT ON COLUMN tktpopinfo.tptime IS '延时时间点';
COMMENT ON COLUMN tktpopinfo.tpendtime IS '第二天截止使用时间';
COMMENT ON COLUMN tktpopinfo.tphyfqmode IS '会员返券方式 0电子券,1指定手工券号,2生成手工券号';
COMMENT ON COLUMN tktpopinfo.tpfhyfqmode IS '非会员返券方式 1指定手工券号,2生成手工券号';
COMMENT ON COLUMN tktpopinfo.tpmzmode IS '面值方式:0 规则合并(一个80),1固定面值(两个40)';
COMMENT ON COLUMN tktpopinfo.tpmanaunit IS '经营公司';
COMMENT ON COLUMN tktpopinfo.tpprintplace IS '手工券打印地点 0前台,1后台';
COMMENT ON COLUMN tktpopinfo.tprulepj IS '规则拼券: 0 不区分规则,1同规则用券(高级规则)';
COMMENT ON COLUMN tktpopinfo.tpiszk IS '是否打折';
COMMENT ON COLUMN tktpopinfo.tpcertarea IS '用券范围: 0通用,1本门店,2指定门店';
COMMENT ON COLUMN tktpopinfo.tpzkfd IS '折扣分担';
COMMENT ON COLUMN tktpopinfo.tpjfbs IS '积分倍数';
COMMENT ON COLUMN tktpopinfo.tpmaxzkl IS '折扣控制';
COMMENT ON COLUMN tktpopinfo.tpispopprn IS '打印促销联';
COMMENT ON COLUMN tktpopinfo.tpprnrate IS '促销联比率';
"""


def upgrade() -> None:
    op.execute(TICKET_ACTIVITY_TABLES_SQL)


def downgrade() -> None:
    op.drop_index("idx_tktcardfqlog_vipseq", table_name="tktcardfqlog")
    op.drop_index("idx_tktcardfqlog_vipno", table_name="tktcardfqlog")
    op.drop_index("idx_tktcardfqlog_trans", table_name="tktcardfqlog")
    op.drop_index("idx_tktcardfqlog_trace", table_name="tktcardfqlog")
    op.drop_index("idx_tktcardfqlog_tcflsource", table_name="tktcardfqlog")
    op.drop_index("idx_tktcardfqlog_tcflenddate", table_name="tktcardfqlog")
    op.drop_index("idx_tktcardfqlog_syj", table_name="tktcardfqlog")
    op.drop_index("idx_tktcardfqlog_date", table_name="tktcardfqlog")
    op.drop_index("idx_tcflsyjinv", table_name="tktcardfqlog")
    op.drop_table("tktpopinfo")
    op.drop_table("tktcardfqlog")
