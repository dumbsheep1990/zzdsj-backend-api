#!/bin/bash
# LightRAG API服务停止脚本

echo "正在停止LightRAG API服务..."
cd "$(dirname "$0")"
docker-compose down
echo "LightRAG API服务已停止"
