#!/usr/bin/env python3
"""
对比Excel字段和数据库字段
Compare Excel fields with database fields
"""
import pandas as pd
import psycopg2

def compare_fields():
    """对比字段名"""
    try:
        # 1. 读取Excel字段
        excel_path = r"C:\Users\购物中心\Desktop\百货柜位系统\初始资料\柜位信息.xlsx"
        df = pd.read_excel(excel_path)
        excel_fields = list(df.columns)
        
        print("📊 字段对比分析")
        print("=" * 60)
        print("Excel文件字段名:")
        for i, field in enumerate(excel_fields, 1):
            print(f"  {i:2d}. {field}")
        
        # 2. 读取数据库字段
        conn = psycopg2.connect(
            host='192.168.98.80',
            port=5432,
            database='sales_db',
            user='sales_user',
            password='sales_password_2024'
        )
        cur = conn.cursor()
        
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'counters' 
            ORDER BY ordinal_position
        """)
        db_columns = cur.fetchall()
        db_fields = [row[0] for row in db_columns]
        
        print(f"\n数据库counters表字段名:")
        for i, field in enumerate(db_fields, 1):
            print(f"  {i:2d}. {field}")
        
        # 3. 对比分析
        print(f"\n🔍 字段对比分析:")
        print("-" * 40)
        
        # Excel中有但数据库中没有的字段
        excel_only = set(excel_fields) - set(db_fields)
        if excel_only:
            print(f"❌ Excel中有但数据库中没有的字段:")
            for field in excel_only:
                print(f"    - {field}")
        else:
            print("✅ Excel字段在数据库中都有对应")
        
        # 数据库中有但Excel中没有的字段
        db_only = set(db_fields) - set(excel_fields)
        if db_only:
            print(f"\n📋 数据库中有但Excel中没有的字段:")
            for field in db_only:
                print(f"    - {field}")
        
        # 完全匹配的字段
        common_fields = set(excel_fields) & set(db_fields)
        print(f"\n✅ 完全匹配的字段 ({len(common_fields)}个):")
        for field in sorted(common_fields):
            print(f"    - {field}")
        
        # 4. 检查数据类型匹配
        print(f"\n🔧 数据类型检查:")
        print("-" * 40)
        
        for field in common_fields:
            # 从数据库获取字段类型
            db_type = next((row[1] for row in db_columns if row[0] == field), "未知")
            
            # 从Excel获取数据类型
            excel_dtype = str(df[field].dtype)
            
            print(f"  {field}:")
            print(f"    数据库类型: {db_type}")
            print(f"    Excel类型: {excel_dtype}")
            
            # 检查空值情况
            null_count = df[field].isnull().sum()
            if null_count > 0:
                print(f"    空值数量: {null_count}")
            print()
        
        # 5. 建议
        print(f"💡 建议:")
        print("-" * 40)
        
        if excel_only:
            print("1. 需要在导入时处理Excel独有的字段")
        
        if db_only:
            print("2. 需要在导入时为数据库独有字段设置默认值")
        
        print("3. 确保字段名完全匹配，避免映射错误")
        print("4. 检查数据类型转换是否正确")
        
    except Exception as e:
        print(f"❌ 对比失败: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    compare_fields()






