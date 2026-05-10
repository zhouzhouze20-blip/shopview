-- 创建几何信息表
-- Create geometry tables for counter management

-- 1. 创建几何信息表
CREATE TABLE IF NOT EXISTS counter_geometries (
    geometry_id SERIAL PRIMARY KEY,
    counter_id INTEGER NOT NULL REFERENCES counters(counter_id) ON DELETE CASCADE,
    shape_type VARCHAR(20) NOT NULL CHECK (shape_type IN ('rectangle', 'polygon', 'circle', 'ellipse')),
    
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
    
    -- 元数据
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 约束：确保每个柜位只有一个几何信息
    CONSTRAINT unique_counter_geometry UNIQUE (counter_id)
);

-- 2. 创建几何属性表
CREATE TABLE IF NOT EXISTS counter_geometry_properties (
    property_id SERIAL PRIMARY KEY,
    geometry_id INTEGER NOT NULL REFERENCES counter_geometries(geometry_id) ON DELETE CASCADE,
    property_name VARCHAR(50) NOT NULL,
    property_value TEXT,
    property_type VARCHAR(20) DEFAULT 'string' CHECK (property_type IN ('string', 'number', 'boolean', 'json')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. 创建索引
CREATE INDEX IF NOT EXISTS idx_counter_geometries_counter_id ON counter_geometries(counter_id);
CREATE INDEX IF NOT EXISTS idx_counter_geometries_shape_type ON counter_geometries(shape_type);
CREATE INDEX IF NOT EXISTS idx_counter_geometries_bounding_box ON counter_geometries(bounding_box_min_x, bounding_box_min_y, bounding_box_max_x, bounding_box_max_y);

CREATE INDEX IF NOT EXISTS idx_geometry_properties_geometry_id ON counter_geometry_properties(geometry_id);
CREATE INDEX IF NOT EXISTS idx_geometry_properties_name ON counter_geometry_properties(property_name);

-- 4. 添加注释
COMMENT ON TABLE counter_geometries IS '柜位几何信息表';
COMMENT ON COLUMN counter_geometries.geometry_id IS '几何信息ID';
COMMENT ON COLUMN counter_geometries.counter_id IS '柜位ID';
COMMENT ON COLUMN counter_geometries.shape_type IS '形状类型：rectangle-矩形, polygon-多边形, circle-圆形, ellipse-椭圆';
COMMENT ON COLUMN counter_geometries.position_x IS 'X坐标（矩形）';
COMMENT ON COLUMN counter_geometries.position_y IS 'Y坐标（矩形）';
COMMENT ON COLUMN counter_geometries.width IS '宽度（矩形）';
COMMENT ON COLUMN counter_geometries.height IS '高度（矩形）';
COMMENT ON COLUMN counter_geometries.rotation IS '旋转角度';
COMMENT ON COLUMN counter_geometries.polygon_coordinates IS '多边形坐标点，JSON格式：[[x1,y1],[x2,y2],...]';
COMMENT ON COLUMN counter_geometries.center_x IS '圆心X坐标';
COMMENT ON COLUMN counter_geometries.center_y IS '圆心Y坐标';
COMMENT ON COLUMN counter_geometries.radius IS '半径';
COMMENT ON COLUMN counter_geometries.ellipse_center_x IS '椭圆中心X坐标';
COMMENT ON COLUMN counter_geometries.ellipse_center_y IS '椭圆中心Y坐标';
COMMENT ON COLUMN counter_geometries.ellipse_radius_x IS '椭圆X轴半径';
COMMENT ON COLUMN counter_geometries.ellipse_radius_y IS '椭圆Y轴半径';
COMMENT ON COLUMN counter_geometries.ellipse_rotation IS '椭圆旋转角度';
COMMENT ON COLUMN counter_geometries.bounding_box_min_x IS '边界框最小X坐标';
COMMENT ON COLUMN counter_geometries.bounding_box_min_y IS '边界框最小Y坐标';
COMMENT ON COLUMN counter_geometries.bounding_box_max_x IS '边界框最大X坐标';
COMMENT ON COLUMN counter_geometries.bounding_box_max_y IS '边界框最大Y坐标';

COMMENT ON TABLE counter_geometry_properties IS '柜位几何属性表';
COMMENT ON COLUMN counter_geometry_properties.property_id IS '属性ID';
COMMENT ON COLUMN counter_geometry_properties.geometry_id IS '几何信息ID';
COMMENT ON COLUMN counter_geometry_properties.property_name IS '属性名';
COMMENT ON COLUMN counter_geometry_properties.property_value IS '属性值（JSON格式）';
COMMENT ON COLUMN counter_geometry_properties.property_type IS '属性类型：string, number, boolean, json';

-- 5. 迁移现有数据（如果有的话）
-- 将现有柜位的几何信息迁移到新表
INSERT INTO counter_geometries (
    counter_id, shape_type, position_x, position_y, width, height,
    polygon_coordinates, center_x, center_y,
    bounding_box_min_x, bounding_box_min_y, bounding_box_max_x, bounding_box_max_y,
    created_at, updated_at
)
SELECT 
    counter_id,
    COALESCE(shape_type, 'rectangle') as shape_type,
    position_x, position_y, width, height,
    polygon_coordinates,
    center_x, center_y,
    bounding_box_min_x, bounding_box_min_y, bounding_box_max_x, bounding_box_max_y,
    created_at, updated_at
FROM counters
WHERE (position_x IS NOT NULL AND position_y IS NOT NULL) 
   OR polygon_coordinates IS NOT NULL
   OR (center_x IS NOT NULL AND center_y IS NOT NULL)
ON CONFLICT (counter_id) DO NOTHING;

-- 6. 创建触发器来自动更新updated_at字段
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_counter_geometries_updated_at 
    BEFORE UPDATE ON counter_geometries 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 7. 创建视图：带几何信息的柜位视图
CREATE OR REPLACE VIEW counters_with_geometry AS
SELECT 
    c.*,
    g.geometry_id,
    g.shape_type,
    g.position_x,
    g.position_y,
    g.width,
    g.height,
    g.rotation,
    g.polygon_coordinates,
    g.center_x,
    g.center_y,
    g.radius,
    g.ellipse_center_x,
    g.ellipse_center_y,
    g.ellipse_radius_x,
    g.ellipse_radius_y,
    g.ellipse_rotation,
    g.bounding_box_min_x,
    g.bounding_box_min_y,
    g.bounding_box_max_x,
    g.bounding_box_max_y
FROM counters c
LEFT JOIN counter_geometries g ON c.counter_id = g.counter_id;

-- 8. 创建函数：获取柜位几何信息
CREATE OR REPLACE FUNCTION get_counter_geometry(counter_id_param INTEGER)
RETURNS TABLE (
    geometry_id INTEGER,
    shape_type VARCHAR(20),
    position_x NUMERIC(10,2),
    position_y NUMERIC(10,2),
    width NUMERIC(10,2),
    height NUMERIC(10,2),
    rotation NUMERIC(5,2),
    polygon_coordinates TEXT,
    center_x NUMERIC(10,2),
    center_y NUMERIC(10,2),
    radius NUMERIC(10,2),
    bounding_box_min_x NUMERIC(10,2),
    bounding_box_min_y NUMERIC(10,2),
    bounding_box_max_x NUMERIC(10,2),
    bounding_box_max_y NUMERIC(10,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        g.geometry_id,
        g.shape_type,
        g.position_x,
        g.position_y,
        g.width,
        g.height,
        g.rotation,
        g.polygon_coordinates,
        g.center_x,
        g.center_y,
        g.radius,
        g.bounding_box_min_x,
        g.bounding_box_min_y,
        g.bounding_box_max_x,
        g.bounding_box_max_y
    FROM counter_geometries g
    WHERE g.counter_id = counter_id_param;
END;
$$ LANGUAGE plpgsql;

-- 9. 创建函数：按形状类型获取柜位
CREATE OR REPLACE FUNCTION get_counters_by_shape(shape_type_param VARCHAR(20))
RETURNS TABLE (
    counter_id INTEGER,
    counter_code VARCHAR(20),
    counter_name VARCHAR(100),
    area NUMERIC(10,2),
    status VARCHAR(20),
    geometry_id INTEGER,
    shape_type VARCHAR(20)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.counter_id,
        c.counter_code,
        c.counter_name,
        c.area,
        c.status,
        g.geometry_id,
        g.shape_type
    FROM counters c
    JOIN counter_geometries g ON c.counter_id = g.counter_id
    WHERE g.shape_type = shape_type_param;
END;
$$ LANGUAGE plpgsql;

-- 完成
SELECT '几何信息表创建完成！' as message;






