# 百货柜位管理系统 - Docker部署指南

## 概述

本指南将帮助您在Linux服务器上部署百货柜位管理系统。系统包含React前端和Python FastAPI后端，使用Docker容器化部署。

## 系统要求

### Linux服务器要求
- Ubuntu 18.04+ 或 CentOS 7+ 或 RHEL 7+
- Docker 20.10+
- Docker Compose 2.0+
- 至少 2GB RAM
- 至少 10GB 磁盘空间
- 已配置的PostgreSQL数据库

### 说明
本指南面向Linux服务器的生产部署流程。

## 部署方式

当前仅保留“部署应用，连接现有 PostgreSQL 数据库”这一种方式。

#### 1. 准备环境配置文件

编辑 `env.app-only.linux` 文件，配置您的数据库连接信息：

```bash
# 数据库配置
DATABASE_URL=postgresql://用户名:密码@数据库地址:端口/数据库名
PGHOST=数据库地址
PGPORT=5432
PGUSER=用户名
PGPASSWORD=密码
PGDATABASE=数据库名
```

#### 2. 在Linux服务器上部署

```bash
# 1. 进入部署目录
cd /opt/shopview

# 2. 配置环境变量
nano env.app-only.linux

# 3. 启动应用
docker compose up --build -d
```

## 配置说明

### 环境变量配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | 数据库连接URL | `postgresql://sales_user:sales_password_2024@192.168.98.80:5432/sales_db` |
| `PGHOST` | 数据库主机 | `192.168.98.80` |
| `PGPORT` | 数据库端口 | `5432` |
| `PGUSER` | 数据库用户名 | `sales_user` |
| `PGPASSWORD` | 数据库密码 | `sales_password_2024` |
| `PGDATABASE` | 数据库名 | `sales_db` |
| `APP_PORT` | 应用端口 | `7000` |
| `NGINX_PORT` | Nginx端口 | `80` |
| `TZ` | 时区 | `Asia/Shanghai` |

### 端口配置

- **7000**: 应用主端口
- **80**: Nginx HTTP端口
- **443**: Nginx HTTPS端口（可选）

## 访问系统

部署完成后，您可以通过以下地址访问系统：

- **前端界面**: http://服务器IP:7000
- **API文档**: http://服务器IP:7000/api/docs
- **健康检查**: http://服务器IP:7000/api/health
- **数据库测试**: http://服务器IP:7000/api/test-db

## 管理命令

### 查看服务状态

```bash
docker compose ps
```

### 查看日志

```bash
# 查看所有服务日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f shopview-app
```

### 重启服务

```bash
# 重启所有服务
docker compose restart

# 重启特定服务
docker compose restart shopview-app
```

### 停止服务

```bash
docker compose down
```

### 更新应用

```bash
# 1. 停止服务
docker compose down

# 2. 重新构建镜像
docker compose build --no-cache

# 3. 启动服务
docker compose up -d
```

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库服务是否运行
   - 验证数据库连接配置
   - 确认防火墙设置

2. **应用启动失败**
   - 查看容器日志：`docker logs shopview-app`
   - 检查端口是否被占用
   - 验证环境变量配置

3. **前端无法访问**
   - 检查Nginx配置
   - 验证端口映射
   - 查看防火墙设置

### 日志位置

- **应用日志**: `/app/logs/` (容器内)
- **Nginx日志**: `/var/log/nginx/` (容器内)
- **Docker日志**: `docker logs 容器名`

### 性能优化

1. **增加工作进程**
   ```bash
   # 在Dockerfile.linux中修改
   CMD ["python", "-m", "uvicorn", "python_app.main:app", "--host", "0.0.0.0", "--port", "7000", "--workers", "4"]
   ```

2. **配置Nginx缓存**
   ```nginx
   # 在config/nginx.conf中添加缓存配置
   location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
       expires 1y;
       add_header Cache-Control "public, immutable";
   }
   ```

## 安全建议

1. **修改默认密码**
   - 更改数据库密码
   - 修改应用密钥

2. **配置防火墙**
   ```bash
   # 只开放必要端口
   ufw allow 80
   ufw allow 443
   ufw allow 22
   ```

3. **使用HTTPS**
   - 配置SSL证书
   - 启用HTTPS重定向

4. **定期备份**
   ```bash
   # 备份外部数据库
   pg_dump -h 192.168.98.80 -U sales_user sales_db > backup.sql
   
   # 备份上传文件
   tar -czf uploads-backup.tar.gz uploads/
   ```

## 支持

如果您在部署过程中遇到问题，请：

1. 查看日志文件
2. 检查配置文件
3. 验证网络连接
4. 联系技术支持

---

**注意**: 请根据您的实际环境调整配置参数，确保系统安全稳定运行。

