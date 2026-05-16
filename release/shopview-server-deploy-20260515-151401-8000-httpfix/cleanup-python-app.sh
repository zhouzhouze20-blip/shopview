#!/bin/bash

# 清理 python_app 目录下的测试和调试文件

echo "🧹 清理 python_app 目录下的测试和调试文件..."
echo ""

cd "$(dirname "$0")/python_app"

# 删除测试文件
echo "1️⃣  删除测试文件..."
rm -f test*.py 2>/dev/null
echo "   ✅ 测试文件已删除"

# 删除检查脚本
echo "2️⃣  删除检查脚本..."
rm -f check*.py 2>/dev/null
echo "   ✅ 检查脚本已删除"

# 删除调试文件
echo "3️⃣  删除调试文件..."
rm -f debug*.py 2>/dev/null
echo "   ✅ 调试文件已删除"

# 删除示例数据文件（如果有）
echo "4️⃣  删除示例数据文件..."
rm -f *sample*.csv *sample*.json 2>/dev/null
rm -f counter_backup_*.csv 2>/dev/null
echo "   ✅ 示例数据文件已删除"

echo ""
echo "✅ python_app 目录清理完成！"
