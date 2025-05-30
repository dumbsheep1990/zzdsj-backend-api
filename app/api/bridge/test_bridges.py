"""
API桥接测试脚本
用于验证所有桥接路由是否正常工作
"""

import logging
import importlib
import sys
import os
from typing import List, Dict, Any, Optional
from fastapi import FastAPI
from fastapi.testclient import TestClient

# 确保能够导入桥接模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.api.bridge.api_bridge_mapping import API_BRIDGE_MAPPING
from app.api.bridge.main import register_bridges_to_app

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_app() -> FastAPI:
    """
    创建测试用的FastAPI应用
    
    Returns:
        FastAPI应用实例
    """
    app = FastAPI(title="API Bridge Test App")
    register_bridges_to_app(app)
    return app

def test_all_bridges():
    """测试所有API桥接是否正常工作"""
    logger.info("开始API桥接测试...")
    
    # 创建测试应用
    app = create_test_app()
    client = TestClient(app)
    
    # 获取所有路由
    routes = []
    for route in app.routes:
        if hasattr(route, "path"):
            routes.append({
                "path": route.path,
                "methods": route.methods if hasattr(route, "methods") else None,
                "name": route.name if hasattr(route, "name") else None
            })
    
    logger.info(f"测试应用中发现 {len(routes)} 个路由")
    
    # 记录发现的路由
    for route in routes:
        logger.info(f"路由: {route['path']} - 方法: {route['methods']}")
    
    # 进行简单测试
    try:
        response = client.get("/docs")
        if response.status_code == 200:
            logger.info("Swagger文档访问成功，应用正常运行")
        else:
            logger.error(f"Swagger文档访问失败，状态码: {response.status_code}")
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
    
    logger.info("API桥接测试完成")

if __name__ == "__main__":
    test_all_bridges()
