"""
百货柜位管理系统 - 数据库配置
Database configuration for Department Store Counter Management System
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# 数据库连接配置 - PostgreSQL数据库
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sales_user:sales_password_2024@192.168.98.80:5432/sales_db")

# 配置数据库引擎，添加连接超时和自动重连
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # 自动检测并重连断开的连接
    connect_args={
        "connect_timeout": 5,  # 连接超时5秒
        "options": "-c statement_timeout=30000"  # 查询超时30秒
    },
    pool_size=5,  # 连接池大小
    max_overflow=10,  # 最大溢出连接数
    echo=False  # 不打印SQL语句
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()

Base = declarative_base(metadata=metadata)

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()