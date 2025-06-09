#!/usr/bin/env python3
"""
高级配置管理器
支持分层配置、环境分离、最小配置集合和动态注入
"""

import os
import json
import yaml
import asyncio
import logging

from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime
import threading
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

logger = logging.getLogger(__name__)


@dataclass
class ConfigValidationResult:
    """配置验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    missing_required: List[str] = field(default_factory=list)
    validation_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConfigVersion:
    """配置版本信息"""
    version: str
    timestamp: datetime
    environment: str
    config_hash: str
    change_summary: str
    author: str = "system"
    backup_path: Optional[str] = None


@dataclass
class ConfigChange:
    """配置变更记录"""
    key: str
    old_value: Any
    new_value: Any
    change_type: str  # added, modified, removed
    timestamp: datetime = field(default_factory=datetime.now)



class ConfigurationError(Exception):
    """配置管理异常"""
    pass


class MinimalConfigSet:
    """最小配置集合 - 23项核心配置"""
    
    def __init__(self):
        self.required_configs = {
            # 系统核心配置 (5项)
            "SERVICE_NAME": "knowledge-qa-backend",
            "SERVICE_IP": "127.0.0.1",
            "SERVICE_PORT": "8000",
            "APP_ENV": "minimal",
            "LOG_LEVEL": "INFO",
            
            # 安全配置 (4项)
            "JWT_SECRET_KEY": self._generate_secure_key(32),
            "JWT_ALGORITHM": "HS256",
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "30",
            "ENCRYPTION_KEY": self._generate_secure_key(32),
            
            # 数据库配置 (1项 - 增强)
            "DATABASE_URL": "sqlite:///./data/minimal.db",
            
            # 服务集成配置 (13项)
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "REDIS_DB": "0",
            "MINIO_ENDPOINT": "localhost:9000",
            "MINIO_ACCESS_KEY": "minioadmin",
            "MINIO_SECRET_KEY": "minioadmin",
            "MINIO_BUCKET": "knowledge-docs-minimal",
            "MILVUS_HOST": "localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_COLLECTION": "knowledge_base_minimal",
            "ELASTICSEARCH_URL": "http://localhost:9200",
            "ELASTICSEARCH_INDEX": "knowledge_docs_minimal",
            "OPENAI_API_KEY": "sk-test-key-for-minimal",
        }
        
        # 扩展数据库配置（运行时自动添加）
        self.extended_db_configs = {
            # SQLite扩展配置
            "DB_ECHO": "false",
            "DB_POOL_SIZE": "1",
            "DB_MAX_OVERFLOW": "0",
            "DB_POOL_TIMEOUT": "10",
            "DB_POOL_RECYCLE": "3600",
            "DB_AUTO_CREATE_TABLES": "true",
            "DB_AUTO_MIGRATE": "true",
            "DB_SEED_MINIMAL_DATA": "true",
            "DB_BACKUP_ENABLED": "false",
            # 数据目录配置
            "DATA_DIR": "./data",
            "UPLOAD_DIR": "./data/uploads",
            "LOG_DIR": "./data/logs",
            "BACKUP_DIR": "./data/backups",
        }
    
    def _generate_secure_key(self, length: int = 32) -> str:
        """生成安全密钥"""
        import secrets
        return secrets.token_urlsafe(length)
    
    def get_minimal_config(self) -> Dict[str, Any]:
        """获取最小配置（23项核心配置）"""
        return self.required_configs.copy()
    
    def get_extended_config(self) -> Dict[str, Any]:
        """获取扩展配置（包含数据库增强配置）"""
        config = self.required_configs.copy()
        config.update(self.extended_db_configs)
        return config
    
    def get_database_config(self) -> Dict[str, Any]:
        """获取数据库专用配置"""
        return {
            # 核心数据库配置
            "DATABASE_URL": self.required_configs["DATABASE_URL"],
            
            # 数据库连接池配置
            "DB_ECHO": self.extended_db_configs["DB_ECHO"],
            "DB_POOL_SIZE": self.extended_db_configs["DB_POOL_SIZE"],
            "DB_MAX_OVERFLOW": self.extended_db_configs["DB_MAX_OVERFLOW"],
            "DB_POOL_TIMEOUT": self.extended_db_configs["DB_POOL_TIMEOUT"],
            "DB_POOL_RECYCLE": self.extended_db_configs["DB_POOL_RECYCLE"],
            
            # 数据库管理配置
            "DB_AUTO_CREATE_TABLES": self.extended_db_configs["DB_AUTO_CREATE_TABLES"],
            "DB_AUTO_MIGRATE": self.extended_db_configs["DB_AUTO_MIGRATE"],
            "DB_SEED_MINIMAL_DATA": self.extended_db_configs["DB_SEED_MINIMAL_DATA"],
            "DB_BACKUP_ENABLED": self.extended_db_configs["DB_BACKUP_ENABLED"],
            
            # 数据目录配置
            "DATA_DIR": self.extended_db_configs["DATA_DIR"],
            "UPLOAD_DIR": self.extended_db_configs["UPLOAD_DIR"],
            "LOG_DIR": self.extended_db_configs["LOG_DIR"],
            "BACKUP_DIR": self.extended_db_configs["BACKUP_DIR"],
        }
    
    def validate_minimal_config(self, config: Dict[str, Any]) -> bool:
        """验证最小配置完整性（23项核心配置）"""
        required_keys = set(self.required_configs.keys())
        provided_keys = set(config.keys())
        missing_keys = required_keys - provided_keys
        
        if missing_keys:
            raise ConfigurationError(f"最小配置缺失以下必需项: {missing_keys}")
        
        return True
    
    def validate_database_config(self, config: Dict[str, Any]) -> Dict[str, str]:
        """验证数据库配置"""
        issues = []
        warnings = []
        
        database_url = config.get("DATABASE_URL", "")
        
        # 检查数据库URL格式
        if not database_url:
            issues.append("DATABASE_URL 不能为空")
        elif database_url.startswith("sqlite:///"):
            # SQLite特定验证
            db_path = database_url.replace("sqlite:///", "")
            if not db_path:
                issues.append("SQLite数据库路径不能为空")
            elif not db_path.startswith("./"):
                warnings.append("建议使用相对路径存储SQLite数据库")
        elif database_url.startswith(("postgresql://", "mysql+pymysql://")):
            # 外部数据库警告
            warnings.append("使用外部数据库会增加部署复杂度，不符合最小配置原则")
        else:
            issues.append(f"不支持的数据库类型: {database_url}")
        
        # 检查数据目录配置
        data_dir = config.get("DATA_DIR", "./data")
        if not data_dir.startswith("./"):
            warnings.append("建议使用相对路径作为数据目录")
        
        return {
            "issues": issues,
            "warnings": warnings,
            "valid": len(issues) == 0
        }
    
    def get_required_config_names(self) -> List[str]:
        """获取必需配置项名称列表（23项）"""
        return list(self.required_configs.keys())
    
    def get_config_categories(self) -> Dict[str, List[str]]:
        """获取配置项分类"""
        return {
            "系统核心配置": ["SERVICE_NAME", "SERVICE_IP", "SERVICE_PORT", "APP_ENV", "LOG_LEVEL"],
            "安全配置": ["JWT_SECRET_KEY", "JWT_ALGORITHM", "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "ENCRYPTION_KEY"],
            "数据库配置": ["DATABASE_URL"],
            "服务集成配置": [
                "REDIS_HOST", "REDIS_PORT", "REDIS_DB",
                "MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "MINIO_BUCKET",
                "MILVUS_HOST", "MILVUS_PORT", "MILVUS_COLLECTION",
                "ELASTICSEARCH_URL", "ELASTICSEARCH_INDEX", "OPENAI_API_KEY"
            ]
        }
    
    def generate_env_template(self) -> str:
        """生成环境变量模板"""
        template = "# 最小配置环境变量模板 (23项核心配置)\n"
        template += "# 复制到 .env 文件并根据需要修改\n\n"
        
        categories = self.get_config_categories()
        
        for category, keys in categories.items():
            template += f"# {category} ({len(keys)}项)\n"
            for key in keys:
                value = self.required_configs[key]
                # 对于生成的密钥，显示为占位符
                if key in ["JWT_SECRET_KEY", "ENCRYPTION_KEY"]:
                    value = "your-secret-key-here"
                template += f"{key}={value}\n"
            template += "\n"
        
        return template
    
    def create_data_directories(self, base_path: str = "./data") -> bool:
        """创建数据目录结构"""
        import os
        from pathlib import Path
        
        try:
            directories = [
                base_path,
                f"{base_path}/uploads",
                f"{base_path}/logs", 
                f"{base_path}/backups"
            ]
            
            for directory in directories:
                Path(directory).mkdir(parents=True, exist_ok=True)
            
            return True
        except Exception as e:
            logger.error(f"创建数据目录失败: {str(e)}")
            return False


class ConfigProvider:
    """配置提供者基类"""
    
    def __init__(self, priority: int = 0):
        self.priority = priority
        self.name = self.__class__.__name__
    
    def load(self) -> Dict[str, Any]:
        """加载配置"""
        raise NotImplementedError
    
    def is_available(self) -> bool:
        """检查提供者是否可用"""
        return True


class EnvironmentConfigProvider(ConfigProvider):
    """环境变量配置提供者"""
    
    def __init__(self):
        super().__init__(priority=10)  # 最高优先级
    
    def load(self) -> Dict[str, Any]:
        """从环境变量加载配置"""
        config = {}
        
        # 获取所有环境变量
        for key, value in os.environ.items():
            # 处理布尔值
            if value.lower() in ('true', 'false'):
                config[key] = value.lower() == 'true'
            # 处理数字
            elif value.isdigit():
                config[key] = int(value)
            # 处理浮点数
            elif self._is_float(value):
                config[key] = float(value)
            else:
                config[key] = value
        
        logger.debug(f"环境变量提供者加载了 {len(config)} 个配置项")
        return config
    
    def _is_float(self, value: str) -> bool:
        """检查字符串是否为浮点数"""
        try:
            float(value)
            return '.' in value
        except ValueError:
            return False


class FileConfigProvider(ConfigProvider):
    """文件配置提供者"""
    
    def __init__(self, environment: str, project_root: Path = None):
        super().__init__(priority=5)
        self.environment = environment
        self.project_root = project_root or Path(__file__).parent.parent.parent.parent
    
    def load(self) -> Dict[str, Any]:
        """从文件加载配置"""
        config = {}
        config_files = self._get_config_file_order()
        
        for config_file in config_files:
            if config_file.exists():
                file_config = self._load_config_file(config_file)
                config = self._deep_merge(config, file_config)
                logger.debug(f"加载配置文件: {config_file}")
        
        logger.info(f"文件配置提供者加载了 {len(config)} 个配置项")
        return config
    
    def _get_config_file_order(self) -> List[Path]:
        """获取配置文件加载顺序（从低优先级到高优先级）"""
        files = [
            # 首先加载默认配置
            self.project_root / "config" / "default.yaml",
            
            # 然后加载环境特定配置
            self.project_root / "config" / f"{self.environment}.yaml",
        ]
        
        # 过滤存在的文件
        existing_files = [f for f in files if f.exists()]
        
        if not existing_files:
            logger.warning(f"未找到环境 {self.environment} 的配置文件")
        
        return existing_files
    
    def _load_config_file(self, file_path: Path) -> Dict[str, Any]:
        """加载单个配置文件"""
        try:
            if file_path.suffix in ['.yaml', '.yml']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            elif file_path.suffix == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            elif file_path.name.startswith('.env'):
                return self._parse_env_file(file_path)
            else:
                logger.warning(f"不支持的配置文件格式: {file_path}")
                return {}
        except Exception as e:
            logger.error(f"加载配置文件失败 {file_path}: {str(e)}")
            return {}
    
    def _parse_env_file(self, file_path: Path) -> Dict[str, Any]:
        """解析.env格式文件"""
        config = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    try:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
                    except ValueError:
                        logger.warning(f"解析 {file_path}:{line_num} 失败: {line}")
        return config
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """递归合并字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base


