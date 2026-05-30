"""create fj_dw_member_dim member dimension table

Revision ID: 5f6a7b8c9d0e
Revises: 2c3d4e5f6a7b
Create Date: 2026-05-11
"""
from typing import Sequence, Union

from alembic import op


revision: str = "5f6a7b8c9d0e"
down_revision: Union[str, Sequence[str], None] = "2c3d4e5f6a7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FJ_DW_MEMBER_DIM_SQL = r"""
CREATE TABLE IF NOT EXISTS fj_dw_member_dim (
    customer_no VARCHAR(50),
    customer_name VARCHAR(100),
    sex VARCHAR(50),
    telephone VARCHAR(50),
    customer_level VARCHAR(50),
    admission_date DATE,
    lead_store VARCHAR(50),
    regist_channel VARCHAR(50),
    birthday DATE,
    age NUMERIC,
    reg_source VARCHAR(50),
    depart_name2 VARCHAR(50),
    area_name VARCHAR(50),
    category_name VARCHAR(50),
    can_consum_score NUMERIC,
    customer_status VARCHAR(50)
);

COMMENT ON TABLE fj_dw_member_dim IS '会员维表：活动分析会员基础信息';
COMMENT ON COLUMN fj_dw_member_dim.customer_no IS '会员编号';
COMMENT ON COLUMN fj_dw_member_dim.customer_name IS '会员姓名';
COMMENT ON COLUMN fj_dw_member_dim.sex IS '性别';
COMMENT ON COLUMN fj_dw_member_dim.telephone IS '手机号';
COMMENT ON COLUMN fj_dw_member_dim.customer_level IS '会员等级';
COMMENT ON COLUMN fj_dw_member_dim.admission_date IS '入会日期';
COMMENT ON COLUMN fj_dw_member_dim.lead_store IS '归属门店';
COMMENT ON COLUMN fj_dw_member_dim.regist_channel IS '注册渠道';
COMMENT ON COLUMN fj_dw_member_dim.birthday IS '生日';
COMMENT ON COLUMN fj_dw_member_dim.age IS '年龄';
COMMENT ON COLUMN fj_dw_member_dim.reg_source IS '注册来源';
COMMENT ON COLUMN fj_dw_member_dim.depart_name2 IS '部门';
COMMENT ON COLUMN fj_dw_member_dim.area_name IS '区域';
COMMENT ON COLUMN fj_dw_member_dim.category_name IS '品类';
COMMENT ON COLUMN fj_dw_member_dim.can_consum_score IS '可用消费积分';
COMMENT ON COLUMN fj_dw_member_dim.customer_status IS '会员状态';
"""


def upgrade() -> None:
    op.execute(FJ_DW_MEMBER_DIM_SQL)


def downgrade() -> None:
    op.drop_table("fj_dw_member_dim")
