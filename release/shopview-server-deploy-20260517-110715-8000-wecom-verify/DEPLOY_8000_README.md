# ShopView 8000 端口部署说明

## 部署

```bash
unzip shopview-server-deploy-*-8000-wecom-verify.zip
cd shopview-server-deploy-*-8000-wecom-verify
# 填写 env.app-only.linux 里的 WECOM_APP_SECRET
docker compose --env-file env.app-only.linux -f docker-compose.app-only.linux.yml up -d --build
```

## 企业微信域名校验

本包内置：

```text
/WW_verify_KMBiJKvPbtnOOZBi.txt
```

部署后确认：

```bash
curl -i http://gw.princesky.com/WW_verify_KMBiJKvPbtnOOZBi.txt
```

正文应只有：

```text
KMBiJKvPbtnOOZBi
```

## Cookie

当前包适合 `http://IP:8000` 测试，默认：

```env
AUTH_COOKIE_SECURE=false
```

正式改用 HTTPS 域名时再改为 `true`。
