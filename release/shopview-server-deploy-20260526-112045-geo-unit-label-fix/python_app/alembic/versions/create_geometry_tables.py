"""Create separate geometry tables for counters

Revision ID: create_geometry_tables
Revises: add_polygon_support
Create Date: 2025-01-08 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'create_geometry_tables'
down_revision = 'add_polygon_support'
branch_labels = None
depends_on = None


def upgrade():
    """Create geometry tables and migrate data"""
    
    # 1. 创建几何信息表
    op.create_table('counter_geometries',
        sa.Column('geometry_id', sa.Integer(), primary_key=True),
        sa.Column('counter_id', sa.Integer(), sa.ForeignKey('counters.counter_id'), nullable=False),
        sa.Column('shape_type', sa.String(20), nullable=False, comment='形状类型：rectangle, polygon, circle, ellipse'),
        
        # 矩形字段
        sa.Column('position_x', sa.Numeric(10, 2), comment='X坐标（矩形）'),
        sa.Column('position_y', sa.Numeric(10, 2), comment='Y坐标（矩形）'),
        sa.Column('width', sa.Numeric(10, 2), comment='宽度（矩形）'),
        sa.Column('height', sa.Numeric(10, 2), comment='高度（矩形）'),
        sa.Column('rotation', sa.Numeric(5, 2), default=0, comment='旋转角度'),
        
        # 多边形字段
        sa.Column('polygon_coordinates', sa.Text(), comment='多边形坐标点，JSON格式'),
        
        # 圆形字段
        sa.Column('center_x', sa.Numeric(10, 2), comment='圆心X坐标'),
        sa.Column('center_y', sa.Numeric(10, 2), comment='圆心Y坐标'),
        sa.Column('radius', sa.Numeric(10, 2), comment='半径'),
        
        # 椭圆字段
        sa.Column('ellipse_center_x', sa.Numeric(10, 2), comment='椭圆中心X坐标'),
        sa.Column('ellipse_center_y', sa.Numeric(10, 2), comment='椭圆中心Y坐标'),
        sa.Column('ellipse_radius_x', sa.Numeric(10, 2), comment='椭圆X轴半径'),
        sa.Column('ellipse_radius_y', sa.Numeric(10, 2), comment='椭圆Y轴半径'),
        sa.Column('ellipse_rotation', sa.Numeric(5, 2), comment='椭圆旋转角度'),
        
        # 通用字段
        sa.Column('bounding_box_min_x', sa.Numeric(10, 2), comment='边界框最小X坐标'),
        sa.Column('bounding_box_min_y', sa.Numeric(10, 2), comment='边界框最小Y坐标'),
        sa.Column('bounding_box_max_x', sa.Numeric(10, 2), comment='边界框最大X坐标'),
        sa.Column('bounding_box_max_y', sa.Numeric(10, 2), comment='边界框最大Y坐标'),
        
        # 元数据
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()')),
        
        comment='柜位几何信息表'
    )
    
    # 2. 创建几何属性表
    op.create_table('counter_geometry_properties',
        sa.Column('property_id', sa.Integer(), primary_key=True),
        sa.Column('geometry_id', sa.Integer(), sa.ForeignKey('counter_geometries.geometry_id'), nullable=False),
        sa.Column('property_name', sa.String(50), nullable=False, comment='属性名'),
        sa.Column('property_value', sa.Text(), comment='属性值（JSON格式）'),
        sa.Column('property_type', sa.String(20), comment='属性类型：string, number, boolean, json'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
        
        comment='柜位几何属性表'
    )
    
    # 3. 迁移现有数据到几何表
    op.execute("""
        INSERT INTO counter_geometries (
            counter_id, shape_type, position_x, position_y, width, height,
            polygon_coordinates, center_x, center_y, radius,
            bounding_box_min_x, bounding_box_min_y, bounding_box_max_x, bounding_box_max_y,
            created_at, updated_at
        )
        SELECT 
            counter_id,
            COALESCE(shape_type, 'rectangle') as shape_type,
            position_x, position_y, width, height,
            polygon_coordinates,
            center_x, center_y,
            NULL as radius,
            bounding_box_min_x, bounding_box_min_y, bounding_box_max_x, bounding_box_max_y,
            created_at, updated_at
        FROM counters
        WHERE position_x IS NOT NULL OR polygon_coordinates IS NOT NULL
    """)
    
    # 4. 为几何表创建索引
    op.create_index('idx_counter_geometries_counter_id', 'counter_geometries', ['counter_id'])
    op.create_index('idx_counter_geometries_shape_type', 'counter_geometries', ['shape_type'])
    op.create_index('idx_counter_geometries_bounding_box', 'counter_geometries', 
                   ['bounding_box_min_x', 'bounding_box_min_y', 'bounding_box_max_x', 'bounding_box_max_y'])
    
    op.create_index('idx_geometry_properties_geometry_id', 'counter_geometry_properties', ['geometry_id'])
    op.create_index('idx_geometry_properties_name', 'counter_geometry_properties', ['property_name'])


def downgrade():
    """Drop geometry tables"""
    op.drop_table('counter_geometry_properties')
    op.drop_table('counter_geometries')






