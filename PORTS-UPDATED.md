# 端口配置说明（方案1 - 避免冲突）

## 双环境端口配置

为了避免与服务器现有系统冲突，本项目采用双环境端口配置：

### Replit开发环境
- **Node.js应用**: 5000端口
- **用途**: 开发和测试

### Docker生产环境
- **PostgreSQL数据库**: 35432端口
- **Node.js应用**: 38000端口（容器内8000）
- **Nginx HTTP**: 38080端口
- **Nginx HTTPS**: 38443端口

## 服务端口映射表

| 服务 | Replit端口 | Docker容器内端口 | Docker主机端口 | 说明 |
|------|-----------|----------------|---------------|------|
| Node.js 应用 | 5000 | 8000 | **38000** | 应用服务器 |
| PostgreSQL | - | 5432 | **35432** | 数据库访问 |
| Nginx HTTP | - | 80 | **38080** | HTTP访问 |
| Nginx HTTPS | - | 443 | **38443** | HTTPS访问 |

## 访问地址

### 开发环境（Replit）
- **应用访问**: http://localhost:5000
- **健康检查**: http://localhost:5000/api/health

### 生产环境（Docker）
- **主要访问**: https://your-server-ip:38443
- **HTTP访问**: http://your-server-ip:38080 → 重定向到HTTPS
- **应用直接访问**: http://your-server-ip:38000
- **健康检查**: http://your-server-ip:38000/api/health
- **数据库连接**: your-server-ip:35432

## 防火墙配置

```bash
# Ubuntu/Debian
sudo ufw allow 38080/tcp  # HTTP
sudo ufw allow 38443/tcp  # HTTPS  
sudo ufw allow 38000/tcp  # 应用直接访问
sudo ufw allow 35432/tcp  # 数据库访问
sudo ufw allow 22/tcp     # SSH
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=38080/tcp
sudo firewall-cmd --permanent --add-port=38443/tcp
sudo firewall-cmd --permanent --add-port=38000/tcp
sudo firewall-cmd --permanent --add-port=35432/tcp
sudo firewall-cmd --reload
```

## 部署验证

```bash
# 检查服务状态
docker-compose ps

# 测试应用访问
curl http://localhost:38000/api/health

# 测试代理访问
curl http://localhost:38080

# 测试数据库连接
telnet localhost 35432
```

## 优势

1. **完全避免端口冲突** - 使用38xxx系列端口
2. **开发生产分离** - Replit用5000，Docker用8000
3. **易于记忆** - 端口号有规律（38xxx）
4. **灵活部署** - 可在任何有现有服务的服务器上部署

这个配置确保您可以在已有其他系统的服务器上安全部署，不会产生任何端口冲突。