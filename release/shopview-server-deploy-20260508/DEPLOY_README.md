# ShopView Server Deploy Package 20260508

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
- `销售AI分析规则库设计.md`

## New In This Package

- Sales dashboard group AI analysis UI.
- Backend rule engine for group-level sales analysis.
- Configurable AI provider support for OpenAI, MiniMax, and OpenAI-compatible APIs.
- MiniMax endpoint defaults to `https://api.minimaxi.com/v1`.

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
- `MINIMAX_API_KEY`

Do not commit real AI keys or database passwords.

## Start

```bash
docker compose up --build -d
docker compose logs -f app
```

## Access

- App: `http://server-ip:8000`
- API docs: `http://server-ip:8000/api/docs`

## AI Analysis Configuration

MiniMax example:

```bash
SALES_ANALYSIS_AI_PROVIDER=minimax
MINIMAX_API_KEY=your-key
MINIMAX_MODEL=MiniMax-M2.7
MINIMAX_BASE_URL=https://api.minimaxi.com/v1
SALES_ANALYSIS_AI_TIMEOUT_SECONDS=90
SALES_ANALYSIS_AI_MAX_OUTPUT_TOKENS=800
```

OpenAI example:

```bash
SALES_ANALYSIS_AI_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-5-mini
```

If AI is not configured or times out, the sales analysis API still returns rule-based analysis results.

