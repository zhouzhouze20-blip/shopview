# ShopView 部署包

生成时间：20260510-131657

## Docker 部署

```bash
tar -xzf shopview-server-deploy-20260510-131657.tar.gz
cd shopview-server-deploy-20260510-131657
docker compose up -d --build
```

默认入口：`http://服务器IP`，健康检查：`http://服务器IP/api/health`。

说明：容器构建时会重新编译 `client/`；`static/` 也已放入本次本机构建后的前端静态文件，供非 Docker 静态部署或排查使用。
