# ShopView Docker 部署包

这套部署包面向 Linux 服务器，只保留“应用连接外部 PostgreSQL”这一种部署方式。

## 包含内容

- `Dockerfile.linux`
- `Dockerfile`
- `docker-compose.yml`
- `docker-compose.app-only.linux.yml`
- `env.app-only.linux`
- `docker-entrypoint.sh`
- `client/`
- `python_app/`
- `config/nginx.conf`
- `python_requirements.txt`

## 服务器部署命令

```bash
tar -xzf shopview-docker-package.tar.gz
cd shopview-docker-package
docker compose up -d --build
```

## 默认访问地址

- 前端和 API: `http://服务器IP`
- 健康检查: `http://服务器IP/api/health`
- API 文档: `http://服务器IP/api/docs`

## 说明

- 容器启动时默认自动执行 Alembic 迁移。
- 如果不想自动迁移，把 `RUN_MIGRATIONS=false` 写进 `env.app-only.linux`。
- Nginx 会把外部请求转发到 `shopview-app:7000`。
- 如果 `docker pull` 或 `docker compose build` 卡在基础镜像拉取，并且日志里出现镜像加速地址返回 `403`，需要先修正服务器的 Docker 镜像源配置。
- 部署包里已经移除了本地 PostgreSQL 容器和初始化脚本。
