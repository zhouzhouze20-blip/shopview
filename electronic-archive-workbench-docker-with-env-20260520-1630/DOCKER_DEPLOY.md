# Docker Deployment

## 1. Prepare Environment Variables

Create a `.env` file in the project root:

```env
ORACLE_USER=your_oracle_user
ORACLE_PASSWORD=your_oracle_password
ORACLE_CONNECT_STRING=host:1521/service_name
# Optional: override base image if the server cannot pull docker.io/library/node.
# NODE_IMAGE=node:22-bookworm-slim
```

The app requires all three Oracle variables at runtime.

## 2. Build Image

```bash
docker build -t electronic-archive-workbench:latest .
```

## 3. Run Container

```bash
docker run -d \
  --name electronic-archive-workbench \
  --restart unless-stopped \
  -p 3020:3000 \
  --env-file .env \
  electronic-archive-workbench:latest
```

## 4. Or Use Docker Compose

```bash
docker compose --env-file .env up -d --build
```

The service will listen on `http://localhost:3020`.

The compose file also uses `env_file: .env`, so `.env` must be in the same directory as `docker-compose.yml`.

## 5. Base Image Pull 403 / Timeout

If build fails while pulling `node:22-bookworm-slim`, for example:

```text
failed open: unexpected status ... mirror.aliyuncs.com ... 403 Forbidden
```

the failure is caused by the Docker registry mirror on the deployment server, not by the application code.

Recommended fixes:

1. Remove or replace the invalid Docker registry mirror in `/etc/docker/daemon.json`, then restart Docker.

```bash
sudo cat /etc/docker/daemon.json
sudo systemctl restart docker
docker pull node:22-bookworm-slim
docker compose build --no-cache
```

2. If the server has another reachable Node image mirror, set `NODE_IMAGE` in `.env` before building.

```env
NODE_IMAGE=your-reachable-registry/node:22-bookworm-slim
```

Then run:

```bash
docker compose build --no-cache
docker compose up -d
```

3. If the server has no reliable internet access, pull the base image on another machine and transfer it:

```bash
docker pull node:22-bookworm-slim
docker save node:22-bookworm-slim -o node-22-bookworm-slim.tar
scp node-22-bookworm-slim.tar user@server:/tmp/
ssh user@server 'docker load -i /tmp/node-22-bookworm-slim.tar'
```

After loading the image, rebuild on the server.

## 6. pnpm Ignored Build Scripts

If build fails during `pnpm install` with:

```text
ERR_PNPM_IGNORED_BUILDS Ignored build scripts: oracledb, sharp
```

use the latest project package. The project explicitly allows these dependency build scripts in `package.json`:

```json
"pnpm": {
  "onlyBuiltDependencies": ["oracledb", "sharp"]
}
```

Then rebuild:

```bash
docker compose build --no-cache
docker compose up -d
```

For local standalone startup with a custom port:

```bash
pnpm build
pnpm start -p 3019
```
