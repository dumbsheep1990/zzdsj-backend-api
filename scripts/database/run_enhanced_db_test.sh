#!/bin/bash
"""
增强版远程PostgreSQL数据库测试脚本快速启动器
"""

echo "🚀 启动增强版PostgreSQL数据库测试..."
echo "📁 当前目录: $(pwd)"
echo "🐍 Python版本: $(python3 --version)"

# 检查脚本是否存在
if [ ! -f "scripts/test_remote_postgres.py" ]; then
    echo "❌ 未找到测试脚本: scripts/test_remote_postgres.py"
    echo "请确保在项目根目录下运行此脚本"
    exit 1
fi

# 检查Python依赖
echo "📦 检查Python依赖..."
python3 -c "import psycopg2" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 缺少psycopg2依赖，正在安装..."
    pip3 install psycopg2-binary
fi

# 运行测试脚本
echo "🔧 启动增强版数据库测试脚本..."
echo "----------------------------------------"
python3 scripts/test_remote_postgres.py

# 检查执行结果
if [ $? -eq 0 ]; then
    echo "✅ 增强版数据库测试完成！"
else
    echo "❌ 增强版数据库测试失败"
    exit 1
fi 