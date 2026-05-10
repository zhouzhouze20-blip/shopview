#!/usr/bin/env python3
"""
从Excel文件重新导入柜位数据
"""
import pandas as pd
import os
from datetime import datetime
from models.database import get_db
from models.models import Counter, Store, Floor
from sqlalchemy import text

def backup_current_data():
    """备份当前柜位数据"""
    print("=== 备份当前柜位数据 ===")
    db = next(get_db())
    
    # 查询所有柜位数据
    counters = db.query(Counter).all()
    
    # 创建备份文件
    backup_data = []
    for counter in counters:
        backup_data.append({
            'counter_id': counter.counter_id,
            'store_id': counter.store_id,
            'floor_id': counter.floor_id,
            'counter_code': counter.counter_code,
            'counter_name': counter.counter_name,
            'area': float(counter.area) if counter.area else None,
            'counter_type': counter.counter_type,
            'status': counter.status,
            'monthly_rent': float(counter.monthly_rent) if counter.monthly_rent else None,
            'management_fee': float(counter.management_fee) if counter.management_fee else None,
            'deposit': float(counter.deposit) if counter.deposit else None,
            'group_code': counter.group_code,
            'facade_image_url': counter.facade_image_url,
            'monthly_revenue': float(counter.monthly_revenue) if counter.monthly_revenue else None,
            'is_active': counter.is_active,
            'created_at': counter.created_at.isoformat() if counter.created_at else None,
            'updated_at': counter.updated_at.isoformat() if counter.updated_at else None
        })
    
    # 保存为CSV文件
    backup_df = pd.DataFrame(backup_data)
    backup_filename = f"counter_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    backup_df.to_csv(backup_filename, index=False, encoding='utf-8-sig')
    print(f"备份数据已保存到: {backup_filename}")
    print(f"备份记录数: {len(backup_data)}")
    
    return backup_filename

def clear_counters_table():
    """清空柜位表"""
    print("\n=== 清空柜位表 ===")
    db = next(get_db())
    
    # 删除所有柜位记录
    deleted_count = db.query(Counter).delete()
    db.commit()
    
    print(f"已删除 {deleted_count} 条柜位记录")
    
    # 验证清空结果
    remaining_count = db.query(Counter).count()
    print(f"剩余记录数: {remaining_count}")

def import_from_excel():
    """从Excel文件导入数据"""
    print("\n=== 从Excel文件导入数据 ===")
    
    # Excel文件路径
    excel_path = r'C:\Users\购物中心\Desktop\百货柜位系统\初始资料\柜位信息.xlsx'
    
    if not os.path.exists(excel_path):
        print(f"Excel文件不存在: {excel_path}")
        return False
    
    # 读取Excel文件
    df = pd.read_excel(excel_path)
    print(f"Excel文件行数: {len(df)}")
    print(f"Excel字段: {list(df.columns)}")
    
    # 检查必需字段
    required_fields = ['floor_id', 'store_id', 'counter_name', 'counter_code', 'area']
    missing_fields = [field for field in required_fields if field not in df.columns]
    if missing_fields:
        print(f"缺少必需字段: {missing_fields}")
        return False
    
    # 获取数据库连接
    db = next(get_db())
    
    # 验证门店和楼层是否存在
    stores = {store.store_id: store for store in db.query(Store).all()}
    floors = {floor.floor_id: floor for store in stores.values() for floor in store.floors}
    
    print(f"数据库中的门店: {list(stores.keys())}")
    print(f"数据库中的楼层: {list(floors.keys())}")
    
    # 处理数据
    imported_count = 0
    error_count = 0
    
    for index, row in df.iterrows():
        try:
            # 检查门店是否存在
            store_id = int(row['store_id'])
            if store_id not in stores:
                print(f"第{index+1}行: 门店ID {store_id} 不存在，跳过")
                error_count += 1
                continue
            
            # 检查楼层是否存在
            floor_id = int(row['floor_id'])
            if floor_id not in floors:
                print(f"第{index+1}行: 楼层ID {floor_id} 不存在，跳过")
                error_count += 1
                continue
            
            # 创建柜位记录
            counter = Counter(
                store_id=store_id,
                floor_id=floor_id,
                counter_code=str(row['counter_code']) if pd.notna(row['counter_code']) else None,
                counter_name=str(row['counter_name']) if pd.notna(row['counter_name']) else None,
                area=float(row['area']) if pd.notna(row['area']) else None,
                counter_type=str(row['counter_type']) if pd.notna(row['counter_type']) else '租赁',
                status='vacant',  # 默认状态为空置
                group_code=str(row['group_code']) if pd.notna(row['group_code']) else None,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            db.add(counter)
            imported_count += 1
            
            if imported_count % 100 == 0:
                print(f"已处理 {imported_count} 条记录...")
                
        except Exception as e:
            print(f"第{index+1}行处理失败: {e}")
            error_count += 1
            continue
    
    # 提交事务
    try:
        db.commit()
        print(f"\n导入完成！")
        print(f"成功导入: {imported_count} 条记录")
        print(f"失败记录: {error_count} 条")
    except Exception as e:
        print(f"提交事务失败: {e}")
        db.rollback()
        return False
    
    return True

def verify_import():
    """验证导入结果"""
    print("\n=== 验证导入结果 ===")
    db = next(get_db())
    
    # 统计总记录数
    total_count = db.query(Counter).count()
    print(f"总柜位数: {total_count}")
    
    # 按门店统计
    stores = db.query(Store).all()
    for store in stores:
        count = db.query(Counter).filter(Counter.store_id == store.store_id).count()
        print(f"{store.store_name}: {count} 个柜位")
    
    # 按状态统计
    status_stats = db.query(Counter.status, db.func.count(Counter.counter_id)).group_by(Counter.status).all()
    print("\n按状态统计:")
    for status, count in status_stats:
        print(f"  {status}: {count} 个")

def main():
    """主函数"""
    print("开始重新导入柜位数据...")
    
    # 1. 备份当前数据
    backup_file = backup_current_data()
    
    # 2. 清空柜位表
    clear_counters_table()
    
    # 3. 从Excel导入数据
    success = import_from_excel()
    
    if success:
        # 4. 验证导入结果
        verify_import()
        print(f"\n重新导入完成！备份文件: {backup_file}")
    else:
        print("\n导入失败！")

if __name__ == "__main__":
    main()
