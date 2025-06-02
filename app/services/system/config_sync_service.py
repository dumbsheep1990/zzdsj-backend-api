"""
配置同步服务 - 管理配置项与环境变量的同步
确保配置管理系统中的配置项与 .env 文件和环境变量保持一致
"""

import os
import logging
import secrets
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from core.system_config import SystemConfigManager
from app.utils.service_decorators import register_service

logger = logging.getLogger(__name__)


@register_service(service_type="config-sync", priority="critical", description="配置同步服务")
class ConfigSyncService:
    """配置同步服务"""
    
    def __init__(self, db: Session):
        """初始化配置同步服务"""
        self.db = db
        self.config_manager = SystemConfigManager(db)
        self.config_definitions = self._get_config_definitions()
    
    def _get_config_definitions(self) -> Dict[str, Dict[str, Any]]:
        """获取配置定义映射"""
        return {
            # 系统配置
            "SERVICE_NAME": {
                "category": "系统配置",
                "key": "service.name",
                "value_type": "string",
                "description": "服务名称",
                "default_value": "knowledge-qa-backend",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"required": True, "min_length": 1, "max_length": 100}
            },
            "SERVICE_IP": {
                "category": "系统配置",
                "key": "service.ip",
                "value_type": "string",
                "description": "服务IP地址",
                "default_value": "127.0.0.1",
                "is_system": True,
                "is_sensitive": False
            },
            "SERVICE_PORT": {
                "category": "系统配置",
                "key": "service.port",
                "value_type": "number",
                "description": "服务端口",
                "default_value": "8000",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"min_value": 1, "max_value": 65535}
            },
            "APP_ENV": {
                "category": "系统配置",
                "key": "app.environment",
                "value_type": "string",
                "description": "应用环境",
                "default_value": "development",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"enum": ["development", "testing", "production"]}
            },
            "DEBUG_MODE": {
                "category": "系统配置",
                "key": "app.debug_mode",
                "value_type": "boolean",
                "description": "调试模式",
                "default_value": "False",
                "is_system": True,
                "is_sensitive": False
            },
            
            # 安全配置
            "JWT_SECRET_KEY": {
                "category": "安全配置",
                "key": "security.jwt_secret_key",
                "value_type": "string",
                "description": "JWT密钥",
                "default_value": "",  # 系统生成
                "is_system": True,
                "is_sensitive": True,
                "validation_rules": {"required": True, "min_length": 32}
            },
            "JWT_ALGORITHM": {
                "category": "安全配置",
                "key": "security.jwt_algorithm",
                "value_type": "string",
                "description": "JWT算法",
                "default_value": "HS256",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"enum": ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]}
            },
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": {
                "category": "安全配置",
                "key": "security.jwt_access_token_expire_minutes",
                "value_type": "number",
                "description": "JWT访问令牌过期时间（分钟）",
                "default_value": "30",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"min_value": 1, "max_value": 43200}
            },
            "JWT_REFRESH_TOKEN_EXPIRE_DAYS": {
                "category": "安全配置",
                "key": "security.jwt_refresh_token_expire_days",
                "value_type": "number",
                "description": "JWT刷新令牌过期时间（天）",
                "default_value": "7",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"min_value": 1, "max_value": 365}
            },
            "ENCRYPTION_KEY": {
                "category": "安全配置",
                "key": "security.encryption_key",
                "value_type": "string",
                "description": "配置数据加密密钥",
                "default_value": "",  # 系统生成
                "is_system": True,
                "is_sensitive": True,
                "validation_rules": {"required": True, "min_length": 32}
            },
            
            # 数据库配置
            "DATABASE_URL": {
                "category": "数据库配置",
                "key": "database.url",
                "value_type": "string",
                "description": "数据库连接URL",
                "default_value": "postgresql://postgres:postgres@localhost:5432/knowledge_qa",
                "is_system": True,
                "is_sensitive": True,
                "validation_rules": {"required": True, "pattern": r"^postgresql://.*"}
            },
            "POSTGRES_HOST": {
                "category": "数据库配置",
                "key": "database.postgres.host",
                "value_type": "string",
                "description": "PostgreSQL主机地址",
                "default_value": "localhost",
                "is_system": True,
                "is_sensitive": False
            },
            "POSTGRES_PORT": {
                "category": "数据库配置",
                "key": "database.postgres.port",
                "value_type": "number",
                "description": "PostgreSQL端口",
                "default_value": "5432",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"min_value": 1, "max_value": 65535}
            },
            "POSTGRES_USER": {
                "category": "数据库配置",
                "key": "database.postgres.user",
                "value_type": "string",
                "description": "PostgreSQL用户名",
                "default_value": "postgres",
                "is_system": True,
                "is_sensitive": False
            },
            "POSTGRES_PASSWORD": {
                "category": "数据库配置",
                "key": "database.postgres.password",
                "value_type": "string",
                "description": "PostgreSQL密码",
                "default_value": "postgres",
                "is_system": True,
                "is_sensitive": True
            },
            "POSTGRES_DB": {
                "category": "数据库配置",
                "key": "database.postgres.database",
                "value_type": "string",
                "description": "PostgreSQL数据库名",
                "default_value": "knowledge_qa",
                "is_system": True,
                "is_sensitive": False
            },
            
            # Redis配置
            "REDIS_HOST": {
                "category": "服务配置",
                "key": "redis.host",
                "value_type": "string",
                "description": "Redis主机地址",
                "default_value": "localhost",
                "is_system": True,
                "is_sensitive": False
            },
            "REDIS_PORT": {
                "category": "服务配置",
                "key": "redis.port",
                "value_type": "number",
                "description": "Redis端口",
                "default_value": "6379",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"min_value": 1, "max_value": 65535}
            },
            "REDIS_DB": {
                "category": "服务配置",
                "key": "redis.db",
                "value_type": "number",
                "description": "Redis数据库索引",
                "default_value": "0",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"min_value": 0, "max_value": 15}
            },
            "REDIS_PASSWORD": {
                "category": "服务配置",
                "key": "redis.password",
                "value_type": "string",
                "description": "Redis密码",
                "default_value": "",
                "is_system": True,
                "is_sensitive": True
            },
            
            # LLM配置
            "OPENAI_API_KEY": {
                "category": "模型配置",
                "key": "llm.openai.api_key",
                "value_type": "string",
                "description": "OpenAI API密钥",
                "default_value": "",
                "is_system": False,
                "is_sensitive": True,
                "validation_rules": {"required": False}
            },
            "OPENAI_API_BASE": {
                "category": "模型配置",
                "key": "llm.openai.api_base",
                "value_type": "string",
                "description": "OpenAI API基础URL",
                "default_value": "https://api.openai.com/v1",
                "is_system": False,
                "is_sensitive": False
            },
            "DEFAULT_MODEL": {
                "category": "模型配置",
                "key": "llm.default_model",
                "value_type": "string",
                "description": "默认LLM模型",
                "default_value": "gpt-4",
                "is_system": False,
                "is_sensitive": False
            },
            
            # MinIO配置
            "MINIO_ENDPOINT": {
                "category": "服务配置",
                "key": "storage.minio.endpoint",
                "value_type": "string",
                "description": "MinIO服务端点",
                "default_value": "localhost:9000",
                "is_system": True,
                "is_sensitive": False
            },
            "MINIO_ACCESS_KEY": {
                "category": "服务配置",
                "key": "storage.minio.access_key",
                "value_type": "string",
                "description": "MinIO访问密钥",
                "default_value": "minioadmin",
                "is_system": True,
                "is_sensitive": True
            },
            "MINIO_SECRET_KEY": {
                "category": "服务配置",
                "key": "storage.minio.secret_key",
                "value_type": "string",
                "description": "MinIO秘密密钥",
                "default_value": "minioadmin",
                "is_system": True,
                "is_sensitive": True
            },
            "MINIO_SECURE": {
                "category": "服务配置",
                "key": "storage.minio.secure",
                "value_type": "boolean",
                "description": "MinIO是否使用HTTPS",
                "default_value": "False",
                "is_system": True,
                "is_sensitive": False
            },
            "MINIO_BUCKET": {
                "category": "服务配置",
                "key": "storage.minio.bucket",
                "value_type": "string",
                "description": "MinIO默认存储桶",
                "default_value": "knowledge-docs",
                "is_system": True,
                "is_sensitive": False
            },
            
            # Milvus配置
            "MILVUS_HOST": {
                "category": "服务配置",
                "key": "vector_store.milvus.host",
                "value_type": "string",
                "description": "Milvus主机地址",
                "default_value": "localhost",
                "is_system": True,
                "is_sensitive": False
            },
            "MILVUS_PORT": {
                "category": "服务配置",
                "key": "vector_store.milvus.port",
                "value_type": "number",
                "description": "Milvus端口",
                "default_value": "19530",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"min_value": 1, "max_value": 65535}
            },
            "MILVUS_COLLECTION": {
                "category": "服务配置",
                "key": "vector_store.milvus.collection",
                "value_type": "string",
                "description": "Milvus集合名",
                "default_value": "document_vectors",
                "is_system": True,
                "is_sensitive": False
            },
            
            # Elasticsearch配置
            "ELASTICSEARCH_URL": {
                "category": "服务配置",
                "key": "elasticsearch.url",
                "value_type": "string",
                "description": "Elasticsearch URL",
                "default_value": "http://localhost:9200",
                "is_system": True,
                "is_sensitive": False
            },
            "ELASTICSEARCH_USERNAME": {
                "category": "服务配置",
                "key": "elasticsearch.username",
                "value_type": "string",
                "description": "Elasticsearch用户名",
                "default_value": "",
                "is_system": True,
                "is_sensitive": False
            },
            "ELASTICSEARCH_PASSWORD": {
                "category": "服务配置",
                "key": "elasticsearch.password",
                "value_type": "string",
                "description": "Elasticsearch密码",
                "default_value": "",
                "is_system": True,
                "is_sensitive": True
            },
            "ELASTICSEARCH_INDEX": {
                "category": "服务配置",
                "key": "elasticsearch.index",
                "value_type": "string",
                "description": "Elasticsearch索引名",
                "default_value": "document_index",
                "is_system": True,
                "is_sensitive": False
            },
            
            # 功能配置
            "VOICE_ENABLED": {
                "category": "功能配置",
                "key": "features.voice.enabled",
                "value_type": "boolean",
                "description": "是否启用语音功能",
                "default_value": "False",
                "is_system": False,
                "is_sensitive": False
            },
            "METRICS_ENABLED": {
                "category": "功能配置",
                "key": "features.metrics.enabled",
                "value_type": "boolean",
                "description": "是否启用指标统计",
                "default_value": "False",
                "is_system": False,
                "is_sensitive": False
            },
            "OWL_TOOLS_ENABLED": {
                "category": "功能配置",
                "key": "features.owl_tools.enabled",
                "value_type": "boolean",
                "description": "是否启用OWL工具系统",
                "default_value": "True",
                "is_system": False,
                "is_sensitive": False
            },
            "LIGHTRAG_ENABLED": {
                "category": "功能配置",
                "key": "features.lightrag.enabled",
                "value_type": "boolean",
                "description": "是否启用LightRAG",
                "default_value": "True",
                "is_system": False,
                "is_sensitive": False
            },
            "SEARXNG_ENABLED": {
                "category": "功能配置",
                "key": "features.searxng.enabled",
                "value_type": "boolean",
                "description": "是否启用SearxNG搜索",
                "default_value": "True",
                "is_system": False,
                "is_sensitive": False
            },
            
            # 文档处理配置
            "DOCUMENT_CHUNK_SIZE": {
                "category": "功能配置",
                "key": "document.chunk_size",
                "value_type": "number",
                "description": "文档分块大小",
                "default_value": "1000",
                "is_system": False,
                "is_sensitive": False,
                "validation_rules": {"min_value": 100, "max_value": 10000}
            },
            "DOCUMENT_CHUNK_OVERLAP": {
                "category": "功能配置",
                "key": "document.chunk_overlap",
                "value_type": "number",
                "description": "文档分块重叠长度",
                "default_value": "200",
                "is_system": False,
                "is_sensitive": False,
                "validation_rules": {"min_value": 0, "max_value": 1000}
            },
            "DOCUMENT_MAX_FILE_SIZE_MB": {
                "category": "功能配置",
                "key": "document.max_file_size_mb",
                "value_type": "number",
                "description": "文档最大文件大小（MB）",
                "default_value": "100",
                "is_system": False,
                "is_sensitive": False,
                "validation_rules": {"min_value": 1, "max_value": 1024}
            },
            
            # 日志配置
            "LOG_LEVEL": {
                "category": "系统配置",
                "key": "logging.level",
                "value_type": "string",
                "description": "日志级别",
                "default_value": "INFO",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]}
            },
            "LOG_FORMAT": {
                "category": "系统配置",
                "key": "logging.format",
                "value_type": "string",
                "description": "日志格式",
                "default_value": "text",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"enum": ["text", "json"]}
            },
        }
    
    def _generate_secret_key(self) -> str:
        """生成安全的密钥"""
        return secrets.token_hex(32)
    
    async def sync_env_to_database(self, force_update: bool = False) -> Dict[str, Any]:
        """同步环境变量到数据库配置管理系统"""
        try:
            created_count = 0
            updated_count = 0
            skipped_count = 0
            error_count = 0
            errors = []
            
            logger.info("开始同步环境变量到数据库配置管理系统...")
            
            for env_key, config_def in self.config_definitions.items():
                try:
                    # 获取环境变量值
                    env_value = os.getenv(env_key)
                    config_value = env_value if env_value is not None else config_def["default_value"]
                    
                    # 特殊处理密钥生成
                    if (not config_value and 
                        config_def["key"] in ["security.jwt_secret_key", "security.encryption_key"]):
                        config_value = self._generate_secret_key()
                        logger.info(f"为 {config_def['key']} 生成了新的密钥")
                    
                    # 确保类别存在
                    category_result = await self.config_manager.create_category(
                        name=config_def["category"],
                        description=f"{config_def['category']}相关配置",
                        is_system=config_def.get("is_system", False)
                    )
                    
                    if (not category_result["success"] and 
                        "已存在" not in category_result.get("error", "")):
                        logger.warning(f"创建类别失败: {category_result.get('error')}")
                        continue
                    
                    # 获取类别ID
                    categories = await self.config_manager.get_categories()
                    category_id = None
                    for cat in categories["data"]:
                        if cat["name"] == config_def["category"]:
                            category_id = cat["id"]
                            break
                    
                    if not category_id:
                        logger.error(f"无法找到类别: {config_def['category']}")
                        error_count += 1
                        continue
                    
                    # 检查配置是否已存在
                    existing_value = await self.config_manager.get_config_value(config_def["key"])
                    
                    if existing_value is not None:
                        # 配置已存在，检查是否需要更新
                        if env_value is not None or force_update:
                            result = await self.config_manager.update_config_value(
                                key=config_def["key"],
                                value=config_value,
                                change_source="env_sync",
                                change_notes=f"从环境变量 {env_key} 同步"
                            )
                            if result["success"]:
                                updated_count += 1
                                logger.debug(f"更新配置: {config_def['key']}")
                            else:
                                logger.error(f"更新配置失败: {config_def['key']}, 错误: {result.get('error')}")
                                error_count += 1
                                errors.append(f"{config_def['key']}: {result.get('error')}")
                        else:
                            skipped_count += 1
                            logger.debug(f"跳过已存在的配置: {config_def['key']}")
                    else:
                        # 创建新配置
                        result = await self.config_manager.create_config(
                            key=config_def["key"],
                            value=config_value,
                            value_type=config_def["value_type"],
                            category_id=category_id,
                            description=config_def["description"],
                            default_value=config_def["default_value"],
                            is_system=config_def.get("is_system", False),
                            is_sensitive=config_def.get("is_sensitive", False),
                            validation_rules=config_def.get("validation_rules"),
                            visible_level="all"
                        )
                        
                        if result["success"]:
                            created_count += 1
                            logger.debug(f"创建配置: {config_def['key']}")
                        else:
                            logger.error(f"创建配置失败: {config_def['key']}, 错误: {result.get('error')}")
                            error_count += 1
                            errors.append(f"{config_def['key']}: {result.get('error')}")
                
                except Exception as e:
                    logger.error(f"处理配置 {env_key} 时发生错误: {str(e)}")
                    error_count += 1
                    errors.append(f"{env_key}: {str(e)}")
            
            # 提交事务
            self.db.commit()
            
            logger.info(f"配置同步完成! 创建: {created_count}, 更新: {updated_count}, 跳过: {skipped_count}, 错误: {error_count}")
            
            return {
                "success": True,
                "created": created_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "errors": error_count,
                "error_details": errors
            }
        
        except Exception as e:
            logger.error(f"配置同步失败: {str(e)}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def validate_config_completeness(self) -> Dict[str, Any]:
        """验证配置完整性"""
        try:
            missing_configs = []
            invalid_configs = []
            
            logger.info("开始验证配置完整性...")
            
            for env_key, config_def in self.config_definitions.items():
                try:
                    # 检查配置是否存在
                    value = await self.config_manager.get_config_value(config_def["key"])
                    
                    if value is None:
                        missing_configs.append({
                            "env_key": env_key,
                            "config_key": config_def["key"],
                            "description": config_def["description"],
                            "required": config_def.get("validation_rules", {}).get("required", False)
                        })
                    else:
                        # 验证配置值
                        if "validation_rules" in config_def:
                            from core.system_config.config_validator import ConfigValidator
                            validator = ConfigValidator()
                            
                            validation_result = validator.validate_config_value(
                                value, 
                                config_def["validation_rules"]
                            )
                            
                            if not validation_result["valid"]:
                                invalid_configs.append({
                                    "env_key": env_key,
                                    "config_key": config_def["key"],
                                    "value": str(value)[:50] + "..." if len(str(value)) > 50 else str(value),
                                    "error": validation_result["error"]
                                })
                
                except Exception as e:
                    logger.error(f"验证配置 {env_key} 时发生错误: {str(e)}")
                    invalid_configs.append({
                        "env_key": env_key,
                        "config_key": config_def["key"],
                        "error": f"验证异常: {str(e)}"
                    })
            
            logger.info(f"配置验证完成! 缺失: {len(missing_configs)}, 无效: {len(invalid_configs)}")
            
            return {
                "success": True,
                "total_configs": len(self.config_definitions),
                "missing_configs": missing_configs,
                "invalid_configs": invalid_configs,
                "is_complete": len(missing_configs) == 0 and len(invalid_configs) == 0
            }
        
        except Exception as e:
            logger.error(f"配置验证失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_config_from_database(self, key: str, default: Any = None) -> Any:
        """从数据库获取配置值"""
        try:
            return await self.config_manager.get_config_value(key, default)
        except Exception as e:
            logger.error(f"从数据库获取配置失败 {key}: {str(e)}")
            return default
    
    async def update_config_in_database(self, key: str, value: Any, 
                                      change_source: str = "api") -> Dict[str, Any]:
        """更新数据库中的配置值"""
        try:
            return await self.config_manager.update_config_value(
                key=key,
                value=value,
                change_source=change_source,
                change_notes=f"通过{change_source}更新"
            )
        except Exception as e:
            logger.error(f"更新数据库配置失败 {key}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_missing_env_vars(self) -> List[str]:
        """获取缺失的必需环境变量"""
        missing_vars = []
        
        for env_key, config_def in self.config_definitions.items():
            # 检查是否是必需的配置
            validation_rules = config_def.get("validation_rules", {})
            if validation_rules.get("required", False):
                if not os.getenv(env_key):
                    missing_vars.append(env_key)
        
        return missing_vars
    
    def check_security_configs(self) -> Dict[str, Any]:
        """检查安全配置是否正确设置"""
        issues = []
        warnings = []
        
        # 检查JWT密钥
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        if not jwt_secret:
            issues.append("JWT_SECRET_KEY 未设置")
        elif len(jwt_secret) < 32:
            warnings.append("JWT_SECRET_KEY 长度过短，建议至少32字符")
        elif jwt_secret == "23f0767704249cd7be7181a0dad23c74e0739c98ce54d7140fc2e94dfa584fb0":
            warnings.append("JWT_SECRET_KEY 使用默认值，生产环境中应更换为随机密钥")
        
        # 检查加密密钥
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if not encryption_key:
            warnings.append("ENCRYPTION_KEY 未设置，系统将自动生成")
        
        # 检查数据库密码
        db_password = os.getenv("POSTGRES_PASSWORD")
        if db_password == "postgres":
            warnings.append("数据库密码使用默认值，生产环境中应更换为强密码")
        
        # 检查Redis密码
        redis_password = os.getenv("REDIS_PASSWORD")
        if not redis_password:
            warnings.append("Redis密码未设置，建议在生产环境中设置密码")
        
        return {
            "issues": issues,
            "warnings": warnings,
            "is_secure": len(issues) == 0
        } 