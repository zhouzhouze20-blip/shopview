#!/usr/bin/env python3
"""
楼层数据初始化脚本
为四家商场创建楼层数据
"""

from models.database import SessionLocal
from models.models import Store, Floor
from decimal import Decimal

def create_floor_data():
    """创建楼层数据"""
    db = SessionLocal()
    try:
        # 获取所有门店
        stores = db.query(Store).all()
        if not stores:
            print("❌ 没有找到门店数据，请先创建门店")
            return
        
        print(f"📋 找到 {len(stores)} 个门店")
        
        # 为每个门店创建楼层数据
        for i, store in enumerate(stores, 1):
            print(f"\n🏢 为门店 {store.store_name} 创建楼层数据...")
            
            # 根据门店顺序创建不同的楼层配置
            if i == 1:
                # 商场1：A栋B栋 + 负一楼到十六楼
                floors_data = create_mall_1_floors(store.store_id)
            elif i == 2:
                # 商场2：负一楼到7楼
                floors_data = create_mall_2_floors(store.store_id)
            elif i == 3:
                # 商场3：1-6楼
                floors_data = create_mall_3_floors(store.store_id)
            elif i == 4:
                # 商场4：9-16楼
                floors_data = create_mall_4_floors(store.store_id)
            else:
                # 默认：1-5楼
                floors_data = create_default_floors(store.store_id)
            
            # 检查是否已存在楼层数据
            existing_floors = db.query(Floor).filter(Floor.store_id == store.store_id).count()
            if existing_floors > 0:
                print(f"⚠️  门店 {store.store_name} 已存在 {existing_floors} 个楼层，跳过创建")
                continue
            
            # 创建楼层
            for floor_data in floors_data:
                floor = Floor(**floor_data)
                db.add(floor)
            
            db.commit()
            print(f"✅ 成功创建 {len(floors_data)} 个楼层")
        
        print("\n🎉 楼层数据初始化完成！")
        
    except Exception as e:
        print(f"❌ 创建楼层数据时出错: {e}")
        db.rollback()
    finally:
        db.close()

def create_mall_1_floors(store_id):
    """商场1：A栋B栋 + 负一楼到十六楼"""
    floors = []
    
    # A栋楼层
    for floor_num in range(-1, 17):  # -1到16
        floor_name = f"A栋{get_floor_display_name(floor_num)}"
        floors.append({
            'store_id': store_id,
            'building_code': 'A',
            'building_name': 'A栋',
            'floor_name': floor_name,
            'floor_number': floor_num,
            'floor_display_name': get_floor_display_name(floor_num),
            'description': f'A栋第{floor_num}层',
            'total_area': Decimal('5000.00'),
            'sort_order': floor_num + 100  # A栋排序靠前
        })
    
    # B栋楼层
    for floor_num in range(-1, 17):  # -1到16
        floor_name = f"B栋{get_floor_display_name(floor_num)}"
        floors.append({
            'store_id': store_id,
            'building_code': 'B',
            'building_name': 'B栋',
            'floor_name': floor_name,
            'floor_number': floor_num,
            'floor_display_name': get_floor_display_name(floor_num),
            'description': f'B栋第{floor_num}层',
            'total_area': Decimal('5000.00'),
            'sort_order': floor_num + 200  # B栋排序靠后
        })
    
    return floors

def create_mall_2_floors(store_id):
    """商场2：负一楼到7楼"""
    floors = []
    
    for floor_num in range(-1, 8):  # -1到7
        floor_name = f"{get_floor_display_name(floor_num)}"
        floors.append({
            'store_id': store_id,
            'building_code': None,
            'building_name': '主楼',
            'floor_name': floor_name,
            'floor_number': floor_num,
            'floor_display_name': get_floor_display_name(floor_num),
            'description': f'第{floor_num}层',
            'total_area': Decimal('3000.00'),
            'sort_order': floor_num
        })
    
    return floors

def create_mall_3_floors(store_id):
    """商场3：1-6楼"""
    floors = []
    
    for floor_num in range(1, 7):  # 1到6
        floor_name = f"{get_floor_display_name(floor_num)}"
        floors.append({
            'store_id': store_id,
            'building_code': None,
            'building_name': '主楼',
            'floor_name': floor_name,
            'floor_number': floor_num,
            'floor_display_name': get_floor_display_name(floor_num),
            'description': f'第{floor_num}层',
            'total_area': Decimal('2500.00'),
            'sort_order': floor_num
        })
    
    return floors

def create_mall_4_floors(store_id):
    """商场4：9-16楼"""
    floors = []
    
    for floor_num in range(9, 17):  # 9到16
        floor_name = f"{get_floor_display_name(floor_num)}"
        floors.append({
            'store_id': store_id,
            'building_code': None,
            'building_name': '主楼',
            'floor_name': floor_name,
            'floor_number': floor_num,
            'floor_display_name': get_floor_display_name(floor_num),
            'description': f'第{floor_num}层',
            'total_area': Decimal('2000.00'),
            'sort_order': floor_num
        })
    
    return floors

def create_default_floors(store_id):
    """默认楼层：1-5楼"""
    floors = []
    
    for floor_num in range(1, 6):  # 1到5
        floor_name = f"{get_floor_display_name(floor_num)}"
        floors.append({
            'store_id': store_id,
            'building_code': None,
            'building_name': '主楼',
            'floor_name': floor_name,
            'floor_number': floor_num,
            'floor_display_name': get_floor_display_name(floor_num),
            'description': f'第{floor_num}层',
            'total_area': Decimal('2000.00'),
            'sort_order': floor_num
        })
    
    return floors

def get_floor_display_name(floor_number):
    """获取楼层显示名称"""
    if floor_number == -1:
        return "B1"
    elif floor_number == 0:
        return "G"
    elif floor_number > 0:
        return f"{floor_number}F"
    else:
        return f"B{abs(floor_number)}"

if __name__ == "__main__":
    print("🚀 开始初始化楼层数据...")
    create_floor_data()
