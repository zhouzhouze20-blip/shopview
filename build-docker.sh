#!/bin/bash

# 商业地产资源管理系统 Docker 构建脚本

set -e

echo "🏢 开始构建商业地产资源管理系统 Docker 镜像..."

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ 错误: Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 设置镜像名称和标签
IMAGE_NAME="commercial-real-estate-app"
TAG="latest"

echo "📦 构建 Docker 镜像: ${IMAGE_NAME}:${TAG}"

# 构建 Docker 镜像
docker build -t ${IMAGE_NAME}:${TAG} .

if [ $? -eq 0 ]; then
    echo "✅ Docker 镜像构建成功!"
    
    # 显示镜像信息
    echo "📋 镜像信息:"
    docker images ${IMAGE_NAME}:${TAG}
    
    echo ""
    echo "🚀 部署选项:"
    echo "1. 本地运行: docker-compose up -d"
    echo "2. 查看日志: docker-compose logs -f"
    echo "3. 停止服务: docker-compose down"
    echo ""
    echo "📖 详细部署说明请查看 DEPLOYMENT.md 文件"
    
else
    echo "❌ Docker 镜像构建失败!"
    exit 1
fi

# 可选：自动启动服务
read -p "🤔 是否立即启动服务? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 启动服务..."
    
    # 检查是否有 .env 文件
    if [ ! -f ".env" ]; then
        echo "📝 创建环境配置文件..."
        cp .env.example .env
        echo "⚠️  请检查并修改 .env 文件中的配置，特别是数据库密码"
    fi
    
    # 启动服务
    docker-compose up -d
    
    echo "✅ 服务启动完成!"
    echo "🌐 应用访问地址: http://localhost:18000"
    echo "🌐 Nginx代理地址: http://localhost:18080 (HTTP) / https://localhost:18443 (HTTPS)"
    echo "💾 数据库端口: 15432"
    echo "📊 健康检查: http://localhost:18000/api/health"
    
    # 等待服务启动
    echo "⏳ 等待服务启动..."
    sleep 10
    
    # 检查服务状态
    echo "📊 服务状态:"
    docker-compose ps
    
else
    echo "👍 镜像已构建完成，稍后可使用 docker-compose up -d 启动服务"
fi