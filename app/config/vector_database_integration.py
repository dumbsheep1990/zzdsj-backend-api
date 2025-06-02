"""
向量数据库配置集成模块
将向量数据库配置与ZZDSJ高级配置管理系统集成
"""

import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from app.core.config.advanced_manager import (
    AdvancedConfigManager,
    ConfigProvider,
    get_config_manager
)
from app.schemas.vector_store import VectorBackendType
from app.config.vector_database import VectorDatabaseConfig

logger = logging.getLogger(__name__)


class VectorDatabaseConfigProvider(ConfigProvider):
    """向量数据库配置提供者"""
    
    def __init__(self):
        super().__init__(priority=6)  # 中等优先级，高于默认配置，低于环境配置
        self.config_file = None
        
    def load(self) -> Dict[str, Any]:
        """从向量数据库配置文件加载配置"""
        try:
            # 查找配置文件
            self.config_file = self._find_vector_config_file()
            
            if not self.config_file or not self.config_file.exists():
                logger.warning("向量数据库配置文件未找到，使用默认配置")
                return {}
            
            # 加载YAML配置
            import yaml
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            logger.info(f"向量数据库配置提供者加载配置文件: {self.config_file}")
            return config
            
        except Exception as e:
            logger.error(f"加载向量数据库配置失败: {str(e)}")
            return {}
    
    def _find_vector_config_file(self) -> Optional[Path]:
        """查找向量数据库配置文件"""
        # 项目根目录
        project_root = Path(__file__).parent.parent.parent
        
        # 可能的配置文件路径
        possible_paths = [
            project_root / "config" / "vector_database.yaml",
            project_root / "config" / "vector_database.yml",
            project_root / "vector_database.yaml",
            project_root / "vector_database.yml",
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None
    
    def is_available(self) -> bool:
        """检查配置提供者是否可用"""
        if self.config_file is None:
            self.config_file = self._find_vector_config_file()
        
        return self.config_file is not None and self.config_file.exists()


class VectorDatabaseConfigManager:
    """向量数据库配置管理器"""
    
    def __init__(self, config_manager: AdvancedConfigManager = None):
        """
        初始化向量数据库配置管理器
        
        参数:
            config_manager: 高级配置管理器实例
        """
        self.config_manager = config_manager or get_config_manager()
        self.vector_config_provider = VectorDatabaseConfigProvider()
        
        # 注册向量数据库配置提供者
        self._register_vector_config_provider()
        
        # 环境变量映射
        self.env_mapping = {
            "VECTOR_DB_AUTO_INIT": "vector_database.auto_init.enabled",
            "VECTOR_DB_PRIMARY_BACKEND": "vector_database.auto_init.primary_backend",
            "VECTOR_DB_FALLBACK_BACKENDS": "vector_database.auto_init.fallback_backends",
            "VECTOR_DB_AUTO_CREATE_COLLECTIONS": "vector_database.auto_init.auto_create_collections",
            "VECTOR_DB_DEFAULT_DIMENSION": "vector_database.common.default_dimension",
            "VECTOR_DB_BATCH_SIZE": "vector_database.common.batch_size",
            "VECTOR_DB_MAX_CONNECTIONS": "vector_database.common.max_connections",
            
            # Milvus配置映射
            "MILVUS_HOST": "vector_database.milvus.connection.host",
            "MILVUS_PORT": "vector_database.milvus.connection.port",
            "MILVUS_USER": "vector_database.milvus.connection.user",
            "MILVUS_PASSWORD": "vector_database.milvus.connection.password",
            "MILVUS_SECURE": "vector_database.milvus.connection.secure",
            "MILVUS_TIMEOUT": "vector_database.milvus.connection.timeout",
            
            # PostgreSQL+pgvector配置映射
            "PGVECTOR_DATABASE_URL": "vector_database.pgvector.connection.database_url",
            "PGVECTOR_HOST": "vector_database.pgvector.connection.host",
            "PGVECTOR_PORT": "vector_database.pgvector.connection.port",
            "PGVECTOR_USER": "vector_database.pgvector.connection.user",
            "PGVECTOR_PASSWORD": "vector_database.pgvector.connection.password",
            "PGVECTOR_DATABASE": "vector_database.pgvector.connection.database",
            "PGVECTOR_SCHEMA": "vector_database.pgvector.connection.schema_name",
            "PGVECTOR_TIMEOUT": "vector_database.pgvector.connection.timeout",
            
            # Elasticsearch配置映射
            "ELASTICSEARCH_URL": "vector_database.elasticsearch.connection.es_url",
            "ELASTICSEARCH_USERNAME": "vector_database.elasticsearch.connection.username",
            "ELASTICSEARCH_PASSWORD": "vector_database.elasticsearch.connection.password",
            "ELASTICSEARCH_API_KEY": "vector_database.elasticsearch.connection.api_key",
            "ELASTICSEARCH_TIMEOUT": "vector_database.elasticsearch.connection.timeout",
        }
        
        logger.info("向量数据库配置管理器初始化完成")
    
    def _register_vector_config_provider(self):
        """注册向量数据库配置提供者"""
        if self.vector_config_provider.is_available():
            # 检查是否已经注册
            provider_names = [p.name for p in self.config_manager.providers]
            if "VectorDatabaseConfigProvider" not in provider_names:
                self.config_manager.providers.append(self.vector_config_provider)
                # 重新排序
                self.config_manager.providers.sort(key=lambda p: p.priority)
                logger.info("向量数据库配置提供者已注册")
    
    def get_vector_database_config(self, reload: bool = False) -> Dict[str, Any]:
        """
        获取向量数据库配置
        
        参数:
            reload: 是否强制重新加载配置
            
        返回:
            向量数据库配置字典
        """
        # 加载完整配置
        full_config = self.config_manager.load_configuration(use_cache=not reload)
        
        # 提取向量数据库配置
        vector_config = full_config.get("vector_database", {})
        
        # 应用环境变量映射
        vector_config = self._apply_env_mapping(vector_config)
        
        return vector_config
    
    def get_backend_config(self, backend_type: VectorBackendType) -> Dict[str, Any]:
        """
        获取指定后端的配置
        
        参数:
            backend_type: 后端类型
            
        返回:
            后端配置字典
        """
        vector_config = self.get_vector_database_config()
        
        if backend_type == VectorBackendType.MILVUS:
            return vector_config.get("milvus", {})
        elif backend_type == VectorBackendType.PGVECTOR:
            return vector_config.get("pgvector", {})
        elif backend_type == VectorBackendType.ELASTICSEARCH:
            return vector_config.get("elasticsearch", {})
        else:
            raise ValueError(f"不支持的后端类型: {backend_type}")
    
    def get_connection_config(self, backend_type: VectorBackendType) -> Dict[str, Any]:
        """
        获取连接配置
        
        参数:
            backend_type: 后端类型
            
        返回:
            连接配置字典
        """
        backend_config = self.get_backend_config(backend_type)
        return backend_config.get("connection", {})
    
    def get_auto_init_config(self) -> Dict[str, Any]:
        """获取自动初始化配置"""
        vector_config = self.get_vector_database_config()
        return vector_config.get("auto_init", {})
    
    def is_auto_init_enabled(self) -> bool:
        """检查是否启用自动初始化"""
        auto_init_config = self.get_auto_init_config()
        return auto_init_config.get("enabled", True)
    
    def get_primary_backend(self) -> VectorBackendType:
        """获取主要后端类型"""
        auto_init_config = self.get_auto_init_config()
        backend_str = auto_init_config.get("primary_backend", "milvus")
        return VectorBackendType(backend_str)
    
    def get_fallback_backends(self) -> List[VectorBackendType]:
        """获取备用后端类型列表"""
        auto_init_config = self.get_auto_init_config()
        fallback_list = auto_init_config.get("fallback_backends", ["pgvector"])
        
        # 处理字符串格式的配置
        if isinstance(fallback_list, str):
            fallback_list = [backend.strip() for backend in fallback_list.split(",")]
        
        return [VectorBackendType(backend) for backend in fallback_list if backend]
    
    def get_auto_create_collections(self) -> List[str]:
        """获取自动创建的集合列表"""
        auto_init_config = self.get_auto_init_config()
        collections = auto_init_config.get("auto_create_collections", ["document_collection", "knowledge_base_collection"])
        
        # 处理字符串格式的配置
        if isinstance(collections, str):
            collections = [col.strip() for col in collections.split(",")]
        
        return collections
    
    def _apply_env_mapping(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用环境变量映射"""
        # 创建配置副本
        result_config = config.copy()
        
        # 应用环境变量覆盖
        for env_var, config_path in self.env_mapping.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # 将配置路径转换为嵌套字典路径
                keys = config_path.split(".")
                current = result_config
                
                # 创建嵌套路径
                for key in keys[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                
                # 设置值，处理数据类型转换
                final_key = keys[-1]
                current[final_key] = self._convert_env_value(env_value)
        
        return result_config
    
    def _convert_env_value(self, value: str) -> Any:
        """转换环境变量值的数据类型"""
        # 布尔值转换
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        
        # 数字转换
        if value.isdigit():
            return int(value)
        
        # 浮点数转换
        try:
            if "." in value:
                return float(value)
        except ValueError:
            pass
        
        # 列表转换（逗号分隔）
        if "," in value:
            return [item.strip() for item in value.split(",")]
        
        # 默认返回字符串
        return value
    
    def validate_vector_config(self) -> Dict[str, Any]:
        """
        验证向量数据库配置
        
        返回:
            验证结果字典
        """
        try:
            vector_config = self.get_vector_database_config()
            
            # 基础验证
            validation_errors = []
            validation_warnings = []
            
            # 检查必需配置
            if not vector_config:
                validation_errors.append("向量数据库配置为空")
                return {
                    "is_valid": False,
                    "errors": validation_errors,
                    "warnings": validation_warnings
                }
            
            # 检查自动初始化配置
            auto_init = vector_config.get("auto_init", {})
            if auto_init.get("enabled", True):
                primary_backend = auto_init.get("primary_backend")
                if not primary_backend:
                    validation_errors.append("未指定主要后端类型")
                else:
                    try:
                        VectorBackendType(primary_backend)
                    except ValueError:
                        validation_errors.append(f"无效的主要后端类型: {primary_backend}")
            
            # 检查后端配置
            for backend_name in ["milvus", "pgvector", "elasticsearch"]:
                backend_config = vector_config.get(backend_name, {})
                if backend_config:
                    backend_errors = self._validate_backend_config(backend_name, backend_config)
                    validation_errors.extend(backend_errors)
            
            return {
                "is_valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "warnings": validation_warnings
            }
            
        except Exception as e:
            logger.error(f"验证向量数据库配置时发生异常: {str(e)}")
            return {
                "is_valid": False,
                "errors": [f"配置验证异常: {str(e)}"],
                "warnings": []
            }
    
    def _validate_backend_config(self, backend_name: str, backend_config: Dict[str, Any]) -> List[str]:
        """验证单个后端配置"""
        errors = []
        
        # 检查连接配置
        connection_config = backend_config.get("connection", {})
        if not connection_config:
            errors.append(f"{backend_name} 缺少连接配置")
            return errors
        
        # 根据后端类型进行特定验证
        if backend_name == "milvus":
            if not connection_config.get("host"):
                errors.append("Milvus 缺少主机地址配置")
            if not connection_config.get("port"):
                errors.append("Milvus 缺少端口配置")
                
        elif backend_name == "pgvector":
            database_url = connection_config.get("database_url")
            host = connection_config.get("host")
            if not database_url and not host:
                errors.append("PostgreSQL+pgvector 缺少数据库连接配置")
                
        elif backend_name == "elasticsearch":
            if not connection_config.get("es_url"):
                errors.append("Elasticsearch 缺少URL配置")
        
        return errors
    
    def export_vector_config(self, file_path: str, format: str = "yaml") -> bool:
        """
        导出向量数据库配置
        
        参数:
            file_path: 导出文件路径
            format: 导出格式（yaml/json）
            
        返回:
            是否导出成功
        """
        try:
            vector_config = self.get_vector_database_config()
            
            if format.lower() == "yaml":
                import yaml
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(
                        {"vector_database": vector_config}, 
                        f, 
                        default_flow_style=False, 
                        allow_unicode=True,
                        indent=2
                    )
            elif format.lower() == "json":
                import json
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(
                        {"vector_database": vector_config}, 
                        f, 
                        ensure_ascii=False, 
                        indent=2
                    )
            else:
                raise ValueError(f"不支持的导出格式: {format}")
            
            logger.info(f"向量数据库配置导出成功: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出向量数据库配置失败: {str(e)}")
            return False


# 全局向量数据库配置管理器实例
_vector_db_config_manager: Optional[VectorDatabaseConfigManager] = None


def get_vector_db_config_manager() -> VectorDatabaseConfigManager:
    """获取向量数据库配置管理器实例"""
    global _vector_db_config_manager
    
    if _vector_db_config_manager is None:
        _vector_db_config_manager = VectorDatabaseConfigManager()
    
    return _vector_db_config_manager


def get_integrated_vector_config() -> Dict[str, Any]:
    """获取集成的向量数据库配置"""
    manager = get_vector_db_config_manager()
    return manager.get_vector_database_config()


def get_integrated_backend_config(backend_type: VectorBackendType) -> Dict[str, Any]:
    """获取集成的后端配置"""
    manager = get_vector_db_config_manager()
    return manager.get_backend_config(backend_type)


def validate_integrated_vector_config() -> Dict[str, Any]:
    """验证集成的向量数据库配置"""
    manager = get_vector_db_config_manager()
    return manager.validate_vector_config() 