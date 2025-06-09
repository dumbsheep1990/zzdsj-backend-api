"""
优化搜索服务模块
集成所有优化组件，提供与现有API完全兼容的高性能搜索接口
支持渐进式迁移和向后兼容
"""

import logging
import time
from typing import List, Dict, Any, Optional, Union
from sqlalchemy.orm import Session

# 导入优化模块
try:
    from core.knowledge.optimization import (
        get_optimized_retrieval_manager,
        get_config_manager,
        get_strategy_selector,
        get_performance_optimizer,
        get_error_handler,
        CacheConfig,
        CacheStrategy
    )
    OPTIMIZATION_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"优化模块不可用: {str(e)}")
    OPTIMIZATION_AVAILABLE = False

# 导入现有服务（向后兼容）
from app.services.knowledge.hybrid_search_service import (
    HybridSearchService as LegacyHybridSearchService,
    SearchConfig
)

# 导入核心组件
try:
    from core.knowledge import RetrievalManager, VectorManager
    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False

# 使用独立配置避免循环导入
try:
    from app.config.optimization_standalone import standalone_settings
    SETTINGS_AVAILABLE = True
except ImportError:
    SETTINGS_AVAILABLE = False
    # 创建一个简单的配置对象
    class SimpleSettings:
        CACHE_MAX_SIZE = 5000
        CACHE_TTL_SECONDS = 1800
        CACHE_ENABLED = True
        ENABLE_SEARCH_OPTIMIZATION = True
    standalone_settings = SimpleSettings()

logger = logging.getLogger(__name__)


