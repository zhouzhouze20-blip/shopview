# ShopView Server Deploy Package 20260509-170830

This package is a source-build Docker deployment package for ShopView.

## Included

- `Dockerfile`
- `docker-compose.yml`
- `.env`
- `python_requirements.txt`
- `docker-entrypoint.sh`
- `python_app/`
- `client/`
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
