#!/bin/bash

# 百货柜位管理系统 Python版本构建和部署脚本
# Department Store Counter Management System - Python Build & Deploy Script

set -e

echo "🏢 百货柜位管理系统 Python版本 - 构建和部署"
echo "================================================"

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ 错误: Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 创建必要的目录
echo "📁 创建必要目录..."
mkdir -p ssl logs

# 检查环境变量文件
if [ ! -f .env.python ]; then
    echo "📝 创建环境配置文件..."
    cat > .env.python << EOF
# 百货柜位管理系统 Python版本 环境配置
DATABASE_URL=postgresql://postgres:postgres123@localhost:15433/counter_management
POSTGRES_PASSWORD=postgres123
DEBUG=true
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
EOF
fi

# 停止现有服务
echo "🛑 停止现有服务..."
docker-compose -f docker-compose.python.yml down 2>/dev/null || true

# 清理旧镜像
echo "🧹 清理旧镜像..."
docker system prune -f || true

# 构建和启动服务
echo "🔨 构建Python应用..."
docker-compose -f docker-compose.python.yml build --no-cache

echo "🚀 启动服务..."
docker-compose -f docker-compose.python.yml up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 15

# 检查服务状态
echo "📊 检查服务状态..."
docker-compose -f docker-compose.python.yml ps

# 健康检查
echo "🏥 执行健康检查..."
for i in {1..10}; do
    if curl -sf http://localhost:18001/api/health > /dev/null 2>&1; then
        echo "✅ Python应用健康检查通过"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "❌ Python应用健康检查失败"
        echo "🔍 查看应用日志:"
        docker-compose -f docker-compose.python.yml logs python-app
        exit 1
    fi
    echo "   等待服务就绪... ($i/10)"
    sleep 3
done

# 显示访问信息
echo ""
echo "🎉 部署成功！"
echo "================================================"
echo "🌐 访问地址:"
echo "   - API文档:         http://localhost:18001/docs"
echo "   - Nginx代理:       http://localhost:18081"
echo "   - 主API:          http://localhost:18001"
echo "   - PostgreSQL:     localhost:15433"
echo ""
echo "📋 管理命令:"
echo "   - 查看日志:        docker-compose -f docker-compose.python.yml logs -f"
echo "   - 停止服务:        docker-compose -f docker-compose.python.yml down"
echo "   - 重启服务:        docker-compose -f docker-compose.python.yml restart"
echo "   - 查看状态:        docker-compose -f docker-compose.python.yml ps"
echo ""
echo "🏪 测试门店数据:"
echo "   - 常州购物中心 (CZ001)"
echo "   - 常州新世纪 (CZ002)"
echo ""

# 显示基本API测试
echo "🧪 API测试:"
echo "curl http://localhost:18001/api/stores"
echo "curl http://localhost:18001/api/dashboard/stats"
echo ""