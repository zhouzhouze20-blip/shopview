# 手工启动后端服务指南

## 方法一：使用 Python 直接启动（推荐）

### 步骤 1: 激活虚拟环境（如果使用）
```bash
cd /Users/zhou/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/zhouzeze2011_6ba3/msg/file/2026-01/ShopView
source venv/bin/activate
```

### 步骤 2: 设置环境变量
```bash
# 方法 A: 手动导出环境变量
export PGHOST=192.168.98.80
export PGPORT=5432
export PGDATABASE=sales_db
export PGUSER=sales_user
export PGPASSWORD=sales_password_2024
export DATABASE_URL=postgresql://sales_user:sales_password_2024@192.168.98.80:5432/sales_db
export PORT=7000

# 方法 B: 从 env.app 文件加载（更简单）
export $(grep -v '^#' env.app | grep '=' | xargs)
```

### 步骤 3: 进入 python_app 目录并启动
```bash
cd python_app
python3 -m uvicorn main:app --host 0.0.0.0 --port 7000 --reload
```

或者使用完整路径：
```bash
python3 -m uvicorn python_app.main:app --host 0.0.0.0 --port 7000 --reload
```

---

## 方法二：使用 Python 脚本启动

### 创建启动脚本 `start-manual.py`:
```python
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
env_file = project_root / "env.app"
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()

# 启动服务
import uvicorn
port = int(os.getenv("PORT", 7000))
uvicorn.run(
    "python_app.main:app",
    host="0.0.0.0",
    port=port,
    reload=True
)
```

### 运行：
```bash
python3 start-manual.py
```

---

## 方法三：一行命令启动（最简单）

在项目根目录运行：

```bash
cd /Users/zhou/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/zhouzeze2011_6ba3/msg/file/2026-01/ShopView && \
export $(grep -v '^#' env.app | grep '=' | xargs) && \
cd python_app && \
python3 -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-7000} --reload
```

---

## 验证启动成功

启动后，你应该看到类似这样的输出：
```
INFO:     Uvicorn running on http://0.0.0.0:7000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

然后可以访问：
- API 文档: http://localhost:7000/api/docs
- 健康检查: http://localhost:7000/api/health

---

## 常见问题

### 问题 1: 找不到模块
如果提示 `ModuleNotFoundError`，确保在项目根目录或 python_app 目录下运行。

### 问题 2: 端口被占用
如果端口 7000 被占用，可以：
- 使用其他端口: `--port 8001`
- 或者停止占用端口的进程: `kill -9 $(lsof -ti:7000)`

### 问题 3: 数据库连接失败
确保环境变量已正确设置，可以运行 `test-db-simple.py` 测试连接。

---

## 停止服务

按 `Ctrl + C` 停止服务。
