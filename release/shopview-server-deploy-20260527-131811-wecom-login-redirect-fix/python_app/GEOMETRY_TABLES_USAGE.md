# 几何信息表使用说明

## 🎯 概述

几何信息表将柜位的几何信息（矩形、多边形、圆形等）从主表中分离出来，通过主键ID关联，实现更好的数据结构和扩展性。

## 📊 数据库结构

### 1. 柜位表（counters）
- 保留业务信息：编号、名称、面积、状态、租金等
- 移除几何字段：position_x, position_y, width, height, polygon_coordinates等

### 2. 几何信息表（counter_geometries）
- 存储所有几何信息
- 支持多种形状类型：rectangle, polygon, circle, ellipse
- 通过counter_id关联到柜位表

### 3. 几何属性表（counter_geometry_properties）
- 存储几何相关的扩展属性
- 支持自定义属性

## 🚀 创建表

### 方法1：使用SQL脚本（推荐）
```bash
# 在PostgreSQL中执行
psql -h 192.168.98.80 -U your_username -d your_database -f create_geometry_tables.sql
```

### 方法2：使用Python脚本
```bash
# 迁移现有数据
python migrate_to_geometry_tables.py migrate

# 创建示例数据
python migrate_to_geometry_tables.py sample

# 验证迁移结果
python migrate_to_geometry_tables.py verify
```

## 🔧 API接口

### 柜位管理接口（已更新）

#### 1. 获取柜位列表（支持几何信息）
```http
GET /api/counters/?include_geometry=true&shape_type=rectangle
```

参数：
- `include_geometry`: 是否包含几何信息
- `shape_type`: 按形状类型筛选（rectangle, polygon, circle, ellipse）

#### 2. 获取单个柜位（支持几何信息）
```http
GET /api/counters/{counter_id}?include_geometry=true
```

#### 3. 获取柜位几何信息
```http
GET /api/counters/{counter_id}/geometry
```

#### 4. 获取带几何信息的柜位列表
```http
GET /api/counters/with-geometry/list?shape_type=rectangle
```

### 几何管理接口

#### 1. 创建矩形几何
```http
POST /api/geometry/rectangle
Content-Type: application/json

{
  "counter_id": 1,
  "position_x": 100.0,
  "position_y": 100.0,
  "width": 50.0,
  "height": 30.0,
  "rotation": 0.0
}
```

#### 2. 创建多边形几何
```http
POST /api/geometry/polygon
Content-Type: application/json

{
  "counter_id": 2,
  "coordinates": [
    {"x": 200, "y": 200},
    {"x": 250, "y": 200},
    {"x": 280, "y": 230},
    {"x": 250, "y": 260},
    {"x": 200, "y": 260},
    {"x": 180, "y": 230}
  ]
}
```

#### 3. 创建圆形几何
```http
POST /api/geometry/circle
Content-Type: application/json

{
  "counter_id": 3,
  "center_x": 300.0,
  "center_y": 300.0,
  "radius": 25.0
}
```

#### 4. 添加几何属性
```http
POST /api/geometry/{geometry_id}/properties
Content-Type: application/json

{
  "property_name": "color",
  "property_value": "#FF0000",
  "property_type": "string"
}
```

## 📝 使用示例

### Python代码示例

#### 1. 创建矩形柜位
```python
from models.database import get_db
from models.models import Counter
from models.geometry_models import CounterGeometry

db = next(get_db())

# 创建柜位
counter = Counter(
    store_id=1,
    floor_id=1,
    counter_code="RECT-001",
    counter_name="矩形柜位",
    area=50.0,
    status="vacant"
)
db.add(counter)
db.commit()

# 创建几何信息
geometry = CounterGeometry(
    counter_id=counter.counter_id,
    shape_type="rectangle",
    position_x=100.0,
    position_y=100.0,
    width=10.0,
    height=5.0,
    bounding_box_min_x=100.0,
    bounding_box_min_y=100.0,
    bounding_box_max_x=110.0,
    bounding_box_max_y=105.0
)
db.add(geometry)
db.commit()
```

