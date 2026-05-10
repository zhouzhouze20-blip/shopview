# ShopView Server Deploy Package

This folder is a minimal source-build deployment package.

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
- empty `logs/`

## Not Included

- Git history
- Python virtual environments
- `node_modules`
- frontend build output
- Python bytecode/cache
- development notes and old release archives

## Start

```bash
docker compose up --build -d
docker compose logs -f app
```

Check `.env` before deploying to a new server, especially database connection, port, upload path, and log path values.
