#!/usr/bin/env python3
"""
直接启动后端服务（不使用虚拟环境，使用系统 Python）
"""
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
python_app_dir = project_root / "python_app"

# 确保 python_app 目录在 Python 路径中
sys.path.insert(0, str(python_app_dir))
sys.path.insert(0, str(project_root))

# 加载环境变量（在检查依赖之前先手动加载，避免导入错误）
env_file = project_root / "env.app"
if env_file.exists():
    print(f"📋 加载环境变量文件: {env_file}")
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# 如果 python-dotenv 已安装，也使用它（更可靠）
try:
    from dotenv import load_dotenv
    load_dotenv(env_file)
except ImportError:
    pass  # 已经手动加载了，继续执行

# 显示配置信息
print("=" * 50)
print("🚀 启动后端服务（系统 Python）")
print("=" * 50)
print()
print("📊 配置信息:")
print(f"   Python 版本: {sys.version.split()[0]}")
print(f"   Python 路径: {sys.executable}")
print(f"   数据库主机: {os.getenv('PGHOST', '未设置')}")
print(f"   数据库端口: {os.getenv('PGPORT', '未设置')}")
print(f"   数据库名称: {os.getenv('PGDATABASE', '未设置')}")
print(f"   应用端口: {os.getenv('PORT', '7000')}")
print()

# 启动服务
try:
    import uvicorn
except ImportError:
    print("❌ 错误: uvicorn 未安装")
    print("💡 请运行: pip3 install uvicorn fastapi")
    sys.exit(1)

port = int(os.getenv("PORT", "7000"))

print(f"🌐 启动地址: http://localhost:{port}")
print(f"📖 API文档: http://localhost:{port}/api/docs")
print(f"🔍 健康检查: http://localhost:{port}/api/health")
print()
print("💡 按 Ctrl+C 停止服务")
print("=" * 50)
print()

# 检查端口是否被占用
import socket
def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

if is_port_in_use(port):
    print(f"❌ 错误: 端口 {port} 已被占用")
    print(f"💡 请运行: kill -9 $(lsof -ti:{port})")
    sys.exit(1)

# 检查必需的依赖是否已安装
missing_modules = []
try:
    import fastapi
except ImportError:
    missing_modules.append("fastapi")

try:
    import uvicorn
except ImportError:
    missing_modules.append("uvicorn")

try:
    import sqlalchemy
except ImportError:
    missing_modules.append("sqlalchemy")

try:
    import psycopg2
except ImportError:
    missing_modules.append("psycopg2-binary")

try:
    from dotenv import load_dotenv
except ImportError:
    missing_modules.append("python-dotenv")

if missing_modules:
    print("❌ 缺少必需的 Python 模块:")
    for module in missing_modules:
        print(f"   - {module}")
    print()
    print("💡 请先安装依赖:")
    print(f"   pip3 install {' '.join(missing_modules)}")
    print()
    print("   或者安装所有依赖:")
    print("   pip3 install -r python_requirements.txt")
    sys.exit(1)

# 切换到 python_app 目录运行（确保相对导入正常工作）
original_dir = os.getcwd()
os.chdir(str(python_app_dir))

try:
    uvicorn.run(
        "main:app",  # 在 python_app 目录下，直接使用 main:app
        host="0.0.0.0",
        port=port,
        reload=False  # 禁用 reload 避免端口冲突
    )
finally:
    os.chdir(original_dir)
