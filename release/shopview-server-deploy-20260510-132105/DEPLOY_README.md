# ShopView 部署包

生成时间：20260510-132105

## Docker 部署

```bash
tar -xzf shopview-server-deploy-20260510-132105.tar.gz
cd shopview-server-deploy-20260510-132105
docker compose up -d --build
```

默认入口：`http://服务器IP`，健康检查：`http://服务器IP/api/health`。

说明：本包包含合同到期明细按合同号去重的后端修复，以及最新前端静态构建结果。
