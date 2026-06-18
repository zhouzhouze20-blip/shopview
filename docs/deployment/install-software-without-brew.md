# 不使用 Homebrew 的安装方法（Mac）

如果 Homebrew 安装失败或网络有问题，可以使用以下方法直接安装软件：

## 1. 安装 Python 3.11+

### 方法 A: 从官网下载安装包
1. 访问：https://www.python.org/downloads/
2. 下载 Python 3.11+ 的 Mac 安装包（.pkg 文件）
3. 双击安装包，按提示安装
4. 安装完成后，验证：
```bash
python3 --version
```

### 方法 B: 使用 pyenv（推荐）
```bash
# 安装 pyenv
curl https://pyenv.run | bash

# 配置环境变量（添加到 ~/.zshrc）
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc

# 重新加载配置
source ~/.zshrc

# 安装 Python 3.11
pyenv install 3.11.9
pyenv global 3.11.9
```

---

## 2. 安装 Node.js 和 npm

### 方法 A: 从官网下载安装包（最简单）
1. 访问：https://nodejs.org/
2. 下载 LTS 版本（推荐 18.x 或 20.x）
3. 下载 `.pkg` 安装包
4. 双击安装包，按提示安装
5. 验证：
```bash
node --version
npm --version
```

### 方法 B: 使用 nvm（Node Version Manager）
```bash
# 安装 nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# 配置环境变量（添加到 ~/.zshrc）
echo 'export NVM_DIR="$HOME/.nvm"' >> ~/.zshrc
echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"' >> ~/.zshrc

# 重新加载配置
source ~/.zshrc

# 安装 Node.js
nvm install 18
nvm use 18
```

---

## 3. 安装 PostgreSQL（如果使用本地数据库）

### 方法 A: 从官网下载安装包
1. 访问：https://www.postgresql.org/download/macosx/
2. 下载 Postgres.app 或使用 EnterpriseDB 的安装包
3. 按提示安装

### 方法 B: 使用 Postgres.app（最简单）
1. 访问：https://postgresapp.com/
2. 下载并安装 Postgres.app
3. 拖到应用程序文件夹
4. 启动应用即可使用

---

## 4. 安装 Docker Desktop（可选）

1. 访问：https://www.docker.com/products/docker-desktop/
2. 下载 Docker Desktop for Mac
3. 双击 `.dmg` 文件安装
4. 启动 Docker Desktop

---

## 快速安装顺序建议

### 最简方案（只安装必需的）：
1. **Python 3.11** → 从官网下载 .pkg 安装包
2. **Node.js** → 从官网下载 .pkg 安装包

安装完这两个就可以开始开发了！

### 完整方案：
1. 先安装 Python 3.11（官网下载）
2. 再安装 Node.js（官网下载）
3. PostgreSQL（如果需要本地数据库，使用 Postgres.app）
4. Docker（如果需要容器化部署）

---

## 安装后验证

```bash
# 检查 Python
python3 --version  # 应该显示 3.11.x 或更高

# 检查 Node.js
node --version     # 应该显示 v18.x 或更高
npm --version      # 应该显示版本号

# 检查 pip
pip3 --version
```

---

## 如果遇到网络问题

如果官网访问慢，可以使用国内镜像：
- Python: https://mirrors.huaweicloud.com/python/
- Node.js: https://npmmirror.com/mirrors/node/
