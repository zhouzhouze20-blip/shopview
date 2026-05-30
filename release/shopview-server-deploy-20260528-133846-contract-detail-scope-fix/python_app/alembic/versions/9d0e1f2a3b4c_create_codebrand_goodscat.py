"""create brand and goods category tables

Revision ID: 9d0e1f2a3b4c
Revises: 8c9d0e1f2a3b
Create Date: 2026-05-13
"""
from typing import Sequence, Union

from alembic import op


revision: str = "9d0e1f2a3b4c"
down_revision: Union[str, Sequence[str], None] = "8c9d0e1f2a3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CODEBRAND_GOODSCAT_SQL = r"""
CREATE TABLE IF NOT EXISTS codebrand (
    cbid VARCHAR(6) NOT NULL,
    cbcname VARCHAR(100) NOT NULL,
    cbename VARCHAR(64),
    cbclass NUMERIC(1) NOT NULL,
    cbpid VARCHAR(6) NOT NULL,
    cbflag CHAR(1) NOT NULL,
    cbseq NUMERIC DEFAULT 0 NOT NULL,
    pptype VARCHAR(1),
    ppqj CHAR(1) DEFAULT '3',
    cbyt VARCHAR(10),
    cbgrade VARCHAR(10),
    cbvalue VARCHAR(10),
    CONSTRAINT pk_codebrand PRIMARY KEY (cbid)
);

COMMENT ON TABLE codebrand IS '品牌定义';
COMMENT ON COLUMN codebrand.cbid IS '品牌编码';
COMMENT ON COLUMN codebrand.cbcname IS '中文名称';
COMMENT ON COLUMN codebrand.cbename IS '英文名称';
COMMENT ON COLUMN codebrand.cbclass IS '级次';
COMMENT ON COLUMN codebrand.cbpid IS '上级编码';
COMMENT ON COLUMN codebrand.cbflag IS '末级标志';
COMMENT ON COLUMN codebrand.cbseq IS '流水号';
COMMENT ON COLUMN codebrand.pptype IS '品牌类别(1一般品牌2地区名牌3国内名牌4国际品牌5国际名牌)';
COMMENT ON COLUMN codebrand.ppqj IS '品牌前景(1、主力品牌2、潜力品牌3、一般品牌)';
COMMENT ON COLUMN codebrand.cbyt IS '业态';
COMMENT ON COLUMN codebrand.cbgrade IS '等级';
COMMENT ON COLUMN codebrand.cbvalue IS '价值';

CREATE TABLE IF NOT EXISTS goodscat (
    catcode VARCHAR(10) NOT NULL,
    catcname VARCHAR(40) NOT NULL,
    catename VARCHAR(60),
    catpcode VARCHAR(10) NOT NULL,
    catclass CHAR(1) NOT NULL,
    catflag CHAR(1) NOT NULL,
    catstatus CHAR(1) NOT NULL,
    catcscode CHAR(2),
    catisxh CHAR(1) NOT NULL,
    catisweb CHAR(1) NOT NULL,
    catcomseq NUMERIC(13),
    catcgy VARCHAR(20),
    catsubject VARCHAR(20),
    catplangdfl NUMERIC(5, 4),
    catplanbdfl NUMERIC(5, 4),
    catplanmll NUMERIC(5, 4),
    catplanxszq NUMERIC(4),
    catplanjhzq NUMERIC(4),
    catplankczq NUMERIC(4),
    catplanmaxkc NUMERIC(6),
    catplanminkc NUMERIC(6),
    catplanpzs NUMERIC(5),
    catlpzs NUMERIC(4),
    catljhml NUMERIC(5, 4),
    catlmaxsj NUMERIC(14, 4),
    catmpzs NUMERIC(4),
    catmjhml NUMERIC(5, 4),
    catmmaxsj NUMERIC(14, 4),
    cathpzs NUMERIC(4),
    cathjhml NUMERIC(5, 4),
    catisfood CHAR(1) DEFAULT 'N' NOT NULL,
    statcode VARCHAR(10),
    cathyjzkl NUMERIC(5, 4) DEFAULT 0,
    catpfjzkl NUMERIC(5, 4) DEFAULT 0,
    catpopsjzkl NUMERIC(5, 4) DEFAULT 0,
    catpophyjzkl NUMERIC(5, 4) DEFAULT 0,
    catpoppfjzkl NUMERIC(5, 4) DEFAULT 0,
    catzkjd NUMERIC(8, 2) DEFAULT 0.01,
    catmfid VARCHAR(20),
    catvc1 VARCHAR(20),
    catvc2 VARCHAR(20),
    catvc3 VARCHAR(20),
    catnum1 NUMERIC,
    catnum2 NUMERIC,
    catnum3 NUMERIC,
    catsupid VARCHAR(20),
    catwmid CHAR(1),
    catppcode VARCHAR(6),
    catispop CHAR(1),
    catbhmode CHAR(1),
    catpsmfid VARCHAR(20),
    catyt VARCHAR(1),
    catsalets NUMERIC,
    catifts CHAR(1),
    CONSTRAINT pk_goodscat PRIMARY KEY (catcode)
);

