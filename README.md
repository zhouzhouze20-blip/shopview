# ShopView - 百货柜位管理系统

## 项目简介
ShopView是一个现代化的百货柜位管理系统，提供门店管理、柜位管理、租户管理等功能。

## 技术栈
- **后端**: Python + FastAPI
- **前端**: React + TypeScript + Tailwind CSS
- **数据库**: PostgreSQL
- **部署**: Docker

## 快速开始

### 前置条件
1. Docker 已安装并运行
2. PostgreSQL 数据库连接信息已准备好：
   - 主机: 按你的生产环境填写
   - 端口: 5432
   - 数据库名: 按你的生产环境填写
   - 用户名: 按你的生产环境填写
   - 密码: 按你的生产环境填写

### 部署应用

项目现在只保留“连接外部 PostgreSQL 数据库”的部署方式。

```bash
# 构建并启动应用
docker compose up --build -d

# 查看日志
docker compose logs -f shopview-app
```

### 访问应用
- **应用地址**: http://localhost:7000
- **API文档**: http://localhost:7000/api/docs
- **健康检查**: http://localhost:7000/api/health

## 项目结构
```
ShopView/
├── python_app/           # Python后端应用
│   ├── main.py          # 主应用入口
│   ├── models/          # 数据模型
│   ├── routers/         # API路由
│   └── schemas/         # 数据模式
├── client/              # React前端应用
├── docker-compose.yml   # 默认部署配置（连接外部数据库）
├── docker-compose.app-only.linux.yml  # Linux服务器部署配置
├── Dockerfile           # 默认生产镜像
├── Dockerfile.linux     # Linux服务器生产镜像
└── env.app-only.linux   # 服务器环境变量配置
```

## 开发

### 本地开发
```bash
# 安装Python依赖
pip install -r python_requirements.txt

# 运行Python应用
cd python_app
python main.py

# 安装前端依赖
cd client
npm install

# 运行前端开发服务器
npm run dev
```

### 数据库迁移
数据库表会在应用启动时自动创建。

## 协作开发

新同事接手开发时，建议先阅读：

- [文档入口](./docs/README.md)
- [开发接手指南](./docs/DEVELOPMENT.md)
- [协作分工规范](./docs/COLLABORATION.md)
- [任务拆分建议](./docs/TASK_SPLIT.md)

## 部署说明
详细的部署说明请参考 [应用部署指南](./docs/deployment/APP-DEPLOYMENT.md)

## 许可证
MIT License
