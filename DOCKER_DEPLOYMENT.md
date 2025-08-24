# 百货柜位管理系统 Docker 部署指南

本文档介绍如何使用 Docker 部署百货柜位管理系统，所有端口配置均避开常用端口以防止冲突。

## 🚀 快速开始

### 前置要求
- Docker 20.10+
- Docker Compose 2.0+
- 至少 2GB 可用内存
- 至少 10GB 可用磁盘空间

### 一键部署
```bash
# 克隆项目（如果还没有）
git clone <your-repo-url>
cd counter-management-system

# 运行部署脚本
./deploy.sh
```

部署脚本会自动：
- 检查系统依赖
- 创建配置文件
- 构建 Docker 镜像
- 启动所有服务
- 运行数据库迁移
- 进行健康检查

## 📋 服务架构

### 服务列表
| 服务名 | 容器名 | 内部端口 | 外部端口 | 说明 |
|--------|--------|----------|----------|------|
| PostgreSQL | counter-management-db | 5432 | 15432 | 数据库服务 |
| 应用服务 | counter-management-app | 8080 | 18080 | Node.js 应用 |
| Nginx | counter-management-nginx | 8081/8444 | 18081/18444 | 反向代理 |

### 端口说明
- **15432**: PostgreSQL 数据库（避开默认 5432）
- **18080**: 应用直接访问端口（避开常用 5000）
- **18081**: Nginx HTTP 端口（避开默认 80，推荐使用）
- **18444**: Nginx HTTPS 端口（避开默认 443，需配置 SSL）

## 🔧 配置文件

### 环境配置 (.env.prod)
```env
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
```

**⚠️ 重要提示**: 请在生产环境中修改所有密码和密钥！

## 🛠️ 管理命令

### 基本操作
```bash
# 部署/重新部署
./deploy.sh deploy

# 停止所有服务
./deploy.sh stop

# 重启所有服务
./deploy.sh restart

# 查看服务状态
./deploy.sh status

# 查看实时日志
./deploy.sh logs

# 健康检查
./deploy.sh health
```

### Docker Compose 命令
```bash
# 查看服务状态
docker-compose -f docker-compose.prod.yml --env-file .env.prod ps

# 查看日志
docker-compose -f docker-compose.prod.yml --env-file .env.prod logs -f [service_name]

# 进入容器
docker-compose -f docker-compose.prod.yml --env-file .env.prod exec app sh
docker-compose -f docker-compose.prod.yml --env-file .env.prod exec postgres psql -U postgres -d counter_management

# 停止并删除容器
docker-compose -f docker-compose.prod.yml --env-file .env.prod down

# 重新构建镜像
docker-compose -f docker-compose.prod.yml --env-file .env.prod build --no-cache
```

## 🔒 SSL/HTTPS 配置（可选）

如果需要启用 HTTPS：

1. **准备 SSL 证书**
   ```bash
   mkdir -p ssl
   # 将证书文件放入 ssl 目录
   # 需要的文件: server.crt, server.key
   ```

2. **启用 HTTPS 配置**
   编辑 `nginx.prod.conf`，取消注释 HTTPS server 配置块

3. **重新部署**
   ```bash
   ./deploy.sh restart
   ```

## 🗄️ 数据库管理

### 数据库连接
```bash
# 连接到数据库
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d counter_management

# 或从外部连接
psql -h localhost -p 15432 -U postgres -d counter_management
```

### 备份与恢复
```bash
# 备份数据库
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres counter_management > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复数据库
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U postgres counter_management < backup_file.sql
```

### 数据库迁移
```bash
# 运行迁移
docker-compose -f docker-compose.prod.yml exec app npm run db:push

# 查看迁移状态
docker-compose -f docker-compose.prod.yml exec app npm run check
```

## 📊 监控与日志

### 日志查看
```bash
# 查看所有服务日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.prod.yml logs -f app
docker-compose -f docker-compose.prod.yml logs -f postgres
docker-compose -f docker-compose.prod.yml logs -f nginx
```

### 健康检查
```bash
# 应用健康检查
curl http://localhost:18081/health

# 数据库健康检查
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U postgres
```

### 性能监控
```bash
# 查看容器资源使用
docker stats

# 查看容器详细信息
docker-compose -f docker-compose.prod.yml exec app top
```

## 🚨 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 检查端口占用
   netstat -tlnp | grep :18081
   
   # 修改 docker-compose.prod.yml 中的端口映射
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据库容器状态
   docker-compose -f docker-compose.prod.yml ps postgres
   
   # 查看数据库日志
   docker-compose -f docker-compose.prod.yml logs postgres
   ```

3. **应用启动失败**
   ```bash
   # 查看应用日志
   docker-compose -f docker-compose.prod.yml logs app
   
   # 检查环境变量
   docker-compose -f docker-compose.prod.yml exec app env | grep -E "(NODE_ENV|DATABASE_URL|PORT)"
   ```

4. **Nginx 配置错误**
   ```bash
   # 测试 Nginx 配置
   docker-compose -f docker-compose.prod.yml exec nginx nginx -t
   
   # 重载 Nginx 配置
   docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
   ```

### 重置环境
```bash
# 停止所有服务
./deploy.sh stop

# 删除所有容器和卷
docker-compose -f docker-compose.prod.yml down -v

# 清理镜像
docker system prune -a -f

# 重新部署
./deploy.sh deploy
```

## 📈 性能优化

### 数据库优化
- 定期进行数据库维护：`VACUUM ANALYZE`
- 监控连接数和慢查询
- 根据需要调整 PostgreSQL 配置参数

### 应用优化
- 监控内存使用和 CPU 占用
- 启用应用性能监控（APM）
- 配置适当的日志级别

### Nginx 优化
- 启用 Gzip 压缩（已配置）
- 配置静态文件缓存（已配置）
- 根据需要调整 worker 进程数

## 🔄 更新部署

### 应用更新
```bash
# 拉取最新代码
git pull origin main

# 重新构建和部署
./deploy.sh deploy
```

### 零停机更新
```bash
# 构建新镜像
docker-compose -f docker-compose.prod.yml build --no-cache app

# 滚动更新
docker-compose -f docker-compose.prod.yml up -d --no-deps app
```

## 📞 支持

如遇到问题，请：
1. 查看相关服务日志
2. 检查配置文件
3. 确认端口可用性
4. 验证环境变量设置

---

**注意**: 本部署方案使用自定义端口以避免与其他服务冲突，请确保防火墙已开放相应端口。