# 百货柜位管理系统 Docker 部署指南

## 🚀 快速开始

### 1. 一键部署
```bash
# 执行部署脚本
./build.sh
```

### 2. 手动部署
```bash
# 复制环境变量文件
cp .env.example .env

# 构建并启动服务
docker-compose up -d --build
```

## 📋 服务配置

### 端口配置
- **应用端口**: 2000
- **数据库端口**: 25432  
- **Nginx代理**: 28090 (HTTP) / 28443 (HTTPS)

### 服务访问地址
| 服务 | 地址 | 说明 |
|------|------|------|
| 主应用 | http://localhost:2000 | 百货柜位管理系统 |
| Nginx代理 | http://localhost:28090 | 带负载均衡的访问入口 |
| 数据库 | localhost:25432 | PostgreSQL数据库 |

## 🗂️ 项目结构

```
.
├── Dockerfile              # 应用容器配置
├── docker-compose.yml      # 容器编排配置
├── nginx.conf              # Nginx反向代理配置
├── build.sh               # 一键部署脚本
├── .dockerignore          # Docker忽略文件
└── .env.example           # 环境变量示例
```

## ⚙️ 环境变量配置

主要环境变量：
```bash
# 应用配置
NODE_ENV=production
PORT=2000

# 数据库配置
DATABASE_URL=postgresql://postgres:postgres123@postgres:5432/commercial_real_estate
POSTGRES_PASSWORD=postgres123
POSTGRES_DB=commercial_real_estate
POSTGRES_USER=postgres

# 数据库配置系统支持
DB_TYPE=postgresql
DB_HOST=postgres
DB_PORT=5432
DB_NAME=commercial_real_estate
DB_USER=postgres
DB_PASSWORD=postgres123
```

## 🔧 管理命令

### 基础操作
```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f app

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 完全清理（删除数据卷）
docker-compose down -v
```

### 数据库管理
```bash
# 连接数据库
docker-compose exec postgres psql -U postgres -d commercial_real_estate

# 数据库备份
docker-compose exec postgres pg_dump -U postgres commercial_real_estate > backup.sql

# 数据库恢复
docker-compose exec -T postgres psql -U postgres commercial_real_estate < backup.sql
```

## 🏥 健康检查

系统提供了完整的健康检查机制：

### 应用健康检查
```bash
curl http://localhost:2000/api/health
```

### 数据库健康检查
```bash
docker-compose exec postgres pg_isready -U postgres
```

### 容器状态监控
```bash
# 查看容器健康状态
docker-compose ps
```

## 📊 监控和日志

### 日志查看
```bash
# 查看应用日志
docker-compose logs -f app

# 查看数据库日志
docker-compose logs -f postgres

# 查看Nginx日志
docker-compose logs -f nginx
```

### 性能监控
系统支持：
- 应用响应时间监控
- 数据库连接池状态
- Nginx访问统计

## 🔒 安全配置

### 生产环境建议
1. **修改默认密码**
   ```bash
   # 修改 .env 文件中的 POSTGRES_PASSWORD
   POSTGRES_PASSWORD=your_secure_password
   ```

2. **启用HTTPS**
   - 取消注释 nginx.conf 中的 HTTPS 配置
   - 添加SSL证书到 ./ssl 目录

3. **防火墙配置**
   ```bash
   # 只开放必要端口
   ufw allow 2000
   ufw allow 28090
   ufw allow 28443
   ```

## 🐛 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 检查端口占用
   netstat -tulpn | grep :2000
   
   # 修改 docker-compose.yml 中的端口映射
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据库容器状态
   docker-compose logs postgres
   
   # 重启数据库服务
   docker-compose restart postgres
   ```

3. **应用启动失败**
   ```bash
   # 查看应用日志
   docker-compose logs app
   
   # 重新构建镜像
   docker-compose build --no-cache app
   ```

## 📈 扩展部署

### 多实例部署
```yaml
# docker-compose.yml 中添加
app2:
  build: .
  ports:
    - "2001:2000"
  environment:
    PORT: 2000
```

### 负载均衡配置
在 nginx.conf 中添加多个upstream服务器：
```nginx
upstream app_backend {
    server app:2000;
    server app2:2000;
}
```

## 📞 技术支持

如遇到部署问题，请检查：
1. Docker和Docker Compose版本
2. 系统资源使用情况
3. 网络连接状态
4. 环境变量配置