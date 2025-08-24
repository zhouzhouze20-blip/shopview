#!/bin/bash

# 百货柜位管理系统 Docker 部署脚本
# 使用自定义端口避免冲突

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 检查依赖
check_dependencies() {
    print_message $BLUE "检查系统依赖..."
    
    if ! command -v docker &> /dev/null; then
        print_message $RED "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_message $RED "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    print_message $GREEN "依赖检查通过"
}

# 创建环境文件
create_env_file() {
    print_message $BLUE "创建环境配置文件..."
    
    if [ ! -f .env.prod ]; then
        cat > .env.prod << EOF
# 数据库配置
POSTGRES_PASSWORD=counter123!@#Change_This_Password
DATABASE_URL=postgresql://postgres:counter123!@#Change_This_Password@postgres:5432/counter_management

# 应用安全配置
SESSION_SECRET=your-super-secret-session-key-please-change-this-in-production
JWT_SECRET=your-jwt-secret-key-please-change-this-in-production

# CORS 配置
CORS_ORIGIN=http://localhost:18081

# 应用配置
NODE_ENV=production
MAX_FILE_SIZE=10485760

# 端口配置 (自定义端口避免冲突)
DB_PORT=15432
APP_PORT=18080
NGINX_HTTP_PORT=18081
NGINX_HTTPS_PORT=18444
EOF
        print_message $YELLOW "已创建 .env.prod 文件，请根据需要修改配置"
    else
        print_message $GREEN ".env.prod 文件已存在"
    fi
}

# 创建 SSL 目录 (如果需要 HTTPS)
create_ssl_dir() {
    print_message $BLUE "创建 SSL 证书目录..."
    
    if [ ! -d ssl ]; then
        mkdir -p ssl
        print_message $YELLOW "已创建 ssl 目录，请将 SSL 证书放置到该目录"
        print_message $YELLOW "需要的文件：server.crt 和 server.key"
    fi
}

# 构建和启动服务
deploy_services() {
    print_message $BLUE "开始部署服务..."
    
    # 停止现有服务
    print_message $YELLOW "停止现有服务..."
    docker-compose -f docker-compose.prod.yml --env-file .env.prod down
    
    # 清理旧镜像
    print_message $YELLOW "清理旧镜像..."
    docker system prune -f
    
    # 构建新镜像
    print_message $BLUE "构建应用镜像..."
    docker-compose -f docker-compose.prod.yml --env-file .env.prod build --no-cache
    
    # 启动服务
    print_message $GREEN "启动服务..."
    docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
    
    # 等待服务启动
    print_message $YELLOW "等待服务启动..."
    sleep 30
    
    # 检查服务状态
    print_message $BLUE "检查服务状态..."
    docker-compose -f docker-compose.prod.yml --env-file .env.prod ps
}

# 运行数据库迁移
run_migrations() {
    print_message $BLUE "运行数据库迁移..."
    
    # 等待数据库完全启动
    sleep 10
    
    # 运行迁移
    docker-compose -f docker-compose.prod.yml --env-file .env.prod exec app npm run db:push
    
    print_message $GREEN "数据库迁移完成"
}

# 显示部署信息
show_deployment_info() {
    print_message $GREEN "🎉 部署完成！"
    echo ""
    print_message $BLUE "服务访问地址："
    echo "  应用直接访问: http://localhost:18080"
    echo "  Nginx 反向代理: http://localhost:18081"
    echo "  数据库连接: localhost:15432"
    echo ""
    print_message $BLUE "端口说明："
    echo "  18080 - 应用服务端口"
    echo "  18081 - Nginx HTTP 端口 (推荐使用)"
    echo "  18444 - Nginx HTTPS 端口 (需要配置 SSL)"
    echo "  15432 - PostgreSQL 数据库端口"
    echo ""
    print_message $YELLOW "管理命令："
    echo "  查看日志: docker-compose -f docker-compose.prod.yml logs -f"
    echo "  停止服务: docker-compose -f docker-compose.prod.yml down"
    echo "  重启服务: docker-compose -f docker-compose.prod.yml restart"
    echo "  查看状态: docker-compose -f docker-compose.prod.yml ps"
}

# 健康检查
health_check() {
    print_message $BLUE "进行健康检查..."
    
    local retries=5
    local wait_time=10
    
    for i in $(seq 1 $retries); do
        if curl -f http://localhost:18081/health > /dev/null 2>&1; then
            print_message $GREEN "✅ 应用健康检查通过"
            return 0
        else
            print_message $YELLOW "⏳ 等待应用启动... ($i/$retries)"
            sleep $wait_time
        fi
    done
    
    print_message $RED "❌ 应用健康检查失败，请检查日志"
    return 1
}

# 主函数
main() {
    print_message $GREEN "🚀 开始部署百货柜位管理系统"
    echo "======================================"
    
    check_dependencies
    create_env_file
    create_ssl_dir
    deploy_services
    
    if health_check; then
        run_migrations
        show_deployment_info
    else
        print_message $RED "部署失败，请检查日志：docker-compose -f docker-compose.prod.yml logs"
        exit 1
    fi
}

# 参数处理
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        print_message $YELLOW "停止所有服务..."
        docker-compose -f docker-compose.prod.yml --env-file .env.prod down
        ;;
    "restart")
        print_message $YELLOW "重启所有服务..."
        docker-compose -f docker-compose.prod.yml --env-file .env.prod restart
        ;;
    "logs")
        docker-compose -f docker-compose.prod.yml --env-file .env.prod logs -f
        ;;
    "status")
        docker-compose -f docker-compose.prod.yml --env-file .env.prod ps
        ;;
    "health")
        health_check
        ;;
    *)
        echo "用法: $0 {deploy|stop|restart|logs|status|health}"
        echo ""
        echo "命令说明："
        echo "  deploy  - 部署应用 (默认)"
        echo "  stop    - 停止所有服务"
        echo "  restart - 重启所有服务"
        echo "  logs    - 查看实时日志"
        echo "  status  - 查看服务状态"
        echo "  health  - 健康检查"
        exit 1
        ;;
esac