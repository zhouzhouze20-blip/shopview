#!/usr/bin/env python3
"""
删除现有柜位数据并重新导入
Delete existing counter data and reimport from Excel
"""
import pandas as pd
import psycopg2
import sys
from pathlib import Path

def delete_existing_data():
    """删除现有柜位数据"""
    try:
        conn = psycopg2.connect(
            host='192.168.98.80',
            port=5432,
            database='sales_db',
            user='sales_user',
            password='sales_password_2024'
        )
        cur = conn.cursor()
        
        print("🗑️ 开始删除现有数据...")
        
        # 1. 先清空柜位表的geometry_id字段
        cur.execute("UPDATE counters SET geometry_id = NULL")
        print("✓ 清空柜位表的geometry_id字段")
        
        # 2. 删除几何属性数据
        cur.execute("DELETE FROM counter_geometry_properties")
        property_count = cur.rowcount
        print(f"✓ 删除几何属性记录: {property_count} 条")
        
        # 3. 删除几何信息数据
        cur.execute("DELETE FROM counter_geometries")
        geometry_count = cur.rowcount
        print(f"✓ 删除几何信息记录: {geometry_count} 条")
        
        # 4. 删除柜位数据
        cur.execute("DELETE FROM counters")
        counter_count = cur.rowcount
        print(f"✓ 删除柜位记录: {counter_count} 条")
        
        # 4. 重置序列
        cur.execute("ALTER SEQUENCE counters_counter_id_seq RESTART WITH 1")
        cur.execute("ALTER SEQUENCE counter_geometries_geometry_id_seq RESTART WITH 1")
        cur.execute("ALTER SEQUENCE counter_geometry_properties_property_id_seq RESTART WITH 1")
        print("✓ 重置序列成功")
        
        conn.commit()
        print("✅ 数据删除完成！")
        
    except Exception as e:
        print(f"❌ 删除数据失败: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    
    return True

def import_from_excel():
    """从Excel文件导入数据"""
    excel_path = r"C:\Users\购物中心\Desktop\百货柜位系统\初始资料\柜位信息.xlsx"
    
    if not Path(excel_path).exists():
        print(f"❌ Excel文件不存在: {excel_path}")
        return False
    
    try:
        # 读取Excel文件
        print("📖 读取Excel文件...")
        df = pd.read_excel(excel_path)
        print(f"✓ 读取成功，共 {len(df)} 行数据")
        
        # 保持原始数据，不做清理
        print("📋 保持原始数据，不做清理...")
        # 只转换数据类型，不删除或填充数据
        df['area'] = pd.to_numeric(df['area'], errors='coerce')
        
        print(f"✓ 数据处理完成，共 {len(df)} 行数据")
        
        # 连接数据库
        conn = psycopg2.connect(
            host='192.168.98.80',
            port=5432,
            database='sales_db',
            user='sales_user',
            password='sales_password_2024'
        )
        cur = conn.cursor()
        
        print("📥 开始导入数据...")
        
        imported_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                # 插入柜位数据 - 完全按照Excel原始数据
                insert_sql = """
                INSERT INTO counters (
                    store_id, floor_id, counter_code, counter_name, 
                    area, counter_type, group_code, status, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING counter_id
                """
                
                # 处理空值，保持原始数据
                counter_code = str(row['counter_code']) if pd.notna(row['counter_code']) else None
                counter_name = str(row['counter_name']) if pd.notna(row['counter_name']) else None
                counter_type = str(row['counter_type']) if pd.notna(row['counter_type']) else None
                group_code = str(row['group_code']) if pd.notna(row['group_code']) else None
                area = float(row['area']) if pd.notna(row['area']) else None
                
                cur.execute(insert_sql, (
                    int(row['store_id']),
                    int(row['floor_id']),
                    counter_code[:20] if counter_code else None,  # 限制长度
                    counter_name[:100] if counter_name else None,  # 限制长度
                    area,
                    counter_type[:50] if counter_type else None,  # 限制长度
                    group_code[:20] if group_code else None,  # 限制长度
                    'vacant',  # 默认状态
                    True  # 默认激活
                ))
                
                counter_id = cur.fetchone()[0]
                
                # 创建默认几何信息（矩形）
                geometry_sql = """
                INSERT INTO counter_geometries (
                    counter_id, shape_type, position_x, position_y, 
                    width, height, bounding_box_min_x, bounding_box_min_y,
                    bounding_box_max_x, bounding_box_max_y
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING geometry_id
                """
                
                # 计算默认位置和尺寸
                default_x = 100 + (index % 10) * 60  # 简单的网格布局
                default_y = 100 + (index // 10) * 40
                default_width = 50
                default_height = 30
                
                cur.execute(geometry_sql, (
                    counter_id,
                    'rectangle',
                    default_x,
                    default_y,
                    default_width,
                    default_height,
                    default_x,
                    default_y,
                    default_x + default_width,
                    default_y + default_height
                ))
                
                geometry_id = cur.fetchone()[0]
                
                # 更新柜位表的geometry_id
                cur.execute(
                    "UPDATE counters SET geometry_id = %s WHERE counter_id = %s",
                    (geometry_id, counter_id)
                )
                
                imported_count += 1
                
                if imported_count % 100 == 0:
                    print(f"  已导入 {imported_count} 条记录...")
                
            except Exception as e:
                error_count += 1
                print(f"⚠️ 导入第 {index+1} 行时出错: {e}")
                continue
        
        conn.commit()
        print(f"\n✅ 导入完成！")
        print(f"   成功导入: {imported_count} 条")
        print(f"   导入失败: {error_count} 条")
        
        # 验证导入结果
        cur.execute("SELECT COUNT(*) FROM counters")
        total_counters = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM counter_geometries")
        total_geometries = cur.fetchone()[0]
        
        print(f"\n📊 验证结果:")
        print(f"   柜位记录数: {total_counters}")
        print(f"   几何信息记录数: {total_geometries}")
        
        return True
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def verify_import():
    """验证导入结果"""
    try:
        conn = psycopg2.connect(
            host='192.168.98.80',
            port=5432,
            database='sales_db',
            user='sales_user',
            password='sales_password_2024'
        )
        cur = conn.cursor()
        
        print("\n🔍 验证导入结果...")
        
        # 检查数据完整性
        cur.execute("""
            SELECT 
                COUNT(*) as total_counters,
                COUNT(geometry_id) as counters_with_geometry
            FROM counters
        """)
        stats = cur.fetchone()
        
        print(f"总柜位数: {stats[0]}")
        print(f"有几何信息的柜位数: {stats[1]}")
        print(f"几何信息覆盖率: {stats[1]/stats[0]*100:.1f}%")
        
        # 显示样本数据
        cur.execute("""
            SELECT 
                c.counter_id, c.counter_code, c.counter_name, 
                c.area, c.counter_type, c.group_code,
                g.shape_type, g.position_x, g.position_y, g.width, g.height
            FROM counters c
            LEFT JOIN counter_geometries g ON c.geometry_id = g.geometry_id
            ORDER BY c.counter_id
            LIMIT 5
        """)
        
        sample_data = cur.fetchall()
        print("\n📋 样本数据:")
        print("ID | 编码 | 名称 | 面积 | 类型 | 柜组 | 形状 | 位置 | 尺寸")
        print("-" * 80)
        for row in sample_data:
            print(f"{row[0]:2d} | {row[1]:4s} | {row[2][:8]:8s} | {row[3]:4.0f} | {row[4][:4]:4s} | {row[5][:6]:6s} | {row[6]:8s} | ({row[7]:.0f},{row[8]:.0f}) | {row[9]:.0f}x{row[10]:.0f}")
        
    except Exception as e:
        print(f"验证失败: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🔄 开始重新导入柜位数据...")
    print("=" * 60)
    
    # 1. 删除现有数据
    if not delete_existing_data():
        print("❌ 删除数据失败，停止导入")
        sys.exit(1)
    
    # 2. 导入新数据
    if not import_from_excel():
        print("❌ 导入数据失败")
        sys.exit(1)
    
    # 3. 验证结果
    verify_import()
    
    print("\n🎉 柜位数据重新导入完成！")
