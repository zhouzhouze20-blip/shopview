# ShopView 测试部署包

生成时间：20260511-132006
目标测试地址：`http://192.168.98.16:7000`
基线提交：6d072c3 Checkpoint current ShopView version

## 本包确认包含

- 联营结算单筛选新增“部门开头”和“经营方式”条件。
- 联营结算单列表经营方式中文显示：1 经销、2 成本代销、3 扣率代销、4 联营、5 租赁。
- 修复带柜组权限查询结算单时数据库 `OperationalError / statement_timeout` 的问题。
- 优化结算单列表权限查询路径，实测王科涵账号同条件从超时降至约 0.23-0.33 秒。
- 结算单详情界面改为票据式表头、关键金额摘要和明细表结构。
- 前端静态构建：`static/index.html` + `static/assets`。

## 与正式实例并行部署

本包已经把宿主机端口改为 `7000`，容器名改为 `shopview-test-app`，可与当前 `192.168.98.16:8000` 正式实例并行运行。

```bash
tar -xzf shopview-test-deploy-20260511-132006.tar.gz
cd shopview-test-deploy-20260511-132006
docker compose up -d --build
```

测试入口：`http://192.168.98.16:7000`
健康检查：`http://192.168.98.16:7000/api/health`

如果只想重建测试实例：

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```
