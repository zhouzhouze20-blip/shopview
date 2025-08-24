-- 百货柜位管理系统数据库初始化脚本
-- 创建数据库和必要的扩展

-- 创建数据库 (如果不存在)
SELECT 'CREATE DATABASE counter_management'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'counter_management')\gexec

-- 连接到目标数据库
\c counter_management;

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 创建门店表
CREATE TABLE IF NOT EXISTS stores (
    store_id SERIAL PRIMARY KEY,
    store_name VARCHAR(255) NOT NULL,
    store_code VARCHAR(50) UNIQUE NOT NULL,
    address TEXT,
    manager_name VARCHAR(255),
    manager_phone VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建柜位表
CREATE TABLE IF NOT EXISTS counters (
    counter_id SERIAL PRIMARY KEY,
    store_id INTEGER REFERENCES stores(store_id) ON DELETE CASCADE,
    counter_number VARCHAR(100) NOT NULL,
    department VARCHAR(255),
    building VARCHAR(100),
    floor VARCHAR(50),
    area DECIMAL(10,2),
    status VARCHAR(50) DEFAULT 'vacant' CHECK (status IN ('occupied', 'vacant', 'maintenance')),
    monthly_rent DECIMAL(15,2),
    group_code VARCHAR(100),
    group_name VARCHAR(255),
    description TEXT,
    tenant_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(store_id, counter_number)
);

-- 创建租户表
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id SERIAL PRIMARY KEY,
    store_id INTEGER REFERENCES stores(store_id) ON DELETE CASCADE,
    company_name VARCHAR(255) NOT NULL,
    contact_person VARCHAR(255),
    phone VARCHAR(50),
    email VARCHAR(255),
    business_category VARCHAR(255),
    registration_number VARCHAR(100),
    address TEXT,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建楼层平面图表
CREATE TABLE IF NOT EXISTS floor_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id INTEGER REFERENCES stores(store_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    image_url TEXT,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建用户标记房间表
CREATE TABLE IF NOT EXISTS user_marked_rooms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id INTEGER REFERENCES stores(store_id) ON DELETE CASCADE,
    floor_plan_id UUID REFERENCES floor_plans(id) ON DELETE CASCADE,
    name VARCHAR(255),
    x DECIMAL(8,4) NOT NULL,
    y DECIMAL(8,4) NOT NULL,
    width DECIMAL(8,4) NOT NULL,
    height DECIMAL(8,4) NOT NULL,
    type VARCHAR(50) DEFAULT 'rectangle' CHECK (type IN ('rectangle', 'polygon')),
    polygon_points JSONB,
    counter_id INTEGER REFERENCES counters(counter_id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 插入初始门店数据
INSERT INTO stores (store_name, store_code, address, manager_name, manager_phone) 
VALUES 
    ('常州购物中心', '601', '江苏省常州市天宁区延陵西路123号', '张经理', '13800001001'),
    ('常州新世纪', '603', '江苏省常州市钟楼区南大街456号', '李经理', '13800001003'),
    ('百货大楼', '602', '江苏省常州市武进区湖塘镇购物大道789号', '王经理', '13800001002'),
    ('常州半山书局', '604', '江苏省常州市新北区太湖路321号', '刘经理', '13800001004')
ON CONFLICT (store_code) DO NOTHING;

-- 插入示例柜位数据
INSERT INTO counters (store_id, counter_number, department, building, floor, area, status, monthly_rent, group_code, group_name, description) 
VALUES 
    (1, 'A001', '服装部', 'A栋', '1F', 25.50, 'maintenance', 8500.00, 'GRP001', '时尚女装区', '主要销售时尚女装'),
    (1, 'A002', '服装部', 'A栋', '1F', 30.00, 'occupied', 9000.00, 'GRP001', '时尚女装区', '知名品牌女装专柜'),
    (1, 'B001', '化妆品部', 'B栋', '1F', 15.00, 'occupied', 12000.00, 'GRP002', '美妆护肤区', '国际化妆品品牌'),
    (1, 'C001', '数码产品部', 'C栋', '2F', 40.00, 'vacant', 15000.00, 'GRP003', '数码科技区', '手机、电脑等数码产品'),
    (1, 'D0333', '名品部', 'A栋', '2F', 30.00, 'occupied', 30000.00, '6010101011', '劳力士厅', '高端品牌专区'),
    (2, 'XS001', '珠宝部', 'A栋', '1F', 20.00, 'occupied', 25000.00, 'GRP004', '珠宝首饰区', '黄金珠宝专区'),
    (3, 'BH001', '家居用品', 'A栋', '3F', 35.00, 'vacant', 6000.00, 'GRP005', '家居生活区', '家居用品和装饰'),
    (4, 'BS001', '图书文具', 'A栋', '1F', 45.00, 'occupied', 4500.00, 'GRP006', '图书阅读区', '图书和文具用品')
ON CONFLICT (store_id, counter_number) DO NOTHING;

-- 创建索引以提高性能
CREATE INDEX IF NOT EXISTS idx_counters_store_id ON counters(store_id);
CREATE INDEX IF NOT EXISTS idx_counters_status ON counters(status);
CREATE INDEX IF NOT EXISTS idx_tenants_store_id ON tenants(store_id);
CREATE INDEX IF NOT EXISTS idx_user_marked_rooms_store_id ON user_marked_rooms(store_id);
CREATE INDEX IF NOT EXISTS idx_floor_plans_store_id ON floor_plans(store_id);

\echo '数据库初始化完成！';
