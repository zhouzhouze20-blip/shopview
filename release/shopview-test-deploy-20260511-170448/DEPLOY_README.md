# ShopView 测试部署包

生成时间：20260511-170448
目标测试地址：`http://192.168.98.16:7000`
基线提交：6d072c3 Checkpoint current ShopView version

## 本包新增

- 合同图纸增加“横向查看”按钮。
- 手机竖屏点“横向查看”时，图纸查看器旋转为横向画布，方便查看合同图纸。
- 普通合同列表、结算单功能和 `:8000` 正式实例不受影响。

## 已保留

- 联营结算单筛选新增“部门开头”和“经营方式”条件。
- 修复带柜组权限查询结算单时数据库 `OperationalError / statement_timeout` 的问题。
- 轻量 Dockerfile：使用包内预构建 `static/`，不在服务器构建时跑 Node/npm，也不安装 gcc/g++/build-essential。

## 部署

```bash
tar -xzf shopview-test-deploy-20260511-170448.tar.gz
cd shopview-test-deploy-20260511-170448
docker compose down
docker compose up -d --build
```

测试入口：`http://192.168.98.16:7000`
