# ShopView Server Deploy Package 20260509-133822

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

- Sales ticket list/export changes the last two columns to separate point values:
  - `消费加积分`
  - `生日月会员加积分`
- Ticket point aggregation reads `order_point.remark` and `order_point.point_type`, and recognizes both `消费加积分` and `消费获得积分`.
- Negative currency values in the ticket table no longer wrap the minus sign onto a separate line.

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