COMMENT ON TABLE goodscat IS '[CAT]商品分类';
COMMENT ON COLUMN goodscat.catcode IS '代码';
COMMENT ON COLUMN goodscat.catcname IS '中文名称';
COMMENT ON COLUMN goodscat.catename IS '英文名称';
COMMENT ON COLUMN goodscat.catpcode IS '上级编码';
COMMENT ON COLUMN goodscat.catclass IS '级次';
COMMENT ON COLUMN goodscat.catflag IS '末级标志';
COMMENT ON COLUMN goodscat.catstatus IS '状态';
COMMENT ON COLUMN goodscat.catcscode IS '消费类别';
COMMENT ON COLUMN goodscat.catisxh IS '是否销红';
COMMENT ON COLUMN goodscat.catisweb IS '是否网上发布';
COMMENT ON COLUMN goodscat.catcomseq IS '商品序号';
COMMENT ON COLUMN goodscat.catcgy IS '主管买手';
COMMENT ON COLUMN goodscat.catsubject IS '核算代码';
COMMENT ON COLUMN goodscat.catplangdfl IS '计划固定费率';
COMMENT ON COLUMN goodscat.catplanbdfl IS '计划变动费率';
COMMENT ON COLUMN goodscat.catplanmll IS '计划毛利率';
COMMENT ON COLUMN goodscat.catplanxszq IS '计划销售周期';
COMMENT ON COLUMN goodscat.catplanjhzq IS '计划进货周期';
COMMENT ON COLUMN goodscat.catplankczq IS '计划库龄';
COMMENT ON COLUMN goodscat.catplanmaxkc IS '计划最大库存';
COMMENT ON COLUMN goodscat.catplanminkc IS '计划最小库存';
COMMENT ON COLUMN goodscat.catplanpzs IS '商品品种数';
COMMENT ON COLUMN goodscat.catlpzs IS '商品品种数(低)';
COMMENT ON COLUMN goodscat.catljhml IS '商品计划毛利(低)';
COMMENT ON COLUMN goodscat.catlmaxsj IS '商品最高价格(低)';
COMMENT ON COLUMN goodscat.catmpzs IS '商品品种数(中)';
COMMENT ON COLUMN goodscat.catmjhml IS '商品计划毛利(中)';
COMMENT ON COLUMN goodscat.catmmaxsj IS '商品最高价格(中)';
COMMENT ON COLUMN goodscat.cathpzs IS '商品品种数(高)';
COMMENT ON COLUMN goodscat.cathjhml IS '商品计划毛利(高)';
COMMENT ON COLUMN goodscat.catisfood IS 'CATISFOOD';
COMMENT ON COLUMN goodscat.statcode IS '国家统计码';
COMMENT ON COLUMN goodscat.cathyjzkl IS '贵宾价缺省折扣率';
COMMENT ON COLUMN goodscat.catpfjzkl IS '批发价缺省折扣率';
COMMENT ON COLUMN goodscat.catpopsjzkl IS '促销零售价缺省折扣率';
COMMENT ON COLUMN goodscat.catpophyjzkl IS '促销零售价缺省折扣率';
COMMENT ON COLUMN goodscat.catpoppfjzkl IS '促销零售价缺省折扣率';
COMMENT ON COLUMN goodscat.catzkjd IS '折扣计算精度';
COMMENT ON COLUMN goodscat.catmfid IS '管理部门(采购部)';
COMMENT ON COLUMN goodscat.catyt IS '业态';
COMMENT ON COLUMN goodscat.catsalets IS '平均试销天数';
COMMENT ON COLUMN goodscat.catifts IS '是否启用停售(Y=停售，N=不停售)';

CREATE INDEX IF NOT EXISTS idx_cat_cname ON goodscat (catcname);
CREATE INDEX IF NOT EXISTS idx_cat_mfid ON goodscat (catmfid);
CREATE INDEX IF NOT EXISTS idx_cat_pcode ON goodscat (catpcode);
CREATE INDEX IF NOT EXISTS idx_s_catpcode ON goodscat (catcode, catpcode, catclass);
"""


def upgrade() -> None:
    op.execute(CODEBRAND_GOODSCAT_SQL)


def downgrade() -> None:
    op.drop_index("idx_s_catpcode", table_name="goodscat")
    op.drop_index("idx_cat_pcode", table_name="goodscat")
    op.drop_index("idx_cat_mfid", table_name="goodscat")
    op.drop_index("idx_cat_cname", table_name="goodscat")
    op.drop_table("goodscat")
    op.drop_table("codebrand")
