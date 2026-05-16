#!/bin/bash

# Mac 环境检查脚本
echo "========================================"
echo "🔍 检查 Mac 开发环境"
echo "========================================"
echo ""

# 检查 Homebrew
echo "📦 检查 Homebrew..."
if command -v brew &> /dev/null; then
    echo "✅ Homebrew 已安装: $(brew --version | head -n 1)"
else
    echo "❌ Homebrew 未安装"
    echo "   安装命令: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
fi
echo ""

# 检查 Python
echo "🐍 检查 Python..."
# 优先检查 /usr/local/bin/python3（新安装的版本）
if [ -f "/usr/local/bin/python3" ]; then
    PYTHON_CMD="/usr/local/bin/python3"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD=""
fi

if [ -n "$PYTHON_CMD" ]; then
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
    PYTHON_PATH=$(which $PYTHON_CMD || echo $PYTHON_CMD)
    echo "✅ Python 已安装: $PYTHON_VERSION"
    echo "   路径: $PYTHON_PATH"
    
    # 检查版本是否 >= 3.11
    PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)' 2>/dev/null)
    PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)' 2>/dev/null)
    
    if [ -n "$PYTHON_MAJOR" ] && [ -n "$PYTHON_MINOR" ]; then
        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
            echo "✅ Python 版本符合要求 (>= 3.11)"
        else
            echo "⚠️  Python 版本过低，建议升级到 3.11+"
            echo "   当前使用的版本: $PYTHON_VERSION"
            echo "   安装命令: 从 https://www.python.org/downloads/ 下载安装"
        fi
    fi
    
    # 检查是否有多个 Python 版本
    if [ -f "/usr/bin/python3" ] && [ "$PYTHON_PATH" != "/usr/bin/python3" ]; then
        SYSTEM_PYTHON_VERSION=$(/usr/bin/python3 --version 2>&1)
        echo "   ℹ️  系统自带版本: $SYSTEM_PYTHON_VERSION (位于 /usr/bin/python3)"
        echo "   ℹ️  当前使用版本: $PYTHON_VERSION (优先使用)"
    fi
else
    echo "❌ Python 未安装"
    echo "   安装命令: 从 https://www.python.org/downloads/ 下载安装"
fi
echo ""

# 检查 pip
echo "📦 检查 pip..."
if command -v pip3 &> /dev/null; then
    echo "✅ pip 已安装: $(pip3 --version | cut -d' ' -f2)"
else
    echo "❌ pip 未安装"
    echo "   通常随 Python 一起安装"
fi
echo ""

# 检查 Node.js
echo "📦 检查 Node.js..."
if command -v node &> /dev/null; then
    echo "✅ Node.js 已安装: $(node --version)"
else
    echo "❌ Node.js 未安装"
    echo "   安装命令: brew install node"
fi
echo ""

# 检查 npm
echo "📦 检查 npm..."
if command -v npm &> /dev/null; then
    echo "✅ npm 已安装: $(npm --version)"
else
    echo "❌ npm 未安装"
    echo "   通常随 Node.js 一起安装"
fi
echo ""

# 检查 PostgreSQL
echo "🐘 检查 PostgreSQL..."
if command -v psql &> /dev/null; then
    echo "✅ PostgreSQL 已安装: $(psql --version | cut -d' ' -f3)"
    
    # 检查 PostgreSQL 服务是否运行
    if pg_isready &> /dev/null; then
        echo "✅ PostgreSQL 服务正在运行"
    else
        echo "⚠️  PostgreSQL 服务未运行"
        echo "   启动命令: brew services start postgresql@14"
    fi
else
    echo "⚠️  PostgreSQL 未安装（如果使用远程数据库可忽略）"
    echo "   安装命令: brew install postgresql@14"
fi
echo ""

# 检查 Docker
echo "🐳 检查 Docker..."
if command -v docker &> /dev/null; then
    echo "✅ Docker 已安装: $(docker --version | cut -d' ' -f3 | tr -d ',')"
    
    # 检查 Docker 是否运行
    if docker info &> /dev/null; then
        echo "✅ Docker 服务正在运行"
    else
        echo "⚠️  Docker 服务未运行"
        echo "   请启动 Docker Desktop"
    fi
else
    echo "⚠️  Docker 未安装（如果只使用本地开发可忽略）"
    echo "   安装命令: brew install --cask docker"
fi
echo ""

# 检查 Git
echo "📝 检查 Git..."
if command -v git &> /dev/null; then
    echo "✅ Git 已安装: $(git --version | cut -d' ' -f3)"
else
    echo "❌ Git 未安装"
    echo "   安装命令: brew install git"
fi
echo ""

# 检查项目依赖
echo "📋 检查项目依赖..."
echo ""

# 检查 Python 依赖
if [ -f "python_requirements.txt" ]; then
    echo "检查 Python 依赖..."
    if python3 -c "import fastapi" 2>/dev/null; then
        echo "✅ Python 依赖已安装"
    else
        echo "⚠️  Python 依赖未安装"
        echo "   安装命令: pip3 install -r python_requirements.txt"
    fi
else
    echo "⚠️  未找到 python_requirements.txt"
fi
echo ""

# 检查 Node 依赖
if [ -d "client" ] && [ -f "client/package.json" ]; then
    echo "检查前端依赖..."
    if [ -d "client/node_modules" ]; then
        echo "✅ 前端依赖已安装"
    else
        echo "⚠️  前端依赖未安装"
        echo "   安装命令: cd client && npm install"
    fi
else
    echo "⚠️  未找到前端项目目录"
fi
echo ""

# 检查环境变量文件
echo "📝 检查环境变量配置..."
if [ -f "env.app" ]; then
    echo "✅ 环境变量文件存在: env.app"
else
    echo "⚠️  环境变量文件不存在: env.app"
    echo "   需要创建并配置数据库连接信息"
fi
echo ""

# 检查脚本权限
echo "🔐 检查脚本权限..."
SCRIPTS=("start-backend.sh" "start-frontend-dev.sh" "start-app.sh" "deploy-app-only.sh")
for script in "${SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            echo "✅ $script 有执行权限"
        else
            echo "⚠️  $script 缺少执行权限"
            echo "   修复命令: chmod +x $script"
        fi
    fi
done
echo ""

echo "========================================"
echo "✅ 环境检查完成"
echo "========================================"
echo ""
echo "📖 详细安装指南请查看: MAC_SETUP_GUIDE.md"
echo ""
