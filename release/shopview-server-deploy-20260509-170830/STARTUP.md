# ShopView 启动与部署

当前数据库配置：
- 主机：`192.168.98.80`
- 端口：`5432`
- 数据库：`sales_db`
- 用户：`sales_user`
- 密码：`sales_password_2024`

## 本地开发启动（前后端分离）

### 后端（FastAPI）
```bash
cd /Users/zhou/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/zhouzeze2011_6ba3/msg/file/2026-01/ShopView

# 当前 `env.app` 已写入上述数据库配置；如需覆盖，也可以再生成 `.env`
cp env.app .env

# 使用 venv
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r python_requirements.txt

# 启动后端（注意 --app-dir）
python -m uvicorn main:app --app-dir python_app --host 0.0.0.0 --port 8000 --reload
```

访问地址：
- http://localhost:8000
- http://localhost:8000/api/docs

### 前端（Vite）
```bash
cd /Users/zhou/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/zhouzeze2011_6ba3/msg/file/2026-01/ShopView/client

# 如遇权限问题，先修权限
sudo chown -R "$USER":staff .
chmod -R u+rwX .

npm install
npm run dev
```

访问地址（以终端输出为准，通常是）：
- http://localhost:5173

## 服务器部署（Docker，仅部署应用）

适用于已有数据库，仅部署应用服务。

1) 编辑环境文件（数据库连接等）：
```bash
cd /opt/shopview
vi env.app-only.linux
```

默认已写入：
- `DATABASE_URL=postgresql://sales_user:sales_password_2024@192.168.98.80:5432/sales_db`
- `PGHOST=192.168.98.80`
- `PGPORT=5432`
- `PGUSER=sales_user`
- `PGPASSWORD=sales_password_2024`
- `PGDATABASE=sales_db`

2) 启动应用：
```bash
docker-compose --env-file env.app-only.linux -f docker-compose.app-only.linux.yml up --build -d
```

3) 查看状态与日志：
```bash
docker-compose -f docker-compose.app-only.linux.yml ps
docker-compose -f docker-compose.app-only.linux.yml logs -f shopview-app
```

4) 访问地址：
- 应用端口：`http://服务器IP:8000`
- 如启用 Nginx（默认 80 端口）：`http://服务器IP`

5) 停止服务：
```bash
docker-compose -f docker-compose.app-only.linux.yml down
```
