# 柜位几何信息分离设计方案

## 方案1：几何信息表（推荐）

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
    ellipse_rotation NUMERIC(5,2), -- 旋转角度
    -- 通用字段
    bounding_box_min_x NUMERIC(10,2),
    bounding_box_min_y NUMERIC(10,2),
    bounding_box_max_x NUMERIC(10,2),
    bounding_box_max_y NUMERIC(10,2),
    -- 元数据
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 3. 几何属性表（counter_geometry_properties）
```sql
CREATE TABLE counter_geometry_properties (
    property_id INTEGER PRIMARY KEY,
    geometry_id INTEGER NOT NULL REFERENCES counter_geometries(geometry_id),
    property_name VARCHAR(50) NOT NULL, -- 属性名
    property_value TEXT, -- 属性值（JSON格式）
    property_type VARCHAR(20), -- string, number, boolean, json
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 方案2：多表分离（更细粒度）

### 1. 柜位表（counters）
```sql
-- 同上，只保留业务信息
```

### 2. 矩形几何表（counter_rectangles）
```sql
CREATE TABLE counter_rectangles (
    rectangle_id INTEGER PRIMARY KEY,
    counter_id INTEGER NOT NULL REFERENCES counters(counter_id),
    position_x NUMERIC(10,2) NOT NULL,
    position_y NUMERIC(10,2) NOT NULL,
    width NUMERIC(10,2) NOT NULL,
    height NUMERIC(10,2) NOT NULL,
    rotation NUMERIC(5,2) DEFAULT 0, -- 旋转角度
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 3. 多边形几何表（counter_polygons）
```sql
CREATE TABLE counter_polygons (
    polygon_id INTEGER PRIMARY KEY,
    counter_id INTEGER NOT NULL REFERENCES counters(counter_id),
    coordinates TEXT NOT NULL, -- JSON格式
    is_closed BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4. 圆形几何表（counter_circles）
```sql
CREATE TABLE counter_circles (
    circle_id INTEGER PRIMARY KEY,
    counter_id INTEGER NOT NULL REFERENCES counters(counter_id),
    center_x NUMERIC(10,2) NOT NULL,
    center_y NUMERIC(10,2) NOT NULL,
    radius NUMERIC(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 方案3：混合方案（平衡）

### 1. 柜位表（counters）
```sql
-- 保留基础几何字段用于快速查询
CREATE TABLE counters (
    counter_id INTEGER PRIMARY KEY,
    -- ... 业务字段 ...
    -- 基础几何信息（用于快速查询）
    shape_type VARCHAR(20),
    center_x NUMERIC(10,2),
    center_y NUMERIC(10,2),
    bounding_box_min_x NUMERIC(10,2),
    bounding_box_min_y NUMERIC(10,2),
    bounding_box_max_x NUMERIC(10,2),
    bounding_box_max_y NUMERIC(10,2),
    area NUMERIC(10,2),
    -- ... 其他字段 ...
);
```

### 2. 详细几何表（counter_geometry_details）
```sql
CREATE TABLE counter_geometry_details (
    detail_id INTEGER PRIMARY KEY,
    counter_id INTEGER NOT NULL REFERENCES counters(counter_id),
    geometry_data TEXT NOT NULL, -- 完整的几何数据JSON
    geometry_version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## 推荐方案：方案1（几何信息表）

### 优势：
1. **结构清晰**：业务信息和几何信息分离
2. **扩展性好**：支持多种几何类型
3. **查询效率**：通过counter_id关联，查询简单
4. **维护方便**：几何信息集中管理
5. **向后兼容**：保留矩形字段用于快速查询

### 使用场景：
- 矩形柜位：使用position_x, position_y, width, height
- 多边形柜位：使用polygon_coordinates
- 圆形柜位：使用center_x, center_y, radius
- 复杂形状：使用polygon_coordinates + 属性表

### 查询示例：
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






