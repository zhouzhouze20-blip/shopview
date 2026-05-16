# 百货柜位管理系统 - 部署文件清单

## 核心部署文件

### Docker配置文件
- `Dockerfile` - 默认生产Dockerfile
- `Dockerfile.linux` - Linux服务器优化的Dockerfile
- `docker-compose.yml` - 默认Docker Compose配置（连接外部数据库）
- `docker-compose.app-only.linux.yml` - 仅应用部署的Docker Compose配置

### 环境配置文件
- `env.app-only.linux` - 仅应用部署的环境配置

### 配置文件
- `config/nginx.conf` - Nginx反向代理配置

### 文档
- `DEPLOYMENT-GUIDE.md` - 详细部署指南
- `DEPLOYMENT-FILES.md` - 本文件清单

## 部署方式选择

当前仅保留“部署应用，连接外部数据库”这一种方式。

**使用文件：**
- `Dockerfile`
- `docker-compose.yml`
- `Dockerfile.linux`
- `docker-compose.app-only.linux.yml`
- `env.app-only.linux`

## 文件说明

### Dockerfile.linux
- 多阶段构建，优化镜像大小
- 基于Python 3.11-slim
- 包含React前端构建
- 配置健康检查
- 使用非root用户运行

### docker-compose.app-only.linux.yml
- 仅包含应用服务
- 连接到外部数据库
- 包含Nginx反向代理
- 配置数据卷持久化

### 环境配置文件
- 数据库连接配置
- 端口配置
- 安全配置
- 日志配置

## 使用步骤

1. **选择部署方式**
   - 默认使用 `docker-compose.yml`
   - Linux服务器也可以使用 `docker-compose.app-only.linux.yml`

2. **配置环境变量**
   - 编辑对应的env文件
   - 设置数据库连接信息

3. **执行部署**
   - 默认部署：`docker compose up --build -d`
   - Linux服务器：`docker compose --env-file env.app-only.linux -f docker-compose.app-only.linux.yml up --build -d`

4. **验证部署**
   - 访问 http://服务器IP:8000
   - 检查健康检查接口

## 注意事项

1. **数据库配置**
   - 确保数据库服务正在运行
   - 验证连接参数正确
   - 检查防火墙设置

2. **端口配置**
   - 确保端口未被占用
   - 配置防火墙规则
   - 检查网络连通性

3. **权限配置**
   - 确保有Docker执行权限
   - 检查文件读写权限
   - 验证SSH连接权限

4. **安全配置**
   - 修改默认密码
   - 配置SSL证书
   - 设置访问控制

## 故障排除

### 常见问题
1. 数据库连接失败
2. 端口被占用
3. 权限不足
4. 网络不通

### 解决方法
1. 检查配置文件
2. 查看日志信息
3. 验证网络连接
4. 检查权限设置

## 支持

如需技术支持，请提供：
1. 错误日志
2. 配置文件
3. 系统环境信息
4. 问题描述

