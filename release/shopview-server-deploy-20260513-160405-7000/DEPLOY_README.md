# ShopView 部署包

生成时间：20260513-160405
默认端口：7000

## 本包包含

- 模块权限菜单控制：用户只看到其角色具备查看权限的模块。
- 登录态返回角色聚合后的权限码，前端菜单、经营概览和模块跳转共用同一套权限判断。
- 前端静态构建：`static/index.html` + `static/assets`。
- 轻量 Dockerfile：使用包内预构建 `static/`，服务器构建镜像时不再执行 Node/npm 前端构建。

## Docker 部署

```bash
unzip shopview-server-deploy-20260513-160405-7000.zip
cd shopview-server-deploy-20260513-160405-7000
docker compose down
docker compose up -d --build
```

当前包内 `.env` 已设置：`PORT=7000`、`APP_PORT=7000`。

默认入口：`http://服务器IP:7000`

健康检查：`http://服务器IP:7000/api/health`

权限配置入口：`http://服务器IP:7000/?view=user-role-scope`
