#!/usr/bin/env python3
"""
验证导入的数据质量
Verify imported data quality
"""
import psycopg2
import pandas as pd

def verify_imported_data():
    """验证导入的数据质量"""
    try:
        conn = psycopg2.connect(
            host='192.168.98.80',
            port=5432,
            database='sales_db',
            user='sales_user',
            password='sales_password_2024'
        )
        cur = conn.cursor()
        
        print("🔍 验证导入数据质量")
        print("=" * 60)
        
        # 1. 基本统计
        cur.execute("SELECT COUNT(*) FROM counters")
        total_counters = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM counter_geometries")
        total_geometries = cur.fetchone()[0]
        
        print(f"📊 数据统计:")
        print(f"   柜位记录数: {total_counters}")
        print(f"   几何信息记录数: {total_geometries}")
        print(f"   几何信息覆盖率: {total_geometries/total_counters*100:.1f}%")
        
        # 2. 字段完整性检查
        print(f"\n📋 字段完整性检查:")
        
        # 检查必填字段
        cur.execute("SELECT COUNT(*) FROM counters WHERE counter_code IS NULL OR counter_code = ''")
        empty_codes = cur.fetchone()[0]
        print(f"   空柜位编码: {empty_codes}")
        
        cur.execute("SELECT COUNT(*) FROM counters WHERE counter_name IS NULL OR counter_name = ''")
        empty_names = cur.fetchone()[0]
        print(f"   空柜位名称: {empty_names}")
        
        cur.execute("SELECT COUNT(*) FROM counters WHERE area IS NULL OR area <= 0")
        invalid_areas = cur.fetchone()[0]
        print(f"   无效面积: {invalid_areas}")
        
        # 3. 数据类型分布
        print(f"\n📈 数据类型分布:")
        
        cur.execute("SELECT counter_type, COUNT(*) FROM counters GROUP BY counter_type ORDER BY COUNT(*) DESC")
        type_dist = cur.fetchall()
        print("   柜位类型分布:")
        for type_name, count in type_dist:
            print(f"     {type_name}: {count} 个")
        
        cur.execute("SELECT group_code, COUNT(*) FROM counters WHERE group_code IS NOT NULL AND group_code != '' GROUP BY group_code ORDER BY COUNT(*) DESC LIMIT 10")
        group_dist = cur.fetchall()
        print("   柜组分布 (前10):")
        for group_code, count in group_dist:
            print(f"     {group_code}: {count} 个")
        
        # 4. 面积统计
        print(f"\n📏 面积统计:")
        
        cur.execute("SELECT MIN(area), MAX(area), AVG(area) FROM counters WHERE area IS NOT NULL")
        area_stats = cur.fetchone()
        print(f"   最小面积: {area_stats[0]:.1f} 平方米")
        print(f"   最大面积: {area_stats[1]:.1f} 平方米")
        print(f"   平均面积: {area_stats[2]:.1f} 平方米")
        
        # 5. 几何信息检查
        print(f"\n🔷 几何信息检查:")
        
        cur.execute("SELECT shape_type, COUNT(*) FROM counter_geometries GROUP BY shape_type")
        shape_dist = cur.fetchall()
        print("   形状类型分布:")
        for shape_type, count in shape_dist:
            print(f"     {shape_type}: {count} 个")
        
        # 6. 门店和楼层分布
        print(f"\n🏢 门店和楼层分布:")
        
        cur.execute("""
            SELECT s.store_name, f.floor_name, COUNT(c.counter_id) as counter_count
            FROM counters c
            JOIN stores s ON c.store_id = s.store_id
            JOIN floors f ON c.floor_id = f.floor_id
            GROUP BY s.store_name, f.floor_name
            ORDER BY counter_count DESC
        """)
        store_floor_dist = cur.fetchall()
        print("   门店-楼层分布:")
        for store_name, floor_name, count in store_floor_dist:
            print(f"     {store_name} - {floor_name}: {count} 个")
        
        # 7. 样本数据展示
        print(f"\n📋 样本数据展示:")
        
        cur.execute("""
            SELECT 
                c.counter_id, c.counter_code, c.counter_name, 
                c.area, c.counter_type, c.group_code,
                s.store_name, f.floor_name,
                g.shape_type, g.position_x, g.position_y, g.width, g.height
            FROM counters c
            JOIN stores s ON c.store_id = s.store_id
            JOIN floors f ON c.floor_id = f.floor_id
            LEFT JOIN counter_geometries g ON c.geometry_id = g.geometry_id
            ORDER BY c.counter_id
            LIMIT 10
        """)
        
        sample_data = cur.fetchall()
        print("   ID | 编码 | 名称 | 面积 | 类型 | 柜组 | 门店 | 楼层 | 形状 | 位置 | 尺寸")
        print("   " + "-" * 100)
        for row in sample_data:
            print(f"   {row[0]:2d} | {row[1]:4s} | {row[2][:8]:8s} | {row[3]:4.0f} | {row[4][:4]:4s} | {row[5][:6]:6s} | {row[6][:4]:4s} | {row[7][:4]:4s} | {row[8]:8s} | ({row[9]:.0f},{row[10]:.0f}) | {row[11]:.0f}x{row[12]:.0f}")
        
        # 8. 数据质量评分
        print(f"\n⭐ 数据质量评分:")
        
        quality_score = 100
        if empty_codes > 0:
            quality_score -= 20
            print("   ❌ 存在空柜位编码 (-20分)")
        else:
            print("   ✅ 柜位编码完整")
        
        if empty_names > 0:
            quality_score -= 10
            print("   ❌ 存在空柜位名称 (-10分)")
        else:
            print("   ✅ 柜位名称完整")
        
        if invalid_areas > 0:
            quality_score -= 15
            print("   ❌ 存在无效面积 (-15分)")
        else:
            print("   ✅ 面积数据有效")
        
        if total_geometries != total_counters:
            quality_score -= 25
            print("   ❌ 几何信息不完整 (-25分)")
        else:
            print("   ✅ 几何信息完整")
        
        print(f"\n🎯 总体质量评分: {quality_score}/100")
        
        if quality_score >= 90:
            print("   🌟 数据质量优秀！")
        elif quality_score >= 80:
            print("   👍 数据质量良好")
        elif quality_score >= 70:
            print("   ⚠️ 数据质量一般，建议优化")
        else:
            print("   ❌ 数据质量较差，需要修复")
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    verify_imported_data()






