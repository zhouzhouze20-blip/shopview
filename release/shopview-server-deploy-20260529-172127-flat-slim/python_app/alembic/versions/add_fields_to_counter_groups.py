"""Add store_id, area, category fields to counter_groups table

Revision ID: add_counter_group_fields
Revises: add_building_support
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_counter_group_fields'
down_revision = 'add_building_support'
branch_labels = None
depends_on = None


def upgrade():
    """Add new fields to counter_groups table"""
    # 添加门店ID字段（先设为可空）
    op.add_column('counter_groups', sa.Column('store_id', sa.Integer(), nullable=True))
    
    # 添加区域字段
    op.add_column('counter_groups', sa.Column('area_code', sa.String(20), nullable=True))
    op.add_column('counter_groups', sa.Column('area_name', sa.String(100), nullable=True))
    
    # 添加类别字段
    op.add_column('counter_groups', sa.Column('category_code', sa.String(20), nullable=True))
    op.add_column('counter_groups', sa.Column('category_name', sa.String(100), nullable=True))
    
    # 为现有数据设置默认门店ID（假设门店ID为1）
    op.execute("UPDATE counter_groups SET store_id = 1 WHERE store_id IS NULL")
    
    # 设置store_id为非空
    op.alter_column('counter_groups', 'store_id', nullable=False)
    
    # 添加外键约束
    op.create_foreign_key('fk_counter_groups_store_id', 'counter_groups', 'stores', ['store_id'], ['store_id'])
    
    # 删除月收益字段
    op.drop_column('counter_groups', 'monthly_revenue')


def downgrade():
    """Remove new fields from counter_groups table"""
    # 添加回月收益字段
    op.add_column('counter_groups', sa.Column('monthly_revenue', sa.Numeric(12, 2), nullable=True))
    
    # 删除外键约束
    op.drop_constraint('fk_counter_groups_store_id', 'counter_groups', type_='foreignkey')
    
    # 删除类别字段
    op.drop_column('counter_groups', 'category_name')
    op.drop_column('counter_groups', 'category_code')
    
    # 删除区域字段
    op.drop_column('counter_groups', 'area_name')
    op.drop_column('counter_groups', 'area_code')
    
    # 删除门店ID字段
    op.drop_column('counter_groups', 'store_id')
