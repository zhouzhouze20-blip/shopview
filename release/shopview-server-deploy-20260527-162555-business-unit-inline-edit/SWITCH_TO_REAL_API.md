# 切换回真实后端 API 指南

## 🔄 切换步骤

### 步骤 1: 停止 Mock API 服务器

如果 Mock API 服务器正在运行，需要先停止它：

1. 找到运行 `./start-mock-api.sh` 的终端窗口
2. 按 `Ctrl + C` 停止 Mock API 服务器

或者使用以下命令：

```bash
# 查找并终止占用 8000 端口的进程（Mock API）
kill -9 $(lsof -ti:8000) 2>/dev/null && echo "✅ Mock API 已停止" || echo "✅ Mock API 未运行"
```

---

### 步骤 2: 启动真实后端服务

在项目根目录下运行：

```bash
cd /Users/zhou/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/zhouzeze2011_6ba3/msg/file/2026-01/ShopView

# 确保在项目根目录
./start-backend.sh
```

后端服务将在 `http://localhost:2000` 或 `http://localhost:8000` 启动（取决于 env.app 中的 PORT 配置）。

---

### 步骤 3: 更新前端 API 配置（如果需要）

**重要**: 前端配置的 API 地址是 `http://localhost:8000`，而 `start-backend.sh` 默认使用端口 2000。

**选项 A**: 修改后端端口为 8000（推荐）

在 `env.app` 文件中添加或修改：

```bash
PORT=8000
```

**选项 B**: 修改前端配置指向 2000 端口

修改 `client/src/lib/api.ts` 文件，将 `8000` 改为 `2000`。

---

### 步骤 4: 验证连接

1. **检查后端健康状态**:
   ```
   http://localhost:8000/api/health
   ```
   或
   ```
   http://localhost:2000/api/health
   ```

2. **检查 API 文档**:
   ```
   http://localhost:8000/api/docs
   ```
   或
   ```
   http://localhost:2000/api/docs
   ```

3. **刷新前端页面**:
   - 按 `F5` 或 `Command + R` 刷新浏览器
   - 查看浏览器控制台（F12），确认 API 请求指向真实后端

---

## 📋 快速切换命令

### 一键切换到真实 API

```bash
cd /Users/zhou/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/zhouzeze2011_6ba3/msg/file/2026-01/ShopView

# 停止 Mock API
kill -9 $(lsof -ti:8000) 2>/dev/null

# 启动真实后端
./start-backend.sh
```

---

## ⚠️ 注意事项

1. **端口冲突**: 
   - Mock API 使用 8000 端口
   - 真实后端可以使用 2000 或 8000 端口
   - 确保两个服务不同时运行

2. **数据库连接**:
   - 确保数据库已连接并可访问
   - 检查 `env.app` 中的数据库配置是否正确

3. **前端不需要重启**:
   - 前端会自动根据域名判断使用哪个 API
   - 只需刷新浏览器页面即可

---

## 🔙 切换回 Mock API（如果需要）

如果以后需要切换回 Mock API 进行演示：

```bash
# 停止真实后端
# 在运行 start-backend.sh 的终端按 Ctrl+C

# 启动 Mock API
./start-mock-api.sh
```
