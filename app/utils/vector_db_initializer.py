"""
向量数据库自动初始化器
在系统启动时根据配置自动初始化向量数据库
支持多种后端类型和故障转移机制
集成ZZDSJ高级配置管理系统
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

# 使用集成的配置管理系统
from app.config.vector_database_integration import (
    get_vector_db_config_manager,
    get_integrated_vector_config,
    get_integrated_backend_config,
    validate_integrated_vector_config
)
from app.schemas.vector_store import VectorBackendType
from app.utils.storage.vector_storage import (
    VectorStoreFactory,
    init_standard_document_collection,
    init_pgvector_document_collection,
    init_elasticsearch_document_collection,
    init_knowledge_base_collection,
    init_elasticsearch_knowledge_base_collection
)

logger = logging.getLogger(__name__)


class IntegratedVectorDatabaseInitializer:
    """集成的向量数据库自动初始化器"""
    
    def __init__(self):
        """初始化"""
        self.config_manager = get_vector_db_config_manager()
        self.current_backend = None
        self.initialized_collections = []
        self.health_check_task = None
        self.failed_attempts = {}  # 记录各后端的连续失败次数
        
    async def initialize(self) -> bool:
        """
        执行向量数据库初始化
        
        返回:
            是否初始化成功
        """
        # 验证配置
        validation_result = validate_integrated_vector_config()
        if not validation_result["is_valid"]:
            logger.error(f"向量数据库配置验证失败: {validation_result['errors']}")
            if validation_result.get("warnings"):
                logger.warning(f"配置警告: {validation_result['warnings']}")
        
        # 检查是否启用自动初始化
        if not self.config_manager.is_auto_init_enabled():
            logger.info("向量数据库自动初始化已禁用")
            return True
        
        logger.info("开始向量数据库自动初始化...")
        
        # 获取要尝试的后端列表
        backends_to_try = [self.config_manager.get_primary_backend()] + self.config_manager.get_fallback_backends()
        
        # 按顺序尝试初始化各个后端
        for backend_type in backends_to_try:
            logger.info(f"尝试初始化 {backend_type.value} 向量数据库...")
            
            success = await self._initialize_backend(backend_type)
            if success:
                self.current_backend = backend_type
                logger.info(f"向量数据库初始化成功，使用后端: {backend_type.value}")
                
                # 启动健康检查
                auto_init_config = self.config_manager.get_auto_init_config()
                if auto_init_config.get("health_check_enabled", True):
                    await self._start_health_check()
                
                return True
            else:
                logger.warning(f"{backend_type.value} 初始化失败，尝试下一个后端...")
        
        logger.error("所有向量数据库后端初始化失败")
        return False
    
    async def _initialize_backend(self, backend_type: VectorBackendType) -> bool:
        """
        初始化指定的后端
        
        参数:
            backend_type: 后端类型
            
        返回:
            是否初始化成功
        """
        try:
            # 获取后端配置
            backend_config = self.config_manager.get_backend_config(backend_type)
            
            # 获取重试配置
            auto_init_config = self.config_manager.get_auto_init_config()
            retry_attempts = auto_init_config.get("retry_attempts", 3)
            retry_delay = auto_init_config.get("retry_delay", 5)
            
            # 执行初始化重试
            for attempt in range(retry_attempts):
                try:
                    logger.info(f"第 {attempt + 1} 次尝试初始化 {backend_type.value}")
                    
                    # 初始化各个集合
                    success = await self._initialize_collections(backend_type, backend_config)
                    if success:
                        # 重置失败计数
                        self.failed_attempts[backend_type] = 0
                        return True
                    
                except Exception as e:
                    logger.error(f"初始化 {backend_type.value} 失败 (尝试 {attempt + 1}): {str(e)}")
                    
                    if attempt < retry_attempts - 1:
                        logger.info(f"等待 {retry_delay} 秒后重试...")
                        await asyncio.sleep(retry_delay)
            
            # 记录失败次数
            self.failed_attempts[backend_type] = self.failed_attempts.get(backend_type, 0) + 1
            return False
            
        except Exception as e:
            logger.error(f"初始化 {backend_type.value} 时发生异常: {str(e)}")
            return False
    
    async def _initialize_collections(self, backend_type: VectorBackendType, backend_config: Dict[str, Any]) -> bool:
        """
        初始化集合
        
        参数:
            backend_type: 后端类型
            backend_config: 后端配置
            
        返回:
            是否成功
        """
        collections_to_create = self.config_manager.get_auto_create_collections()
        
        for collection_template in collections_to_create:
            try:
                success = await self._create_collection(
                    backend_type, 
                    collection_template, 
                    backend_config
                )
                
                if success:
                    self.initialized_collections.append((backend_type, collection_template))
                    logger.info(f"成功创建集合: {collection_template} ({backend_type.value})")
                else:
                    logger.error(f"创建集合失败: {collection_template} ({backend_type.value})")
                    return False
                    
            except Exception as e:
                logger.error(f"创建集合 {collection_template} 时发生异常: {str(e)}")
                return False
        
        return True
    
    async def _create_collection(self, 
                               backend_type: VectorBackendType, 
                               collection_template: str, 
                               backend_config: Dict[str, Any]) -> bool:
        """
        创建单个集合
        
        参数:
            backend_type: 后端类型
            collection_template: 集合模板名称
            backend_config: 后端配置
            
        返回:
            是否成功
        """
        # 使用线程池执行同步的初始化函数
        loop = asyncio.get_event_loop()
        
        # 获取通用配置
        vector_config = get_integrated_vector_config()
        common_config = vector_config.get("common", {})
        default_dimension = common_config.get("default_dimension", 1536)
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            if collection_template == "document_collection":
                if backend_type == VectorBackendType.MILVUS:
                    connection_config = backend_config.get("connection", {})
                    return await loop.run_in_executor(
                        executor,
                        lambda: init_standard_document_collection(
                            host=connection_config.get("host", "localhost"),
                            port=connection_config.get("port", 19530),
                            backend_type=backend_type,
                            dimension=default_dimension,
                            user=connection_config.get("user"),
                            password=connection_config.get("password"),
                            secure=connection_config.get("secure", False),
                            timeout=connection_config.get("timeout", 10)
                        )
                    )
                elif backend_type == VectorBackendType.PGVECTOR:
                    connection_config = backend_config.get("connection", {})
                    database_url = connection_config.get("database_url")
                    
                    # 如果没有完整的database_url，构建一个
                    if not database_url:
                        host = connection_config.get("host", "localhost")
                        port = connection_config.get("port", 5432)
                        user = connection_config.get("user", "postgres")
                        password = connection_config.get("password", "password")
                        database = connection_config.get("database", "postgres")
                        database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
                    
                    return await loop.run_in_executor(
                        executor,
                        lambda: init_pgvector_document_collection(
                            database_url=database_url,
                            dimension=default_dimension
                        )
                    )
                elif backend_type == VectorBackendType.ELASTICSEARCH:
                    connection_config = backend_config.get("connection", {})
                    return await loop.run_in_executor(
                        executor,
                        lambda: init_elasticsearch_document_collection(
                            es_url=connection_config.get("es_url", "http://localhost:9200"),
                            dimension=default_dimension,
                            username=connection_config.get("username"),
                            password=connection_config.get("password"),
                            api_key=connection_config.get("api_key"),
                            timeout=connection_config.get("timeout", 30)
                        )
                    )
                    
            elif collection_template == "knowledge_base_collection":
                if backend_type == VectorBackendType.MILVUS:
                    connection_config = backend_config.get("connection", {})
                    return await loop.run_in_executor(
                        executor,
                        lambda: init_knowledge_base_collection(
                            host=connection_config.get("host", "localhost"),
                            port=connection_config.get("port", 19530),
                            backend_type=backend_type,
                            dimension=default_dimension,
                            user=connection_config.get("user"),
                            password=connection_config.get("password"),
                            secure=connection_config.get("secure", False),
                            timeout=connection_config.get("timeout", 10)
                        )
                    )
                elif backend_type == VectorBackendType.PGVECTOR:
                    connection_config = backend_config.get("connection", {})
                    database_url = connection_config.get("database_url")
                    
                    if not database_url:
                        host = connection_config.get("host", "localhost")
                        port = connection_config.get("port", 5432)
                        user = connection_config.get("user", "postgres")
                        password = connection_config.get("password", "password")
                        database = connection_config.get("database", "postgres")
                        database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
                    
                    return await loop.run_in_executor(
                        executor,
                        lambda: init_pgvector_document_collection(
                            database_url=database_url,
                            table_name="knowledge_base_vectors",
                            dimension=default_dimension
                        )
                    )
                elif backend_type == VectorBackendType.ELASTICSEARCH:
                    connection_config = backend_config.get("connection", {})
                    return await loop.run_in_executor(
                        executor,
                        lambda: init_elasticsearch_knowledge_base_collection(
                            es_url=connection_config.get("es_url", "http://localhost:9200"),
                            dimension=default_dimension,
                            username=connection_config.get("username"),
                            password=connection_config.get("password"),
                            api_key=connection_config.get("api_key"),
                            timeout=connection_config.get("timeout", 30)
                        )
                    )
        
        logger.warning(f"未知的集合模板: {collection_template}")
        return False
    
    async def _start_health_check(self) -> None:
        """启动健康检查任务"""
        if self.health_check_task:
            return
        
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("已启动向量数据库健康检查")
    
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        auto_init_config = self.config_manager.get_auto_init_config()
        health_check_interval = auto_init_config.get("health_check_interval", 60)
        auto_failover = auto_init_config.get("auto_failover", True)
        failover_threshold = auto_init_config.get("failover_threshold", 3)
        
        while True:
            try:
                await asyncio.sleep(health_check_interval)
                
                if self.current_backend:
                    is_healthy = await self._check_backend_health(self.current_backend)
                    
                    if not is_healthy:
                        logger.warning(f"检测到 {self.current_backend.value} 健康状况异常")
                        
                        # 增加失败计数
                        self.failed_attempts[self.current_backend] = \
                            self.failed_attempts.get(self.current_backend, 0) + 1
                        
                        # 检查是否需要故障转移
                        if (auto_failover and 
                            self.failed_attempts[self.current_backend] >= failover_threshold):
                            
                            logger.error(f"{self.current_backend.value} 连续失败 {self.failed_attempts[self.current_backend]} 次，执行故障转移")
                            await self._perform_failover()
                    else:
                        # 重置失败计数
                        self.failed_attempts[self.current_backend] = 0
                        
            except Exception as e:
                logger.error(f"健康检查过程中发生异常: {str(e)}")
    
    async def _check_backend_health(self, backend_type: VectorBackendType) -> bool:
        """
        检查后端健康状况
        
        参数:
            backend_type: 后端类型
            
        返回:
            是否健康
        """
        try:
            backend_config = self.config_manager.get_backend_config(backend_type)
            connection_config = backend_config.get("connection", {})
            
            if backend_type == VectorBackendType.MILVUS:
                # 检查Milvus健康状况
                from pymilvus import connections, utility
                try:
                    connections.connect(
                        alias="health_check",
                        host=connection_config.get("host"),
                        port=connection_config.get("port"),
                        user=connection_config.get("user"),
                        password=connection_config.get("password"),
                        secure=connection_config.get("secure", False),
                        timeout=5
                    )
                    # 简单查询测试
                    collections = utility.list_collections(using="health_check")
                    connections.disconnect("health_check")
                    return True
                except Exception:
                    return False
                    
            elif backend_type == VectorBackendType.PGVECTOR:
                # 检查PostgreSQL健康状况
                import asyncpg
                try:
                    database_url = connection_config.get("database_url")
                    if not database_url:
                        host = connection_config.get("host", "localhost")
                        port = connection_config.get("port", 5432)
                        user = connection_config.get("user", "postgres")
                        password = connection_config.get("password", "password")
                        database = connection_config.get("database", "postgres")
                        database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
                    
                    conn = await asyncpg.connect(database_url, timeout=5)
                    await conn.execute("SELECT 1")
                    await conn.close()
                    return True
                except Exception:
                    return False
                    
            elif backend_type == VectorBackendType.ELASTICSEARCH:
                # 检查Elasticsearch健康状况
                from elasticsearch import Elasticsearch
                try:
                    es_config = {
                        "hosts": [connection_config.get("es_url", "http://localhost:9200")],
                        "timeout": 5
                    }
                    
                    # 添加认证信息
                    username = connection_config.get("username")
                    password = connection_config.get("password")
                    api_key = connection_config.get("api_key")
                    
                    if api_key:
                        es_config["api_key"] = api_key
                    elif username and password:
                        es_config["basic_auth"] = (username, password)
                    
                    client = Elasticsearch(**es_config)
                    health = client.cluster.health()
                    return health["status"] in ["green", "yellow"]
                except Exception:
                    return False
                    
        except Exception as e:
            logger.error(f"健康检查 {backend_type.value} 时发生异常: {str(e)}")
            return False
    
    async def _perform_failover(self) -> None:
        """执行故障转移"""
        logger.info("开始执行向量数据库故障转移...")
        
        # 获取备用后端列表
        fallback_backends = self.config_manager.get_fallback_backends()
        
        for backend_type in fallback_backends:
            if backend_type == self.current_backend:
                continue  # 跳过当前失败的后端
            
            logger.info(f"尝试故障转移到 {backend_type.value}")
            
            success = await self._initialize_backend(backend_type)
            if success:
                old_backend = self.current_backend
                self.current_backend = backend_type
                logger.info(f"故障转移成功: {old_backend.value} -> {backend_type.value}")
                return
        
        logger.error("故障转移失败，没有可用的后端")
    
    def get_current_backend(self) -> Optional[VectorBackendType]:
        """获取当前使用的后端类型"""
        return self.current_backend
    
    def get_initialized_collections(self) -> List[Tuple[VectorBackendType, str]]:
        """获取已初始化的集合列表"""
        return self.initialized_collections.copy()
    
    async def shutdown(self) -> None:
        """关闭初始化器"""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("向量数据库初始化器已关闭")


# 全局初始化器实例
_vector_db_initializer = None


async def get_vector_db_initializer() -> IntegratedVectorDatabaseInitializer:
    """获取向量数据库初始化器实例"""
    global _vector_db_initializer
    
    if _vector_db_initializer is None:
        _vector_db_initializer = IntegratedVectorDatabaseInitializer()
        await _vector_db_initializer.initialize()
    
    return _vector_db_initializer


async def initialize_vector_database() -> bool:
    """
    初始化向量数据库（系统启动时调用）
    
    返回:
        是否初始化成功
    """
    try:
        initializer = await get_vector_db_initializer()
        return initializer.current_backend is not None
    except Exception as e:
        logger.error(f"向量数据库初始化失败: {str(e)}")
        return False


def get_current_vector_backend() -> Optional[VectorBackendType]:
    """
    获取当前使用的向量数据库后端类型
    
    返回:
        当前后端类型，如果未初始化则返回None
    """
    global _vector_db_initializer
    
    if _vector_db_initializer:
        return _vector_db_initializer.get_current_backend()
    
    return None


async def shutdown_vector_database() -> None:
    """关闭向量数据库（系统关闭时调用）"""
    global _vector_db_initializer
    
    if _vector_db_initializer:
        await _vector_db_initializer.shutdown()
        _vector_db_initializer = None


# 保持与原有接口的兼容性
VectorDatabaseInitializer = IntegratedVectorDatabaseInitializer 