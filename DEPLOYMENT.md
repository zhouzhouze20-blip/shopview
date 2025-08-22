# 商业地产资源管理系统 Docker 部署指南

## 概述

这是一个完整的 Docker 部署配置，包含了商业地产资源管理系统的所有组件：
- Node.js/Express 后端应用
- React 前端应用
- PostgreSQL 数据库
- Nginx 反向代理

## 快速部署

### 1. 准备服务器环境

确保服务器已安装：
- Docker (>= 20.10)
- Docker Compose (>= 2.0)

```bash
# 安装 Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 上传项目文件

将以下文件上传到服务器：
```
商业地产管理系统/
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── init-db.sql
├── .dockerignore
├── 项目源代码文件...
```

### 3. 配置环境变量

创建 `.env` 文件：
```bash
# 数据库配置
POSTGRES_PASSWORD=your_secure_password_here

# 应用配置
NODE_ENV=production
```

### 4. 生成 SSL 证书（可选）

如果需要 HTTPS 支持，创建 SSL 证书：
```bash
mkdir ssl
cd ssl

# 生成自签名证书（开发环境）
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout server.key -out server.crt

# 或者使用 Let's Encrypt 证书（生产环境）
# certbot certonly --webroot -w /path/to/webroot -d yourdomain.com
```

### 5. 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 6. 验证部署

访问以下地址验证部署：
- HTTP: http://your-server-ip:18080
- HTTPS: https://your-server-ip:18443
- 应用直接访问: http://your-server-ip:18000
- 健康检查: http://your-server-ip:18000/api/health

## 服务配置

### 端口配置
- **18080**: HTTP 访问（重定向到 HTTPS）
- **18443**: HTTPS 访问
- **15432**: PostgreSQL 数据库
- **18000**: 应用直接访问（不经过Nginx）

### 数据持久化
- PostgreSQL 数据: `postgres_data` 卷
- 应用日志: `app_logs` 卷

## 管理命令

### 查看服务状态
```bash
docker-compose ps
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f app
docker-compose logs -f postgres
```

### 重启服务
```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart app
```

### 停止服务
```bash
docker-compose down
```

### 更新应用
```bash
# 重新构建并部署
docker-compose down
docker-compose build app
docker-compose up -d
```

### 数据库管理

```bash
# 连接到数据库
docker-compose exec postgres psql -U postgres -d commercial_real_estate

# 备份数据库
docker-compose exec postgres pg_dump -U postgres commercial_real_estate > backup.sql

# 恢复数据库
docker-compose exec -T postgres psql -U postgres commercial_real_estate < backup.sql
```

## 监控和维护

### 健康检查
系统内置健康检查端点：
- `/api/health` - 应用健康状态
- Docker 健康检查会自动重启异常容器

### 日志管理
```bash
# 清理日志
docker system prune -f

# 查看容器资源使用
docker stats
```

### 备份策略
1. **数据库备份**: 每日自动备份 PostgreSQL
2. **应用数据**: 持久化卷定期备份
3. **配置文件**: 版本控制管理

## 安全配置

### 防火墙设置
```bash
# 只开放必要端口
ufw allow 18080/tcp
ufw allow 18443/tcp
ufw allow 18000/tcp
ufw allow 15432/tcp
ufw allow 22/tcp
ufw enable
```

### SSL 配置
- 使用强加密算法
- 启用 HSTS
- 配置安全头

### 数据库安全
- 强密码策略
- 网络隔离
- 定期更新

## 故障排除

### 常见问题

1. **容器无法启动**
   ```bash
   docker-compose logs container_name
   ```

2. **数据库连接失败**
   - 检查环境变量配置
   - 确认数据库容器运行状态

3. **Nginx 配置错误**
   ```bash
   docker-compose exec nginx nginx -t
   ```

4. **端口冲突**
   - 检查系统端口占用
   - 修改 docker-compose.yml 端口映射

### 性能优化

1. **增加资源限制**
   ```yaml
   deploy:
     resources:
       limits:
         memory: 1G
         cpus: '0.5'
   ```

2. **数据库优化**
   - 调整 PostgreSQL 配置
   - 添加适当索引

3. **Nginx 缓存**
   - 启用静态文件缓存
   - 配置 gzip 压缩

## 扩展部署

### 多实例部署
```yaml
app:
  scale: 3  # 运行 3 个应用实例
```

### 负载均衡
配置 Nginx upstream 多个应用实例。

## 支持

如有问题，请检查：
1. Docker 和 Docker Compose 版本
2. 服务器资源（内存、磁盘空间）
3. 网络连接
4. 防火墙配置

部署成功后，您的商业地产资源管理系统将在服务器上稳定运行！