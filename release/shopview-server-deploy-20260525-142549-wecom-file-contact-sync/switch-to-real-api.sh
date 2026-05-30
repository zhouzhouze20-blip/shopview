#!/bin/bash

# 切换到真实后端 API 的快速脚本

echo "=========================================="
echo "🔄 切换到真实后端 API"
echo "=========================================="
echo ""

# 检查是否在项目根目录
if [ ! -f "python_app/main.py" ]; then
    echo "❌ 错误: 请在项目根目录下运行此脚本"
    exit 1
fi

# 步骤 1: 停止 Mock API 服务器
echo "1️⃣  停止 Mock API 服务器..."
MOCK_API_PID=$(lsof -ti:8000)
if [ -n "$MOCK_API_PID" ]; then
    echo "   发现 Mock API 进程 (PID: $MOCK_API_PID)"
    kill -9 $MOCK_API_PID 2>/dev/null
    echo "   ✅ Mock API 已停止"
else
    echo "   ✅ Mock API 未运行"
fi
echo ""

# 等待端口释放
sleep 1

# 步骤 2: 检查端口是否被占用
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "⚠️  警告: 端口 8000 仍被占用"
    echo "   请手动检查: lsof -i:8000"
    echo ""
fi

# 步骤 3: 检查 env.app 配置
echo "2️⃣  检查后端配置..."
if [ -f "env.app" ]; then
    PORT=$(grep "^PORT=" env.app | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    if [ -z "$PORT" ]; then
        PORT=2000
        echo "   ⚠️  未在 env.app 中找到 PORT，使用默认值: $PORT"
        echo "   💡 提示: 如果前端配置的是 8000 端口，请在 env.app 中添加 PORT=8000"
    else
        echo "   ✅ 后端端口配置: $PORT"
    fi
else
    PORT=2000
    echo "   ⚠️  未找到 env.app 文件，使用默认端口: $PORT"
fi
echo ""

# 步骤 4: 显示下一步操作
echo "=========================================="
echo "✅ 切换准备完成"
echo "=========================================="
echo ""
echo "📋 下一步操作:"
echo ""
echo "   启动真实后端服务:"
echo "   ./start-backend.sh"
echo ""
echo "   💡 如果后端端口与前端不匹配:"
echo "   - 后端端口: $PORT"
echo "   - 前端配置: http://localhost:8000 (查看 client/src/lib/api.ts)"
echo "   - 如果不同，请修改 env.app 中的 PORT=8000"
echo ""
echo "   验证连接:"
echo "   curl http://localhost:$PORT/api/health"
echo ""
echo "=========================================="
