#!/bin/bash

# 启动 Mock API 服务器（用于前端展示，无需数据库）

echo "=========================================="
echo "🚀 启动 Mock API 服务器"
echo "=========================================="
echo ""

# 检查 Node.js 是否安装
if ! command -v node &> /dev/null; then
    echo "❌ 错误: 未找到 Node.js"
    echo "   请先安装 Node.js: https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js 版本: $(node --version)"
echo ""

# 检查 mock-api-server.js 是否存在
if [ ! -f "mock-api-server.js" ]; then
    echo "❌ 错误: 未找到 mock-api-server.js"
    exit 1
fi

# 启动服务器
echo "🌐 启动 Mock API 服务器..."
echo "   地址: http://localhost:8000"
echo "   健康检查: http://localhost:8000/api/health"
echo ""
echo "💡 提示: 按 Ctrl+C 停止服务器"
echo "=========================================="
echo ""

node mock-api-server.js
