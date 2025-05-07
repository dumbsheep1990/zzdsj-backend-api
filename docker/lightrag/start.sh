#!/bin/bash
# LightRAG API服务启动脚本

echo "正在启动LightRAG API服务..."
cd "$(dirname "$0")"
docker-compose up -d
echo "LightRAG API服务启动完成，地址: http://localhost:9621"
echo "可通过 http://localhost:9621/health 检查服务健康状态"
