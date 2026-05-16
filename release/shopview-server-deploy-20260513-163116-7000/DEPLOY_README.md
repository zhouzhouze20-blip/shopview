# ShopView 部署包

生成时间：20260513-163116
默认端口：7000

## 本包包含

- 新增独立权限点：`activity_analysis.view`（查看活动分析）。
- 后台角色权限分组显示中文模块名，角色编辑里会出现“活动分析”。
- 活动分析接口改为校验 `activity_analysis.view`，不再复用 `sales.view`。
- 模块权限菜单控制：用户只看到其角色具备查看权限的模块。
- 前端静态构建：`static/index.html` + `static/assets`。
- 轻量 Dockerfile：使用包内预构建 `static/`，服务器构建镜像时不再执行 Node/npm 前端构建。

## Docker 部署

```bash
unzip shopview-server-deploy-20260513-163116-7000.zip
cd shopview-server-deploy-20260513-163116-7000
docker compose down
docker compose up -d --build
```

当前包内 `.env` 已设置：`PORT=7000`、`APP_PORT=7000`。

默认入口：`http://服务器IP:7000`

健康检查：`http://服务器IP:7000/api/health`

权限配置入口：`http://服务器IP:7000/?view=user-role-scope`
