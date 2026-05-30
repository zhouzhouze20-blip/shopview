# ShopView 应用部署指南

## 概述
本配置仅部署应用服务，数据库和Nginx需要单独配置。

## 前置条件
1. Docker 已安装并运行
2. 本地PostgreSQL数据库已配置：
   - 主机: 192.168.98.80
   - 端口: 5432
   - 数据库名: sales_db
   - 用户名: sales_user
   - 密码: sales_password_2024

## 快速部署

```bash
# 构建并启动应用
docker-compose --env-file env.app-only.linux -f docker-compose.app-only.linux.yml up --build -d

# 查看日志
docker-compose -f docker-compose.app-only.linux.yml logs -f shopview-app

# 停止应用
docker-compose -f docker-compose.app-only.linux.yml down
```

## 配置说明

### 环境变量
建议使用 `env.app-only.linux` 并通过 `--env-file` 注入配置：
- 数据库连接信息
- 应用端口 (7000)
- 运行模式 (production)

### 端口映射
- 容器内端口: 7000
- 主机端口: 7000
- 访问地址: http://localhost:7000

## 验证部署
```bash
# 健康检查
curl http://localhost:7000/api/health

# 查看API文档
# 浏览器访问: http://localhost:7000/api/docs
```

## 故障排除

### 应用无法启动
1. 检查数据库连接是否正常
2. 查看应用日志: `docker-compose -f docker-compose.app-only.linux.yml logs shopview-app`
3. 确认端口7000未被占用

### 数据库连接失败
1. 确认PostgreSQL服务正在运行
2. 检查网络连接: `ping 192.168.98.80`
3. 验证数据库凭据是否正确

## 文件说明
- `docker-compose.app-only.linux.yml`: 仅包含应用的Docker Compose配置
- `Dockerfile.linux`: Python应用的Docker镜像构建文件
- `env.app-only.linux`: 应用环境变量配置
- `APP-DEPLOYMENT.md`: 本部署指南
