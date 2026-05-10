# ShopView Server Deploy Package 20260509-175953

This package is a runtime-only Docker deployment package for ShopView.

## Why This Package

The previous source-build package failed on the deployment server while pulling the frontend build image from the configured Docker registry mirror. This package avoids that path:

- The frontend has already been built locally into `static/`.
- The Dockerfile only uses the Python runtime image.
- Deployment no longer needs to build the frontend or pull a Node image.

## Included

- `Dockerfile`
- `docker-compose.yml`
- `.env`
- `python_requirements.txt`
- `docker-entrypoint.sh`
- `python_app/`
- `static/`
- `uploads/`
- `config/`
- `ssl/`

## New In This Package

- 商品销售明细报表直接通过 SQL 查询 `salegoodslist`，不再依赖 `rpt_goods_sales_detail`。
- 使用 `counter_groups` 替换 ERP `VIEW_MFRAME_ALL` 的柜组/部门/库区维度。
- 商品销售明细支持部门下拉、柜组编码/名称模糊查询、固定关键列、紧凑行距、分割线和导出 Excel。
- 部门下拉通过 `counter_groups` distinct 部门接口生成，并按当前用户数据权限过滤。

## Before Deploying

Edit `.env` on the server and verify database and runtime settings:

```bash
nano .env
```

At minimum, check:

- `DATABASE_URL`
- `PGHOST`
- `PGPORT`
- `PGUSER`
- `PGPASSWORD`
- `PGDATABASE`
- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `APP_TIMEZONE=Asia/Shanghai`

## Start

```bash
docker compose up --build -d
docker compose logs -f app
```

The container entrypoint runs Alembic migrations automatically.

## Access

- App: `http://server-ip:8000`
- API docs: `http://server-ip:8000/api/docs`
