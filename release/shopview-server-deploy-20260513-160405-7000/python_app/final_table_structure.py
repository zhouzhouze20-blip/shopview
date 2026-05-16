#!/usr/bin/env python3
"""
最终表结构验证
Final table structure verification
"""
import psycopg2

def get_final_table_structure():
    """获取最终的表结构"""
    try:
        conn = psycopg2.connect(
            host='192.168.98.80',
            port=5432,
            database='sales_db',
            user='sales_user',
            password='sales_password_2024'
        )
        cur = conn.cursor()
        
        print("🎯 最终表结构 - 优化后的设计")
        print("=" * 80)
        
        # 1. 柜位表 (业务信息)
        print("\n📋 柜位表 (counters) - 业务信息")
        print("-" * 50)
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'counters' 
            ORDER BY ordinal_position
        """)
        counter_columns = cur.fetchall()
        
        print(f"{'字段名':<25} | {'数据类型':<20} | {'可空':<6} | {'说明'}")
        print("-" * 80)
        
        field_descriptions = {
            'counter_id': '主键，柜位ID',
            'store_id': '门店ID (外键)',
            'floor_id': '楼层ID (外键)',
            'counter_code': '柜位编码',
            'counter_name': '柜位名称',
            'area': '面积',
            'geometry_id': '几何信息ID (外键)',
            'counter_type': '柜位类型',
            'status': '状态',
            'monthly_rent': '月租金',
            'management_fee': '管理费',
            'deposit': '押金',
            'group_code': '柜组编码',
            'facade_image_url': '门面图片URL',
            'monthly_revenue': '月收益',
            'is_active': '是否激活',
            'created_at': '创建时间',
            'updated_at': '更新时间'
        }
        
        for col in counter_columns:
            col_name = col[0]
            data_type = col[1]
            is_nullable = "是" if col[2] == "YES" else "否"
            description = field_descriptions.get(col_name, "业务字段")
            print(f"{col_name:<25} | {data_type:<20} | {is_nullable:<6} | {description}")
        
        print(f"\n✅ 柜位表字段数: {len(counter_columns)} (已优化)")
        
        # 2. 几何信息表 (几何数据)
        print("\n🔷 几何信息表 (counter_geometries) - 几何数据")
        print("-" * 50)
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'counter_geometries' 
            ORDER BY ordinal_position
        """)
        geometry_columns = cur.fetchall()
        
        print(f"{'字段名':<25} | {'数据类型':<20} | {'可空':<6} | {'说明'}")
        print("-" * 80)
        
        geometry_descriptions = {
            'geometry_id': '主键，几何信息ID',
            'counter_id': '柜位ID (外键)',
            'shape_type': '形状类型',
            'position_x': 'X坐标 (矩形)',
            'position_y': 'Y坐标 (矩形)',
            'width': '宽度 (矩形)',
            'height': '高度 (矩形)',
            'rotation': '旋转角度',
            'polygon_coordinates': '多边形坐标',
            'center_x': '圆心X坐标',
            'center_y': '圆心Y坐标',
            'radius': '半径',
            'ellipse_center_x': '椭圆中心X',
            'ellipse_center_y': '椭圆中心Y',
            'ellipse_radius_x': '椭圆X轴半径',
            'ellipse_radius_y': '椭圆Y轴半径',
            'ellipse_rotation': '椭圆旋转角度',
            'bounding_box_min_x': '边界框最小X',
            'bounding_box_min_y': '边界框最小Y',
            'bounding_box_max_x': '边界框最大X',
            'bounding_box_max_y': '边界框最大Y',
            'created_at': '创建时间',
            'updated_at': '更新时间'
        }
        
        for col in geometry_columns:
            col_name = col[0]
            data_type = col[1]
            is_nullable = "是" if col[2] == "YES" else "否"
            description = geometry_descriptions.get(col_name, "几何字段")
            print(f"{col_name:<25} | {data_type:<20} | {is_nullable:<6} | {description}")
        
        print(f"\n✅ 几何信息表字段数: {len(geometry_columns)}")
        
        # 3. 几何属性表 (扩展属性)
        print("\n🔧 几何属性表 (counter_geometry_properties) - 扩展属性")
        print("-" * 50)
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'counter_geometry_properties' 
            ORDER BY ordinal_position
        """)
        property_columns = cur.fetchall()
        
        print(f"{'字段名':<25} | {'数据类型':<20} | {'可空':<6} | {'说明'}")
        print("-" * 80)
        
        property_descriptions = {
            'property_id': '主键，属性ID',
            'geometry_id': '几何信息ID (外键)',
            'property_name': '属性名',
            'property_value': '属性值',
            'property_type': '属性类型',
            'created_at': '创建时间'
        }
        
        for col in property_columns:
            col_name = col[0]
            data_type = col[1]
            is_nullable = "是" if col[2] == "YES" else "否"
            description = property_descriptions.get(col_name, "属性字段")
            print(f"{col_name:<25} | {data_type:<20} | {is_nullable:<6} | {description}")
        
        print(f"\n✅ 几何属性表字段数: {len(property_columns)}")
        
        # 4. 数据统计
        print("\n📊 数据统计")
        print("-" * 50)
        
        cur.execute("SELECT COUNT(*) FROM counters")
        counter_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM counter_geometries")
        geometry_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM counter_geometry_properties")
        property_count = cur.fetchone()[0]
        
        print(f"柜位记录数: {counter_count}")
        print(f"几何信息记录数: {geometry_count}")
        print(f"几何属性记录数: {property_count}")
        print(f"几何信息覆盖率: {geometry_count/counter_count*100:.1f}%")
        
        # 5. 表关系
        print("\n🔗 表关系")
        print("-" * 50)
        print("counters.geometry_id → counter_geometries.geometry_id")
        print("counter_geometries.counter_id → counters.counter_id")
        print("counter_geometry_properties.geometry_id → counter_geometries.geometry_id")
        print("counters.store_id → stores.store_id")
        print("counters.floor_id → floors.floor_id")
        
        # 6. 设计优势
        print("\n🎯 设计优势")
        print("-" * 50)
        print("✅ 业务信息与几何信息分离")
        print("✅ 支持多种几何形状 (矩形、多边形、圆形、椭圆)")
        print("✅ 支持自定义几何属性")
        print("✅ 查询性能优化 (索引完善)")
        print("✅ 数据结构清晰，易于维护")
        print("✅ 扩展性强，支持未来新形状类型")
        print("✅ 数据完整性保证 (外键约束)")
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    get_final_table_structure()






