#!/usr/bin/env python3
"""
清空柜位表并重新导入Excel数据
Clear counters table and reimport from Excel
"""
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import pandas as pd

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from models.database import get_db
from models.models import Counter, CounterGroup, Store, Floor
from sqlalchemy.orm import Session


def clear_counters_table():
    """清空柜位表"""
    db = next(get_db())
    try:
        # 删除所有柜位数据
        deleted_count = db.query(Counter).delete()
        db.commit()
        print(f"已删除 {deleted_count} 条柜位数据")
        return True
    except Exception as e:
        db.rollback()
        print(f"删除柜位数据失败: {str(e)}")
        return False
    finally:
        db.close()


def import_counters_from_excel():
    """从Excel文件导入柜位数据"""
    # 读取Excel文件
    excel_path = r'C:\Users\购物中心\Desktop\百货柜位系统\初始资料\柜位信息.xlsx'
    df = pd.read_excel(excel_path)
    
    print(f"Excel文件总行数: {len(df)}")
    print(f"列名: {df.columns.tolist()}")
    
    # 清理数据
    df = df.dropna(subset=['柜组编码'])  # 删除柜组编码为空的行
    print(f"清理后行数: {len(df)}")
    
    db = next(get_db())
    
    try:
        # 获取门店和楼层信息
        stores = db.query(Store).all()
        floors = db.query(Floor).all()
        
        if not stores:
            print("没有找到门店数据，请先创建门店")
            return False
        
        if not floors:
            print("没有找到楼层数据，请先创建楼层")
            return False
        
        # 创建门店名称到ID的映射
        store_name_mapping = {
            '购物中心': 1,
            '百货': 2,
            '新世纪商城': 3,
            '半山书局': 4
        }
        
        # 创建楼层名称到ID的映射
        floor_name_mapping = {}
        for floor in floors:
            floor_name_mapping[floor.floor_name] = floor.floor_id
        
        print(f"门店映射: {store_name_mapping}")
        print(f"楼层映射: {floor_name_mapping}")
        
        imported_count = 0
        updated_groups = 0
        
        for index, row in df.iterrows():
            try:
                # 获取门店ID
                store_name = str(row.get('门店', '购物中心'))
                store_id = store_name_mapping.get(store_name, 1)
                
                # 获取楼层ID
                floor_name = str(row.get('当前楼层', '1F'))
                floor_id = floor_name_mapping.get(floor_name, floors[0].floor_id)
                
                # 柜位信息
                group_code = str(row.get('柜组编码', ''))
                brand_name = str(row.get('品牌厅', ''))
                operation_method = str(row.get('经营模式', ''))
                counter_number = str(row.get('柜位号', ''))
                
                # 处理面积字段，避免非数字值
                try:
                    area_value = row.get('图纸面积', 50.0)
                    if pd.isna(area_value) or str(area_value).strip() == '' or str(area_value) == '面积':
                        area = 50.0
                    else:
                        area = float(area_value)
                except (ValueError, TypeError):
                    area = 50.0
                
                department = str(row.get('部门', ''))
                building = str(row.get('楼栋', ''))
                
                # 生成柜位编码，限制长度为20个字符
                if counter_number and counter_number != 'nan':
                    counter_code = f"{group_code}-{counter_number}"[:20]  # 限制长度为20
                else:
                    counter_code = f"{group_code}-001"[:20]
                
                # 创建柜位
                counter = Counter(
                    store_id=store_id,
                    floor_id=floor_id,
                    counter_code=counter_code,
                    counter_name=(f"{brand_name}柜位" if brand_name and brand_name != 'nan' else f"{group_code}柜位")[:100],  # 限制长度为100
                    area=Decimal(str(area)),
                    position_x=Decimal('100.00'),
                    position_y=Decimal('100.00'),
                    width=Decimal('10.00'),
                    height=Decimal('5.00'),
                    counter_type="标准柜位",
                    status="occupied" if operation_method in ["租赁", "非租赁"] else "vacant",
                    monthly_rent=Decimal('5000.00'),
                    management_fee=Decimal('500.00'),
                    deposit=Decimal('10000.00'),
                    group_code=group_code[:20] if group_code else None,  # 限制长度为20
                    facade_image_url=None,
                    monthly_revenue=Decimal('0.00'),
                    is_active=True
                )
                
                db.add(counter)
                imported_count += 1
                
                # 更新柜组表的经营方式
                if group_code and operation_method in ["租赁", "非租赁", "空厅"]:
                    counter_group = db.query(CounterGroup).filter(
                        CounterGroup.group_code == group_code
                    ).first()
                    
                    if counter_group:
                        # 映射经营方式
                        operation_mapping = {
                            "租赁": "租赁",
                            "非租赁": "联营", 
                            "空厅": "空置"
                        }
                        
                        mapped_operation = operation_mapping.get(operation_method, operation_method)
                        
                        if counter_group.operation_method != mapped_operation:
                            counter_group.operation_method = mapped_operation
                            updated_groups += 1
                            print(f"更新柜组 {group_code} 经营方式: {operation_method} -> {mapped_operation}")
                
                if imported_count % 50 == 0:
                    print(f"已处理 {imported_count} 条记录...")
                    
            except Exception as e:
                print(f"处理第 {index} 行时出错: {e}")
                continue
        
        db.commit()
        print(f"成功导入 {imported_count} 条柜位数据")
        print(f"成功更新 {updated_groups} 个柜组的经营方式")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"导入失败: {str(e)}")
        return False
    finally:
        db.close()


def main():
    """主函数"""
    print("开始清空柜位表并重新导入数据...")
    
    # 1. 清空柜位表
    print("\n1. 清空柜位表...")
    if not clear_counters_table():
        print("清空柜位表失败，退出")
        return
    
    # 2. 重新导入Excel数据
    print("\n2. 重新导入Excel数据...")
    if not import_counters_from_excel():
        print("导入Excel数据失败")
        return
    
    print("\n✅ 数据重新导入完成！")
    
    # 3. 验证结果
    print("\n3. 验证导入结果...")
    db = next(get_db())
    try:
        counter_count = db.query(Counter).count()
        print(f"柜位表数据总数: {counter_count}")
        
        # 显示前5个柜位
        counters = db.query(Counter).limit(5).all()
        print("前5个柜位:")
        for counter in counters:
            print(f"  {counter.counter_code} - {counter.counter_name} (状态: {counter.status}, 柜组: {counter.group_code})")
            
    finally:
        db.close()


if __name__ == "__main__":
    main()






