#!/usr/bin/env python3
"""
百货柜位管理系统 Python版本启动脚本
Department Store Counter Management System - Python Version Launcher
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    """启动Python版本的百货柜位管理系统"""
    print("🏢 启动百货柜位管理系统 (Python版本)")
    print("=" * 50)
    
    # 检查Python环境
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("❌ 错误: 需要Python 3.8或更高版本")
        return
    
    print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 设置环境变量
    env_file = Path(".env.python")
    if env_file.exists():
        print("✅ 加载环境配置文件")
    else:
        print("⚠️  环境配置文件不存在，使用默认配置")
    
    # 启动FastAPI应用
    try:
        print("🚀 启动FastAPI服务器...")
        print("📍 访问地址:")
        print("   - API文档: http://localhost:8000/api/docs")
        print("   - 主页: http://localhost:8000")
        print("   - 健康检查: http://localhost:8000/api/health")
        print()
        print("💡 门店信息:")
        print("   1. 常州购物中心 (CZ001)")
        print("   2. 常州新世纪 (CZ002)")
        print()
        print("按 Ctrl+C 停止服务")
        print("=" * 50)
        
        # 设置PYTHONPATH
        current_dir = Path(__file__).parent
        os.environ["PYTHONPATH"] = str(current_dir)
        
        # 启动uvicorn服务器
        os.chdir(current_dir)
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "python_app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
        
    except KeyboardInterrupt:
        print("\n🛑 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    main()