#!/usr/bin/env python3
"""
创建几何信息表
Create geometry tables for counter management
"""
import psycopg2
import sys

def create_geometry_tables():
    """创建几何信息表"""
    try:
        # 连接数据库
        conn = psycopg2.connect(
            host='192.168.98.80',
            port=5432,
            database='sales_db',
            user='sales_user',
            password='sales_password_2024'
        )
        cur = conn.cursor()
        
        print("开始创建几何信息表...")
        
        # 1. 创建几何信息表
        create_geometries_table = """
        CREATE TABLE IF NOT EXISTS counter_geometries (
            geometry_id SERIAL PRIMARY KEY,
            counter_id INTEGER NOT NULL REFERENCES counters(counter_id) ON DELETE CASCADE,
            shape_type VARCHAR(20) NOT NULL CHECK (shape_type IN ('rectangle', 'polygon', 'circle', 'ellipse')),
            
            -- 矩形字段
            position_x NUMERIC(10,2),
            position_y NUMERIC(10,2),
            width NUMERIC(10,2),
            height NUMERIC(10,2),
            rotation NUMERIC(5,2) DEFAULT 0,
            
            -- 多边形字段
            polygon_coordinates TEXT,
            
            -- 圆形字段
            center_x NUMERIC(10,2),
            center_y NUMERIC(10,2),
            radius NUMERIC(10,2),
            
            -- 椭圆字段
            ellipse_center_x NUMERIC(10,2),
            ellipse_center_y NUMERIC(10,2),
            ellipse_radius_x NUMERIC(10,2),
            ellipse_radius_y NUMERIC(10,2),
            ellipse_rotation NUMERIC(5,2),
            
            -- 通用字段
            bounding_box_min_x NUMERIC(10,2),
            bounding_box_min_y NUMERIC(10,2),
            bounding_box_max_x NUMERIC(10,2),
            bounding_box_max_y NUMERIC(10,2),
            
            -- 元数据
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            
            -- 约束：确保每个柜位只有一个几何信息
            CONSTRAINT unique_counter_geometry UNIQUE (counter_id)
        )
        """
        
        cur.execute(create_geometries_table)
        print("✓ 几何信息表创建成功！")
        
        # 2. 创建几何属性表
        create_properties_table = """
        CREATE TABLE IF NOT EXISTS counter_geometry_properties (
            property_id SERIAL PRIMARY KEY,
            geometry_id INTEGER NOT NULL REFERENCES counter_geometries(geometry_id) ON DELETE CASCADE,
            property_name VARCHAR(50) NOT NULL,
            property_value TEXT,
            property_type VARCHAR(20) DEFAULT 'string' CHECK (property_type IN ('string', 'number', 'boolean', 'json')),
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
        
        cur.execute(create_properties_table)
        print("✓ 几何属性表创建成功！")
        
        # 3. 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_counter_geometries_counter_id ON counter_geometries(counter_id)",
            "CREATE INDEX IF NOT EXISTS idx_counter_geometries_shape_type ON counter_geometries(shape_type)",
            "CREATE INDEX IF NOT EXISTS idx_counter_geometries_bounding_box ON counter_geometries(bounding_box_min_x, bounding_box_min_y, bounding_box_max_x, bounding_box_max_y)",
            "CREATE INDEX IF NOT EXISTS idx_geometry_properties_geometry_id ON counter_geometry_properties(geometry_id)",
            "CREATE INDEX IF NOT EXISTS idx_geometry_properties_name ON counter_geometry_properties(property_name)"
        ]
        
        for index_sql in indexes:
            cur.execute(index_sql)
        
        print("✓ 索引创建成功！")
        
        # 4. 添加注释
        comments = [
            "COMMENT ON TABLE counter_geometries IS '柜位几何信息表'",
            "COMMENT ON COLUMN counter_geometries.geometry_id IS '几何信息ID'",
            "COMMENT ON COLUMN counter_geometries.counter_id IS '柜位ID'",
            "COMMENT ON COLUMN counter_geometries.shape_type IS '形状类型：rectangle-矩形, polygon-多边形, circle-圆形, ellipse-椭圆'",
            "COMMENT ON TABLE counter_geometry_properties IS '柜位几何属性表'",
            "COMMENT ON COLUMN counter_geometry_properties.property_id IS '属性ID'",
            "COMMENT ON COLUMN counter_geometry_properties.geometry_id IS '几何信息ID'"
        ]
        
        for comment_sql in comments:
            try:
                cur.execute(comment_sql)
            except Exception as e:
                print(f"注释添加警告: {e}")
        
        print("✓ 注释添加完成！")
        
        # 5. 创建触发器
        trigger_function = """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql'
        """
        
        cur.execute(trigger_function)
        
        trigger = """
        CREATE TRIGGER update_counter_geometries_updated_at 
            BEFORE UPDATE ON counter_geometries 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
        """
        
        cur.execute(trigger)
        print("✓ 触发器创建成功！")
        
        # 6. 创建视图
        view_sql = """
        CREATE OR REPLACE VIEW counters_with_geometry AS
        SELECT 
            c.counter_id,
            c.store_id,
            c.floor_id,
            c.counter_code,
            c.counter_name,
            c.area,
            c.counter_type,
            c.status,
            c.monthly_rent,
            c.management_fee,
            c.deposit,
            c.is_active,
            c.group_code,
            c.facade_image_url,
            c.monthly_revenue,
            c.created_at,
            c.updated_at,
            g.geometry_id,
            g.shape_type as geometry_shape_type,
            g.position_x as geometry_position_x,
            g.position_y as geometry_position_y,
            g.width as geometry_width,
            g.height as geometry_height,
            g.rotation,
            g.polygon_coordinates as geometry_polygon_coordinates,
            g.center_x as geometry_center_x,
            g.center_y as geometry_center_y,
            g.radius,
            g.ellipse_center_x,
            g.ellipse_center_y,
            g.ellipse_radius_x,
            g.ellipse_radius_y,
            g.ellipse_rotation,
            g.bounding_box_min_x as geometry_bounding_box_min_x,
            g.bounding_box_min_y as geometry_bounding_box_min_y,
            g.bounding_box_max_x as geometry_bounding_box_max_x,
            g.bounding_box_max_y as geometry_bounding_box_max_y
        FROM counters c
        LEFT JOIN counter_geometries g ON c.counter_id = g.counter_id
        """
        
        cur.execute(view_sql)
        print("✓ 视图创建成功！")
        
        # 提交事务
        conn.commit()
        print("\n🎉 所有表创建完成！")
        
        # 验证表是否创建成功
        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('counter_geometries', 'counter_geometry_properties')")
        table_count = cur.fetchone()[0]
        print(f"✓ 验证：成功创建 {table_count} 个表")
        
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def migrate_existing_data():
    """迁移现有数据到几何信息表"""
    try:
        conn = psycopg2.connect(
            host='192.168.98.80',
            port=5432,
            database='sales_db',
            user='sales_user',
            password='sales_password_2024'
        )
        cur = conn.cursor()
        
        print("\n开始迁移现有数据...")
        
        # 检查是否有需要迁移的数据
        cur.execute("""
            SELECT COUNT(*) FROM counters 
            WHERE (position_x IS NOT NULL AND position_y IS NOT NULL) 
               OR polygon_coordinates IS NOT NULL
               OR (center_x IS NOT NULL AND center_y IS NOT NULL)
        """)
        count = cur.fetchone()[0]
        
        if count == 0:
            print("✓ 没有需要迁移的数据")
            return
        
        print(f"找到 {count} 个需要迁移的柜位")
        
        # 迁移数据
        migrate_sql = """
        INSERT INTO counter_geometries (
            counter_id, shape_type, position_x, position_y, width, height,
            polygon_coordinates, center_x, center_y,
            bounding_box_min_x, bounding_box_min_y, bounding_box_max_x, bounding_box_max_y,
            created_at, updated_at
        )
        SELECT 
            counter_id,
            COALESCE(shape_type, 'rectangle') as shape_type,
            position_x, position_y, width, height,
            polygon_coordinates,
            center_x, center_y,
            bounding_box_min_x, bounding_box_min_y, bounding_box_max_x, bounding_box_max_y,
            created_at, updated_at
        FROM counters
        WHERE (position_x IS NOT NULL AND position_y IS NOT NULL) 
           OR polygon_coordinates IS NOT NULL
           OR (center_x IS NOT NULL AND center_y IS NOT NULL)
        ON CONFLICT (counter_id) DO NOTHING
        """
        
        cur.execute(migrate_sql)
        migrated_count = cur.rowcount
        
        conn.commit()
        print(f"✓ 成功迁移 {migrated_count} 个柜位的几何信息")
        
    except Exception as e:
        print(f"❌ 迁移数据失败: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def verify_tables():
    """验证表创建结果"""
    try:
        conn = psycopg2.connect(
            host='192.168.98.80',
            port=5432,
            database='sales_db',
            user='sales_user',
            password='sales_password_2024'
        )
        cur = conn.cursor()
        
        print("\n验证表创建结果...")
        
        # 检查表是否存在
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name IN ('counter_geometries', 'counter_geometry_properties')
            ORDER BY table_name
        """)
        tables = cur.fetchall()
        
        print("✓ 创建的表:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # 检查几何信息表数据
        cur.execute("SELECT COUNT(*) FROM counter_geometries")
        geometry_count = cur.fetchone()[0]
        print(f"✓ 几何信息表记录数: {geometry_count}")
        
        # 检查属性表数据
        cur.execute("SELECT COUNT(*) FROM counter_geometry_properties")
        property_count = cur.fetchone()[0]
        print(f"✓ 几何属性表记录数: {property_count}")
        
        # 检查索引
        cur.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename IN ('counter_geometries', 'counter_geometry_properties')
            ORDER BY tablename, indexname
        """)
        indexes = cur.fetchall()
        
        print("✓ 创建的索引:")
        for index in indexes:
            print(f"  - {index[0]}")
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 开始创建几何信息表...")
    create_geometry_tables()
    migrate_existing_data()
    verify_tables()
    print("\n✅ 数据库表结构同步完成！")
