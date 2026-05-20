# 柜位几何信息分离设计方案

## 🎯 设计目标

将柜位表的几何信息（矩形、多边形、圆形等）分离到独立的表中，通过主键ID关联，实现更好的数据结构和扩展性。

## 📊 数据库设计

### 1. 柜位表（counters）- 业务信息
```sql
CREATE TABLE counters (
    counter_id INTEGER PRIMARY KEY,
    store_id INTEGER NOT NULL,
    floor_id INTEGER NOT NULL,
    counter_code VARCHAR(20) NOT NULL,
    counter_name VARCHAR(100),
    area NUMERIC(10,2),
    counter_type VARCHAR(50),
    status VARCHAR(20) DEFAULT 'vacant',
    monthly_rent NUMERIC(10,2),
    management_fee NUMERIC(10,2),
    deposit NUMERIC(10,2),
    group_code VARCHAR(20),
    facade_image_url VARCHAR(500),
    monthly_revenue NUMERIC(12,2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2. 几何信息表（counter_geometries）
```sql
CREATE TABLE counter_geometries (
    geometry_id INTEGER PRIMARY KEY,
    counter_id INTEGER NOT NULL REFERENCES counters(counter_id),
    shape_type VARCHAR(20) NOT NULL, -- rectangle, polygon, circle, ellipse
    
    -- 矩形字段
    position_x NUMERIC(10,2),
    position_y NUMERIC(10,2),
    width NUMERIC(10,2),
    height NUMERIC(10,2),
    rotation NUMERIC(5,2) DEFAULT 0,
    
    -- 多边形字段
    polygon_coordinates TEXT, -- JSON格式：[[x1,y1],[x2,y2],...]
    
    -- 圆形字段
    center_x NUMERIC(10,2),
    center_y NUMERIC(10,2),
    radius NUMERIC(10,2),
    
    -- 椭圆字段
    ellipse_center_x NUMERIC(10,2),
    ellipse_center_y NUMERIC(10,2),
    ellipse_radius_x NUMERIC(10,2),
    ellipse_radius_y NUMERIC(10,2),
    ellipse_rotation NUMERIC(5,2),
    
    -- 通用字段
    bounding_box_min_x NUMERIC(10,2),
    bounding_box_min_y NUMERIC(10,2),
    bounding_box_max_x NUMERIC(10,2),
    bounding_box_max_y NUMERIC(10,2),
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 3. 几何属性表（counter_geometry_properties）
```sql
CREATE TABLE counter_geometry_properties (
    property_id INTEGER PRIMARY KEY,
    geometry_id INTEGER NOT NULL REFERENCES counter_geometries(geometry_id),
    property_name VARCHAR(50) NOT NULL,
    property_value TEXT,
    property_type VARCHAR(20), -- string, number, boolean, json
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 🔗 关联关系

```
counters (1) ←→ (1) counter_geometries (1) ←→ (N) counter_geometry_properties
```

- 一个柜位对应一个几何信息
- 一个几何信息可以有多个属性

## 🚀 优势

### 1. **结构清晰**
- 业务信息和几何信息分离
- 职责明确，易于维护

### 2. **扩展性好**
- 支持多种几何类型（矩形、多边形、圆形、椭圆）
- 通过属性表支持自定义属性
- 易于添加新的几何类型

### 3. **查询效率**
- 通过counter_id关联，查询简单
- 可以单独查询几何信息
- 支持按形状类型快速筛选

### 4. **向后兼容**
- 保留原有字段用于快速查询
- 渐进式迁移，不影响现有功能

### 5. **数据完整性**
- 外键约束保证数据一致性
- 级联删除保证数据清理

## 📝 使用示例

### 创建矩形柜位
```python
# 1. 创建柜位
counter = Counter(
    store_id=1,
    floor_id=1,
    counter_code="RECT-001",
    counter_name="矩形柜位",
    area=50.0,
    status="vacant"
)

# 2. 创建几何信息
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
```

### 创建多边形柜位
```python
# 1. 创建柜位
counter = Counter(
    store_id=1,
    floor_id=1,
    counter_code="POLY-001",
    counter_name="L形柜位",
    area=45.0,
    status="vacant"
)

# 2. 创建几何信息
geometry = CounterGeometry(
    counter_id=counter.counter_id,
    shape_type="polygon",
    polygon_coordinates='[[100,100],[150,100],[150,120],[130,120],[130,150],[100,150]]',
    bounding_box_min_x=100.0,
    bounding_box_min_y=100.0,
    bounding_box_max_x=150.0,
    bounding_box_max_y=150.0
)
```

### 查询柜位及其几何信息
```sql
-- 获取柜位及其几何信息
SELECT c.*, g.shape_type, g.polygon_coordinates
FROM counters c
LEFT JOIN counter_geometries g ON c.counter_id = g.counter_id;

-- 查询矩形柜位
SELECT c.*, g.position_x, g.position_y, g.width, g.height
FROM counters c
JOIN counter_geometries g ON c.counter_id = g.counter_id
WHERE g.shape_type = 'rectangle';

-- 查询多边形柜位
SELECT c.*, g.polygon_coordinates
FROM counters c
JOIN counter_geometries g ON c.counter_id = g.counter_id
WHERE g.shape_type = 'polygon';
```

## 🔧 API接口

### 几何信息管理
- `POST /api/geometry/rectangle` - 创建矩形几何
- `POST /api/geometry/polygon` - 创建多边形几何
- `POST /api/geometry/circle` - 创建圆形几何
- `GET /api/geometry/counter/{counter_id}` - 获取柜位几何信息
- `POST /api/geometry/{geometry_id}/properties` - 添加几何属性

### 柜位查询
- `GET /api/geometry/counters/with-geometry` - 获取带几何信息的柜位列表
- `GET /api/geometry/counters/with-geometry?shape_type=rectangle` - 按形状类型筛选

## 📈 迁移策略

### 阶段1：创建新表
1. 创建几何信息表和属性表
2. 保持现有柜位表不变

### 阶段2：数据迁移
1. 将现有柜位的几何信息迁移到新表
2. 建立关联关系

### 阶段3：功能切换
1. 更新API接口使用新表
2. 逐步废弃旧字段

### 阶段4：清理
1. 删除不再使用的字段
2. 优化数据库结构

## 🎯 总结

这个设计方案将几何信息从柜位表中分离出来，通过主键ID关联，实现了：

1. **更好的数据结构**：业务信息和几何信息分离
2. **更强的扩展性**：支持多种几何类型和自定义属性
3. **更高的查询效率**：可以单独查询几何信息
4. **更好的维护性**：职责明确，易于维护

这是一个平衡了性能、扩展性和维护性的优秀设计方案！






