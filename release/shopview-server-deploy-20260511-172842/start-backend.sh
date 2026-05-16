#!/bin/bash

# 启动后端服务 - Linux/Mac版本
echo "========================================"
echo "🏢 启动后端服务 - ShopView"
echo "========================================"
echo ""

# 检查是否在项目根目录
if [ ! -f "python_app/main.py" ]; then
    echo "❌ 错误: 请在项目根目录下运行此脚本"
    exit 1
fi

# 检查Python是否安装
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ 错误: 未找到Python，请先安装Python"
    exit 1
fi

# 确定Python命令
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
    PIP_CMD=pip3
else
    PYTHON_CMD=python
    PIP_CMD=pip
fi

echo "✅ Python版本: $($PYTHON_CMD --version)"

# 检查依赖是否安装
echo "📦 检查Python依赖..."
if ! $PYTHON_CMD -c "import fastapi" 2>/dev/null; then
    echo "⚠️  检测到依赖未安装，正在安装..."
    $PIP_CMD install -r python_requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        exit 1
    fi
else
    echo "✅ 依赖已安装"
fi

# 加载环境变量
if [ -f "env.app" ]; then
    echo "📋 加载环境变量..."
    export $(grep -v '^#' env.app | grep '=' | xargs)
fi

# 显示配置信息
PORT=${PORT:-8000}
echo ""
echo "📊 配置信息:"
echo "   数据库主机: ${PGHOST:-未设置}"
echo "   数据库端口: ${PGPORT:-未设置}"
echo "   数据库名称: ${PGDATABASE:-未设置}"
echo "   应用端口: $PORT"
echo ""

# 启动应用
echo "🚀 启动后端服务..."
echo ""
echo "🌐 访问地址: http://localhost:$PORT"
echo "📖 API文档: http://localhost:$PORT/api/docs"
echo "🔍 健康检查: http://localhost:$PORT/api/health"
echo ""
echo "💡 按 Ctrl+C 停止服务"
echo "========================================"
echo ""

# 切换到 python_app 目录前，确保环境变量已加载
# 注意：需要在项目根目录运行，以便能找到 env.app 文件
cd python_app

# 运行 uvicorn，并确保 Python 路径包含项目根目录
PYTHONPATH="$PWD/..:$PYTHONPATH" $PYTHON_CMD -m uvicorn main:app --host 0.0.0.0 --port $PORT --reload
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 后端服务启动失败"
    cd ..
    exit 1
fi

cd ..
