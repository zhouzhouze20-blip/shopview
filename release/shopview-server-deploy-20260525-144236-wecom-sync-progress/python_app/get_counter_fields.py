#!/usr/bin/env python3
"""
获取柜位表字段信息
Get counter table field information
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from models.database import get_db
from models.models import Counter

def get_counter_fields():
    """获取柜位表字段信息"""
    db = next(get_db())
    try:
        print("柜位表（counters）字段信息:")
        print("=" * 80)
        print(f"{'序号':<4} {'字段名':<25} {'数据类型':<20} {'注释'}")
        print("-" * 80)
        
        for i, column in enumerate(Counter.__table__.columns, 1):
            field_name = column.name
            field_type = str(column.type)
            field_comment = column.comment or "无注释"
            
            print(f"{i:<4} {field_name:<25} {field_type:<20} {field_comment}")
        
        print("=" * 80)
        print(f"总计: {len(Counter.__table__.columns)} 个字段")
        
    finally:
        db.close()

if __name__ == "__main__":
    get_counter_fields()






