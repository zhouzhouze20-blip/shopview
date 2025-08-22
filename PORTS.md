# 端口配置说明

为避免与服务器现有服务冲突，本Docker配置使用了自定义端口：

## 服务端口映射

| 服务 | 容器内端口 | 主机端口 | 说明 |
|------|-----------|---------|------|
| PostgreSQL 数据库 | 5432 | **25432** | 数据库访问端口 |
| Node.js 应用 | 8000 | **28000** | 应用直接访问 |
| Nginx HTTP | 80 | **28080** | HTTP访问（开发环境） |
| Nginx HTTPS | 443 | **28443** | HTTPS安全访问（生产环境，需要SSL证书） |

## 访问地址

### 开发环境推荐
- **应用直接访问**: http://your-server-ip:28000
- **HTTP代理**: http://your-server-ip:28080
- **健康检查**: http://your-server-ip:28000/api/health
- **数据库连接**: your-server-ip:25432

### 生产环境（需要SSL证书）
- **主要访问**: https://your-server-ip:28443
- **HTTP重定向**: http://your-server-ip:28080 → https://your-server-ip:28443

## 防火墙配置

```bash
# Ubuntu/Debian 使用 ufw
sudo ufw allow 28080/tcp  # HTTP
sudo ufw allow 28443/tcp  # HTTPS  
sudo ufw allow 28000/tcp  # 应用直接访问
sudo ufw allow 25432/tcp  # 数据库访问
sudo ufw allow 22/tcp     # SSH
sudo ufw enable

# CentOS/RHEL 使用 firewalld
sudo firewall-cmd --permanent --add-port=28080/tcp
sudo firewall-cmd --permanent --add-port=28443/tcp
sudo firewall-cmd --permanent --add-port=28000/tcp
sudo firewall-cmd --permanent --add-port=25432/tcp
sudo firewall-cmd --reload
```

## 部署后验证

```bash
# 检查服务状态
docker-compose ps

# 测试应用访问
curl http://localhost:28000/api/health

# 测试代理访问
curl http://localhost:28080

# 测试数据库连接
telnet localhost 25432
```

## 常见问题解决

### 1. SSL证书问题
如果遇到SSL证书错误，可以：
- 使用HTTP模式（端口28080）
- 生成自签名证书：`cd ssl && ./generate-ssl.sh`
- 或注释掉nginx.conf中的HTTPS配置

### 2. 应用启动失败
检查：
- 端口是否被占用
- 文件路径是否正确
- 环境变量是否配置正确

### 3. 数据库连接问题
确保：
- 数据库容器已启动
- 端口映射正确
- 环境变量配置正确

## 修改端口（如需要）

如果需要修改端口，编辑 `docker-compose.yml` 文件中的端口映射：

```yaml
ports:
  - "您的端口:容器端口"
```

然后重新部署：
```bash
docker-compose down
docker-compose up -d
```