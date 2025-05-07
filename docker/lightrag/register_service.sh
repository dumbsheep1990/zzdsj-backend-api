#!/bin/bash
# LightRAG服务注册脚本

echo "正在启动LightRAG服务并注册到服务发现系统..."
cd "$(dirname "$0")"

# 启动服务
docker-compose up -d

# 等待服务启动
echo "等待LightRAG服务启动..."
sleep 10

# 运行服务注册脚本
echo "正在注册LightRAG服务到服务发现系统..."
python register_service.py

echo "LightRAG API服务已启动并注册，地址: http://localhost:9621"
