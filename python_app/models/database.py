"""
百货柜位管理系统 - 数据库配置
Database configuration for Department Store Counter Management System
"""
from sqlalchemy import create_engine, event, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import time
from dotenv import load_dotenv

load_dotenv()

# 数据库连接配置 - PostgreSQL数据库
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sales_user:sales_password_2024@192.168.98.80:5432/sales_db")
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Shanghai")


def _get_int_env(name: str, default: int, *, minimum: int) -> int:
    """读取数据库连接池整数配置，非法值回退到安全默认值。"""
    raw_value = (os.getenv(name) or "").strip()
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return max(value, minimum)


DB_POOL_SIZE = _get_int_env("DB_POOL_SIZE", 2, minimum=1)
DB_MAX_OVERFLOW = _get_int_env("DB_MAX_OVERFLOW", 2, minimum=0)
DB_POOL_TIMEOUT = _get_int_env("DB_POOL_TIMEOUT", 15, minimum=1)
DB_POOL_RECYCLE = _get_int_env("DB_POOL_RECYCLE", 1800, minimum=30)

# 统一 Python 进程本地时间，避免 datetime.now() 在服务器 UTC 环境下写入非北京时间。
os.environ["TZ"] = APP_TIMEZONE
if hasattr(time, "tzset"):
    time.tzset()

# 配置数据库引擎，添加连接超时和自动重连
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # 自动检测并重连断开的连接
    connect_args={
        "connect_timeout": 5,  # 连接超时5秒
        "options": f"-c statement_timeout=30000 -c timezone={APP_TIMEZONE}"  # 查询超时30秒，并使用北京时间会话
    },
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    pool_use_lifo=True,
    echo=False  # 不打印SQL语句
)


@event.listens_for(engine, "connect")
def set_db_timezone(dbapi_connection, _connection_record):
    """连接池中新建连接时固定数据库会话时区。"""
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET TIME ZONE %s", (APP_TIMEZONE,))


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
