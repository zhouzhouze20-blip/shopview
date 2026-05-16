"""Add building support to floors table

Revision ID: add_building_support
Revises: 9027644da811
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_building_support'
down_revision = '9027644da811'
branch_labels = None
depends_on = None


def upgrade():
    # 添加新字段
    op.add_column('floors', sa.Column('building_code', sa.String(20), nullable=True, comment='栋号编码（如A栋、B栋）'))
    op.add_column('floors', sa.Column('building_name', sa.String(50), nullable=True, comment='栋号名称（如A栋、B栋、主楼）'))
    op.add_column('floors', sa.Column('floor_display_name', sa.String(50), nullable=True, comment='楼层显示名称（如B1、1F、16F）'))
    op.add_column('floors', sa.Column('sort_order', sa.Integer(), nullable=True, comment='排序顺序（用于楼层列表排序）'))
    
    # 修改floor_number字段为NOT NULL
    op.alter_column('floors', 'floor_number', nullable=False, comment='楼层编号（-1表示负一楼，0表示地面层，1表示一楼）')
    
    # 为现有数据设置默认值
    op.execute("UPDATE floors SET floor_number = 1 WHERE floor_number IS NULL")
    op.execute("UPDATE floors SET sort_order = floor_number WHERE sort_order IS NULL")
    
    # 设置sort_order字段的默认值
    op.alter_column('floors', 'sort_order', nullable=False, server_default='0')


def downgrade():
    # 删除新添加的字段
    op.drop_column('floors', 'sort_order')
    op.drop_column('floors', 'floor_display_name')
    op.drop_column('floors', 'building_name')
    op.drop_column('floors', 'building_code')
    
    # 恢复floor_number字段为可空
    op.alter_column('floors', 'floor_number', nullable=True)