#### 2. 创建多边形柜位
```python
import json

# 创建多边形几何
polygon_coords = [[200, 200], [250, 200], [280, 230], [250, 260], [200, 260], [180, 230]]
geometry = CounterGeometry(
    counter_id=counter.counter_id,
    shape_type="polygon",
    polygon_coordinates=json.dumps(polygon_coords),
    bounding_box_min_x=180.0,
    bounding_box_min_y=200.0,
    bounding_box_max_x=280.0,
    bounding_box_max_y=260.0
)
db.add(geometry)
db.commit()
```

#### 3. 查询带几何信息的柜位
```python
from sqlalchemy.orm import joinedload

# 查询所有柜位及其几何信息
counters = db.query(Counter).options(
    joinedload(Counter.geometry)
).all()

for counter in counters:
    print(f"柜位: {counter.counter_code}")
    if counter.geometry:
        print(f"  形状: {counter.geometry.shape_type}")
        if counter.geometry.shape_type == "rectangle":
            print(f"  位置: ({counter.geometry.position_x}, {counter.geometry.position_y})")
            print(f"  尺寸: {counter.geometry.width}x{counter.geometry.height}")
        elif counter.geometry.shape_type == "polygon":
            coords = json.loads(counter.geometry.polygon_coordinates)
            print(f"  坐标点: {len(coords)} 个")
```

### SQL查询示例

#### 1. 查询所有带几何信息的柜位
```sql
SELECT 
    c.counter_code,
    c.counter_name,
    g.shape_type,
    g.position_x,
    g.position_y,
    g.width,
    g.height
FROM counters c
LEFT JOIN counter_geometries g ON c.counter_id = g.counter_id;
```

#### 2. 查询矩形柜位
```sql
SELECT 
    c.counter_code,
    c.counter_name,
    g.position_x,
    g.position_y,
    g.width,
    g.height
FROM counters c
JOIN counter_geometries g ON c.counter_id = g.counter_id
WHERE g.shape_type = 'rectangle';
```

#### 3. 查询多边形柜位
```sql
SELECT 
    c.counter_code,
    c.counter_name,
    g.polygon_coordinates
FROM counters c
JOIN counter_geometries g ON c.counter_id = g.counter_id
WHERE g.shape_type = 'polygon';
```

#### 4. 使用视图查询
```sql
-- 使用预定义的视图
SELECT * FROM counters_with_geometry WHERE shape_type = 'rectangle';
```

#### 5. 使用函数查询
```sql
-- 获取特定柜位的几何信息
SELECT * FROM get_counter_geometry(1);

-- 按形状类型获取柜位
SELECT * FROM get_counters_by_shape('rectangle');
```

## 🔍 数据验证

### 1. 检查表是否创建成功
```sql
-- 检查表结构
\d counter_geometries
\d counter_geometry_properties

-- 检查数据
SELECT COUNT(*) FROM counter_geometries;
SELECT COUNT(*) FROM counter_geometry_properties;
```

### 2. 验证数据完整性
```sql
-- 检查是否有孤立的几何信息
SELECT g.* FROM counter_geometries g
LEFT JOIN counters c ON g.counter_id = c.counter_id
WHERE c.counter_id IS NULL;

-- 检查是否有柜位没有几何信息
SELECT c.* FROM counters c
LEFT JOIN counter_geometries g ON c.counter_id = g.counter_id
WHERE g.counter_id IS NULL;
```

## 🚨 注意事项

1. **数据迁移**：现有数据需要迁移到新表结构
2. **API兼容性**：现有API保持兼容，新增几何信息参数
3. **性能优化**：几何信息表有适当的索引
4. **数据完整性**：使用外键约束保证数据一致性
5. **扩展性**：支持未来添加新的几何类型

## 📈 性能优化

1. **索引**：在counter_id、shape_type、边界框字段上创建索引
2. **查询优化**：使用JOIN查询减少数据库往返
3. **缓存**：几何信息可以缓存以提高性能
4. **分页**：大数据量时使用分页查询

## 🎯 总结

几何信息表分离设计提供了：
- 更清晰的数据结构
- 更好的扩展性
- 更高的查询效率
- 更强的数据完整性

这是一个平衡了性能、扩展性和维护性的优秀设计方案！






