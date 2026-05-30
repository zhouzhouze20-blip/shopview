"""
将数据库中的 alembic_version 从 initial_shopview 改为 replace_floors。
当本机没有 initial_shopview_tables.py 导致 alembic stamp 报错时，可先运行此脚本再执行 upgrade head。

用法（在 python_app 目录下）：
  ../venv/bin/python scripts_stamp_replace_floors.py
"""
import os
import sys
from pathlib import Path

# 确保能加载到项目配置（.env 可能在上级目录）
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.chdir(Path(__file__).resolve().parent)

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sales_user:sales_password_2024@192.168.98.80:5432/sales_db")

def main():
    try:
        import psycopg2
    except ImportError:
        print("需要 psycopg2，请先: pip install psycopg2-binary")
        sys.exit(1)
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("UPDATE alembic_version SET version_num = %s WHERE version_num = %s", ("replace_floors", "initial_shopview"))
    updated = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    if updated:
        print("已将 alembic_version 从 initial_shopview 改为 replace_floors。")
        print("请执行: ../venv/bin/python -m alembic upgrade head")
    else:
        conn2 = psycopg2.connect(DATABASE_URL)
        cur2 = conn2.cursor()
        cur2.execute("SELECT version_num FROM alembic_version")
        row = cur2.fetchone()
        cur2.close()
        conn2.close()
        if row:
            print(f"当前版本已是: {row[0]}，无需修改。")
        else:
            print("alembic_version 表为空，请先运行一次 alembic upgrade 或 stamp。")

if __name__ == "__main__":
    main()
