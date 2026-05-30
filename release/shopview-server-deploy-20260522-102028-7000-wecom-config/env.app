# ShopView 应用环境变量配置
# 数据库配置
DATABASE_URL=postgresql://sales_user:sales_password_2024@192.168.98.80:5432/sales_db
PGHOST=192.168.98.80
PGPORT=5432
PGUSER=sales_user
PGPASSWORD=sales_password_2024
PGDATABASE=sales_db

# 应用配置
PORT=7000
NODE_ENV=production
DEBUG=false

# CORS配置
CORS_ORIGINS=*

# 企业微信扫码登录
WECOM_ENABLED=true
WECOM_CORP_ID=wx2096f4ca2d706e3a
WECOM_AGENT_ID=1000145
WECOM_APP_SECRET=4bp8mf9h1qru629hrubIUtcJWZMx6xBYk4q8gSxliKM
WECOM_REDIRECT_BASE_URL=http://da.princesky.com:7000
WECOM_FRONTEND_BASE_URL=http://da.princesky.com:7000
