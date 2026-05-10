# ShopView Server Deploy Package 20260509

This package is a source-build Docker deployment package for the ShopView server.

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
- `logs/`
- `SYSTEM_ARCHITECTURE.md`
- `销售AI分析规则库设计.md`

## New In This Package

- System audit page: login log query and module operation log query.
- Sidebar modules default to collapsed state.
- Backend database timezone defaults to `Asia/Shanghai`.
- Sales ticket list/export removes `卡券金额`.
- Sales ticket list/export adds `积分` and `积分类型` from `order_point`.
- `order_point.point_type` is `VARCHAR(250)` with no value restriction.
- `order_point` primary key is `(order_id, point_type)`.
- New migrations for `order_point` and `business_unit_binding`.

## Before Deploying

Edit `.env` on the server:

```bash
nano .env
```

At minimum, verify:

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

The container entrypoint runs Alembic migrations automatically. This package will update `order_point` to:

- `order_id VARCHAR(50) NOT NULL`
- `point NUMERIC(10, 2)`
- `point_type VARCHAR(250) NOT NULL`
- primary key `(order_id, point_type)`

## Access

- App: `http://server-ip:8000`
- API docs: `http://server-ip:8000/api/docs`
