#!/bin/bash

# 数据库连接诊断脚本

echo "=========================================="
echo "🔍 数据库连接详细诊断"
echo "=========================================="
echo ""

# 加载环境变量
if [ -f "env.app" ]; then
    export $(grep -v '^#' env.app | grep '=' | xargs)
fi

PGHOST=${PGHOST:-192.168.98.80}
PGPORT=${PGPORT:-5432}
PGDATABASE=${PGDATABASE:-sales_db}
PGUSER=${PGUSER:-sales_user}
PGPASSWORD=${PGPASSWORD:-sales_password_2024}

echo "📊 配置信息:"
echo "   主机: $PGHOST"
echo "   端口: $PGPORT"
echo "   数据库: $PGDATABASE"
echo "   用户: $PGUSER"
echo ""

# 1. 测试网络连通性
echo "1️⃣  测试网络连通性..."
if ping -c 2 -W 2 $PGHOST > /dev/null 2>&1; then
    echo "   ✅ 可以 ping 通 $PGHOST"
else
    echo "   ❌ 无法 ping 通 $PGHOST"
    echo "   💡 可能原因: 网络不通、需要 VPN、IP 地址错误"
fi
echo ""

# 2. 测试端口连通性
echo "2️⃣  测试端口连通性..."
if command -v nc &> /dev/null; then
    if nc -zv -w 2 $PGHOST $PGPORT > /dev/null 2>&1; then
        echo "   ✅ 端口 $PGPORT 可以访问"
    else
        echo "   ❌ 端口 $PGPORT 无法访问"
        echo "   💡 可能原因: 防火墙阻止、数据库服务未运行"
    fi
else
    echo "   ⚠️  nc (netcat) 未安装，跳过端口测试"
fi
echo ""

# 3. 使用 Python 测试数据库连接
echo "3️⃣  测试 PostgreSQL 数据库连接..."
python3 << 'PYTHON_SCRIPT'
import sys
import os
import socket

pg_host = os.getenv('PGHOST', '192.168.98.80')
pg_port = int(os.getenv('PGPORT', '5432'))
pg_database = os.getenv('PGDATABASE', 'sales_db')
pg_user = os.getenv('PGUSER', 'sales_user')
pg_password = os.getenv('PGPASSWORD', 'sales_password_2024')

print(f"   尝试连接到: {pg_user}@{pg_host}:{pg_port}/{pg_database}")

# 先测试 TCP 连接
try:
    print(f"   - 测试 TCP 连接...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex((pg_host, pg_port))
    sock.close()
    
    if result == 0:
        print(f"   ✅ TCP 连接成功")
    else:
        print(f"   ❌ TCP 连接失败 (错误码: {result})")
        print(f"   💡 无法连接到 {pg_host}:{pg_port}")
        print(f"   💡 请检查:")
        print(f"      1. 网络连接是否正常")
        print(f"      2. 是否需要 VPN 或内网访问")
        print(f"      3. IP 地址是否正确")
        print(f"      4. 防火墙是否允许访问")
        sys.exit(1)
except socket.gaierror as e:
    print(f"   ❌ DNS 解析失败: {e}")
    print(f"   💡 无法解析主机名 {pg_host}")
    print(f"   💡 请检查 IP 地址是否正确")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ 连接测试失败: {e}")
    sys.exit(1)

# 测试 PostgreSQL 连接
try:
    import psycopg2
    print(f"   - 测试 PostgreSQL 连接...")
    conn = psycopg2.connect(
        host=pg_host,
        port=pg_port,
        database=pg_database,
        user=pg_user,
        password=pg_password,
        connect_timeout=5
    )
    print(f"   ✅ PostgreSQL 连接成功!")
    
    # 查询数据库信息
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print(f"   📊 PostgreSQL 版本: {version.split(',')[0]}")
    
    cur.execute("SELECT current_database();")
    db_name = cur.fetchone()[0]
    print(f"   📊 当前数据库: {db_name}")
    
    # 检查表是否存在
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        LIMIT 5
    """)
    tables = cur.fetchall()
    if tables:
        print(f"   📊 发现 {len(tables)} 个表（示例）: {', '.join([t[0] for t in tables])}")
    else:
        print(f"   ⚠️  数据库中没有表")
    
    cur.close()
    conn.close()
    sys.exit(0)
    
except psycopg2.OperationalError as e:
    error_msg = str(e)
    if "does not exist" in error_msg:
        print(f"   ❌ 数据库不存在: {pg_database}")
        print(f"   💡 数据库 '{pg_database}' 在服务器上不存在")
        print(f"   💡 请检查数据库名称是否正确，或联系数据库管理员创建数据库")
    elif "authentication failed" in error_msg or "password authentication failed" in error_msg:
        print(f"   ❌ 认证失败: 用户名或密码错误")
        print(f"   💡 请检查 env.app 中的 PGUSER 和 PGPASSWORD")
    elif "could not translate host name" in error_msg or "nodename nor servname" in error_msg:
        print(f"   ❌ 无法解析主机名: {pg_host}")
        print(f"   💡 网络连接问题，无法解析 IP 地址")
    else:
        print(f"   ❌ PostgreSQL 连接失败: {error_msg}")
    sys.exit(1)
except ImportError:
    print(f"   ❌ psycopg2 未安装")
    print(f"   💡 请运行: pip install psycopg2-binary")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ 发生错误: {e}")
    sys.exit(1)

PYTHON_SCRIPT

EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 诊断完成 - 数据库连接正常"
else
    echo "❌ 诊断完成 - 发现问题，请查看上面的错误信息"
fi
echo "=========================================="
