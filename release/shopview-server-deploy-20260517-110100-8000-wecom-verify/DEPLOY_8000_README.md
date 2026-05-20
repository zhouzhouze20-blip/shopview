# ShopView 8000 端口部署说明

## 部署

```bash
tar -xzf shopview-server-deploy-*-8000-wecom-verify.tar.gz
cd shopview-server-deploy-*-8000-wecom-verify
# 填写 env.app-only.linux 里的 WECOM_APP_SECRET
docker compose --env-file env.app-only.linux -f docker-compose.app-only.linux.yml up -d --build
```

## 企业微信域名校验

本包已内置：

```text
/WW_verify_KMBiJKvPbtnOOZBi.txt
```

部署后确认外网返回纯文本：

```bash
curl -i http://gw.princesky.com/WW_verify_KMBiJKvPbtnOOZBi.txt
```

正确响应应为 `200 OK`，正文只有：

```text
KMBiJKvPbtnOOZBi
```

如果仍返回 HTML，说明线上还没有部署本包，或域名没有转发到新容器。