class RemoteConfigProvider(ConfigProvider):
    """远程配置中心提供者（占位实现）"""
    
    def __init__(self, config_center_url: str = None):
        super().__init__(priority=3)
        self.config_center_url = config_center_url
    
    def load(self) -> Dict[str, Any]:
        """从远程配置中心加载配置"""
        if not self.config_center_url:
            return {}
        
        # TODO: 实现具体的远程配置中心集成
        # 例如: Consul, etcd, Nacos等
        logger.info("远程配置中心提供者（暂未实现）")
        return {}
    
    def is_available(self) -> bool:
        """检查远程配置中心是否可用"""
        return self.config_center_url is not None


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self):
        self.validation_schema = self._build_validation_schema()
    
    def validate(self, config: Dict[str, Any]) -> ConfigValidationResult:
        """验证配置"""
        errors = []
        warnings = []
        missing_required = []
        
        # 检查必需配置
        minimal_config = MinimalConfigSet()
        required_keys = minimal_config.get_required_config_names()
        
        for key in required_keys:
            if key not in config:
                missing_required.append(key)
        
        # 类型和格式验证
        for key, value in config.items():
            validation_result = self._validate_single_config(key, value)
            if validation_result.get('error'):
                errors.append(f"{key}: {validation_result['error']}")
            if validation_result.get('warning'):
                warnings.append(f"{key}: {validation_result['warning']}")
        
        is_valid = len(errors) == 0 and len(missing_required) == 0
        
        return ConfigValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            missing_required=missing_required
        )
    
    def _build_validation_schema(self) -> Dict[str, Dict[str, Any]]:
        """构建验证模式"""
        return {
            'SERVICE_NAME': {
                'type': str,
                'required': True,
                'min_length': 1,
                'max_length': 100
            },
            'SERVICE_PORT': {
                'type': int,
                'required': True,
                'min_value': 1,
                'max_value': 65535
            },
            'DATABASE_URL': {
                'type': str,
                'required': True,
                'pattern': r'^(sqlite|postgresql|mysql)://.*'
            },
            'JWT_SECRET_KEY': {
                'type': str,
                'required': True,
                'min_length': 32
            },
            'LOG_LEVEL': {
                'type': str,
                'required': False,
                'allowed_values': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            }
        }
    
    def _validate_single_config(self, key: str, value: Any) -> Dict[str, str]:
        """验证单个配置项"""
        result = {}
        
        if key not in self.validation_schema:
            return result
        
        schema = self.validation_schema[key]
        
        # 类型检查
        expected_type = schema.get('type')
        if expected_type and not isinstance(value, expected_type):
            result['error'] = f"期望类型 {expected_type.__name__}，实际类型 {type(value).__name__}"
            return result
        
        # 字符串长度检查
        if isinstance(value, str):
            min_length = schema.get('min_length')
            max_length = schema.get('max_length')
            
            if min_length and len(value) < min_length:
                result['error'] = f"长度不能少于 {min_length} 个字符"
            elif max_length and len(value) > max_length:
                result['error'] = f"长度不能超过 {max_length} 个字符"
        
        # 数值范围检查
        if isinstance(value, (int, float)):
            min_value = schema.get('min_value')
            max_value = schema.get('max_value')
            
            if min_value and value < min_value:
                result['error'] = f"值不能小于 {min_value}"
            elif max_value and value > max_value:
                result['error'] = f"值不能大于 {max_value}"
        
        # 允许值检查
        allowed_values = schema.get('allowed_values')
        if allowed_values and value not in allowed_values:
            result['error'] = f"值必须是以下之一: {allowed_values}"
        
        # 模式匹配检查
        pattern = schema.get('pattern')
        if pattern and isinstance(value, str):
            import re
            if not re.match(pattern, value):
                result['warning'] = f"格式可能不正确（期望模式: {pattern}）"
        
        return result


