# ShopView 部署包

生成时间：20260511-101652
基线提交：6d072c3 Checkpoint current ShopView version

## 本包确认包含

- 合同页 SVG 图纸手势拖动、双指缩放、按钮缩放、重置和全屏查看
- 前端静态构建：static/index.html + static/assets

## Docker 部署

```bash
tar -xzf shopview-server-deploy-20260511-101652.tar.gz
cd shopview-server-deploy-20260511-101652
docker compose up -d --build
```

默认入口：`http://服务器IP:8000`，健康检查：`http://服务器IP:8000/api/health`。

如果服务器已有旧容器，建议先执行：

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```
