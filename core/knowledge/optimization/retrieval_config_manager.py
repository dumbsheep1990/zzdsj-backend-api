"""
统一检索配置管理器
提供类型安全的配置管理，支持动态更新和验证
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field, validator
import yaml
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class SearchEngine(str, Enum):
    """搜索引擎类型"""
    ELASTICSEARCH = "elasticsearch"
    MILVUS = "milvus"
    PGVECTOR = "pgvector"
    HYBRID = "hybrid"


class CacheStrategy(str, Enum):
    """缓存策略"""
    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"
    HYBRID = "hybrid"


class VectorSearchConfig(BaseModel):
    """向量搜索配置"""
    top_k: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="相似度阈值")
    engine: SearchEngine = Field(default=SearchEngine.MILVUS, description="向量搜索引擎")
    index_type: str = Field(default="HNSW", description="索引类型")
    metric_type: str = Field(default="COSINE", description="距离度量")
    search_params: Dict[str, Any] = Field(default_factory=dict, description="搜索参数")
    timeout: int = Field(default=30, ge=1, le=300, description="搜索超时时间(秒)")
    
    @validator('search_params')
    def validate_search_params(cls, v):
        """验证搜索参数"""
        allowed_keys = ['nprobe', 'ef', 'nlist', 'search_k']
        return {k: v for k, v in v.items() if k in allowed_keys}


class KeywordSearchConfig(BaseModel):
    """关键词搜索配置"""
    top_k: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    engine: SearchEngine = Field(default=SearchEngine.ELASTICSEARCH, description="全文搜索引擎")
    analyzer: str = Field(default="standard", description="分析器")
    boost_fields: Dict[str, float] = Field(default_factory=dict, description="字段权重")
    fuzzy_enabled: bool = Field(default=True, description="启用模糊搜索")
    fuzzy_distance: int = Field(default=2, ge=0, le=3, description="模糊搜索距离")
    timeout: int = Field(default=30, ge=1, le=300, description="搜索超时时间(秒)")


class HybridSearchConfig(BaseModel):
    """混合搜索配置"""
    vector_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="向量搜索权重")
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="关键词搜索权重")
    rrf_k: int = Field(default=60, ge=1, description="倒数排名融合参数")
    top_k: int = Field(default=10, ge=1, le=100, description="最终返回结果数量")
    vector_top_k: int = Field(default=20, ge=1, le=200, description="向量搜索候选数量")
    keyword_top_k: int = Field(default=20, ge=1, le=200, description="关键词搜索候选数量")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="最小分数阈值")
    
    @validator('vector_weight', 'keyword_weight')
    def validate_weights(cls, v, values):
        """验证权重和为1.0"""
        if 'vector_weight' in values and 'keyword_weight' in values:
            if abs(values['vector_weight'] + v - 1.0) > 0.01:
                raise ValueError("向量权重和关键词权重之和必须等于1.0")
        return v


class CacheConfig(BaseModel):
    """缓存配置"""
    enabled: bool = Field(default=True, description="启用缓存")
    strategy: CacheStrategy = Field(default=CacheStrategy.LRU, description="缓存策略")
    max_size: int = Field(default=1000, ge=1, description="最大缓存条目数")
    ttl_seconds: int = Field(default=3600, ge=1, description="TTL时间(秒)")
    redis_enabled: bool = Field(default=False, description="启用Redis缓存")
    redis_url: Optional[str] = Field(default=None, description="Redis连接URL")
    compression_enabled: bool = Field(default=True, description="启用压缩")


class PerformanceConfig(BaseModel):
    """性能配置"""
    max_concurrent_requests: int = Field(default=50, ge=1, le=1000, description="最大并发请求数")
    request_timeout: int = Field(default=60, ge=1, le=600, description="请求超时时间(秒)")
    batch_size: int = Field(default=10, ge=1, le=100, description="批处理大小")
    enable_query_optimization: bool = Field(default=True, description="启用查询优化")
    enable_result_deduplication: bool = Field(default=True, description="启用结果去重")
    monitoring_enabled: bool = Field(default=True, description="启用性能监控")


class RetrievalConfig(BaseModel):
    """完整检索配置"""
    vector_search: VectorSearchConfig = Field(default_factory=VectorSearchConfig)
    keyword_search: KeywordSearchConfig = Field(default_factory=KeywordSearchConfig)
    hybrid_search: HybridSearchConfig = Field(default_factory=HybridSearchConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    
    # 系统配置
    default_search_type: str = Field(default="hybrid", description="默认搜索类型")
    environment: str = Field(default="development", description="运行环境")
    debug_enabled: bool = Field(default=False, description="启用调试模式")
    
    class Config:
        extra = "allow"  # 允许额外字段


class RetrievalConfigManager:
    """检索配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path or self._get_default_config_path()
        self._config: Optional[RetrievalConfig] = None
        self._config_version = 0
        self._update_callbacks: List[Callable[[RetrievalConfig], None]] = []
        self._file_watcher_task: Optional[asyncio.Task] = None
        
    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        # 首先尝试环境变量
        if os.getenv("RETRIEVAL_CONFIG_PATH"):
            return os.getenv("RETRIEVAL_CONFIG_PATH")
        
        # 然后尝试项目根目录
        project_root = Path(__file__).parent.parent.parent.parent
        config_file = project_root / "config" / "retrieval_config.yaml"
        
        if config_file.exists():
            return str(config_file)
        
        # 最后使用默认配置
        return "config/retrieval_config.yaml"
    
    async def initialize(self) -> None:
        """初始化配置管理器"""
        try:
            await self.load_config()
            
            # 启动文件监控
            if os.path.exists(self.config_path):
                self._file_watcher_task = asyncio.create_task(
                    self._watch_config_file()
                )
                
            logger.info(f"检索配置管理器初始化成功，配置文件: {self.config_path}")
            
        except Exception as e:
            logger.error(f"检索配置管理器初始化失败: {str(e)}")
            # 使用默认配置
            self._config = RetrievalConfig()
            logger.info("使用默认配置")
    
    async def load_config(self) -> None:
        """加载配置"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                        config_data = yaml.safe_load(f)
                    else:
                        config_data = json.load(f)
                
                # 应用环境变量覆盖
                config_data = self._apply_env_overrides(config_data)
                
                # 验证和创建配置对象
                self._config = RetrievalConfig(**config_data)
                self._config_version += 1
                
                logger.info(f"配置加载成功，版本: {self._config_version}")
                
                # 通知回调函数
                await self._notify_config_update()
                
            else:
                # 配置文件不存在，使用默认配置
                self._config = RetrievalConfig()
                logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
                
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")
            if not self._config:
                self._config = RetrievalConfig()
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """应用环境变量覆盖"""
        # 环境变量映射
        env_mappings = {
            "VECTOR_SEARCH_TOP_K": ["vector_search", "top_k"],
            "VECTOR_SEARCH_THRESHOLD": ["vector_search", "similarity_threshold"],
            "KEYWORD_SEARCH_TOP_K": ["keyword_search", "top_k"],
            "HYBRID_VECTOR_WEIGHT": ["hybrid_search", "vector_weight"],
            "HYBRID_KEYWORD_WEIGHT": ["hybrid_search", "keyword_weight"],
            "CACHE_ENABLED": ["cache", "enabled"],
            "CACHE_MAX_SIZE": ["cache", "max_size"],
            "REDIS_URL": ["cache", "redis_url"],
            "MAX_CONCURRENT_REQUESTS": ["performance", "max_concurrent_requests"],
            "DEFAULT_SEARCH_TYPE": ["default_search_type"],
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # 类型转换
                if env_var.endswith("_ENABLED"):
                    env_value = env_value.lower() in ('true', '1', 'yes')
                elif env_var.endswith(("_K", "_SIZE", "_REQUESTS")):
                    env_value = int(env_value)
                elif env_var.endswith(("_THRESHOLD", "_WEIGHT")):
                    env_value = float(env_value)
                
                # 设置配置值
                current_level = config_data
                for key in config_path[:-1]:
                    if key not in current_level:
                        current_level[key] = {}
                    current_level = current_level[key]
                current_level[config_path[-1]] = env_value
        
        return config_data
    
    async def _watch_config_file(self) -> None:
        """监控配置文件变化"""
        last_modified = os.path.getmtime(self.config_path)
        
        while True:
            try:
                await asyncio.sleep(5)  # 每5秒检查一次
                
                if os.path.exists(self.config_path):
                    current_modified = os.path.getmtime(self.config_path)
                    if current_modified > last_modified:
                        logger.info("检测到配置文件变化，重新加载配置")
                        await self.load_config()
                        last_modified = current_modified
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控配置文件时出错: {str(e)}")
                await asyncio.sleep(30)  # 出错时等待更长时间
    
    async def _notify_config_update(self) -> None:
        """通知配置更新"""
        for callback in self._update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self._config)
                else:
                    callback(self._config)
            except Exception as e:
                logger.error(f"配置更新回调执行失败: {str(e)}")
    
    def register_update_callback(self, callback: Callable[[RetrievalConfig], None]) -> None:
        """注册配置更新回调"""
        self._update_callbacks.append(callback)
    
    def get_config(self) -> RetrievalConfig:
        """获取当前配置"""
        if not self._config:
            self._config = RetrievalConfig()
        return self._config
    
    def get_vector_search_config(self) -> VectorSearchConfig:
        """获取向量搜索配置"""
        return self.get_config().vector_search
    
    def get_keyword_search_config(self) -> KeywordSearchConfig:
        """获取关键词搜索配置"""
        return self.get_config().keyword_search
    
    def get_hybrid_search_config(self) -> HybridSearchConfig:
        """获取混合搜索配置"""
        return self.get_config().hybrid_search
    
    def get_cache_config(self) -> CacheConfig:
        """获取缓存配置"""
        return self.get_config().cache
    
    def get_performance_config(self) -> PerformanceConfig:
        """获取性能配置"""
        return self.get_config().performance
    
    async def update_config(self, updates: Dict[str, Any]) -> bool:
        """动态更新配置"""
        try:
            current_data = self._config.dict() if self._config else {}
            
            # 深度合并更新
            def deep_merge(target: Dict, source: Dict) -> Dict:
                for key, value in source.items():
                    if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                        target[key] = deep_merge(target[key], value)
                    else:
                        target[key] = value
                return target
            
            updated_data = deep_merge(current_data, updates)
            
            # 验证新配置
            new_config = RetrievalConfig(**updated_data)
            
            # 更新配置
            self._config = new_config
            self._config_version += 1
            
            # 保存到文件（可选）
            if os.path.exists(self.config_path):
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                        yaml.dump(updated_data, f, default_flow_style=False, allow_unicode=True)
                    else:
                        json.dump(updated_data, f, indent=2, ensure_ascii=False)
            
            # 通知更新
            await self._notify_config_update()
            
            logger.info(f"配置更新成功，版本: {self._config_version}")
            return True
            
        except Exception as e:
            logger.error(f"配置更新失败: {str(e)}")
            return False
    
    def get_config_version(self) -> int:
        """获取配置版本号"""
        return self._config_version
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return self._config.dict() if self._config else {}
    
    def validate_config(self) -> bool:
        """验证配置有效性"""
        try:
            if not self._config:
                return False
                
            # 权重验证
            hybrid = self._config.hybrid_search
            if abs(hybrid.vector_weight + hybrid.keyword_weight - 1.0) > 0.01:
                logger.error("混合搜索权重和不等于1.0")
                return False
            
            # 数值范围验证
            configs = [
                self._config.vector_search,
                self._config.keyword_search,
                self._config.hybrid_search
            ]
            
            for config in configs:
                if hasattr(config, 'top_k') and (config.top_k < 1 or config.top_k > 100):
                    logger.error(f"top_k值超出范围: {config.top_k}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"配置验证失败: {str(e)}")
            return False
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self._file_watcher_task:
            self._file_watcher_task.cancel()
            try:
                await self._file_watcher_task
            except asyncio.CancelledError:
                pass
        
        logger.info("检索配置管理器清理完成")


# 全局配置管理器实例
_config_manager: Optional[RetrievalConfigManager] = None


async def get_config_manager() -> RetrievalConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = RetrievalConfigManager()
        await _config_manager.initialize()
    
    return _config_manager


def get_config_manager_sync() -> RetrievalConfigManager:
    """同步获取配置管理器（用于非异步上下文）"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = RetrievalConfigManager()
        # 注意：同步模式下不会启动文件监控
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_config_manager.initialize())
        except:
            _config_manager._config = RetrievalConfig()
    
    return _config_manager 