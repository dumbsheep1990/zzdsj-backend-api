"""
搜索路由集成模块
将优化搜索路由集成到主路由系统中
"""

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

def integrate_optimized_routes(main_router: APIRouter) -> None:
    """
    将优化搜索路由集成到主路由中
    
    Args:
        main_router: 主路由器实例
    """
    try:
        # 导入优化搜索路由
        from app.api.frontend.search.optimized import router as optimized_router
        
        # 将优化路由集成到主路由
        main_router.include_router(
            optimized_router,
            prefix="/search",
            tags=["search-optimized"]
        )
        
        logger.info("✅ 优化搜索路由已成功集成")
        
    except ImportError as e:
        logger.warning(f"⚠️ 优化搜索路由不可用: {str(e)}")
        logger.info("系统将继续使用传统搜索功能")
    except Exception as e:
        logger.error(f"❌ 优化搜索路由集成失败: {str(e)}")


def check_integration_status() -> dict:
    """
    检查集成状态
    
    Returns:
        集成状态信息
    """
    try:
        from app.api.frontend.search.optimized import router as optimized_router
        from app.services.knowledge.optimized_search_service import OPTIMIZATION_AVAILABLE
        
        return {
            "optimized_routes": True,
            "optimization_modules": OPTIMIZATION_AVAILABLE,
            "status": "fully_integrated" if OPTIMIZATION_AVAILABLE else "partially_integrated"
        }
    except ImportError:
        return {
            "optimized_routes": False,
            "optimization_modules": False,
            "status": "not_integrated"
        }


# 便捷函数
def is_optimization_integrated() -> bool:
    """检查优化功能是否已集成"""
    status = check_integration_status()
    return status["status"] in ["fully_integrated", "partially_integrated"] 