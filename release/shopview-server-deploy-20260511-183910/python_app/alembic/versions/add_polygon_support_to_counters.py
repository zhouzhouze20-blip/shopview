"""Add polygon support to counters table

Revision ID: add_polygon_support
Revises: add_fields_to_counter_groups
Create Date: 2025-01-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_polygon_support'
down_revision = 'add_counter_group_fields'
branch_labels = None
depends_on = None


def upgrade():
    """Add polygon support fields to counters table"""
    # 添加形状类型字段
    op.add_column('counters', sa.Column('shape_type', sa.String(20), nullable=True, comment='形状类型：rectangle, polygon, circle'))
    
    # 添加多边形坐标字段（JSON格式存储坐标点）
    op.add_column('counters', sa.Column('polygon_coordinates', sa.Text, nullable=True, comment='多边形坐标点，JSON格式'))
    
    # 添加中心点坐标字段（用于快速定位）
    op.add_column('counters', sa.Column('center_x', sa.Numeric(10, 2), nullable=True, comment='中心点X坐标'))
    op.add_column('counters', sa.Column('center_y', sa.Numeric(10, 2), nullable=True, comment='中心点Y坐标'))
    
    # 添加边界框字段（用于快速查询和碰撞检测）
    op.add_column('counters', sa.Column('bounding_box_min_x', sa.Numeric(10, 2), nullable=True, comment='边界框最小X坐标'))
    op.add_column('counters', sa.Column('bounding_box_min_y', sa.Numeric(10, 2), nullable=True, comment='边界框最小Y坐标'))
    op.add_column('counters', sa.Column('bounding_box_max_x', sa.Numeric(10, 2), nullable=True, comment='边界框最大X坐标'))
    op.add_column('counters', sa.Column('bounding_box_max_y', sa.Numeric(10, 2), nullable=True, comment='边界框最大Y坐标'))
    
    # 为现有数据设置默认值
    op.execute("UPDATE counters SET shape_type = 'rectangle' WHERE shape_type IS NULL")
    op.execute("UPDATE counters SET center_x = position_x WHERE center_x IS NULL")
    op.execute("UPDATE counters SET center_y = position_y WHERE center_y IS NULL")
    op.execute("UPDATE counters SET bounding_box_min_x = position_x WHERE bounding_box_min_x IS NULL")
    op.execute("UPDATE counters SET bounding_box_min_y = position_y WHERE bounding_box_min_y IS NULL")
    op.execute("UPDATE counters SET bounding_box_max_x = position_x + width WHERE bounding_box_max_x IS NULL")
    op.execute("UPDATE counters SET bounding_box_max_y = position_y + height WHERE bounding_box_max_y IS NULL")
    
    # 为矩形柜位生成多边形坐标
    op.execute("""
        UPDATE counters 
        SET polygon_coordinates = json_build_array(
            json_build_array(position_x, position_y),
            json_build_array(position_x + width, position_y),
            json_build_array(position_x + width, position_y + height),
            json_build_array(position_x, position_y + height)
        )::text
        WHERE shape_type = 'rectangle' AND polygon_coordinates IS NULL
    """)


def downgrade():
    """Remove polygon support fields from counters table"""
    op.drop_column('counters', 'bounding_box_max_y')
    op.drop_column('counters', 'bounding_box_max_x')
    op.drop_column('counters', 'bounding_box_min_y')
    op.drop_column('counters', 'bounding_box_min_x')
    op.drop_column('counters', 'center_y')
    op.drop_column('counters', 'center_x')
    op.drop_column('counters', 'polygon_coordinates')
    op.drop_column('counters', 'shape_type')
