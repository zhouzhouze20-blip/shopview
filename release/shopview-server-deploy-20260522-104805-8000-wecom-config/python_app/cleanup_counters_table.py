#!/usr/bin/env python3
"""
清理柜位表，移除冗余的几何字段
Clean up counters table by removing redundant geometry fields
"""
import psycopg2

def cleanup_counters_table():
    """清理柜位表，移除几何字段"""
    try:
        conn = psycopg2.connect(
            host='192.168.98.80',
            port=5432,
            database='sales_db',
            user='sales_user',
            password='sales_password_2024'
        )
        cur = conn.cursor()
        
        print("开始清理柜位表，移除冗余的几何字段...")
        
        # 1. 首先添加 geometry_id 字段（如果不存在）
        print("1. 添加 geometry_id 字段...")
        try:
            cur.execute("""
                ALTER TABLE counters 
                ADD COLUMN geometry_id INTEGER REFERENCES counter_geometries(geometry_id)
            """)
            print("✓ geometry_id 字段添加成功")
        except Exception as e:
            if "already exists" in str(e) or "duplicate column" in str(e):
                print("✓ geometry_id 字段已存在")
            else:
                print(f"⚠ geometry_id 字段添加警告: {e}")
        
        # 2. 更新 geometry_id 字段，从几何信息表获取
        print("2. 更新 geometry_id 字段...")
        cur.execute("""
            UPDATE counters 
            SET geometry_id = cg.geometry_id
            FROM counter_geometries cg
            WHERE counters.counter_id = cg.counter_id
        """)
        updated_count = cur.rowcount
        print(f"✓ 更新了 {updated_count} 个柜位的 geometry_id")
        
        # 3. 移除冗余的几何字段
        geometry_fields_to_remove = [
            'position_x',
            'position_y', 
            'width',
            'height',
            'shape_type',
            'polygon_coordinates',
            'center_x',
            'center_y',
            'bounding_box_min_x',
            'bounding_box_min_y',
            'bounding_box_max_x',
            'bounding_box_max_y'
        ]
        
        print("3. 移除冗余的几何字段...")
        for field in geometry_fields_to_remove:
            try:
                cur.execute(f"ALTER TABLE counters DROP COLUMN IF EXISTS {field}")
                print(f"✓ 移除字段: {field}")
            except Exception as e:
                print(f"⚠ 移除字段 {field} 警告: {e}")
        
        # 4. 添加注释
        print("4. 添加字段注释...")
        try:
            cur.execute("COMMENT ON COLUMN counters.geometry_id IS '几何信息ID，关联counter_geometries表'")
            print("✓ 字段注释添加成功")
        except Exception as e:
            print(f"⚠ 注释添加警告: {e}")
        
        # 5. 创建索引
        print("5. 创建索引...")
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_counters_geometry_id ON counters(geometry_id)")
            print("✓ geometry_id 索引创建成功")
        except Exception as e:
            print(f"⚠ 索引创建警告: {e}")
        
        # 提交事务
        conn.commit()
        print("\n🎉 柜位表清理完成！")
        
        # 6. 验证清理结果
        print("\n验证清理结果...")
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'counters' 
            ORDER BY ordinal_position
        """)
        remaining_columns = cur.fetchall()
        
        print(f"清理后柜位表字段数: {len(remaining_columns)}")
        print("剩余字段:")
        for col in remaining_columns:
            print(f"  - {col[0]}: {col[1]}")
        
        # 检查几何关联
        cur.execute("""
            SELECT 
                COUNT(*) as total_counters,
                COUNT(geometry_id) as counters_with_geometry
            FROM counters
        """)
        stats = cur.fetchone()
        print(f"\n数据统计:")
        print(f"  总柜位数: {stats[0]}")
        print(f"  有几何信息的柜位数: {stats[1]}")
        print(f"  几何信息覆盖率: {stats[1]/stats[0]*100:.1f}%")
        
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    
    return True

def verify_cleanup():
    """验证清理结果"""
    try:
        conn = psycopg2.connect(
            host='192.168.98.80',
            port=5432,
            database='sales_db',
            user='sales_user',
            password='sales_password_2024'
        )
        cur = conn.cursor()
        
        print("\n=== 清理验证 ===")
        
        # 检查柜位表结构
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'counters' 
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        
        print(f"柜位表字段数: {len(columns)}")
        print("字段列表:")
        for col in columns:
            print(f"  {col[0]}: {col[1]}")
        
        # 检查几何字段是否已移除
        geometry_fields = ['position_x', 'position_y', 'width', 'height', 'shape_type', 'polygon_coordinates']
        remaining_geometry_fields = [col[0] for col in columns if col[0] in geometry_fields]
        
        if remaining_geometry_fields:
            print(f"⚠ 警告: 仍有几何字段未移除: {remaining_geometry_fields}")
        else:
            print("✓ 所有几何字段已成功移除")
        
        # 检查 geometry_id 字段
        has_geometry_id = any(col[0] == 'geometry_id' for col in columns)
        if has_geometry_id:
            print("✓ geometry_id 字段存在")
        else:
            print("❌ geometry_id 字段不存在")
        
        # 检查数据完整性
        cur.execute("""
            SELECT 
                c.counter_id,
                c.counter_code,
                c.geometry_id,
                cg.shape_type
            FROM counters c
            LEFT JOIN counter_geometries cg ON c.geometry_id = cg.geometry_id
            LIMIT 5
        """)
        sample_data = cur.fetchall()
        
        print("\n样本数据:")
        for row in sample_data:
            print(f"  柜位ID: {row[0]}, 编码: {row[1]}, 几何ID: {row[2]}, 形状: {row[3]}")
        
    except Exception as e:
        print(f"验证失败: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🧹 开始清理柜位表...")
    success = cleanup_counters_table()
    if success:
        verify_cleanup()
        print("\n✅ 柜位表清理完成！现在柜位表只保留业务字段和 geometry_id 关联字段。")
    else:
        print("\n❌ 柜位表清理失败！")






