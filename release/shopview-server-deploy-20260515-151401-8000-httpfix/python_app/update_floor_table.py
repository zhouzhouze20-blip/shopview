#!/usr/bin/env python3
"""
更新Floor表结构，添加新字段
"""

from models.database import engine, SessionLocal
from models.models import Floor
from sqlalchemy import text

def update_floor_table():
    """更新Floor表结构"""
    db = SessionLocal()
    try:
        print("🔄 开始更新Floor表结构...")
        
        # 检查表是否存在
        result = db.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'floors')"))
        table_exists = result.scalar()
        
        if not table_exists:
            print("❌ floors表不存在，请先创建表")
            return
        
        # 检查新字段是否已存在
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'floors' AND column_name = 'building_code'
        """))
        building_code_exists = result.scalar()
        
        if building_code_exists:
            print("✅ 新字段已存在，无需更新")
            return
        
        print("📝 添加新字段...")
        
        # 添加新字段
        db.execute(text("ALTER TABLE floors ADD COLUMN building_code VARCHAR(20)"))
        print("  ✅ 添加 building_code 字段")
        
        db.execute(text("ALTER TABLE floors ADD COLUMN building_name VARCHAR(50)"))
        print("  ✅ 添加 building_name 字段")
        
        db.execute(text("ALTER TABLE floors ADD COLUMN floor_display_name VARCHAR(50)"))
        print("  ✅ 添加 floor_display_name 字段")
        
        db.execute(text("ALTER TABLE floors ADD COLUMN sort_order INTEGER DEFAULT 0"))
        print("  ✅ 添加 sort_order 字段")
        
        # 修改floor_number字段为NOT NULL
        db.execute(text("UPDATE floors SET floor_number = 1 WHERE floor_number IS NULL"))
        db.execute(text("ALTER TABLE floors ALTER COLUMN floor_number SET NOT NULL"))
        print("  ✅ 修改 floor_number 字段为 NOT NULL")
        
        # 为现有数据设置sort_order
        db.execute(text("UPDATE floors SET sort_order = floor_number WHERE sort_order IS NULL"))
        print("  ✅ 设置现有数据的 sort_order")
        
        db.commit()
        print("🎉 Floor表结构更新完成！")
        
    except Exception as e:
        print(f"❌ 更新Floor表结构时出错: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_floor_table()
