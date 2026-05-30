#!/usr/bin/env python3
"""
从Excel文件导入柜位数据
"""
import pandas as pd
import os
from models.database import get_db
from models.models import Counter
from sqlalchemy.orm import Session
from decimal import Decimal

def import_counters_from_excel():
    """从Excel文件导入柜位数据"""
    excel_path = r"C:\Users\购物中心\Desktop\百货柜位系统\初始资料\柜位信息.xlsx"
    
    try:
        print("🔍 开始导入柜位数据...")
        
        # 检查文件是否存在
        if not os.path.exists(excel_path):
            print(f"❌ 文件不存在: {excel_path}")
            return False
        
        # 读取Excel文件
        df = pd.read_excel(excel_path)
        print(f"📊 读取到 {len(df)} 行数据")
        
        # 获取数据库连接
        db = next(get_db())
        
        # 清空现有数据
        db.query(Counter).delete()
        db.commit()
        print("✅ 已清空现有数据")
        
        # 导入数据
        success_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                # 处理字段长度限制
                counter_code = str(row['counter_code'])[:20] if pd.notna(row['counter_code']) else None
                counter_name = str(row['counter_name'])[:100] if pd.notna(row['counter_name']) else None
                counter_type = str(row['counter_type'])[:50] if pd.notna(row['counter_type']) else None
                group_code = str(row['group_code'])[:20] if pd.notna(row['group_code']) else None
                
                # 创建柜位对象
                counter = Counter(
                    store_id=int(row['store_id']),
                    floor_id=int(row['floor_id']),
                    counter_code=counter_code,
                    counter_name=counter_name,
                    area=Decimal(str(row['area'])) if pd.notna(row['area']) else None,
                    counter_type=counter_type,
                    group_code=group_code,
                    status='vacant',  # 默认状态为空置
                    is_active=True,   # 默认启用
                    monthly_rent=Decimal('0'),  # 默认月租金为0
                    management_fee=Decimal('0'),  # 默认管理费为0
                    deposit=Decimal('0'),  # 默认押金为0
                    monthly_revenue=Decimal('0')  # 默认月收益为0
                )
                
                db.add(counter)
                success_count += 1
                
                if (index + 1) % 100 == 0:
                    print(f"📝 已处理 {index + 1} 行数据...")
                    
            except Exception as e:
                print(f"❌ 第 {index + 1} 行数据导入失败: {e}")
                error_count += 1
                continue
        
        # 提交事务
        db.commit()
        print(f"✅ 数据导入完成！")
        print(f"📊 成功导入: {success_count} 条")
        print(f"📊 失败: {error_count} 条")
        
        # 验证导入结果
        total_count = db.query(Counter).count()
        print(f"📊 数据库中共有: {total_count} 条柜位记录")
        
        return True
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import_counters_from_excel()