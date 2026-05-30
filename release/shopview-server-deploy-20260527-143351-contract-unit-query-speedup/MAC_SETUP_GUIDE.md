# Mac 环境安装与运行指南

## 📦 需要安装的软件

### 1. **Python 3.11+** (必需)
```bash
# 使用 Homebrew 安装（推荐）
brew install python@3.11

# 或者从官网下载安装
# https://www.python.org/downloads/

# 验证安装
python3 --version
# 应该显示 Python 3.11.x 或更高版本
```

### 2. **Node.js 和 npm** (必需，用于前端开发)
```bash
# 使用 Homebrew 安装（推荐）
brew install node

# 或者安装 LTS 版本
brew install node@18

# 验证安装
node --version
npm --version
```

### 3. **PostgreSQL** (必需，数据库)
```bash
# 使用 Homebrew 安装
brew install postgresql@14

# 启动 PostgreSQL 服务
brew services start postgresql@14

# 或者手动启动
pg_ctl -D /usr/local/var/postgresql@14 start

# 验证安装
psql --version
```

**注意**: 根据你的项目配置，数据库连接信息是：
- 主机: 192.168.98.80
- 端口: 5432
- 数据库名: sales_db
- 用户名: sales_user
- 密码: sales_password_2024

如果数据库在远程服务器上，你只需要确保能连接到该服务器即可。

### 4. **Homebrew** (推荐，Mac 包管理器)
如果还没有安装 Homebrew：
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 5. **Git** (通常 Mac 已自带)
```bash
# 验证是否已安装
git --version

# 如果没有，使用 Homebrew 安装
brew install git
```

---

## 🚀 运行程序

### 方式一：本地开发模式（推荐）

#### 步骤 1: 安装 Python 依赖
```bash
# 在项目根目录下
cd /Users/zhou/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/zhouzeze2011_6ba3/msg/file/2026-01/ShopView

# 创建虚拟环境（推荐）
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -r python_requirements.txt
```

#### 步骤 2: 安装前端依赖
```bash
# 进入前端目录
cd client

# 安装依赖
npm install

# 返回根目录
cd ..
```

#### 步骤 3: 配置环境变量
```bash
# 检查 env.app 文件是否存在
cat env.app

# 如果不存在，创建它（根据你的数据库配置）
# 编辑 env.app 文件，设置数据库连接信息
```

#### 步骤 4: 运行后端服务
```bash
# 在项目根目录下，给脚本执行权限
chmod +x start-backend.sh

# 运行后端
./start-backend.sh

# 或者直接运行
cd python_app
python3 -m uvicorn main:app --host 0.0.0.0 --port 2000 --reload
```

后端服务将在 `http://localhost:2000` 启动

#### 步骤 5: 运行前端服务（新终端窗口）
```bash
# 在项目根目录下
chmod +x start-frontend-dev.sh

# 运行前端
./start-frontend-dev.sh

# 或者直接运行
cd client
npm run dev
```

前端开发服务器通常会在 `http://localhost:5173` 启动（Vite 默认端口）

---

### 方式二：使用 Docker（生产环境）

#### 步骤 1: 安装 Docker Desktop for Mac
```bash
# 从官网下载安装
# https://www.docker.com/products/docker-desktop

# 或者使用 Homebrew
brew install --cask docker
```

#### 步骤 2: 使用 Docker Compose 运行
```bash
# 在项目根目录下
chmod +x deploy-app-only.sh

# 运行部署脚本
./deploy-app-only.sh

# 或者手动运行
docker-compose -f docker-compose.app-only.yml up --build -d

# 查看日志
docker-compose -f docker-compose.app-only.yml logs -f app
```

应用将在 `http://localhost:7000` 启动（根据 docker-compose 配置）

---

## 🔧 常见问题排查

### 1. Python 版本问题
```bash
# 检查 Python 版本
python3 --version

# 如果版本不对，使用 pyenv 管理多个 Python 版本
brew install pyenv
pyenv install 3.11.0
pyenv local 3.11.0
```

### 2. 数据库连接问题
```bash
# 测试数据库连接
psql -h 192.168.98.80 -p 5432 -U sales_user -d sales_db

# 如果连接失败，检查：
# - 网络连接
# - 防火墙设置
# - 数据库服务器是否运行
```

### 3. 端口被占用
```bash
# 查看端口占用情况
lsof -i :2000
lsof -i :5173

# 杀死占用端口的进程
kill -9 <PID>
```

### 4. 权限问题
```bash
# 给所有脚本添加执行权限
chmod +x *.sh

# 如果遇到权限问题，可能需要：
chmod +x start-*.sh
chmod +x deploy-*.sh
```

### 5. 依赖安装失败
```bash
# Python 依赖安装失败
pip install --upgrade pip
pip install -r python_requirements.txt

# Node 依赖安装失败
cd client
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

---

## 📝 快速启动命令总结

### 开发模式（前后端分离）
```bash
# 终端 1: 启动后端
cd /Users/zhou/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/zhouzeze2011_6ba3/msg/file/2026-01/ShopView
source .venv/bin/activate  # 如果使用虚拟环境
./start-backend.sh

# 终端 2: 启动前端
cd /Users/zhou/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/zhouzeze2011_6ba3/msg/file/2026-01/ShopView
./start-frontend-dev.sh
```

### 生产模式（Docker）
```bash
cd /Users/zhou/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/zhouzeze2011_6ba3/msg/file/2026-01/ShopView
./deploy-app-only.sh
```

---

## 🌐 访问地址

- **前端开发服务器**: http://localhost:5173
- **后端 API**: http://localhost:2000
- **API 文档**: http://localhost:2000/api/docs
- **健康检查**: http://localhost:2000/api/health

---

## 💡 提示

1. **使用虚拟环境**: 强烈建议使用 Python 虚拟环境来隔离项目依赖
2. **环境变量**: 确保 `env.app` 文件配置正确
3. **数据库迁移**: 首次运行前，确保数据库已创建并运行了迁移
4. **日志查看**: 开发模式下，后端和前端都会输出详细的日志信息
