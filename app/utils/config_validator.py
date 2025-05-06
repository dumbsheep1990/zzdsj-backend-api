"""
配置验证工具 - 负责验证配置的完整性和有效性
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, validator
from app.config import settings

logger = logging.getLogger(__name__)

class DatabaseConfig(BaseModel):
    """数据库配置验证模型"""
    url: str
    
    @validator('url')
    def validate_url(cls, v):
        if not v or v == "postgresql://postgres:postgres@localhost:5432/knowledge_qa":
            raise ValueError("数据库URL未配置或使用默认值")
        return v


class MilvusConfig(BaseModel):
    """Milvus配置验证模型"""
    host: str
    port: str
    collection: str
    
    @validator('host')
    def validate_host(cls, v):
        if v == "localhost":
            logger.warning("Milvus使用本地主机配置，可能不适用于生产环境")
        return v


class RedisConfig(BaseModel):
    """Redis配置验证模型"""
    host: str
    port: int
    
    @validator('host')
    def validate_host(cls, v):
        if v == "localhost":
            logger.warning("Redis使用本地主机配置，可能不适用于生产环境")
        return v


class MinioConfig(BaseModel):
    """MinIO配置验证模型"""
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str
    
    @validator('endpoint')
    def validate_endpoint(cls, v):
        if v == "localhost:9000":
            logger.warning("MinIO使用本地主机配置，可能不适用于生产环境")
        return v
    
    @validator('access_key', 'secret_key')
    def validate_credentials(cls, v):
        if v == "minioadmin":
            logger.warning("MinIO使用默认凭据，不适用于生产环境")
        return v


class SecurityConfig(BaseModel):
    """安全配置验证模型"""
    jwt_secret_key: str
    
    @validator('jwt_secret_key')
    def validate_jwt_key(cls, v):
        if v == "23f0767704249cd7be7181a0dad23c74e0739c98ce54d7140fc2e94dfa584fb0":
            logger.warning("JWT使用默认密钥，生产环境应更改")
        return v


class ConfigValidator:
    """配置验证器，负责检查配置的完整性和有效性"""
    
    @staticmethod
    def validate_database_config() -> Tuple[bool, List[str]]:
        """验证数据库配置"""
        try:
            DatabaseConfig(url=settings.DATABASE_URL)
            return True, []
        except ValueError as e:
            return False, [str(e)]
    
    @staticmethod
    def validate_milvus_config() -> Tuple[bool, List[str]]:
        """验证Milvus配置"""
        try:
            MilvusConfig(
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
                collection=settings.MILVUS_COLLECTION
            )
            return True, []
        except ValueError as e:
            return False, [str(e)]
    
    @staticmethod
    def validate_redis_config() -> Tuple[bool, List[str]]:
        """验证Redis配置"""
        try:
            RedisConfig(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT
            )
            return True, []
        except ValueError as e:
            return False, [str(e)]
    
    @staticmethod
    def validate_minio_config() -> Tuple[bool, List[str]]:
        """验证MinIO配置"""
        try:
            MinioConfig(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                bucket=settings.MINIO_BUCKET
            )
            return True, []
        except ValueError as e:
            return False, [str(e)]
    
    @staticmethod
    def validate_security_config() -> Tuple[bool, List[str]]:
        """验证安全配置"""
        try:
            SecurityConfig(jwt_secret_key=settings.JWT_SECRET_KEY)
            return True, []
        except ValueError as e:
            return False, [str(e)]
    
    @staticmethod
    def validate_model_config() -> Tuple[bool, List[str]]:
        """验证模型配置"""
        warnings = []
        if not settings.DEFAULT_MODEL or settings.DEFAULT_MODEL == "gpt-4":
            warnings.append("未设置或使用默认模型配置")
        
        # 检查关键模型提供商配置
        if not any([
            settings.OPENAI_API_KEY,
            settings.ZHIPU_API_KEY,
            settings.DEEPSEEK_API_KEY,
            settings.DASHSCOPE_API_KEY,
            settings.ANTHROPIC_API_KEY,
            settings.BAIDU_API_KEY,
            settings.GLM_API_KEY
        ]):
            warnings.append("未配置任何模型提供商API密钥")
        
        return len(warnings) == 0, warnings
    
    @classmethod
    def validate_all_configs(cls) -> Dict[str, Any]:
        """验证所有配置，返回验证结果"""
        result = {
            "all_valid": True,
            "configs": {}
        }
        
        # 验证所有配置组
        config_validators = {
            "database": cls.validate_database_config,
            "milvus": cls.validate_milvus_config,
            "redis": cls.validate_redis_config,
            "minio": cls.validate_minio_config,
            "security": cls.validate_security_config,
            "model": cls.validate_model_config
        }
        
        for name, validator_func in config_validators.items():
            valid, messages = validator_func()
            result["configs"][name] = {
                "valid": valid,
                "messages": messages
            }
            
            if not valid:
                result["all_valid"] = False
        
        return result
