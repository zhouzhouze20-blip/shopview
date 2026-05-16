# ShopView 部署包

生成时间：20260511-183910

## 本包确认包含

- 默认应用端口改为 `7000`。
- Docker、启动脚本、前端 API 地址、CORS、健康检查均已切换到 `7000`。
- 新增会员维表迁移：`fj_dw_member_dim`。
- 新增卡券返券日志表迁移：`tktcardfqlog`。
- 新增活动档期表迁移：`tktpopinfo`。
- 新增活动分析后端接口：`/api/activity-analysis/activities`、`/api/activity-analysis/overview`。
- 新增前端页面：销售管理 -> 活动分析。
- 前端静态构建：`static/index.html` + `static/assets`。

## Docker 部署

```bash
unzip shopview-server-deploy-20260511-183910.zip
cd shopview-server-deploy-20260511-183910
docker compose up -d --build
```

默认入口：`http://服务器IP:7000`

健康检查：`http://服务器IP:7000/api/health`

活动分析入口：`http://服务器IP:7000/?view=activity-analysis`

如果服务器已有旧容器，建议先执行：

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```
