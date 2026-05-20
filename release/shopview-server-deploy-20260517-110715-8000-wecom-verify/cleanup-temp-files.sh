#!/bin/bash

# 清理临时和测试文件的脚本

echo "🧹 开始清理临时和测试文件..."
echo ""

# 项目根目录
cd "$(dirname "$0")"

# 1. 删除测试文件
echo "1️⃣  删除测试文件..."
rm -f test*.py test*.sh test*.bat test*.ps1 test*.html 2>/dev/null
echo "   ✅ 测试文件已删除"

# 2. 删除检查脚本（保留环境检查脚本）
echo "2️⃣  删除检查脚本..."
rm -f check*.py 2>/dev/null
# 保留有用的检查脚本
# check-mac-env.sh - 保留
# check-db-connection.sh - 保留
# diagnose-db-connection.sh - 保留
echo "   ✅ 检查脚本已删除（保留环境检查脚本）"

# 3. 删除调试文件
echo "3️⃣  删除调试文件..."
rm -f debug*.py 2>/dev/null
echo "   ✅ 调试文件已删除"

# 4. 删除多余的 Dockerfile（只保留主要的）
echo "4️⃣  删除多余的 Dockerfile..."
rm -f Dockerfile.almalinux Dockerfile.debug Dockerfile.esbuild-fix \
      Dockerfile.final Dockerfile.fixed Dockerfile.linux \
      Dockerfile.simple Dockerfile.simple-build Dockerfile.simple-fixed \
      Dockerfile.typescript-fix Dockerfile.ubuntu Dockerfile.verbose \
      Dockerfile.webpack Dockerfile.working 2>/dev/null
echo "   ✅ 多余的 Dockerfile 已删除（保留主要的 Dockerfile）"

# 5. 删除旧的更新脚本
echo "5️⃣  删除旧的更新脚本..."
rm -f update_*.py 2>/dev/null
echo "   ✅ 旧的更新脚本已删除"

# 6. 删除临时的安装脚本（保留有用的）
echo "6️⃣  删除临时的安装脚本..."
rm -f install-homebrew-retry.sh quick-install.sh fix-permissions.sh 2>/dev/null
echo "   ✅ 临时安装脚本已删除"

# 7. 删除旧的运行脚本
echo "7️⃣  删除旧的运行脚本..."
rm -f run-app-direct.py run_python.py start-simple.py 2>/dev/null
echo "   ✅ 旧的运行脚本已删除"

# 8. 删除 Windows 批处理文件（Mac 环境不需要）
echo "8️⃣  删除 Windows 批处理文件..."
rm -f *.bat 2>/dev/null
echo "   ✅ Windows 批处理文件已删除"

# 9. 删除 PowerShell 脚本（Mac 环境不需要）
echo "9️⃣  删除 PowerShell 脚本..."
rm -f *.ps1 2>/dev/null
echo "   ✅ PowerShell 脚本已删除"

# 10. 删除旧的部署脚本变体（保留主要的）
echo "🔟 删除旧的部署脚本变体..."
rm -f build-*.sh build-*.bat build-*.ps1 2>/dev/null
rm -f deploy-*-windows-*.sh deploy-*-windows-*.ps1 2>/dev/null
rm -f redeploy.ps1 redeploy.sh 2>/dev/null
rm -f fix-api-and-redeploy.* 2>/dev/null
echo "   ✅ 旧的部署脚本已删除（保留主要的部署脚本）"

# 11. 删除多余的启动脚本变体（保留主要的）
echo "1️⃣1️⃣ 删除多余的启动脚本变体..."
rm -f start-frontend-debug.bat start-frontend-fixed.bat 2>/dev/null
rm -f start-app-direct.ps1 2>/dev/null
echo "   ✅ 多余的启动脚本已删除（保留主要的启动脚本）"

echo ""
echo "=========================================="
echo "✅ 清理完成！"
echo "=========================================="
echo ""
echo "保留的有用文件："
echo "  - 启动脚本: start-*.sh, start-manual.py"
echo "  - 部署脚本: deploy-*.sh"
echo "  - 检查脚本: check-mac-env.sh, diagnose-db-connection.sh"
echo "  - 配置文件: env.app, *.yml"
echo ""
