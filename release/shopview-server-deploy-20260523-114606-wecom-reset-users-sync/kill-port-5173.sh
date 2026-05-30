#!/bin/bash

# 查找并终止占用端口 5173 的进程

echo "🔍 查找占用端口 5173 的进程..."

# 查找占用端口的进程
PID=$(lsof -ti:5173)

if [ -z "$PID" ]; then
    echo "✅ 端口 5173 未被占用"
else
    echo "⚠️  发现进程占用端口 5173: PID=$PID"
    echo ""
    echo "进程详情:"
    lsof -i:5173
    echo ""
    read -p "是否要终止该进程? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill -9 $PID
        echo "✅ 进程已被终止"
    else
        echo "❌ 取消操作"
    fi
fi
