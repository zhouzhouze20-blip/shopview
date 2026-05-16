#!/usr/bin/env python3
"""
手工启动后端服务的 Python 脚本
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

# 加载环境变量
from dotenv import load_dotenv
env_file = project_root / "env.app"
if env_file.exists():
    print(f"📋 加载环境变量文件: {env_file}")
    load_dotenv(env_file)
else:
    print("⚠️  未找到 env.app 文件，使用默认配置")
    load_dotenv()

# 显示配置信息
print("=" * 50)
print("🚀 启动后端服务")
print("=" * 50)
print()
print("📊 配置信息:")
print(f"   数据库主机: {os.getenv('PGHOST', '未设置')}")
print(f"   数据库端口: {os.getenv('PGPORT', '未设置')}")
print(f"   数据库名称: {os.getenv('PGDATABASE', '未设置')}")
print(f"   应用端口: {os.getenv('PORT', '7000')}")
print()

# 启动服务
import uvicorn
port = int(os.getenv("PORT", 7000))

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

# 切换到 python_app 目录运行（确保相对导入正常工作）
import os
original_dir = os.getcwd()
os.chdir(str(python_app_dir))

try:
    uvicorn.run(
        "main:app",  # 在 python_app 目录下，直接使用 main:app
        host="0.0.0.0",
        port=port,
        reload=False  # 暂时禁用 reload 避免端口冲突
    )
finally:
    os.chdir(original_dir)
