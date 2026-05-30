#!/bin/bash

# 查找并终止占用 8000 端口的进程

echo "🔍 查找占用 8000 端口的进程..."

PID=$(lsof -ti:8000)

if [ -z "$PID" ]; then
    echo "✅ 端口 8000 未被占用"
else
    echo "⚠️  发现进程占用端口 8000:"
    lsof -i:8000
    
    echo ""
    echo "进程详情:"
    ps -p $PID -o pid,comm,args
    
    echo ""
    read -p "是否要终止该进程? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill -9 $PID
        echo "✅ 进程已被终止"
        sleep 1
        
        # 再次检查
        if lsof -ti:8000 > /dev/null 2>&1; then
            echo "⚠️  端口可能仍被占用，可能需要强制终止"
        else
            echo "✅ 端口已释放"
        fi
    else
        echo "❌ 取消操作"
    fi
fi
