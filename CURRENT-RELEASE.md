# ShopView 服务器部署包 - 图片部门数据范围授权

## 本次更新

- 新增 `python_app/assign_department_scopes_from_image.py`。
- 按用户提供图片中的部门与人员关系，批量分配用户 `business_scope` 部门数据范围。
- 同时为匹配到的用户补充分配 `部门经理(dept_manager)` 角色。
- 保留前序修复：企微职位 `经理` / `副经理` 自动设为部门经理、管理员代看支持用户名搜索、企业微信只同步百货条线与集团总裁办。

## 部署

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 执行授权

先 dry-run 查看用户是否都能匹配：

```bash
docker-compose exec app python python_app/assign_department_scopes_from_image.py
```

确认无误后正式写入：

```bash
docker-compose exec app python python_app/assign_department_scopes_from_image.py --apply
```

脚本会替换这些用户现有的企业微信业务数据范围，只保留图片中对应部门。
