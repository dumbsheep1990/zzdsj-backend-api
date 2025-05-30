"""
系统配置服务 - 管理系统配置的持久化存储和操作
"""
from app.utils.service_decorators import register_service
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.system_config import SystemConfig, ConfigCategory, ConfigHistory, ServiceHealthRecord
from app.utils.config_manager import get_config
import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# 简单加密工具，用于敏感配置
class ConfigEncryption:
    """配置加密工具"""
    
    @staticmethod
    def _get_encryption_key():
        """获取或生成加密密钥"""
        # 使用系统配置的JWT密钥作为基础
        base_key = get_config("security", "jwt_secret_key", 
                      default="23f0767704249cd7be7181a0dad23c74e0739c98ce54d7140fc2e94dfa584fb0")
        salt = b'knowledge_qa_system_config_salt'
        
        # 从基础密钥生成Fernet密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(base_key.encode()))
        return key
    
    @classmethod
    def encrypt(cls, value: str) -> str:
        """加密配置值"""
        if not value:
            return value
        
        key = cls._get_encryption_key()
        f = Fernet(key)
        encrypted = f.encrypt(value.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    @classmethod
    def decrypt(cls, encrypted_value: str) -> str:
        """解密配置值"""
        if not encrypted_value:
            return encrypted_value
        
        try:
            key = cls._get_encryption_key()
            f = Fernet(key)
            decrypted = f.decrypt(base64.urlsafe_b64decode(encrypted_value))
            return decrypted.decode()
        except Exception as e:
            logger.error(f"解密配置值失败: {str(e)}")
            return "[解密失败]"


@register_service(service_type="system-config", priority="critical", description="系统配置管理服务")
class SystemConfigService:
    """系统配置服务"""
    
    def __init__(self, db: Session):
        """初始化配置服务"""
        self.db = db
    
    # ============ 配置类别管理 ============
    
    def get_categories(self) -> List[ConfigCategory]:
        """获取所有配置类别"""
        return self.db.query(ConfigCategory).order_by(ConfigCategory.order).all()
    
    def get_category(self, id: str) -> Optional[ConfigCategory]:
        """通过ID获取配置类别"""
        return self.db.query(ConfigCategory).filter(ConfigCategory.id == id).first()
    
    def get_category_by_name(self, name: str) -> Optional[ConfigCategory]:
        """通过名称获取配置类别"""
        return self.db.query(ConfigCategory).filter(ConfigCategory.name == name).first()
    
    def create_category(self, name: str, description: str = None, 
                      is_system: bool = False, order: int = 0) -> ConfigCategory:
        """创建配置类别"""
        category = ConfigCategory(
            name=name, 
            description=description,
            is_system=is_system,
            order=order
        )
        self.db.add(category)
        self.db.flush()
        return category
    
    def update_category(self, id: str, name: str = None, description: str = None,
                       order: int = None) -> Optional[ConfigCategory]:
        """更新配置类别"""
        category = self.get_category(id)
        if not category:
            return None
        
        # 系统类别不允许修改名称
        if name and not category.is_system:
            category.name = name
        if description is not None:
            category.description = description
        if order is not None:
            category.order = order
        
        self.db.flush()
        return category
    
    def delete_category(self, id: str) -> bool:
        """删除配置类别"""
        category = self.get_category(id)
        if not category:
            return False
        
        # 系统类别不允许删除
        if category.is_system:
            return False
        
        # 检查是否有关联配置
        if self.db.query(SystemConfig).filter(SystemConfig.category_id == id).count() > 0:
            return False
        
        self.db.delete(category)
        self.db.flush()
        return True
    
    # ============ 配置项管理 ============
    
    def get_configs(self, category_id: str = None, include_sensitive: bool = False) -> List[SystemConfig]:
        """获取配置项列表"""
        query = self.db.query(SystemConfig)
        
        if category_id:
            query = query.filter(SystemConfig.category_id == category_id)
        
        if not include_sensitive:
            query = query.filter(SystemConfig.is_sensitive == False)
        
        return query.all()
    
    def get_config(self, id: str) -> Optional[SystemConfig]:
        """通过ID获取配置项"""
        config = self.db.query(SystemConfig).filter(SystemConfig.id == id).first()
        if config and config.is_encrypted:
            # 解密敏感配置
            config.value = ConfigEncryption.decrypt(config.value)
        return config
    
    def get_config_by_key(self, key: str) -> Optional[SystemConfig]:
        """通过键获取配置项"""
        config = self.db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if config and config.is_encrypted:
            # 解密敏感配置
            config.value = ConfigEncryption.decrypt(config.value)
        return config
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """获取配置值，自动转换类型"""
        config = self.get_config_by_key(key)
        if not config:
            return default
        
        # 根据类型转换值
        try:
            if config.value_type == "number":
                if "." in config.value:
                    return float(config.value)
                return int(config.value)
            elif config.value_type == "boolean":
                return config.value.lower() in ["true", "yes", "1"]
            elif config.value_type == "json":
                return json.loads(config.value)
            else:  # string
                return config.value
        except (ValueError, json.JSONDecodeError):
            logger.error(f"配置值类型转换失败: {key}")
            return default
    
    def create_config(self, key: str, value: Any, value_type: str, category_id: str,
                    description: str = None, default_value: Any = None,
                    is_system: bool = False, is_sensitive: bool = False,
                    validation_rules: Dict = None, visible_level: str = "all") -> SystemConfig:
        """创建配置项"""
        # 将值转换为字符串
        str_value = self._value_to_string(value, value_type)
        str_default = self._value_to_string(default_value, value_type) if default_value is not None else None
        
        # 加密敏感数据
        is_encrypted = is_sensitive
        if is_encrypted and str_value:
            str_value = ConfigEncryption.encrypt(str_value)
        
        config = SystemConfig(
            key=key,
            value=str_value,
            value_type=value_type,
            default_value=str_default,
            category_id=category_id,
            description=description,
            is_system=is_system,
            is_sensitive=is_sensitive,
            is_encrypted=is_encrypted,
            validation_rules=validation_rules,
            visible_level=visible_level
        )
        
        self.db.add(config)
        # 添加历史记录
        history = ConfigHistory(
            config=config,
            new_value=str_value,
            change_source="system",
            change_notes="初始创建"
        )
        self.db.add(history)
        
        self.db.flush()
        return config
    
    def update_config(self, id: str, value: Any = None, description: str = None,
                     is_sensitive: bool = None, validation_rules: Dict = None,
                     visible_level: str = None, change_source: str = "user",
                     changed_by: str = None, change_notes: str = None) -> Optional[SystemConfig]:
        """更新配置项"""
        config = self.get_config(id)
        if not config:
            return None
        
        # 记录旧值
        old_value = config.value if not config.is_encrypted else ConfigEncryption.decrypt(config.value)
        
        # 更新值
        if value is not None:
            # 将值转换为字符串
            str_value = self._value_to_string(value, config.value_type)
            
            # 如果敏感性发生变化
            if is_sensitive is not None and is_sensitive != config.is_sensitive:
                config.is_sensitive = is_sensitive
                # 如果变为敏感，加密
                if is_sensitive:
                    config.is_encrypted = True
                    str_value = ConfigEncryption.encrypt(str_value)
                # 如果不再敏感，解密旧值
                elif config.is_encrypted:
                    config.is_encrypted = False
            # 处理现有敏感配置
            elif config.is_encrypted:
                str_value = ConfigEncryption.encrypt(str_value)
            
            config.value = str_value
        
        # 更新其他字段
        if description is not None:
            config.description = description
        if validation_rules is not None:
            config.validation_rules = validation_rules
        if visible_level is not None:
            config.visible_level = visible_level
        
        # 添加历史记录
        new_value = config.value if not config.is_encrypted else ConfigEncryption.decrypt(config.value)
        if old_value != new_value:
            history = ConfigHistory(
                config=config,
                old_value=old_value,
                new_value=new_value,
                change_source=change_source,
                changed_by=changed_by,
                change_notes=change_notes
            )
            self.db.add(history)
        
        self.db.flush()
        return config
    
    def delete_config(self, id: str) -> bool:
        """删除配置项"""
        config = self.get_config(id)
        if not config:
            return False
        
        # 系统配置不允许删除
        if config.is_system:
            return False
        
        self.db.delete(config)
        self.db.flush()
        return True
    
    def mark_config_overridden(self, key: str, source: str) -> bool:
        """标记配置被覆盖"""
        config = self.get_config_by_key(key)
        if not config:
            return False
        
        config.is_overridden = True
        config.override_source = source
        self.db.flush()
        return True
    
    # ============ 配置历史管理 ============
    
    def get_config_history(self, config_id: str) -> List[ConfigHistory]:
        """获取配置历史记录"""
        return self.db.query(ConfigHistory).filter(
            ConfigHistory.config_id == config_id
        ).order_by(ConfigHistory.created_at.desc()).all()
    
    # ============ 健康记录管理 ============
    
    def save_health_record(self, service_name: str, status: bool, 
                          response_time_ms: int = None, error_message: str = None,
                          details: Dict = None) -> ServiceHealthRecord:
        """保存服务健康记录"""
        record = ServiceHealthRecord(
            service_name=service_name,
            status=status,
            response_time_ms=response_time_ms,
            error_message=error_message,
            details=details
        )
        self.db.add(record)
        self.db.flush()
        return record
    
    def get_latest_health_records(self) -> Dict[str, ServiceHealthRecord]:
        """获取最新的健康记录"""
        # 使用子查询获取每个服务的最新记录
        latest_records = {}
        
        # 获取所有服务名称
        service_names = [r[0] for r in self.db.query(ServiceHealthRecord.service_name).distinct().all()]
        
        for service_name in service_names:
            record = self.db.query(ServiceHealthRecord).filter(
                ServiceHealthRecord.service_name == service_name
            ).order_by(ServiceHealthRecord.check_time.desc()).first()
            
            if record:
                latest_records[service_name] = record
        
        return latest_records
    
    # ============ 批量操作 ============
    
    def import_configs_from_dict(self, config_dict: Dict[str, Any], 
                               change_source: str = "import") -> Tuple[int, int, List[str]]:
        """从字典导入配置"""
        created = 0
        updated = 0
        errors = []
        
        for key, data in config_dict.items():
            try:
                category_name = data.get("category", "未分类")
                # 获取或创建类别
                category = self.get_category_by_name(category_name)
                if not category:
                    category = self.create_category(name=category_name)
                
                # 检查配置是否存在
                config = self.get_config_by_key(key)
                if config:
                    # 更新配置
                    self.update_config(
                        id=config.id,
                        value=data.get("value"),
                        description=data.get("description"),
                        change_source=change_source,
                        change_notes=f"从导入更新: {data.get('source', '未知')}"
                    )
                    updated += 1
                else:
                    # 创建配置
                    value_type = data.get("type", "string")
                    # 创建新配置
                    self.create_config(
                        key=key,
                        value=data.get("value"),
                        value_type=value_type,
                        category_id=category.id,
                        description=data.get("description"),
                        default_value=data.get("default"),
                        is_system=data.get("is_system", False),
                        is_sensitive=data.get("is_sensitive", False)
                    )
                    created += 1
            except Exception as e:
                logger.error(f"导入配置失败: {key}, 错误: {str(e)}")
                errors.append(f"{key}: {str(e)}")
        
        return created, updated, errors
    
    def export_configs_to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """导出配置到字典"""
        result = {}
        categories = self.get_categories()
        
        for category in categories:
            configs = self.get_configs(category_id=category.id, include_sensitive=include_sensitive)
            for config in configs:
                value = config.value
                if config.is_encrypted and include_sensitive:
                    value = ConfigEncryption.decrypt(value)
                
                result[config.key] = {
                    "value": self._string_to_value(value, config.value_type),
                    "type": config.value_type,
                    "default": self._string_to_value(config.default_value, config.value_type) if config.default_value else None,
                    "category": category.name,
                    "description": config.description,
                    "is_system": config.is_system,
                    "is_sensitive": config.is_sensitive,
                    "is_overridden": config.is_overridden,
                    "override_source": config.override_source
                }
        
        return result
    
    # ============ 初始化功能 ============
    
    def sync_from_settings(self, settings_obj, prefix: str = "", only_missing: bool = True) -> Tuple[int, int]:
        """从设置对象同步配置到数据库"""
        created = 0
        updated = 0
        
        # 获取或创建系统配置类别
        system_category = self.get_category_by_name("系统配置")
        if not system_category:
            system_category = self.create_category(
                name="系统配置",
                description="系统基础配置项",
                is_system=True,
                order=0
            )
        
        # 从设置对象提取配置项
        for attr_name in dir(settings_obj):
            # 跳过私有属性和方法
            if attr_name.startswith('_') or callable(getattr(settings_obj, attr_name)):
                continue
            
            value = getattr(settings_obj, attr_name)
            # 跳过非基础类型值
            if not isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                continue
            
            # 构建配置键
            key = f"{prefix}{attr_name}" if prefix else attr_name
            
            # 判断值类型
            if isinstance(value, bool):
                value_type = "boolean"
            elif isinstance(value, (int, float)):
                value_type = "number"
            elif isinstance(value, (list, dict)):
                value_type = "json"
            else:
                value_type = "string"
            
            # 检查是否敏感配置（包含关键词）
            is_sensitive = any(kw in key.lower() for kw in 
                            ["password", "secret", "key", "token", "api_key"])
            
            # 检查是否已存在
            existing_config = self.get_config_by_key(key)
            if existing_config:
                if not only_missing:
                    # 更新配置
                    self.update_config(
                        id=existing_config.id,
                        value=value,
                        change_source="system",
                        change_notes="从设置对象同步"
                    )
                    updated += 1
            else:
                # 创建配置
                self.create_config(
                    key=key,
                    value=value,
                    value_type=value_type,
                    category_id=system_category.id,
                    description=f"从设置自动导入: {attr_name}",
                    is_system=True,
                    is_sensitive=is_sensitive
                )
                created += 1
        
        return created, updated
    
    def initialize_default_categories(self) -> List[ConfigCategory]:
        """初始化默认配置类别"""
        default_categories = [
            {"name": "系统配置", "description": "系统基础配置", "is_system": True, "order": 0},
            {"name": "数据库配置", "description": "数据库连接配置", "is_system": True, "order": 1},
            {"name": "安全配置", "description": "安全和认证配置", "is_system": True, "order": 2},
            {"name": "服务配置", "description": "服务连接配置", "is_system": True, "order": 3},
            {"name": "模型配置", "description": "AI模型配置", "is_system": True, "order": 4},
            {"name": "框架配置", "description": "AI框架配置", "is_system": True, "order": 5},
            {"name": "接口配置", "description": "API接口配置", "is_system": False, "order": 6},
            {"name": "自定义配置", "description": "用户自定义配置", "is_system": False, "order": 7},
        ]
        
        created_categories = []
        for cat_data in default_categories:
            cat = self.get_category_by_name(cat_data["name"])
            if not cat:
                cat = self.create_category(
                    name=cat_data["name"],
                    description=cat_data["description"],
                    is_system=cat_data["is_system"],
                    order=cat_data["order"]
                )
            created_categories.append(cat)
        
        return created_categories
    
    # ============ 工具方法 ============
    
    def _value_to_string(self, value: Any, value_type: str) -> str:
        """将值转换为字符串存储"""
        if value is None:
            return None
            
        if value_type == "json" and isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        else:
            return str(value)
    
    def _string_to_value(self, string_value: str, value_type: str) -> Any:
        """将字符串值转换为实际类型"""
        if string_value is None:
            return None
            
        try:
            if value_type == "number":
                if "." in string_value:
                    return float(string_value)
                return int(string_value)
            elif value_type == "boolean":
                return string_value.lower() in ["true", "yes", "1"]
            elif value_type == "json":
                return json.loads(string_value)
            else:  # string
                return string_value
        except (ValueError, json.JSONDecodeError):
            return string_value
