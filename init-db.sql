-- 初始化数据库脚本
-- PostgreSQL 不需要 CREATE DATABASE IF NOT EXISTS，因为数据库已经在 docker-compose 中创建

-- 连接到数据库
\c commercial_real_estate;

-- 创建必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 这个文件将在容器启动时自动执行
-- Drizzle migrations 将在应用启动时运行