#!/usr/bin/env python3
"""
将现有柜位数据迁移到几何信息表
Migrate existing counter data to geometry tables
"""
import sys
from pathlib import Path
import json

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from models.database import get_db
from models.models import Counter
try:
    from models.geometry_models import CounterGeometry, CounterGeometryProperty
except ImportError:
    # 如果geometry_models不存在，定义空的类
    CounterGeometry = None
    CounterGeometryProperty = None
from utils.polygon_utils import PolygonUtils


def migrate_existing_data():
    """迁移现有数据到几何信息表"""
    print("开始迁移现有柜位数据到几何信息表...")
    
    db = next(get_db())
    try:
        # 获取所有有几何信息的柜位
        counters = db.query(Counter).filter(
            (Counter.position_x.isnot(None)) | 
            (Counter.polygon_coordinates.isnot(None)) |
            (Counter.center_x.isnot(None))
        ).all()
        
        print(f"找到 {len(counters)} 个需要迁移的柜位")
        
        migrated_count = 0
        skipped_count = 0
        
        for counter in counters:
            try:
                # 检查是否已有几何信息
                existing_geometry = db.query(CounterGeometry).filter(
                    CounterGeometry.counter_id == counter.counter_id
                ).first()
                
                if existing_geometry:
                    print(f"跳过已存在几何信息的柜位: {counter.counter_code}")
                    skipped_count += 1
                    continue
                
                # 创建几何信息
                geometry = CounterGeometry(
                    counter_id=counter.counter_id,
                    shape_type=counter.shape_type or 'rectangle',
                    position_x=counter.position_x,
                    position_y=counter.position_y,
                    width=counter.width,
                    height=counter.height,
                    polygon_coordinates=counter.polygon_coordinates,
                    center_x=counter.center_x,
                    center_y=counter.center_y,
                    bounding_box_min_x=counter.bounding_box_min_x,
                    bounding_box_min_y=counter.bounding_box_min_y,
                    bounding_box_max_x=counter.bounding_box_max_x,
                    bounding_box_max_y=counter.bounding_box_max_y
                )
                
                db.add(geometry)
                migrated_count += 1
                
                if migrated_count % 100 == 0:
                    print(f"已迁移 {migrated_count} 个柜位...")
                    
            except Exception as e:
                print(f"迁移柜位 {counter.counter_code} 时出错: {e}")
                continue
        
        db.commit()
        print(f"迁移完成！成功迁移 {migrated_count} 个柜位，跳过 {skipped_count} 个已存在的柜位")
        
    except Exception as e:
        db.rollback()
        print(f"迁移失败: {e}")
    finally:
        db.close()


def create_sample_geometry_data():
    """创建示例几何数据"""
    print("创建示例几何数据...")
    
    db = next(get_db())
    try:
        # 创建矩形几何示例
        rect_geometry = CounterGeometry(
            counter_id=1,  # 假设柜位ID为1
            shape_type='rectangle',
            position_x=100.0,
            position_y=100.0,
            width=50.0,
            height=30.0,
            rotation=0.0,
            bounding_box_min_x=100.0,
            bounding_box_min_y=100.0,
            bounding_box_max_x=150.0,
            bounding_box_max_y=130.0
        )
        
        # 创建多边形几何示例
        polygon_coords = [[200, 200], [250, 200], [280, 230], [250, 260], [200, 260], [180, 230]]
        polygon_geometry = CounterGeometry(
            counter_id=2,  # 假设柜位ID为2
            shape_type='polygon',
            polygon_coordinates=json.dumps(polygon_coords),
            bounding_box_min_x=180.0,
            bounding_box_min_y=200.0,
            bounding_box_max_x=280.0,
            bounding_box_max_y=260.0
        )
        
        # 创建圆形几何示例
        circle_geometry = CounterGeometry(
            counter_id=3,  # 假设柜位ID为3
            shape_type='circle',
            center_x=300.0,
            center_y=300.0,
            radius=25.0,
            bounding_box_min_x=275.0,
            bounding_box_min_y=275.0,
            bounding_box_max_x=325.0,
            bounding_box_max_y=325.0
        )
        
        # 检查是否已存在
        existing_rect = db.query(CounterGeometry).filter(CounterGeometry.counter_id == 1).first()
        existing_poly = db.query(CounterGeometry).filter(CounterGeometry.counter_id == 2).first()
        existing_circle = db.query(CounterGeometry).filter(CounterGeometry.counter_id == 3).first()
        
        if not existing_rect:
            db.add(rect_geometry)
            print("创建矩形几何示例")
        
        if not existing_poly:
            db.add(polygon_geometry)
            print("创建多边形几何示例")
        
        if not existing_circle:
            db.add(circle_geometry)
            print("创建圆形几何示例")
        
        db.commit()
        print("示例几何数据创建完成！")
        
    except Exception as e:
        db.rollback()
        print(f"创建示例数据失败: {e}")
    finally:
        db.close()


def verify_migration():
    """验证迁移结果"""
    print("验证迁移结果...")
    
    db = next(get_db())
    try:
        # 统计几何信息
        total_geometries = db.query(CounterGeometry).count()
        rect_count = db.query(CounterGeometry).filter(CounterGeometry.shape_type == 'rectangle').count()
        poly_count = db.query(CounterGeometry).filter(CounterGeometry.shape_type == 'polygon').count()
        circle_count = db.query(CounterGeometry).filter(CounterGeometry.shape_type == 'circle').count()
        
        print(f"几何信息总数: {total_geometries}")
        print(f"矩形: {rect_count}")
        print(f"多边形: {poly_count}")
        print(f"圆形: {circle_count}")
        
        # 显示前5个几何信息
        geometries = db.query(CounterGeometry).limit(5).all()
        print("\n前5个几何信息:")
        for geo in geometries:
            print(f"  {geo.counter_id}: {geo.shape_type}")
            if geo.shape_type == 'rectangle':
                print(f"    位置: ({geo.position_x}, {geo.position_y}), 尺寸: {geo.width}x{geo.height}")
            elif geo.shape_type == 'polygon':
                coords = json.loads(geo.polygon_coordinates) if geo.polygon_coordinates else []
                print(f"    坐标点: {len(coords)} 个")
            elif geo.shape_type == 'circle':
                print(f"    圆心: ({geo.center_x}, {geo.center_y}), 半径: {geo.radius}")
        
    finally:
        db.close()


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "migrate":
            migrate_existing_data()
        elif sys.argv[1] == "sample":
            create_sample_geometry_data()
        elif sys.argv[1] == "verify":
            verify_migration()
        else:
            print("用法: python migrate_to_geometry_tables.py [migrate|sample|verify]")
    else:
        print("几何信息表迁移工具")
        print("用法:")
        print("  python migrate_to_geometry_tables.py migrate  - 迁移现有数据")
        print("  python migrate_to_geometry_tables.py sample   - 创建示例数据")
        print("  python migrate_to_geometry_tables.py verify   - 验证迁移结果")


if __name__ == "__main__":
    main()






