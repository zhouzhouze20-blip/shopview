# ShopView 8000 端口部署说明

## 部署

```bash
tar -xzf shopview-server-deploy-*-8000.tar.gz
cd shopview-server-deploy-*-8000
# 填写 env.app-only.linux 或 .env 里的 WECOM_APP_SECRET
docker compose --env-file env.app-only.linux -f docker-compose.app-only.linux.yml up -d --build
```

## 访问

- 直连应用端口: `http://服务器IP:8000`
- 如果启用随包 nginx: `http://服务器IP` 或 `https://gw.princesky.com`

## 企业微信配置

包内已预填：

```env
WECOM_ENABLED=true
WECOM_CORP_ID=wx2096f4ca2d706e3a
WECOM_AGENT_ID=1000144
WECOM_REDIRECT_BASE_URL=https://gw.princesky.com
WECOM_FRONTEND_BASE_URL=https://gw.princesky.com
AUTH_COOKIE_SECURE=true
```

部署前必须在服务器环境文件中填写：

```env
WECOM_APP_SECRET=你的企业微信应用Secret
```

企业微信后台授权回调域名填写：`gw.princesky.com`。

## 测试用户绑定

扫码登录前，需要先把企业微信 userid 绑定到本地用户，例如：

```bash
WECOM_CORP_ID=wx2096f4ca2d706e3a python3 python_app/bind_wecom_identity.py --username admin --wecom-user-id 308
```
