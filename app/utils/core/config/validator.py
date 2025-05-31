"""
配置验证模块
提供配置项的验证和校验功能
"""

import re
import logging
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_database_config(self, config: Dict[str, Any]) -> bool:
        """
        验证数据库配置
        
        Args:
            config: 数据库配置字典
            
        Returns:
            验证是否通过
        """
        self._clear_results()
        
        # 检查必需字段
        required_fields = ["url"]
        if not self._check_required_fields(config, required_fields, "database"):
            return False
        
        # 验证数据库URL格式
        db_url = config.get("url", "")
        if not self._validate_database_url(db_url):
            self.errors.append("数据库URL格式无效")
            return False
        
        # 验证连接池配置
        pool_size = config.get("pool_size", 10)
        if not isinstance(pool_size, int) or pool_size <= 0:
            self.errors.append("数据库连接池大小必须是正整数")
            return False
        
        max_overflow = config.get("max_overflow", 20)
        if not isinstance(max_overflow, int) or max_overflow < 0:
            self.errors.append("数据库最大溢出连接数必须是非负整数")
            return False
        
        return len(self.errors) == 0
    
    def validate_redis_config(self, config: Dict[str, Any]) -> bool:
        """
        验证Redis配置
        
        Args:
            config: Redis配置字典
            
        Returns:
            验证是否通过
        """
        self._clear_results()
        
        # 检查必需字段
        required_fields = ["host", "port"]
        if not self._check_required_fields(config, required_fields, "redis"):
            return False
        
        # 验证主机名
        host = config.get("host", "")
        if not host or not isinstance(host, str):
            self.errors.append("Redis主机名不能为空")
            return False
        
        # 验证端口
        port = config.get("port", 6379)
        if not isinstance(port, int) or port <= 0 or port > 65535:
            self.errors.append("Redis端口必须是1-65535之间的整数")
            return False
        
        # 验证数据库索引
        db = config.get("db", 0)
        if not isinstance(db, int) or db < 0 or db > 15:
            self.errors.append("Redis数据库索引必须是0-15之间的整数")
            return False
        
        return len(self.errors) == 0
    
    def validate_minio_config(self, config: Dict[str, Any]) -> bool:
        """
        验证MinIO配置
        
        Args:
            config: MinIO配置字典
            
        Returns:
            验证是否通过
        """
        self._clear_results()
        
        # 检查必需字段
        required_fields = ["endpoint", "access_key", "secret_key", "bucket"]
        if not self._check_required_fields(config, required_fields, "minio"):
            return False
        
        # 验证endpoint格式
        endpoint = config.get("endpoint", "")
        if not self._validate_url(endpoint):
            self.errors.append("MinIO endpoint格式无效")
            return False
        
        # 验证bucket名称
        bucket = config.get("bucket", "")
        if not self._validate_bucket_name(bucket):
            self.errors.append("MinIO bucket名称格式无效")
            return False
        
        return len(self.errors) == 0
    
    def validate_milvus_config(self, config: Dict[str, Any]) -> bool:
        """
        验证Milvus配置
        
        Args:
            config: Milvus配置字典
            
        Returns:
            验证是否通过
        """
        self._clear_results()
        
        # 检查必需字段
        required_fields = ["host", "port", "collection"]
        if not self._check_required_fields(config, required_fields, "milvus"):
            return False
        
        # 验证端口
        port = config.get("port", 19530)
        if not isinstance(port, int) or port <= 0 or port > 65535:
            self.errors.append("Milvus端口必须是1-65535之间的整数")
            return False
        
        return len(self.errors) == 0
    
    def validate_elasticsearch_config(self, config: Dict[str, Any]) -> bool:
        """
        验证Elasticsearch配置
        
        Args:
            config: Elasticsearch配置字典
            
        Returns:
            验证是否通过
        """
        self._clear_results()
        
        # 检查必需字段
        required_fields = ["url", "index"]
        if not self._check_required_fields(config, required_fields, "elasticsearch"):
            return False
        
        # 验证URL格式
        url = config.get("url", "")
        if not self._validate_url(url):
            self.errors.append("Elasticsearch URL格式无效")
            return False
        
        return len(self.errors) == 0
    
    def validate_llm_config(self, config: Dict[str, Any]) -> bool:
        """
        验证LLM配置
        
        Args:
            config: LLM配置字典
            
        Returns:
            验证是否通过
        """
        self._clear_results()
        
        # 检查API密钥
        api_key = config.get("openai_api_key", "")
        if not api_key or not isinstance(api_key, str):
            self.warnings.append("OpenAI API密钥未设置")
        
        # 检查默认模型
        default_model = config.get("default_model", "")
        if not default_model or not isinstance(default_model, str):
            self.warnings.append("未设置默认LLM模型")
        
        return len(self.errors) == 0
    
    def validate_jwt_config(self, config: Dict[str, Any]) -> bool:
        """
        验证JWT配置
        
        Args:
            config: JWT配置字典
            
        Returns:
            验证是否通过
        """
        self._clear_results()
        
        # 检查密钥
        secret_key = config.get("jwt_secret_key", "")
        if not secret_key or len(secret_key) < 32:
            self.errors.append("JWT密钥长度至少为32个字符")
            return False
        
        # 检查算法
        algorithm = config.get("jwt_algorithm", "HS256")
        valid_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if algorithm not in valid_algorithms:
            self.errors.append(f"JWT算法必须是以下之一: {', '.join(valid_algorithms)}")
            return False
        
        # 检查过期时间
        expire_minutes = config.get("access_token_expire_minutes", 30)
        if not isinstance(expire_minutes, int) or expire_minutes <= 0:
            self.errors.append("JWT访问令牌过期时间必须是正整数")
            return False
        
        return len(self.errors) == 0
    
    def validate_required_fields(self, config: Dict[str, Any], required: List[str]) -> bool:
        """
        验证必需字段
        
        Args:
            config: 配置字典
            required: 必需字段列表
            
        Returns:
            验证是否通过
        """
        self._clear_results()
        return self._check_required_fields(config, required, "config")
    
    def validate_full_config(self, config: Dict[str, Any]) -> bool:
        """
        验证完整配置
        
        Args:
            config: 完整配置字典
            
        Returns:
            验证是否通过
        """
        self._clear_results()
        
        all_valid = True
        
        # 验证数据库配置
        if "database" in config:
            if not self.validate_database_config(config["database"]):
                all_valid = False
        
        # 验证Redis配置
        if "redis" in config:
            if not self.validate_redis_config(config["redis"]):
                all_valid = False
        
        # 验证MinIO配置
        if "storage" in config and "minio" in config["storage"]:
            if not self.validate_minio_config(config["storage"]["minio"]):
                all_valid = False
        
        # 验证Milvus配置
        if "vector_store" in config and "milvus" in config["vector_store"]:
            if not self.validate_milvus_config(config["vector_store"]["milvus"]):
                all_valid = False
        
        # 验证Elasticsearch配置
        if "vector_store" in config and "elasticsearch" in config["vector_store"]:
            if not self.validate_elasticsearch_config(config["vector_store"]["elasticsearch"]):
                all_valid = False
        
        # 验证LLM配置
        if "llm" in config:
            if not self.validate_llm_config(config["llm"]):
                all_valid = False
        
        # 验证JWT配置
        if "auth" in config:
            if not self.validate_jwt_config(config["auth"]):
                all_valid = False
        
        return all_valid
    
    def _clear_results(self):
        """清除验证结果"""
        self.errors.clear()
        self.warnings.clear()
    
    def _check_required_fields(self, config: Dict[str, Any], required: List[str], section: str) -> bool:
        """检查必需字段"""
        missing_fields = []
        for field in required:
            if field not in config or config[field] is None or config[field] == "":
                missing_fields.append(field)
        
        if missing_fields:
            self.errors.append(f"{section}配置缺少必需字段: {', '.join(missing_fields)}")
            return False
        
        return True
    
    def _validate_database_url(self, url: str) -> bool:
        """验证数据库URL格式"""
        if not url:
            return False
        
        try:
            parsed = urlparse(url)
            # 检查基本组件
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # 检查支持的数据库类型
            supported_schemes = ["postgresql", "mysql", "sqlite", "oracle", "mssql"]
            scheme = parsed.scheme.split("+")[0]  # 处理如 postgresql+psycopg2 的情况
            
            return scheme in supported_schemes
        except Exception:
            return False
    
    def _validate_url(self, url: str) -> bool:
        """验证URL格式"""
        if not url:
            return False
        
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False
    
    def _validate_bucket_name(self, bucket_name: str) -> bool:
        """验证bucket名称格式"""
        if not bucket_name:
            return False
        
        # MinIO bucket名称规则
        if len(bucket_name) < 3 or len(bucket_name) > 63:
            return False
        
        # 只能包含小写字母、数字和连字符
        if not re.match(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$', bucket_name):
            return False
        
        # 不能包含连续的连字符
        if '--' in bucket_name:
            return False
        
        return True
    
    def get_errors(self) -> List[str]:
        """获取错误列表"""
        return self.errors.copy()
    
    def get_warnings(self) -> List[str]:
        """获取警告列表"""
        return self.warnings.copy()
    
    def get_validation_report(self) -> Dict[str, Any]:
        """获取验证报告"""
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors.copy(),
            "warnings": self.warnings.copy(),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings)
        }


# 全局验证器实例
_validator = None


def get_validator() -> ConfigValidator:
    """获取全局配置验证器实例"""
    global _validator
    if _validator is None:
        _validator = ConfigValidator()
    return _validator


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证配置的便捷函数
    
    Args:
        config: 要验证的配置字典
        
    Returns:
        验证报告
    """
    validator = get_validator()
    validator.validate_full_config(config)
    return validator.get_validation_report() 