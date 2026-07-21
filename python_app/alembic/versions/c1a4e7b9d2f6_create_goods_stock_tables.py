"""create goods stock tables

Revision ID: c1a4e7b9d2f6
Revises: b8d4e6f0a2c3
Create Date: 2026-07-20

GOODSCAT is intentionally not recreated here: revision 9d0e1f2a3b4c already
creates it with the same Oracle source definition. This revision adds the two
remaining tables supplied with that definition set.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c1a4e7b9d2f6"
down_revision: Union[str, Sequence[str], None] = "b8d4e6f0a2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
CREATE TABLE goodsstock (
    gstgdid VARCHAR(20) NOT NULL,
    gstgdtype CHAR(1) NOT NULL,
    gstmfid VARCHAR(20) NOT NULL,
    gstsupid VARCHAR(20) NOT NULL,
    gstwmid CHAR(1) NOT NULL,
    gstmanncls NUMERIC NOT NULL,
    gstmarket VARCHAR(20) NOT NULL,
    gstkl NUMERIC NOT NULL,
    gstzkfd NUMERIC NOT NULL,
    gsthsjj NUMERIC(14, 4) NOT NULL,
    gstbhsjj NUMERIC(14, 4) NOT NULL,
    gststatus CHAR(1) NOT NULL,
    gstistg CHAR(1) NOT NULL,
    gsttgrq TIMESTAMP WITHOUT TIME ZONE,
    gstists CHAR(1) NOT NULL,
    gsttsrq TIMESTAMP WITHOUT TIME ZONE,
    gstisdj CHAR(1) NOT NULL,
    gstdjrq TIMESTAMP WITHOUT TIME ZONE,
    gstkcjs NUMERIC(16, 4) NOT NULL,
    gstkcsl NUMERIC(16, 4) NOT NULL,
    gstkchsjjje NUMERIC(16, 4) NOT NULL,
    gstkcbhsjjje NUMERIC(16, 4) NOT NULL,
    gstkchssjje NUMERIC(14, 2) NOT NULL,
    gstkchsjxcj NUMERIC(16, 4) NOT NULL,
    gstqckcjs NUMERIC(16, 4) NOT NULL,
    gstqckcsl NUMERIC(16, 4) NOT NULL,
    gstqckchsjjje NUMERIC(16, 4) NOT NULL,
    gstqckcbhsjjje NUMERIC(16, 4) NOT NULL,
    gstqckchssjje NUMERIC(14, 2) NOT NULL,
    gstqckchsjxcj NUMERIC(16, 4) NOT NULL,
    gstkcsuphsje NUMERIC(16, 4) NOT NULL,
    gstkcsupbhsje NUMERIC(16, 4) NOT NULL,
    gstqcsuphsje NUMERIC(16, 4) NOT NULL,
    gstqcsupbhsje NUMERIC(16, 4) NOT NULL,
    gstmd CHAR(1) DEFAULT '1' NOT NULL,
    gstshelf VARCHAR(20) DEFAULT '0' NOT NULL,
    gstsample CHAR(1) DEFAULT 'N' NOT NULL,
    CONSTRAINT pk_goodsstock PRIMARY KEY (
        gstgdid, gstmfid, gstsupid, gstwmid, gstmd, gstshelf, gstsample
    )
);

COMMENT ON TABLE goodsstock IS '[GSC]商品存货信息（当前库存）';
COMMENT ON COLUMN goodsstock.gstgdid IS '商品代码';
COMMENT ON COLUMN goodsstock.gstgdtype IS '编码类别';
COMMENT ON COLUMN goodsstock.gstmfid IS '管理架购';
COMMENT ON COLUMN goodsstock.gstsupid IS '供应商';
COMMENT ON COLUMN goodsstock.gstwmid IS '经营方式';
COMMENT ON COLUMN goodsstock.gstmanncls IS '经营级别';
COMMENT ON COLUMN goodsstock.gstmarket IS '管理架购第一级';
COMMENT ON COLUMN goodsstock.gstkl IS '扣率';
COMMENT ON COLUMN goodsstock.gstzkfd IS '折扣分担';
COMMENT ON COLUMN goodsstock.gsthsjj IS '平均含税进价';
COMMENT ON COLUMN goodsstock.gstbhsjj IS '平均不含税进价';
COMMENT ON COLUMN goodsstock.gststatus IS '有效状态';
COMMENT ON COLUMN goodsstock.gstistg IS '停购';
COMMENT ON COLUMN goodsstock.gsttgrq IS '停购日期';
COMMENT ON COLUMN goodsstock.gstists IS '停售';
COMMENT ON COLUMN goodsstock.gsttsrq IS '停售日期';
COMMENT ON COLUMN goodsstock.gstisdj IS '冻结';
COMMENT ON COLUMN goodsstock.gstdjrq IS '冻结日期';
COMMENT ON COLUMN goodsstock.gstkcjs IS '库存件数';
COMMENT ON COLUMN goodsstock.gstkcsl IS '库存数量';
COMMENT ON COLUMN goodsstock.gstkchsjjje IS '库存含税进价金额';
COMMENT ON COLUMN goodsstock.gstkcbhsjjje IS '库存不含税进价金额';
COMMENT ON COLUMN goodsstock.gstkchssjje IS '库存含税收价金额';
COMMENT ON COLUMN goodsstock.gstkchsjxcj IS '库存含税进销差价';
COMMENT ON COLUMN goodsstock.gstqckcjs IS 'GSTQCKCJS';
COMMENT ON COLUMN goodsstock.gstqckcsl IS 'GSTQCKCSL';
COMMENT ON COLUMN goodsstock.gstqckchsjjje IS 'GSTQCKCHSJJJE';
COMMENT ON COLUMN goodsstock.gstqckcbhsjjje IS 'GSTQCKCBHSJJJE';
COMMENT ON COLUMN goodsstock.gstqckchssjje IS 'GSTQCKCHSSJJE';
COMMENT ON COLUMN goodsstock.gstqckchsjxcj IS 'GSTQCKCHSJXCJ';
COMMENT ON COLUMN goodsstock.gstkcsuphsje IS 'GSTKCSUPHSJE';
COMMENT ON COLUMN goodsstock.gstkcsupbhsje IS 'GSTKCSUPBHSJE';
COMMENT ON COLUMN goodsstock.gstqcsuphsje IS 'GSTQCSUPHSJE';
COMMENT ON COLUMN goodsstock.gstqcsupbhsje IS 'GSTQCSUPBHSJE';
COMMENT ON COLUMN goodsstock.gstmd IS '子库存';
COMMENT ON COLUMN goodsstock.gstshelf IS '货位';
COMMENT ON COLUMN goodsstock.gstsample IS '是否样品';

CREATE INDEX index_gst_market ON goodsstock (gstmarket, gstshelf);
CREATE INDEX index_gst_mfcode ON goodsstock (gstmfid);
CREATE INDEX index_gst_sup ON goodsstock (gstsupid);

CREATE TABLE goodsstock_bak (
    gstdate TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    gstgdid VARCHAR(20) NOT NULL,
    gstgdtype CHAR(1) NOT NULL,
    gstmfid VARCHAR(20) NOT NULL,
    gstsupid VARCHAR(20) NOT NULL,
    gstwmid CHAR(1) NOT NULL,
    gstmanncls NUMERIC NOT NULL,
    gstmarket VARCHAR(20) NOT NULL,
    gstkl NUMERIC NOT NULL,
    gstzkfd NUMERIC NOT NULL,
    gsthsjj NUMERIC(14, 4) NOT NULL,
    gstbhsjj NUMERIC(14, 4) NOT NULL,
    gststatus CHAR(1) NOT NULL,
    gstistg CHAR(1) NOT NULL,
    gsttgrq TIMESTAMP WITHOUT TIME ZONE,
    gstists CHAR(1) NOT NULL,
    gsttsrq TIMESTAMP WITHOUT TIME ZONE,
    gstisdj CHAR(1) NOT NULL,
    gstdjrq TIMESTAMP WITHOUT TIME ZONE,
    gstkcjs NUMERIC(16, 4) NOT NULL,
    gstkcsl NUMERIC(16, 4) NOT NULL,
    gstkchsjjje NUMERIC(16, 4) NOT NULL,
    gstkcbhsjjje NUMERIC(16, 4) NOT NULL,
    gstkchssjje NUMERIC(14, 2) NOT NULL,
    gstkchsjxcj NUMERIC(16, 4) NOT NULL,
    gstqckcjs NUMERIC(16, 4) NOT NULL,
    gstqckcsl NUMERIC(16, 4) NOT NULL,
    gstqckchsjjje NUMERIC(16, 4) NOT NULL,
    gstqckcbhsjjje NUMERIC(16, 4) NOT NULL,
    gstqckchssjje NUMERIC(14, 2) NOT NULL,
    gstqckchsjxcj NUMERIC(16, 4) NOT NULL,
    gstkcsuphsje NUMERIC(16, 4) NOT NULL,
    gstkcsupbhsje NUMERIC(16, 4) NOT NULL,
    gstqcsuphsje NUMERIC(16, 4) NOT NULL,
    gstqcsupbhsje NUMERIC(16, 4) NOT NULL,
    gstmd CHAR(1) DEFAULT '1' NOT NULL,
    gstshelf VARCHAR(20) DEFAULT '0' NOT NULL,
    gstsample CHAR(1) DEFAULT 'N' NOT NULL,
    gstsj NUMERIC(16, 4),
    gstsjje NUMERIC(16, 4),
    gstanalcode VARCHAR(20),
    CONSTRAINT pk_goodsstock_bak PRIMARY KEY (
        gstdate, gstgdid, gstmfid, gstsupid, gstwmid, gstmd, gstshelf, gstsample
    )
);

COMMENT ON TABLE goodsstock_bak IS '[GSC]商品存货信息（当前库存）';
COMMENT ON COLUMN goodsstock_bak.gstgdid IS '商品代码';
COMMENT ON COLUMN goodsstock_bak.gstgdtype IS '编码类别';
COMMENT ON COLUMN goodsstock_bak.gstmfid IS '管理架购';
COMMENT ON COLUMN goodsstock_bak.gstsupid IS '供应商';
COMMENT ON COLUMN goodsstock_bak.gstwmid IS '经营方式';
COMMENT ON COLUMN goodsstock_bak.gstmanncls IS '经营级别';
COMMENT ON COLUMN goodsstock_bak.gstmarket IS '管理架购第一级';
COMMENT ON COLUMN goodsstock_bak.gstkl IS '扣率';
COMMENT ON COLUMN goodsstock_bak.gstzkfd IS '折扣分担';
COMMENT ON COLUMN goodsstock_bak.gsthsjj IS '平均含税进价';
COMMENT ON COLUMN goodsstock_bak.gstbhsjj IS '平均不含税进价';
COMMENT ON COLUMN goodsstock_bak.gststatus IS '有效状态';
COMMENT ON COLUMN goodsstock_bak.gstistg IS '停购';
COMMENT ON COLUMN goodsstock_bak.gsttgrq IS '停购日期';
COMMENT ON COLUMN goodsstock_bak.gstists IS '停售';
COMMENT ON COLUMN goodsstock_bak.gsttsrq IS '停售日期';
COMMENT ON COLUMN goodsstock_bak.gstisdj IS '冻结';
COMMENT ON COLUMN goodsstock_bak.gstdjrq IS '冻结日期';
COMMENT ON COLUMN goodsstock_bak.gstkcjs IS '库存件数';
COMMENT ON COLUMN goodsstock_bak.gstkcsl IS '库存数量';
COMMENT ON COLUMN goodsstock_bak.gstkchsjjje IS '库存含税进价金额';
COMMENT ON COLUMN goodsstock_bak.gstkcbhsjjje IS '库存不含税进价金额';
COMMENT ON COLUMN goodsstock_bak.gstkchssjje IS '库存售价金额';
COMMENT ON COLUMN goodsstock_bak.gstkchsjxcj IS '库存含税进销差价';
COMMENT ON COLUMN goodsstock_bak.gstqckcjs IS 'GSTQCKCJS';
COMMENT ON COLUMN goodsstock_bak.gstqckcsl IS 'GSTQCKCSL';
COMMENT ON COLUMN goodsstock_bak.gstqckchsjjje IS 'GSTQCKCHSJJJE';
COMMENT ON COLUMN goodsstock_bak.gstqckcbhsjjje IS 'GSTQCKCBHSJJJE';
COMMENT ON COLUMN goodsstock_bak.gstqckchssjje IS 'GSTQCKCHSSJJE';
COMMENT ON COLUMN goodsstock_bak.gstqckchsjxcj IS 'GSTQCKCHSJXCJ';
COMMENT ON COLUMN goodsstock_bak.gstkcsuphsje IS 'GSTKCSUPHSJE';
COMMENT ON COLUMN goodsstock_bak.gstkcsupbhsje IS 'GSTKCSUPBHSJE';
COMMENT ON COLUMN goodsstock_bak.gstqcsuphsje IS 'GSTQCSUPHSJE';
COMMENT ON COLUMN goodsstock_bak.gstqcsupbhsje IS 'GSTQCSUPBHSJE';
COMMENT ON COLUMN goodsstock_bak.gstmd IS '子库存';
COMMENT ON COLUMN goodsstock_bak.gstshelf IS '货位';
COMMENT ON COLUMN goodsstock_bak.gstsample IS '是否样品';
COMMENT ON COLUMN goodsstock_bak.gstsj IS '售价';
COMMENT ON COLUMN goodsstock_bak.gstsjje IS '售价金额';

CREATE INDEX index_gstb_gstdate ON goodsstock_bak (gstdate);
CREATE INDEX index_gstb_market ON goodsstock_bak (gstmarket);
CREATE INDEX index_gstb_mfcode ON goodsstock_bak (gstmfid);
CREATE INDEX index_gstb_sup ON goodsstock_bak (gstsupid);
"""


DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS goodsstock_bak;
DROP TABLE IF EXISTS goodsstock;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
