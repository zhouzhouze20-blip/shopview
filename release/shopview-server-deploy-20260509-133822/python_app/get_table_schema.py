#!/usr/bin/env python3
"""
获取表结构信息
Get table schema information
"""
import psycopg2

def get_counters_table_schema():
    """获取柜位表结构"""
    try:
        conn = psycopg2.connect(
            host='192.168.98.80',
            port=5432,
            database='sales_db',
            user='sales_user',
            password='sales_password_2024'
        )
        cur = conn.cursor()
        
        print("=== 柜位表 (counters) 字段结构 ===")
        print()
        
        # 获取字段信息
        cur.execute("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable, 
                column_default,
                character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = 'counters' 
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        
        print(f"{'字段名':<25} | {'数据类型':<20} | {'可空':<6} | {'长度':<8} | {'默认值'}")
        print("-" * 80)
        
        for col in columns:
            col_name = col[0]
            data_type = col[1]
            is_nullable = "是" if col[2] == "YES" else "否"
            default_value = col[3] or "无"
            max_length = col[4] or ""
            
            # 处理数据类型显示
            if max_length:
                data_type_display = f"{data_type}({max_length})"
            else:
                data_type_display = data_type
            
            print(f"{col_name:<25} | {data_type_display:<20} | {is_nullable:<6} | {str(max_length):<8} | {default_value}")
        
        print()
        print(f"总字段数: {len(columns)}")
        
        # 获取几何信息表结构
        print("\n" + "="*60)
        print("=== 几何信息表 (counter_geometries) 字段结构 ===")
        print()
        
        cur.execute("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable, 
                column_default,
                character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = 'counter_geometries' 
            ORDER BY ordinal_position
        """)
        geometry_columns = cur.fetchall()
        
        print(f"{'字段名':<25} | {'数据类型':<20} | {'可空':<6} | {'长度':<8} | {'默认值'}")
        print("-" * 80)
        
        for col in geometry_columns:
            col_name = col[0]
            data_type = col[1]
            is_nullable = "是" if col[2] == "YES" else "否"
            default_value = col[3] or "无"
            max_length = col[4] or ""
            
            # 处理数据类型显示
            if max_length:
                data_type_display = f"{data_type}({max_length})"
            else:
                data_type_display = data_type
            
            print(f"{col_name:<25} | {data_type_display:<20} | {is_nullable:<6} | {str(max_length):<8} | {default_value}")
        
        print()
        print(f"几何信息表字段数: {len(geometry_columns)}")
        
        # 获取几何属性表结构
        print("\n" + "="*60)
        print("=== 几何属性表 (counter_geometry_properties) 字段结构 ===")
        print()
        
        cur.execute("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable, 
                column_default,
                character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = 'counter_geometry_properties' 
            ORDER BY ordinal_position
        """)
        property_columns = cur.fetchall()
        
        print(f"{'字段名':<25} | {'数据类型':<20} | {'可空':<6} | {'长度':<8} | {'默认值'}")
        print("-" * 80)
        
        for col in property_columns:
            col_name = col[0]
            data_type = col[1]
            is_nullable = "是" if col[2] == "YES" else "否"
            default_value = col[3] or "无"
            max_length = col[4] or ""
            
            # 处理数据类型显示
            if max_length:
                data_type_display = f"{data_type}({max_length})"
            else:
                data_type_display = data_type
            
            print(f"{col_name:<25} | {data_type_display:<20} | {is_nullable:<6} | {str(max_length):<8} | {default_value}")
        
        print()
        print(f"几何属性表字段数: {len(property_columns)}")
        
        # 获取表关系信息
        print("\n" + "="*60)
        print("=== 表关系信息 ===")
        print()
        
        cur.execute("""
            SELECT 
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name IN ('counters', 'counter_geometries', 'counter_geometry_properties')
            ORDER BY tc.table_name, kcu.column_name
        """)
        foreign_keys = cur.fetchall()
        
        if foreign_keys:
            print(f"{'表名':<25} | {'字段名':<20} | {'关联表':<25} | {'关联字段'}")
            print("-" * 80)
            for fk in foreign_keys:
                print(f"{fk[0]:<25} | {fk[1]:<20} | {fk[2]:<25} | {fk[3]}")
        else:
            print("没有找到外键关系")
        
    except Exception as e:
        print(f"查询失败: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    get_counters_table_schema()






