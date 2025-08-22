-- 百货柜位管理系统数据库初始化脚本
-- Department Store Counter Management System - Database Initialization

-- 创建数据库（如果不存在）
SELECT 'CREATE DATABASE counter_management'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'counter_management');

-- 连接到数据库
\c counter_management;

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 设置时区
SET timezone = 'Asia/Shanghai';

-- 数据库初始化完成
SELECT 'Database initialized successfully' as status;