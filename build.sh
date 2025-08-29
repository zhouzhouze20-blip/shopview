#!/bin/bash

# 百货柜位管理系统 Docker 部署脚本

echo "🏢 构建百货柜位管理系统 Docker 镜像..."

# 检查是否存在 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  .env 文件不存在，复制示例文件..."
    cp .env.example .env
    echo "✅ 已创建 .env 文件，请根据需要修改配置"
fi

# 停止并删除现有容器
echo "🔄 停止现有服务..."
docker-compose down

# 删除旧镜像（可选）
echo "🗑️  清理旧镜像..."
docker image prune -f

# 构建镜像
echo "🔨 构建 Docker 镜像..."
docker-compose build --no-cache

# 启动服务
echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "📊 检查服务状态..."
docker-compose ps

# 检查应用健康状态
echo "🏥 检查应用健康状态..."
curl -f http://localhost:2000/api/health || echo "❌ 应用健康检查失败"

echo ""
echo "✅ 部署完成！"
echo ""
echo "📋 服务访问地址:"
echo "   🌐 应用地址: http://localhost:2000"
echo "   🗄️  数据库地址: localhost:25432"
echo "   🔧 Nginx代理: http://localhost:28090"
echo ""
echo "🔧 管理命令:"
echo "   查看日志: docker-compose logs -f"
echo "   停止服务: docker-compose down"
echo "   重启服务: docker-compose restart"
echo "