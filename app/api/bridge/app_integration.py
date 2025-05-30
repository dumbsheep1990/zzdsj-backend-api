"""
API桥接系统与主应用集成示例
展示如何将API桥接系统集成到主应用中
"""

from fastapi import FastAPI
import logging

# 导入桥接系统
from app.api.bridge.main import register_bridges_to_app

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app_with_bridges() -> FastAPI:
    """
    创建包含所有API桥接的FastAPI应用
    
    Returns:
        FastAPI应用实例
    """
    # 创建FastAPI应用
    app = FastAPI(
        title="ZZ Backend API",
        description="ZZ Backend API服务",
        version="1.0.0"
    )
    
    # 注册所有桥接路由
    logger.info("注册API桥接路由...")
    register_bridges_to_app(app)
    logger.info("API桥接路由注册完成")
    
    # 返回应用实例
    return app

# 示例：在主应用中使用
if __name__ == "__main__":
    # 在实际项目中，这部分代码应该放在main.py或类似的入口文件中
    app = create_app_with_bridges()
    
    # 这里可以继续添加其他路由和中间件
    
    # 启动应用
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
