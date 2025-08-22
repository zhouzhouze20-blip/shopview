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

# 数据库连接配置
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/counter_management")

engine = create_engine(DATABASE_URL)
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