class AdvancedConfigManager:
    """高级配置管理器"""
    
    def __init__(self, environment: str = None, project_root: Path = None):
        self.environment = environment or os.getenv("APP_ENV", "development")
        self.project_root = project_root or Path(__file__).parent.parent.parent.parent
        
        # 初始化组件
        self.minimal_config = MinimalConfigSet()
        self.validator = ConfigValidator()

class ConfigFileWatcher(FileSystemEventHandler):
    """配置文件监控器"""
    
    def __init__(self, config_manager, reload_callback: Callable = None):
        super().__init__()
        self.config_manager = config_manager
        self.reload_callback = reload_callback
        self.last_reload = time.time()
        self.reload_cooldown = 2  # 2秒冷却期防止频繁重载
    
    def on_modified(self, event):
        """文件修改事件处理"""
        if event.is_directory:
            return
        
        # 检查是否为配置文件
        if self._is_config_file(event.src_path):
            current_time = time.time()
            if current_time - self.last_reload > self.reload_cooldown:
                logger.info(f"检测到配置文件变更: {event.src_path}")
                self._trigger_reload()
                self.last_reload = current_time
    
    def _is_config_file(self, file_path: str) -> bool:
        """判断是否为配置文件"""
        config_extensions = ['.env', '.yaml', '.yml', '.json', '.toml']
        config_files = ['config.yaml', 'config.yml', 'config.json', '.env', '.env.local']
        
        file_path = Path(file_path)
        return (
            file_path.suffix.lower() in config_extensions or
            file_path.name in config_files or
            'config' in file_path.name.lower()
        )
    
    def _trigger_reload(self):
        """触发配置重载"""
        try:
            old_config = self.config_manager.config_cache.copy()
            new_config = self.config_manager.refresh_configuration()
            
            # 检测配置变更
            changes = self._detect_changes(old_config, new_config)
            if changes:
                logger.info(f"配置热重载完成，检测到 {len(changes)} 个变更")
                
                # 执行回调
                if self.reload_callback:
                    self.reload_callback(changes, new_config)
            else:
                logger.debug("配置文件已更新，但内容无变化")
                
        except Exception as e:
            logger.error(f"配置热重载失败: {str(e)}")
    
    def _detect_changes(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> List[ConfigChange]:
        """检测配置变更"""
        changes = []
        
        # 检查新增和修改
        for key, new_value in new_config.items():
            if key not in old_config:
                changes.append(ConfigChange(key, None, new_value, "added"))
            elif old_config[key] != new_value:
                changes.append(ConfigChange(key, old_config[key], new_value, "modified"))
        
        # 检查删除
        for key in old_config:
            if key not in new_config:
                changes.append(ConfigChange(key, old_config[key], None, "removed"))
        
        return changes


class ConfigVersionManager:
    """配置版本管理器"""
    
    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.versions_file = self.backup_dir / "versions.json"
        self.versions: List[ConfigVersion] = self._load_versions()
    
    def create_version(self, config: Dict[str, Any], environment: str, 
                      change_summary: str = "Auto backup", author: str = "system") -> ConfigVersion:
        """创建配置版本"""
        config_hash = self._calculate_config_hash(config)
        version_id = f"v{len(self.versions) + 1}_{int(time.time())}"
        timestamp = datetime.now()
        
        # 创建备份文件
        backup_filename = f"{version_id}_{environment}_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = self.backup_dir / backup_filename
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2, default=str)
        
        # 创建版本记录
        version = ConfigVersion(
            version=version_id,
            timestamp=timestamp,
            environment=environment,
            config_hash=config_hash,
            change_summary=change_summary,
            author=author,
            backup_path=str(backup_path)
        )
        
        self.versions.append(version)
        self._save_versions()
        
        # 清理旧版本（保留最近20个版本）
        self._cleanup_old_versions()
        
        logger.info(f"配置版本创建完成: {version_id}")
        return version
    
    def restore_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        """恢复指定版本的配置"""
        version = self._find_version(version_id)
        if not version or not version.backup_path:
            logger.error(f"版本 {version_id} 不存在或备份文件丢失")
            return None
        
        try:
            with open(version.backup_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            logger.info(f"配置版本恢复成功: {version_id}")
            return config
            
        except Exception as e:
            logger.error(f"恢复版本 {version_id} 失败: {str(e)}")
            return None
    
    def list_versions(self, environment: str = None, limit: int = 10) -> List[ConfigVersion]:
        """列出配置版本"""
        versions = self.versions
        
        if environment:
            versions = [v for v in versions if v.environment == environment]
        
        # 按时间倒序排列
        versions.sort(key=lambda v: v.timestamp, reverse=True)
        
        return versions[:limit]
    
    def get_version_diff(self, version1_id: str, version2_id: str) -> Optional[List[ConfigChange]]:
        """获取两个版本之间的差异"""
        config1 = self.restore_version(version1_id)
        config2 = self.restore_version(version2_id)
        
        if not config1 or not config2:
            return None
        
        changes = []
        
        # 检查变更
        all_keys = set(config1.keys()) | set(config2.keys())
        for key in all_keys:
            if key not in config1:
                changes.append(ConfigChange(key, None, config2[key], "added"))
            elif key not in config2:
                changes.append(ConfigChange(key, config1[key], None, "removed"))
            elif config1[key] != config2[key]:
                changes.append(ConfigChange(key, config1[key], config2[key], "modified"))
        
        return changes
    
    def _calculate_config_hash(self, config: Dict[str, Any]) -> str:
        """计算配置哈希值"""
        config_str = json.dumps(config, sort_keys=True, default=str)
        return hashlib.md5(config_str.encode()).hexdigest()
    
    def _find_version(self, version_id: str) -> Optional[ConfigVersion]:
        """查找指定版本"""
        for version in self.versions:
            if version.version == version_id:
                return version
        return None
    
    def _load_versions(self) -> List[ConfigVersion]:
        """加载版本记录"""
        if not self.versions_file.exists():
            return []
        
        try:
            with open(self.versions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            versions = []
            for item in data:
                versions.append(ConfigVersion(
                    version=item['version'],
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    environment=item['environment'],
                    config_hash=item['config_hash'],
                    change_summary=item['change_summary'],
                    author=item.get('author', 'system'),
                    backup_path=item.get('backup_path')
                ))
            
            return versions
            
        except Exception as e:
            logger.error(f"加载版本记录失败: {str(e)}")
            return []
    
    def _save_versions(self):
        """保存版本记录"""
        try:
            data = []
            for version in self.versions:
                data.append({
                    'version': version.version,
                    'timestamp': version.timestamp.isoformat(),
                    'environment': version.environment,
                    'config_hash': version.config_hash,
                    'change_summary': version.change_summary,
                    'author': version.author,
                    'backup_path': version.backup_path
                })
            
            with open(self.versions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"保存版本记录失败: {str(e)}")
    
    def _cleanup_old_versions(self, keep_count: int = 20):
        """清理旧版本"""
        if len(self.versions) <= keep_count:
            return
        
        # 按时间排序，删除最老的版本
        self.versions.sort(key=lambda v: v.timestamp, reverse=True)
        
        versions_to_remove = self.versions[keep_count:]
        for version in versions_to_remove:
            # 删除备份文件
            if version.backup_path and Path(version.backup_path).exists():
                try:
                    Path(version.backup_path).unlink()
                    logger.debug(f"删除旧版本备份: {version.backup_path}")
                except Exception as e:
                    logger.warning(f"删除备份文件失败: {str(e)}")
        
        # 保留最新的版本
        self.versions = self.versions[:keep_count]
        self._save_versions()


class AdvancedConfigManager:
    """高级配置管理器"""
    
    def __init__(self, environment: str = None, project_root: Path = None, 
                 enable_hot_reload: bool = True, enable_versioning: bool = True):
        """初始化配置管理器"""
        self.environment = environment or os.getenv("APP_ENV", "development")
        self.project_root = project_root or Path(__file__).parent.parent.parent.parent
        
        # 初始化组件
        self.minimal_config = MinimalConfigSet()
        self.validator = ConfigValidator()
        self.config_cache: Dict[str, Any] = {}
        self.cache_timestamp: Optional[datetime] = None
        self.cache_ttl = 300  # 5分钟缓存
        
        # 配置提供者
        self.providers = self._setup_providers()
        
        # 热重载功能
        self.enable_hot_reload = enable_hot_reload
        self.file_watcher: Optional[ConfigFileWatcher] = None
        self.observer: Optional[Observer] = None
        self.reload_callbacks: List[Callable] = []
        
        # 版本管理功能
        self.enable_versioning = enable_versioning
        self.version_manager: Optional[ConfigVersionManager] = None
        if enable_versioning:
            backup_dir = self.project_root / "config" / "backups"
            self.version_manager = ConfigVersionManager(backup_dir)
        
        # 启动热重载
        if enable_hot_reload:
            self._start_hot_reload()
        
        logger.info(f"高级配置管理器初始化完成 - 环境: {self.environment}, "
                   f"热重载: {enable_hot_reload}, 版本管理: {enable_versioning}")

    
    def _setup_providers(self) -> List[ConfigProvider]:
        """设置配置提供者"""
        providers = [
            EnvironmentConfigProvider(),
            FileConfigProvider(self.environment, self.project_root),
        ]
        
        # 生产环境或预发布环境添加远程配置中心
        if self.environment in ["production", "staging"]:
            remote_url = os.getenv("CONFIG_CENTER_URL")
            if remote_url:
                providers.append(RemoteConfigProvider(remote_url))
        
        # 按优先级排序（高优先级在后面）
        providers.sort(key=lambda p: p.priority)
        
        logger.info(f"配置提供者初始化完成: {[p.name for p in providers]}")
        return providers
    
    def load_configuration(self, minimal_mode: bool = False, use_cache: bool = True) -> Dict[str, Any]:
        """加载配置"""
        
        # 最小配置模式
        if minimal_mode:
            logger.info("使用最小配置模式")
            return self.minimal_config.get_minimal_config()
        
        # 检查缓存
        if use_cache and self._is_cache_valid():
            logger.debug("使用缓存的配置")
            return self.config_cache.copy()
        
        # 从配置提供者加载
        config = {}
        
        for provider in self.providers:
            if provider.is_available():
                try:
                    provider_config = provider.load()
                    config = self._deep_merge(config, provider_config)
                    logger.debug(f"从 {provider.name} 加载了 {len(provider_config)} 个配置项")
                except Exception as e:
                    logger.error(f"从 {provider.name} 加载配置失败: {str(e)}")
        
        # 更新缓存
        self.config_cache = config
        self.cache_timestamp = datetime.now()
        
        logger.info(f"配置加载完成 - 总计 {len(config)} 个配置项")
        return config
    
    def validate_configuration(self, config: Dict[str, Any] = None) -> ConfigValidationResult:
        """验证配置"""
        if config is None:
            config = self.load_configuration()
        
        return self.validator.validate(config)
    
    def switch_environment(self, new_environment: str) -> Dict[str, Any]:
        """切换环境并重新加载配置"""
        old_env = self.environment
        self.environment = new_environment
        os.environ["APP_ENV"] = new_environment
        
        # 清理缓存
        self.config_cache.clear()
        self.cache_timestamp = None
        
        # 重新设置提供者
        self.providers = self._setup_providers()
        
        # 重新加载配置
        config = self.load_configuration(use_cache=False)
        
        logger.info(f"环境切换完成: {old_env} -> {new_environment}")
        return config
    
    def get_config_value(self, key: str, default: Any = None, minimal_mode: bool = False) -> Any:
        """获取单个配置值"""
        config = self.load_configuration(minimal_mode=minimal_mode)
        return config.get(key, default)
    
    def refresh_configuration(self) -> Dict[str, Any]:
        """刷新配置（强制重新加载）"""
        logger.info("强制刷新配置")
        return self.load_configuration(use_cache=False)
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """获取配置总览"""
        config = self.load_configuration()
        minimal_keys = set(self.minimal_config.get_required_config_names())
        
        summary = {
            "environment": self.environment,
            "total_configs": len(config),
            "minimal_configs": len(minimal_keys),
            "minimal_coverage": len(minimal_keys & set(config.keys())),
            "last_loaded": self.cache_timestamp.isoformat() if self.cache_timestamp else None,
            "providers": [p.name for p in self.providers if p.is_available()],
            "validation_result": self.validate_configuration(config),
        }
        
        return summary
    
    def export_configuration(self, file_path: str, format: str = "json", include_sensitive: bool = False) -> bool:
        """导出配置到文件"""
        try:
            config = self.load_configuration()
            
            # 是否包含敏感配置
            if not include_sensitive:
                config = self._mask_sensitive_configs(config)
            
            file_path = Path(file_path)
            
            if format.lower() == "json":
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2, default=str)
            elif format.lower() in ["yaml", "yml"]:
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            else:
                raise ValueError(f"不支持的导出格式: {format}")
            
            logger.info(f"配置导出成功: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"配置导出失败: {str(e)}")
            return False
    
    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self.cache_timestamp or not self.config_cache:
            return False
        
        cache_age = (datetime.now() - self.cache_timestamp).total_seconds()
        return cache_age < self.cache_ttl
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """递归合并字典"""
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _mask_sensitive_configs(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """屏蔽敏感配置"""
        masked_config = config.copy()
        sensitive_keywords = ["PASSWORD", "SECRET", "KEY", "TOKEN", "CREDENTIAL"]
        
        for key, value in masked_config.items():
            if any(keyword in key.upper() for keyword in sensitive_keywords):
                if isinstance(value, str) and len(value) > 4:
                    masked_config[key] = value[:2] + "*" * (len(value) - 4) + value[-2:]
                else:
                    masked_config[key] = "***"
        
        return masked_config

    
    # ==================== 热重载功能 ====================
    
    def _start_hot_reload(self):
        """启动配置文件热重载监控"""
        try:
            self.file_watcher = ConfigFileWatcher(self, self._on_config_reload)
            self.observer = Observer()
            
            # 监控项目根目录下的配置文件
            watch_dirs = [
                self.project_root,
                self.project_root / "config",
                self.project_root / "app" / "config"
            ]
            
            for watch_dir in watch_dirs:
                if watch_dir.exists():
                    self.observer.schedule(self.file_watcher, str(watch_dir), recursive=False)
                    logger.debug(f"添加配置文件监控目录: {watch_dir}")
            
            self.observer.start()
            logger.info("配置文件热重载监控已启动")
            
        except Exception as e:
            logger.error(f"启动配置文件热重载失败: {str(e)}")
            self.enable_hot_reload = False
    
    def stop_hot_reload(self):
        """停止配置文件热重载监控"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("配置文件热重载监控已停止")
    
    def add_reload_callback(self, callback: Callable[[List[ConfigChange], Dict[str, Any]], None]):
        """添加配置重载回调函数"""
        self.reload_callbacks.append(callback)
    
    def remove_reload_callback(self, callback: Callable):
        """移除配置重载回调函数"""
        if callback in self.reload_callbacks:
            self.reload_callbacks.remove(callback)
    
    def _on_config_reload(self, changes: List[ConfigChange], new_config: Dict[str, Any]):
        """配置重载事件处理"""
        # 创建版本备份
        if self.enable_versioning and self.version_manager:
            change_summary = f"热重载检测到{len(changes)}个配置变更"
            self.version_manager.create_version(
                new_config, 
                self.environment, 
                change_summary,
                "hot_reload"
            )
        
        # 执行用户回调
        for callback in self.reload_callbacks:
            try:
                callback(changes, new_config)
            except Exception as e:
                logger.error(f"执行配置重载回调失败: {str(e)}")
    
    # ==================== 版本管理功能 ====================
    
    def create_config_backup(self, change_summary: str = "Manual backup", 
                           author: str = "manual") -> Optional[ConfigVersion]:
        """手动创建配置备份"""
        if not self.enable_versioning or not self.version_manager:
            logger.warning("版本管理功能未启用")
            return None
        
        config = self.load_configuration()
        return self.version_manager.create_version(config, self.environment, change_summary, author)
    
    def restore_config_version(self, version_id: str, apply_immediately: bool = True) -> bool:
        """恢复配置版本"""
        if not self.enable_versioning or not self.version_manager:
            logger.warning("版本管理功能未启用")
            return False
        
        restored_config = self.version_manager.restore_version(version_id)
        if not restored_config:
            return False
        
        if apply_immediately:
            # 清空缓存，下次加载时使用恢复的配置
            self.config_cache = restored_config
            self.cache_timestamp = datetime.now()
            
            # 创建恢复版本的备份记录
            self.version_manager.create_version(
                restored_config,
                self.environment,
                f"恢复版本: {version_id}",
                "version_restore"
            )
        
        return True
    
    def list_config_versions(self, limit: int = 10) -> List[ConfigVersion]:
        """列出配置版本历史"""
        if not self.enable_versioning or not self.version_manager:
            return []
        
        return self.version_manager.list_versions(self.environment, limit)
    
    def get_config_diff(self, version1_id: str, version2_id: str = None) -> Optional[List[ConfigChange]]:
        """获取配置版本差异"""
        if not self.enable_versioning or not self.version_manager:
            return None
        
        if version2_id is None:
            # 与当前配置比较
            current_config = self.load_configuration()
            version1_config = self.version_manager.restore_version(version1_id)
            
            if not version1_config:
                return None
            
            changes = []
            all_keys = set(current_config.keys()) | set(version1_config.keys())
            
            for key in all_keys:
                if key not in version1_config:
                    changes.append(ConfigChange(key, None, current_config[key], "added"))
                elif key not in current_config:
                    changes.append(ConfigChange(key, version1_config[key], None, "removed"))
                elif version1_config[key] != current_config[key]:
                    changes.append(ConfigChange(key, version1_config[key], current_config[key], "modified"))
            
            return changes
        else:
            # 比较两个版本
            return self.version_manager.get_version_diff(version1_id, version2_id)
    
    def export_config_with_version(self, file_path: str, format: str = "json", 
                                 include_sensitive: bool = False, create_version: bool = True) -> bool:
        """导出配置并创建版本记录"""
        # 导出配置
        success = self.export_configuration(file_path, format, include_sensitive)
        
        # 创建版本记录
        if success and create_version and self.enable_versioning:
            self.create_config_backup(f"配置导出到 {file_path}", "export")
        
        return success
    
    # ==================== 增强功能 ====================
    
    def get_config_health_status(self) -> Dict[str, Any]:
        """获取配置健康状态"""
        config = self.load_configuration()
        validation_result = self.validate_configuration(config)
        
        health_status = {
            "overall_health": "healthy" if validation_result.is_valid else "unhealthy",
            "validation_result": validation_result,
            "cache_status": {
                "cached": bool(self.config_cache),
                "cache_age_seconds": (datetime.now() - self.cache_timestamp).total_seconds() if self.cache_timestamp else None,
                "cache_valid": self._is_cache_valid()
            },
            "hot_reload_status": {
                "enabled": self.enable_hot_reload,
                "active": self.observer.is_alive() if self.observer else False,
                "callbacks_count": len(self.reload_callbacks)
            },
            "versioning_status": {
                "enabled": self.enable_versioning,
                "version_count": len(self.version_manager.versions) if self.version_manager else 0,
                "latest_version": self.version_manager.versions[-1].version if self.version_manager and self.version_manager.versions else None
            }
        }
        
        return health_status
    
    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            if self.observer and self.observer.is_alive():
                self.stop_hot_reload()
        except Exception as e:
            logger.debug(f"配置管理器资源清理时出现异常: {str(e)}")



# 全局配置管理器实例
_global_config_manager: Optional[AdvancedConfigManager] = None



def get_config_manager(environment: str = None, enable_hot_reload: bool = True, 
                      enable_versioning: bool = True) -> AdvancedConfigManager:

    """获取全局配置管理器实例"""
    global _global_config_manager
    
    if _global_config_manager is None or (environment and _global_config_manager.environment != environment):
        _global_config_manager = AdvancedConfigManager(
            environment, 
            enable_hot_reload=enable_hot_reload,
            enable_versioning=enable_versioning
        )
    
    return _global_config_manager


def load_minimal_config() -> Dict[str, Any]:
    """快速加载最小配置"""
    manager = get_config_manager()
    return manager.load_configuration(minimal_mode=True)


def validate_current_config() -> ConfigValidationResult:
    """验证当前配置"""
    manager = get_config_manager()
    return manager.validate_configuration()


def switch_to_environment(environment: str) -> Dict[str, Any]:
    """切换到指定环境"""
    manager = get_config_manager()
    return manager.switch_environment(environment) 



def create_config_backup(change_summary: str = "Manual backup") -> Optional[ConfigVersion]:
    """创建配置备份"""
    manager = get_config_manager()
    return manager.create_config_backup(change_summary)


def restore_config_version(version_id: str) -> bool:
    """恢复配置版本"""
    manager = get_config_manager()
    return manager.restore_config_version(version_id)


def list_config_versions(limit: int = 10) -> List[ConfigVersion]:
    """列出配置版本"""
    manager = get_config_manager()
    return manager.list_config_versions(limit)


def get_config_health() -> Dict[str, Any]:
    """获取配置健康状态"""
    manager = get_config_manager()
    return manager.get_config_health_status()


def add_config_reload_callback(callback: Callable[[List[ConfigChange], Dict[str, Any]], None]):
    """添加配置重载回调"""
    manager = get_config_manager()
    manager.add_reload_callback(callback)


def remove_config_reload_callback(callback: Callable):
    """移除配置重载回调"""
    manager = get_config_manager()
    manager.remove_reload_callback(callback) 

