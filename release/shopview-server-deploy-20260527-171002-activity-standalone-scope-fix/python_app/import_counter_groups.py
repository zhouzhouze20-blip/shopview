#!/usr/bin/env python3
"""
柜组数据导入脚本
Counter Groups Data Import Script
"""
import csv
import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from models.database import get_db
from models.models import CounterGroup
from sqlalchemy.orm import Session


def import_from_csv(file_path: str, db: Session) -> int:
    """从CSV文件导入柜组数据"""
    imported_count = 0
    
    # 尝试不同的编码格式
    encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']
    file_content = None
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                file_content = file.read()
            print(f"成功使用 {encoding} 编码读取文件")
            break
        except UnicodeDecodeError:
            continue
    
    if file_content is None:
        print("无法读取文件，尝试了所有编码格式")
        return 0
    
    try:
        from io import StringIO
        import csv
        file_obj = StringIO(file_content)
        reader = csv.DictReader(file_obj)
        
        for row in reader:
            # 检查是否已存在相同group_code的记录
            existing = db.query(CounterGroup).filter(
                CounterGroup.group_code == row['group_code']
            ).first()
            
            if existing:
                print(f"跳过已存在的柜组: {row['group_code']} - {row['group_name']}")
                continue
            
            # 门店编码到ID的映射
            store_code_mapping = {
                '601': 1,  # 常州购物中心
                '602': 2,  # 常州百货
                '603': 3,  # 常州新世纪商城
                '604': 4,  # 常州半山书局
            }
            
            # 获取门店ID
            store_code = str(row.get('store_id', '601'))
            store_id = store_code_mapping.get(store_code, 1)  # 默认使用门店1
            
            # 创建新记录
            counter_group = CounterGroup(
                group_code=row['group_code'],
                group_name=row['group_name'],
                store_id=store_id,
                department_code=row.get('department_code'),
                department_name=row.get('department_name'),
                area_code=row.get('area_code'),
                area_name=row.get('area_name'),
                category_code=row.get('category_code'),
                category_name=row.get('category_name'),
                operation_method=row.get('operation_method'),
                brand_name=row.get('brand_name'),
                is_active=row.get('is_active', 'true').lower() == 'true',
                erp_sync_time=datetime.now()
            )
            
            db.add(counter_group)
            imported_count += 1
            print(f"导入柜组: {row['group_code']} - {row['group_name']}")
        
        db.commit()
        print(f"成功导入 {imported_count} 条柜组数据")
        return imported_count
        
    except Exception as e:
        db.rollback()
        print(f"导入失败: {str(e)}")
        return 0


def import_from_json(file_path: str, db: Session) -> int:
    """从JSON文件导入柜组数据"""
    imported_count = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
            if not isinstance(data, list):
                print("JSON文件格式错误：根元素应该是数组")
                return 0
            
            for item in data:
                # 检查是否已存在相同group_code的记录
                existing = db.query(CounterGroup).filter(
                    CounterGroup.group_code == item['group_code']
                ).first()
                
                if existing:
                    print(f"跳过已存在的柜组: {item['group_code']} - {item['group_name']}")
                    continue
                
                # 创建新记录
                counter_group = CounterGroup(
                    group_code=item['group_code'],
                    group_name=item['group_name'],
                    store_id=item.get('store_id', 1),
                    department_code=item.get('department_code'),
                    department_name=item.get('department_name'),
                    area_code=item.get('area_code'),
                    area_name=item.get('area_name'),
                    category_code=item.get('category_code'),
                    category_name=item.get('category_name'),
                    operation_method=item.get('operation_method'),
                    brand_name=item.get('brand_name'),
                    is_active=item.get('is_active', True),
                    erp_sync_time=datetime.now()
                )
                
                db.add(counter_group)
                imported_count += 1
                print(f"导入柜组: {item['group_code']} - {item['group_name']}")
        
        db.commit()
        print(f"成功导入 {imported_count} 条柜组数据")
        return imported_count
        
    except Exception as e:
        db.rollback()
        print(f"导入失败: {str(e)}")
        return 0


def import_from_data_list(data_list: List[Dict[str, Any]], db: Session) -> int:
    """从数据列表导入柜组数据"""
    imported_count = 0
    
    try:
        for item in data_list:
            # 检查是否已存在相同group_code的记录
            existing = db.query(CounterGroup).filter(
                CounterGroup.group_code == item['group_code']
            ).first()
            
            if existing:
                print(f"跳过已存在的柜组: {item['group_code']} - {item['group_name']}")
                continue
            
            # 创建新记录
            counter_group = CounterGroup(
                group_code=item['group_code'],
                group_name=item['group_name'],
                store_id=item.get('store_id', 1),
                department_code=item.get('department_code'),
                department_name=item.get('department_name'),
                area_code=item.get('area_code'),
                area_name=item.get('area_name'),
                category_code=item.get('category_code'),
                category_name=item.get('category_name'),
                operation_method=item.get('operation_method'),
                brand_name=item.get('brand_name'),
                is_active=item.get('is_active', True),
                erp_sync_time=datetime.now()
            )
            
            db.add(counter_group)
            imported_count += 1
            print(f"导入柜组: {item['group_code']} - {item['group_name']}")
        
        db.commit()
        print(f"成功导入 {imported_count} 条柜组数据")
        return imported_count
        
    except Exception as e:
        db.rollback()
        print(f"导入失败: {str(e)}")
        return 0


def list_existing_groups(db: Session):
    """列出现有的柜组数据"""
    groups = db.query(CounterGroup).all()
    
    if not groups:
        print("数据库中没有柜组数据")
        return
    
    print(f"\n现有柜组数据 ({len(groups)} 条):")
    print("-" * 100)
    print(f"{'柜组编码':<12} {'柜组名称':<15} {'门店ID':<8} {'部门':<12} {'区域':<12} {'类别':<12} {'经营方式':<8} {'品牌':<12}")
    print("-" * 100)
    
    for group in groups:
        print(f"{group.group_code:<12} {group.group_name:<15} {group.store_id:<8} {group.department_name or '-':<12} {group.area_name or '-':<12} {group.category_name or '-':<12} {group.operation_method or '-':<8} {group.brand_name or '-':<12}")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python import_counter_groups.py csv <文件路径>")
        print("  python import_counter_groups.py json <文件路径>")
        print("  python import_counter_groups.py list")
        print("\n示例:")
        print("  python import_counter_groups.py csv counter_groups.csv")
        print("  python import_counter_groups.py json counter_groups.json")
        print("  python import_counter_groups.py list")
        return
    
    command = sys.argv[1]
    
    # 获取数据库连接
    db = next(get_db())
    
    try:
        if command == "csv" and len(sys.argv) > 2:
            file_path = sys.argv[2]
            import_from_csv(file_path, db)
        elif command == "json" and len(sys.argv) > 2:
            file_path = sys.argv[2]
            import_from_json(file_path, db)
        elif command == "list":
            list_existing_groups(db)
        else:
            print("无效的命令或参数")
    except Exception as e:
        print(f"执行失败: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
