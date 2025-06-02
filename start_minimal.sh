#!/bin/bash
# 环境启动脚本 - minimal
# 自动生成，请勿手动修改

echo "🚀 启动 minimal 环境..."

# 设置环境变量
export APP_ENV=minimal
export CONFIG_MODE=standard

# 激活Python虚拟环境 (如果存在)
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ 已激活虚拟环境"
fi

# 切换到项目目录
cd "/Users/wxn/Desktop/ZZDSJ/zzdsj-backend-api"

# 验证环境配置
python scripts/env_manager.py validate --environment minimal

if [ $? -eq 0 ]; then
    echo "✅ 环境配置验证通过"
    
    # 启动应用
    echo "🔥 启动应用..."
    python main.py
else
    echo "❌ 环境配置验证失败，请检查配置"
    exit 1
fi
