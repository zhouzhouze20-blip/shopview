# 前端展示指南（无需数据库）

当你需要展示前端页面但没有数据库连接时，可以使用 Mock API 服务器。

## 🚀 快速开始

### 方法一：使用 Mock API 服务器（推荐）

1. **启动 Mock API 服务器**
   ```bash
   # 给脚本添加执行权限（首次运行）
   chmod +x start-mock-api.sh
   
   # 启动 Mock API 服务器
   ./start-mock-api.sh
   ```
   
   服务器将在 `http://localhost:8000` 启动

2. **启动前端开发服务器**（新开一个终端窗口）
   ```bash
   cd client
   npm run dev
   ```
   
   前端将在 `http://localhost:5173` 启动

3. **访问前端页面**
   - 打开浏览器访问: `http://localhost:5173`
   - 现在可以正常浏览和展示前端页面了！

---

### 方法二：直接运行前端（如果前端能处理 API 错误）

如果前端代码已经有错误处理，也可以直接运行前端，只是数据会显示为空或错误提示。

```bash
cd client
npm run dev
```

---

## 📋 Mock API 服务器功能

Mock 服务器提供了以下 API 端点（返回模拟数据）：

- `GET /api/stores` - 获取门店列表
- `GET /api/floors` - 获取楼层列表
- `GET /api/counters` - 获取柜位列表
- `GET /api/tenants` - 获取租户列表
- `GET /api/revenue-data` - 获取收益数据
- `GET /api/dashboard/summary` - 获取仪表板摘要
- `GET /api/health` - 健康检查

### 查询参数支持

- `/api/floors?storeId=1` - 根据门店ID筛选楼层
- `/api/counters?storeId=1&floorId=1` - 根据门店和楼层筛选柜位
- `/api/revenue-data?storeId=1` - 根据门店筛选收益数据

---

## 📊 Mock 数据说明

Mock 服务器包含以下模拟数据：

- **门店**: 2 个门店（旗舰店、分店）
- **楼层**: 每个门店有 2 层
- **柜位**: 每个楼层有多个柜位（不同状态：占用、空闲）
- **租户**: 2 个租户
- **收益数据**: 示例收益数据

---

## 🔧 自定义 Mock 数据

如果需要修改 Mock 数据，编辑 `mock-api-server.js` 文件中的 `mockData` 对象：

```javascript
const mockData = {
  stores: [
    // 在这里添加或修改门店数据
  ],
  counters: [
    // 在这里添加或修改柜位数据
  ],
  // ... 其他数据
};
```

---

## ⚠️ 注意事项

1. **Mock 服务器仅用于展示**: 所有数据都是模拟的，不会保存到数据库
2. **不支持 POST/PUT/DELETE**: Mock 服务器只支持 GET 请求，用于展示数据
3. **端口冲突**: 如果 8000 端口被占用，需要修改 `mock-api-server.js` 中的 `PORT` 变量

---

## 🐛 故障排除

### 问题 1: 端口被占用
```bash
# 查看端口占用
lsof -i :8000

# 如果被占用，可以修改 mock-api-server.js 中的 PORT 变量
# 或者停止占用端口的进程
```

### 问题 2: 前端无法连接 API
- 确认 Mock API 服务器正在运行
- 检查浏览器控制台是否有 CORS 错误
- 确认前端配置的 API 地址是 `http://localhost:8000`

### 问题 3: 数据不显示
- 打开浏览器开发者工具（F12）
- 查看 Network 标签，检查 API 请求是否成功
- 查看 Console 标签，检查是否有 JavaScript 错误

---

## 📝 完整启动命令

```bash
# 终端 1: 启动 Mock API 服务器
./start-mock-api.sh

# 终端 2: 启动前端开发服务器
cd client
npm run dev

# 终端 3: 打开浏览器访问
# http://localhost:5173
```

---

## 💡 提示

- Mock 服务器支持 CORS，可以正常与前端通信
- 所有数据都是静态的，刷新页面后数据不会改变
- 适合用于演示、展示、前端开发调试等场景