class OptimizedSearchService:
    """
    优化搜索服务
    
    整合所有优化组件，提供高性能、高可用的搜索服务
    完全兼容现有API接口，支持渐进式迁移
    """
    
    def __init__(self, db: Session, enable_optimization: bool = True):
        """
        初始化优化搜索服务
        
        Args:
            db: 数据库会话
            enable_optimization: 是否启用优化功能，False时使用传统服务
        """
        self.db = db
        self.enable_optimization = enable_optimization and OPTIMIZATION_AVAILABLE
        
        if self.enable_optimization:
            self._init_optimized_components()
        else:
            # 回退到传统服务
            self.legacy_service = LegacyHybridSearchService(db)
            logger.info("使用传统搜索服务（优化功能已禁用）")
    
    def _init_optimized_components(self):
        """初始化优化组件"""
        try:
            # 异步初始化标记
            self._optimization_ready = False
            self._optimized_manager = None
            self._config_manager = None
            self._strategy_selector = None
            
            logger.info("优化搜索服务初始化中...")
            
        except Exception as e:
            logger.error(f"优化组件初始化失败，回退到传统服务: {str(e)}")
            self.enable_optimization = False
            self.legacy_service = LegacyHybridSearchService(self.db)
    
    async def _ensure_optimization_ready(self):
        """确保优化组件已准备就绪"""
        if not self.enable_optimization:
            return
            
        if not self._optimization_ready:
            try:
                # 初始化优化管理器
                cache_config = CacheConfig(
                    strategy=CacheStrategy.HYBRID,
                    max_size=getattr(standalone_settings, 'CACHE_MAX_SIZE', 5000),
                    ttl_seconds=getattr(standalone_settings, 'CACHE_TTL_SECONDS', 1800),
                    enabled=getattr(standalone_settings, 'CACHE_ENABLED', True)
                )
                
                self._optimized_manager = await get_optimized_retrieval_manager(
                    cache_config=cache_config
                )
                self._config_manager = await get_config_manager()
                self._strategy_selector = await get_strategy_selector()
                
                self._optimization_ready = True
                logger.info("优化组件初始化完成")
                
            except Exception as e:
                logger.error(f"优化组件初始化失败: {str(e)}")
                raise
    
    async def search(self, config: SearchConfig) -> Dict[str, Any]:
        """
        执行搜索（主要接口，完全兼容现有API）
        
        Args:
            config: 搜索配置对象
            
        Returns:
            搜索结果字典
        """
        if not self.enable_optimization:
            # 使用传统服务
            return await self.legacy_service.search(config)
        
        try:
            await self._ensure_optimization_ready()
            return await self._optimized_search(config)
            
        except Exception as e:
            logger.error(f"优化搜索失败，回退到传统搜索: {str(e)}")
            # 自动回退到传统服务
            if not hasattr(self, 'legacy_service'):
                self.legacy_service = LegacyHybridSearchService(self.db)
            return await self.legacy_service.search(config)
    
    async def _optimized_search(self, config: SearchConfig) -> Dict[str, Any]:
        """
        使用优化组件执行搜索
        
        Args:
            config: 搜索配置
            
        Returns:
            优化的搜索结果
        """
        start_time = time.time()
        
        try:
            # 转换配置格式
            search_params = {
                "knowledge_base_id": config.knowledge_base_ids[0] if config.knowledge_base_ids else None,
                "search_type": self._map_search_engine(config.search_engine),
                "user_preferences": {
                    "vector_weight": config.vector_weight,
                    "text_weight": config.text_weight,
                    "hybrid_method": config.hybrid_method
                },
                "size": config.size,
                "threshold": config.threshold
            }
            
            # 使用优化管理器执行搜索
            result = await self._optimized_manager.search(
                query=config.query_text,
                **search_params
            )
            
            # 转换结果格式以兼容现有API
            return await self._format_optimized_result(result, config, start_time)
            
        except Exception as e:
            logger.error(f"优化搜索执行失败: {str(e)}")
            raise
    
    def _map_search_engine(self, engine: str) -> str:
        """映射搜索引擎类型"""
        engine_mapping = {
            "es": "keyword",
            "milvus": "vector", 
            "hybrid": "hybrid",
            "semantic": "vector",
            "keyword": "keyword",
            "auto": None  # 让策略选择器自动选择
        }
        return engine_mapping.get(engine, "hybrid")
    
    async def _format_optimized_result(
        self, 
        result: Dict[str, Any], 
        config: SearchConfig, 
        start_time: float
    ) -> Dict[str, Any]:
        """
        格式化优化搜索结果以兼容现有API
        
        Args:
            result: 优化管理器返回的结果
            config: 原始搜索配置
            start_time: 搜索开始时间
            
        Returns:
            兼容现有API的结果格式
        """
        search_time = (time.time() - start_time) * 1000  # 毫秒
        
        # 转换结果格式
        formatted_results = []
        for item in result.get("results", []):
            formatted_results.append({
                "id": item.get("id", ""),
                "score": item.get("score", 0.0),
                "document_id": item.get("document_id", ""),
                "knowledge_base_id": item.get("knowledge_base_id"),
                "title": item.get("title"),
                "content": item.get("content"),
                "vector_score": item.get("vector_score"),
                "text_score": item.get("text_score"),
                "highlight": item.get("highlight"),
                "metadata": item.get("metadata", {})
            })
        
        return {
            "results": formatted_results,
            "total": len(formatted_results),
            "query": config.query_text,
            "strategy_used": result.get("strategy", config.hybrid_method),
            "engine_used": f"optimized_{result.get('strategy', 'hybrid')}",
            "search_time_ms": search_time,
            "knowledge_base_ids": config.knowledge_base_ids,
            "optimization_enabled": True,
            "performance_stats": await self._get_performance_stats()
        }
    
    async def _get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        if not self._optimization_ready:
            return {}
            
        try:
            stats = await self._optimized_manager.get_system_status()
            return {
                "cache_hit_rate": stats["performance_stats"]["cache_metrics"]["hit_rate"],
                "avg_response_time": stats["performance_stats"]["request_metrics"]["avg_response_time"],
                "active_requests": stats["performance_stats"]["concurrency_metrics"]["active_requests"],
                "error_rate": stats["error_stats"]["global_stats"]["failure_rate"]
            }
        except Exception as e:
            logger.warning(f"获取性能统计失败: {str(e)}")
            return {}
    
    # 兼容性方法：保持与现有API的完全兼容
    async def semantic_search(
        self,
        query: str,
        knowledge_base_ids: Optional[List[str]] = None,
        top_k: int = 10,
        threshold: float = 0.7
    ) -> Dict[str, Any]:
        """语义搜索接口（兼容现有API）"""
        config = SearchConfig(
            query_text=query,
            knowledge_base_ids=knowledge_base_ids or [],
            size=top_k,
            search_engine="semantic",
            threshold=threshold
        )
        return await self.search(config)
    
    async def keyword_search(
        self,
        query: str,
        knowledge_base_ids: Optional[List[str]] = None,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """关键词搜索接口（兼容现有API）"""
        config = SearchConfig(
            query_text=query,
            knowledge_base_ids=knowledge_base_ids or [],
            size=top_k,
            search_engine="keyword"
        )
        return await self.search(config)
    
    async def hybrid_search(
        self,
        query: str,
        knowledge_base_ids: Optional[List[str]] = None,
        top_k: int = 10,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """混合搜索接口（兼容现有API）"""
        config = SearchConfig(
            query_text=query,
            knowledge_base_ids=knowledge_base_ids or [],
            size=top_k,
            search_engine="hybrid",
            vector_weight=semantic_weight,
            text_weight=keyword_weight,
            threshold=threshold
        )
        return await self.search(config)
    
    async def get_optimization_status(self) -> Dict[str, Any]:
        """获取优化状态信息"""
        if not self.enable_optimization:
            return {
                "enabled": False,
                "status": "disabled",
                "message": "优化功能已禁用"
            }
        
        if not self._optimization_ready:
            return {
                "enabled": True,
                "status": "initializing",
                "message": "优化组件初始化中"
            }
        
        try:
            await self._ensure_optimization_ready()
            system_status = await self._optimized_manager.get_system_status()
            
            return {
                "enabled": True,
                "status": "ready",
                "config_version": system_status["config_version"],
                "health": system_status["health"]["status"],
                "performance_stats": await self._get_performance_stats(),
                "message": "优化功能运行正常"
            }
        except Exception as e:
            return {
                "enabled": True,
                "status": "error",
                "error": str(e),
                "message": "优化功能出现错误"
            }
    
    async def cleanup(self):
        """清理资源"""
        if hasattr(self, '_optimized_manager') and self._optimized_manager:
            try:
                await self._optimized_manager.cleanup()
            except Exception as e:
                logger.error(f"清理优化管理器失败: {str(e)}")


# 工厂函数
def get_optimized_search_service(
    db: Session, 
    enable_optimization: Optional[bool] = None
) -> OptimizedSearchService:
    """
    获取优化搜索服务实例
    
    Args:
        db: 数据库会话
        enable_optimization: 是否启用优化，None时从配置读取
        
    Returns:
        OptimizedSearchService实例
    """
    if enable_optimization is None:
        # 从配置读取
        enable_optimization = getattr(standalone_settings, 'ENABLE_SEARCH_OPTIMIZATION', True)
    
    return OptimizedSearchService(db, enable_optimization)


# 向后兼容的别名
def get_hybrid_search_service(db: Session) -> OptimizedSearchService:
    """
    向后兼容的工厂函数
    
    Args:
        db: 数据库会话
        
    Returns:
        OptimizedSearchService实例（如果禁用优化则使用传统服务）
    """
    return get_optimized_search_service(db) 