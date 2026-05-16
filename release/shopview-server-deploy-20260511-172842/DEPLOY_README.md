# ShopView 部署包

生成时间：20260511-172842

## 本包确认包含

- 新增会员维表迁移：`fj_dw_member_dim`。
- 新增卡券返券日志表迁移：`tktcardfqlog`。
- 新增活动档期表迁移：`tktpopinfo`。
- 新增活动分析后端接口：`/api/activity-analysis/activities`、`/api/activity-analysis/overview`。
- 新增前端页面：销售管理 -> 活动分析。
- 活动分析一期口径：聚焦卡券使用，销售、成本、毛利取 `salegoodslist`，会员取实时会员表。
- 前端静态构建：`static/index.html` + `static/assets`。

## Docker 部署

```bash
tar -xzf shopview-server-deploy-20260511-172842.tar.gz
cd shopview-server-deploy-20260511-172842
docker compose up -d --build
```

默认入口：`http://服务器IP:8000`

健康检查：`http://服务器IP:8000/api/health`

活动分析入口：`http://服务器IP:8000/?view=activity-analysis`

如果服务器已有旧容器，建议先执行：

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

## 数据库迁移

本包包含 Alembic 迁移文件。容器启动后如未自动迁移，可进入包目录执行：

```bash
cd python_app
../.venv/bin/alembic upgrade head
```

或按服务器 Python 环境执行：

```bash
cd python_app
alembic upgrade head
```
