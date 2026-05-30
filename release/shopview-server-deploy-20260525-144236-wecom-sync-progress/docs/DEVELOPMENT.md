# ShopView Codex 开发接手指南

本文面向“开发者主要通过 Codex 完成代码修改”的协作方式。新同事不需要手写代码，但需要会把任务描述清楚、检查 Codex 的改动范围，并能运行基本验证。

## 1. 项目定位

ShopView 是百货柜位管理系统，当前主要包含：

- 前端：React + TypeScript + Vite + Tailwind CSS。
- 后端：Python + FastAPI + SQLAlchemy + Alembic。
- 数据库：PostgreSQL。
- 部署：Docker / Docker Compose。

核心代码入口：

| 类型 | 路径 |
| --- | --- |
| 前端入口 | `client/src/main.tsx`, `client/src/App.tsx` |
| 前端页面 | `client/src/pages/` |
| 前端 API 封装 | `client/src/lib/api.ts` |
| 后端入口 | `python_app/main.py` |
| 后端路由 | `python_app/routers/` |
| 数据模型 | `python_app/models/` |
| 数据迁移 | `python_app/alembic/versions/` |

## 2. 新同事接手时先让 Codex 做什么

建议新同事打开项目后，先给 Codex 这段任务：

```text
请先只阅读项目，不要修改代码。帮我梳理 ShopView 的技术栈、前后端启动方式、主要目录、当前有无未提交改动，以及我作为新协作者接手时应该先看哪些文件。最后给我一个 5 条以内的上手清单。
```

如果要开始做具体任务，再单独开一个任务分支，不要直接在 `main` 上让 Codex 修改。

## 3. 准备环境

建议版本：

- Node.js 18 或更高。
- Python 3.11。
- PostgreSQL 14 或更高，或者使用团队提供的开发库。

首次拉代码后：

```bash
cd /Users/zhou/Projects/ShopView
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r python_requirements.txt

cd client
npm install
```

## 4. 配置环境变量

从示例文件复制：

```bash
cd /Users/zhou/Projects/ShopView
cp .env.example .env
```

至少确认以下配置：

```bash
DATABASE_URL=postgresql://user:password@host:5432/database
PGHOST=host
PGPORT=5432
PGUSER=user
PGPASSWORD=password
PGDATABASE=database
```

注意：

- `.env` 不提交到 Git。
- `env.app`、`env.app-only.linux` 这类部署环境文件如果含真实配置，分享前需要脱敏。
- 企业微信配置只放在本地环境或部署平台，不写入公开文档。

## 5. 启动后端

推荐在项目根目录启动：

```bash
cd /Users/zhou/Projects/ShopView
source .venv/bin/activate
python -m uvicorn main:app --app-dir python_app --host 0.0.0.0 --port 7000 --reload
```

访问：

- 后端健康检查：http://localhost:7000/api/health
- API 文档：http://localhost:7000/api/docs

也可以使用脚本：

```bash
./start-backend.sh
```

## 6. 启动前端

前端开发服务默认端口是 `5173`：

```bash
cd /Users/zhou/Projects/ShopView/client
npm run dev
```

默认情况下，Vite 代理目标是 `http://localhost:8000`。如果真实后端运行在 `7000`，启动前端时建议显式指定：

```bash
cd /Users/zhou/Projects/ShopView/client
VITE_API_PROXY_TARGET=http://localhost:7000 VITE_API_PORT=7000 npm run dev
```

访问：

- 前端页面：http://localhost:5173

## 7. 无数据库前端演示

如果同事只做前端页面或交互，可以先跑 mock API：

```bash
cd /Users/zhou/Projects/ShopView
./start-mock-api.sh
```

然后启动前端：

```bash
cd client
npm run dev
```

mock API 地址：

- http://localhost:8000/api/health

## 8. 让 Codex 做修改前的标准提示

每次交给 Codex 一个任务，建议包含这些信息：

```text
你在 /Users/zhou/Projects/ShopView 工作。
请先查看相关文件和 git status，再动手。
本次只处理：[具体功能/问题]。
不要改无关文件，不要提交真实密钥，不要重置我已有改动。
完成后请说明改了哪些文件、如何验证、是否还有风险。
```

涉及前端页面时补充：

```text
请保持现有 UI 风格，优先复用当前组件和 hooks。完成后运行前端构建；如果启动了本地服务，请告诉我访问地址。
```

涉及后端接口时补充：

```text
请说明新增或修改的 API 路径、请求参数、返回字段、权限影响和数据库影响。涉及迁移时先解释迁移策略。
```

## 9. 提交前检查

当前仓库没有统一测试脚本，提交前至少执行：

```bash
cd /Users/zhou/Projects/ShopView/client
npm run build
```

如果改了后端接口或数据模型，还需要：

```bash
cd /Users/zhou/Projects/ShopView
source .venv/bin/activate
python -m uvicorn main:app --app-dir python_app --host 0.0.0.0 --port 7000
```

启动成功后检查 `/api/health` 和相关接口。

## 10. Codex 输出怎么验收

不要只看 Codex 的总结，至少检查：

- `git diff` 里是否只改了任务相关文件。
- 是否误提交 `.env`、压缩包、构建产物、上传文件。
- 是否改了数据库、权限、登录、部署配置等高风险区域。
- 前端任务是否能 `npm run build`。
- 后端任务是否能启动服务并访问相关接口。

可以直接让 Codex 做二次检查：

```text
请以 code review 视角检查你刚才的改动，只列风险、bug、遗漏测试和可能影响现有功能的地方。不要继续修改，先给我结论。
```

## 11. 常见问题

### 前端请求到了 8000 端口

这是因为 `client/vite.config.ts` 和 `client/src/lib/api.ts` 默认端口是 `8000`。真实后端在 `7000` 时，使用：

```bash
VITE_API_PROXY_TARGET=http://localhost:7000 VITE_API_PORT=7000 npm run dev
```

### 端口占用

```bash
lsof -i :7000
lsof -i :5173
```

确认进程后再停止对应进程。

### 数据库连接失败

先检查 `.env` 或 `env.app` 中的 `DATABASE_URL`、`PGHOST`、`PGPORT`、`PGUSER`、`PGPASSWORD`、`PGDATABASE`。如果是同事本机开发，优先使用开发库账号，不要共用生产库账号。
