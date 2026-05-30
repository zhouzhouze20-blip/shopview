#!/usr/bin/env python3
"""
从聊天数据导入柜组数据
Import counter groups from chat data
"""
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from models.database import get_db
from models.models import CounterGroup
from sqlalchemy.orm import Session


def import_counter_groups_from_chat(data_list):
    """
    从聊天中提供的数据导入柜组
    
    Args:
        data_list: 柜组数据列表，每个元素包含柜组信息
    """
    db = next(get_db())
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
                department_code=item.get('department_code'),
                department_name=item.get('department_name'),
                operation_method=item.get('operation_method'),
                brand_name=item.get('brand_name'),
                monthly_revenue=Decimal(str(item['monthly_revenue'])) if item.get('monthly_revenue') else None,
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
    finally:
        db.close()


if __name__ == "__main__":
    # 示例数据
    sample_data = [
        {
            "group_code": "G009",
            "group_name": "测试柜组",
            "department_code": "D009",
            "department_name": "测试部",
            "operation_method": "租赁",
            "brand_name": "测试品牌",
            "monthly_revenue": 10000.00,
            "is_active": True
        }
    ]
    
    print("导入示例数据...")
    import_counter_groups_from_chat(sample_data)

