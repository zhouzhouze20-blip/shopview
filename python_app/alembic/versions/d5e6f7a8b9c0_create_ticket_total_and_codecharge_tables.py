"""create ticket total and codecharge tables

Revision ID: d5e6f7a8b9c0
Revises: 0b1c2d3e4f5a, 5e6f7a8b9c0d, c4d5e6f7a8b9
Create Date: 2026-07-08
"""
from typing import Sequence, Union

from alembic import op


revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = (
    "0b1c2d3e4f5a",
    "5e6f7a8b9c0d",
    "c4d5e6f7a8b9",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS tktcardfqtotal (
    tcftseqno NUMERIC NOT NULL,
    tcftvipno VARCHAR(20) NOT NULL,
    tcftstartdate DATE NOT NULL,
    tcftenddate DATE NOT NULL,
    tcftqtype CHAR(1) NOT NULL,
    tcftfqje NUMERIC DEFAULT 0 NOT NULL,
    tcftstatus CHAR(1) NOT NULL,
    tcftvipexno VARCHAR(20) NOT NULL,
    tcftmemo VARCHAR(60),
    tcftzpno VARCHAR(20),
    tcftfstpid VARCHAR(20) NOT NULL,
    tcftcltpid VARCHAR(20),
    tcftflag CHAR(1) DEFAULT 'Y',
    tcftransno NUMERIC,
    tcfttype CHAR(1) DEFAULT '1' NOT NULL,
    tcftqmz NUMERIC(12, 2),
    tcftmkt VARCHAR(20),
    tcftjygs VARCHAR(20) NOT NULL,
    tcftfqmkt VARCHAR(20) NOT NULL,
    tcftfqrule VARCHAR(20) DEFAULT '0' NOT NULL,
    tcftrulepj CHAR(1) DEFAULT '0' NOT NULL,
    tcftsource CHAR(1) DEFAULT '1',
    tcftismzq CHAR(1) DEFAULT 'N',
    tcftqno VARCHAR(20),
    CONSTRAINT pk_tktcardfq PRIMARY KEY (tcftseqno)
);

COMMENT ON TABLE tktcardfqtotal IS '[TCFT]VIP卡返券表';
COMMENT ON COLUMN tktcardfqtotal.tcftseqno IS '序号';
COMMENT ON COLUMN tktcardfqtotal.tcftvipno IS 'VIP卡号';
COMMENT ON COLUMN tktcardfqtotal.tcftstartdate IS '券有效期';
COMMENT ON COLUMN tktcardfqtotal.tcftenddate IS '券有效期';
COMMENT ON COLUMN tktcardfqtotal.tcftqtype IS '券种';
COMMENT ON COLUMN tktcardfqtotal.tcftfqje IS '券金额';
COMMENT ON COLUMN tktcardfqtotal.tcftstatus IS '状态';
COMMENT ON COLUMN tktcardfqtotal.tcftvipexno IS 'VIP卡磁道信息';
COMMENT ON COLUMN tktcardfqtotal.tcftmemo IS '备注';
COMMENT ON COLUMN tktcardfqtotal.tcftzpno IS '支票号';
COMMENT ON COLUMN tktcardfqtotal.tcftfstpid IS '生成档期';
COMMENT ON COLUMN tktcardfqtotal.tcftcltpid IS '处理档期';
COMMENT ON COLUMN tktcardfqtotal.tcftflag IS '可用标志';
COMMENT ON COLUMN tktcardfqtotal.tcftransno IS '事务号';
COMMENT ON COLUMN tktcardfqtotal.tcfttype IS '1:vip电子券,2:手工券';
COMMENT ON COLUMN tktcardfqtotal.tcftqmz IS '返券面值';
COMMENT ON COLUMN tktcardfqtotal.tcftmkt IS '使用范围模式（必选）';
COMMENT ON COLUMN tktcardfqtotal.tcftjygs IS '经营公司（必选）';
COMMENT ON COLUMN tktcardfqtotal.tcftfqmkt IS '返券门店（必选）';
COMMENT ON COLUMN tktcardfqtotal.tcftfqrule IS '返券规则（必选）0 通收  invalid';
COMMENT ON COLUMN tktcardfqtotal.tcftrulepj IS '规则拼券（必选）               invalid';
COMMENT ON COLUMN tktcardfqtotal.tcftsource IS '券来源1:销售返券 2:买券 3:银行追送 4:退货返券 5券转入7后台手工新增';
COMMENT ON COLUMN tktcardfqtotal.tcftismzq IS '是否面值券';
COMMENT ON COLUMN tktcardfqtotal.tcftqno IS '券号';

CREATE INDEX IF NOT EXISTS idx_tcft_unique
    ON tktcardfqtotal (
        tcftvipno,
        tcftstartdate,
        tcftenddate,
        tcftqtype,
        tcftmkt,
        tcftjygs,
        tcftfqmkt,
        tcftsource
    );
CREATE INDEX IF NOT EXISTS idx_tkt_qno ON tktcardfqtotal (tcftqno);
CREATE INDEX IF NOT EXISTS idx_tkt_tcftdate ON tktcardfqtotal (tcftstartdate, tcftenddate);
CREATE INDEX IF NOT EXISTS idx_tkt_tcftransno ON tktcardfqtotal (tcftransno);
CREATE INDEX IF NOT EXISTS idx_tkt_tcftvipno ON tktcardfqtotal (tcftvipno, tcftqtype);

CREATE TABLE IF NOT EXISTS codecharge (
    cccode CHAR(2) NOT NULL,
    ccname VARCHAR(32) NOT NULL,
    ccdeftype VARCHAR(4) NOT NULL,
    cctdefvalue NUMERIC NOT NULL,
    cctstatus CHAR(1) NOT NULL,
    ccflag CHAR(1) NOT NULL,
    ccprt CHAR(1) DEFAULT 'N',
    cctype VARCHAR(10),
    ccnum1 NUMERIC DEFAULT 0.01,
    ccnum2 NUMERIC DEFAULT 0.01,
    cctax CHAR(1) DEFAULT 'Y',
    ccret CHAR(1) DEFAULT 'N',
    cciskp CHAR(1),
    ccvc1 VARCHAR(20),
    ccvc2 VARCHAR(20),
    ccvc3 VARCHAR(20),
    ccnum3 NUMERIC,
    ccnum4 NUMERIC,
    ccnum5 NUMERIC,
    ccvc4 VARCHAR(20),
    ccvc5 VARCHAR(20),
    ccvc6 CHAR(1) DEFAULT 'N',
    ccvc7 CHAR(1),
    CONSTRAINT pk_codecharge PRIMARY KEY (cccode)
);

COMMENT ON TABLE codecharge IS '[CC]费用编码';
COMMENT ON COLUMN codecharge.cccode IS '代码';
COMMENT ON COLUMN codecharge.ccname IS '名称';
COMMENT ON COLUMN codecharge.ccdeftype IS '提取方式';
COMMENT ON COLUMN codecharge.cctdefvalue IS '缺省指标';
COMMENT ON COLUMN codecharge.cctstatus IS '状态';
COMMENT ON COLUMN codecharge.ccflag IS '是否帐扣';
COMMENT ON COLUMN codecharge.ccprt IS '是否单独打印收据';
COMMENT ON COLUMN codecharge.cctype IS '类别';
COMMENT ON COLUMN codecharge.ccnum1 IS '数值精度';
COMMENT ON COLUMN codecharge.cctax IS '计算税金';
COMMENT ON COLUMN codecharge.ccret IS '是否返还型费用';
COMMENT ON COLUMN codecharge.cciskp IS '是否开票';
COMMENT ON COLUMN codecharge.ccvc1 IS '结算主体';
COMMENT ON COLUMN codecharge.ccvc2 IS '账单分类';
COMMENT ON COLUMN codecharge.ccvc3 IS '面积基数';
COMMENT ON COLUMN codecharge.ccvc4 IS '费用阶段';
COMMENT ON COLUMN codecharge.ccvc5 IS '是否抵扣';
COMMENT ON COLUMN codecharge.ccvc6 IS '是否系统默认(Y/N)';
COMMENT ON COLUMN codecharge.ccvc7 IS '是否合同默认费用';
"""


DOWNGRADE_SQL = r"""
DROP INDEX IF EXISTS idx_tkt_tcftvipno;
DROP INDEX IF EXISTS idx_tkt_tcftransno;
DROP INDEX IF EXISTS idx_tkt_tcftdate;
DROP INDEX IF EXISTS idx_tkt_qno;
DROP INDEX IF EXISTS idx_tcft_unique;

DROP TABLE IF EXISTS codecharge;
DROP TABLE IF EXISTS tktcardfqtotal;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
