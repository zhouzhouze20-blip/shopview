# 烟花弹幕互动大屏：Docker 部署说明

本包是独立的 Node.js + SQLite 应用，不依赖 ShopView 的前端、后端、数据库或 Docker 网络。容器只在服务器本机监听一个端口，由服务器现有的 Nginx/Caddy 接入公网域名。

## 1. 服务器准备

- 一台可从公网访问的 Linux 服务器
- Docker Engine 与 Docker Compose 插件
- 已解析到该服务器的二级域名，例如 `fireworks.example.com`
- 服务器已有 Nginx/Caddy，或另行安装一个反向代理

建议至少保留 1 CPU、1 GB 内存和 2 GB 可用磁盘。活动规模扩大前应先做并发压测。

## 2. 配置并启动

解压后进入目录，从示例生成服务器专用配置和随机管理员令牌：

```bash
cp .env.example .env
ADMIN_TOKEN_VALUE="$(openssl rand -hex 32)"
sed -i "s/replace-with-a-strong-random-token/$ADMIN_TOKEN_VALUE/" .env
chmod 600 .env
```

请把生成的 `ADMIN_TOKEN_VALUE` 安全保存到密码管理器；它不会写入部署 ZIP。当前 `.env.example` 已按已解析的域名和 8787 端口直连填写：

```dotenv
PUBLIC_BASE_URL=http://gwzxcj.cbxsj.com:8787
ADMIN_TOKEN=服务器上生成的64位后台口令
FIREWORKS_BIND_IP=192.168.98.81
FIREWORKS_PORT=8787
```

此方式适合当前尚未配置 HTTPS 反向代理的过渡阶段。完成 Nginx 与证书配置后，建议改为 `https://gwzxcj.cbxsj.com`，并将 `FIREWORKS_BIND_IP` 改为 `127.0.0.1`。

`.env` 只保留在服务器，禁止上传到网盘或代码仓库。Docker 构建会通过 `.dockerignore` 排除 `.env`，口令不会写入镜像层。

校验配置、构建并启动：

```bash
docker compose config --quiet
docker compose build --pull
docker compose up -d
docker compose ps
curl --fail --silent --show-error http://192.168.98.81:8787/healthz
```

健康检查应返回类似：

```json
{"status":"ok","service":"interactive-fireworks","version":"0.2.2"}
```

## 3. 接入二级域名

正式接入二级域名时，将 `.env` 中的 `PUBLIC_BASE_URL` 改为 HTTPS 域名，并将 `FIREWORKS_BIND_IP` 改回 `127.0.0.1`，避免应用端口直接暴露到外网。

将 `deploy/nginx/fireworks.conf.example` 复制到服务器 Nginx 配置目录，全文替换 `fireworks.example.com`，再配置对应 HTTPS 证书。确认 Nginx 配置无误后重载：

```bash
nginx -t
systemctl reload nginx
```

应用包含 WebSocket 实时通信，反向代理必须保留 `Upgrade` 和 `Connection` 请求头。不要只代理普通 HTTP。

正式入口：

- 大屏：`https://你的二级域名/display.html?room=lobby`
- 手机：`https://你的二级域名/join.html?room=lobby`
- 后台：`https://你的二级域名/admin.html?room=lobby`

后台地址可以公开访问，但管理操作必须输入 `.env` 中的 `ADMIN_TOKEN`。建议额外在 Nginx 层对 `/admin.html` 和 `/api/admin/` 增加 IP 白名单、VPN 或 Basic Auth。

## 4. 后面更换域名

修改 `.env` 中的 `PUBLIC_BASE_URL`，同步修改 Nginx 域名和证书，然后执行：

```bash
docker compose up -d
```

不需要改代码，也不需要重新构建镜像。旧二维码包含旧域名，域名变更后需要刷新大屏并重新展示二维码。

## 5. 数据与升级

SQLite 数据和清空祝福前的自动备份都保存在 Docker 命名卷 `interactive-fireworks_fireworks_data`，删除或替换容器不会丢失。不要执行 `docker compose down -v`，它会删除数据卷。

升级代码包时：

```bash
docker compose build --pull
docker compose up -d
docker compose ps
```

查看日志：

```bash
docker compose logs --tail=200 -f fireworks
```

需要做完整卷备份时，先短暂停止应用以保证 SQLite 文件一致：

```bash
mkdir -p backups
docker compose stop fireworks
docker run --rm \
  -v interactive-fireworks_fireworks_data:/source:ro \
  -v "$PWD/backups:/backup" \
  alpine sh -c 'cd /source && tar czf /backup/fireworks-data.tar.gz .'
docker compose start fireworks
```

## 6. 与 ShopView 的隔离边界

- 独立 Compose 项目名：`interactive-fireworks`
- 独立镜像：`interactive-fireworks:0.2.2`
- 独立数据卷：`interactive-fireworks_fireworks_data`
- 独立应用端口：当前域名直连为 `192.168.98.81:8787`；接入 HTTPS 反向代理后改为 `127.0.0.1:8787`
- 不加入 ShopView 的 Docker 网络，不读取 ShopView 环境变量，不访问 ShopView 数据库

如果服务器的 8787 端口已被占用，只改 `.env` 的 `FIREWORKS_PORT`（例如 `8877`），并同步修改 Nginx 的 `proxy_pass` 端口即可。
