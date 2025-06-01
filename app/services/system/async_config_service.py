"""
异步系统配置服务 - 管理系统配置的持久化存储和操作
"""
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from app.models.system_config import SystemConfig, ConfigCategory, ConfigHistory, ServiceHealthRecord
from app.utils.core.config import get_config
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
        try:
            key = cls._get_encryption_key()
            f = Fernet(key)
            encrypted = f.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"加密配置值失败: {str(e)}")
            return value
    
    @classmethod
    def decrypt(cls, encrypted_value: str) -> str:
        """解密配置值"""
        try:
            key = cls._get_encryption_key()
            f = Fernet(key)
            decrypted = f.decrypt(base64.urlsafe_b64decode(encrypted_value))
            return decrypted.decode()
        except Exception as e:
            logger.error(f"解密配置值失败: {str(e)}")
            return "[解密失败]"


class AsyncSystemConfigService:
    """异步系统配置服务"""
    
    def __init__(self, db: Session):
        """初始化配置服务"""
        self.db = db
    
    # ============ 配置类别管理 ============
    
    async def get_categories(self) -> List[ConfigCategory]:
        """获取所有配置类别"""
        result = await self.db.execute(select(ConfigCategory).order_by(ConfigCategory.order))
        return result.scalars().all()
    
    async def get_category(self, id: str) -> Optional[ConfigCategory]:
        """通过ID获取配置类别"""
        result = await self.db.execute(select(ConfigCategory).filter(ConfigCategory.id == id))
        return result.scalar_one_or_none()
    
    async def get_category_by_name(self, name: str) -> Optional[ConfigCategory]:
        """通过名称获取配置类别"""
        result = await self.db.execute(select(ConfigCategory).filter(ConfigCategory.name == name))
        return result.scalar_one_or_none()
    
    async def create_category(self, name: str, description: str = None, 
                       is_system: bool = False, order: int = 0) -> ConfigCategory:
        """创建配置类别"""
        category = ConfigCategory(
            name=name, 
            description=description,
            is_system=is_system,
            order=order
        )
        self.db.add(category)
        await self.db.flush()
        return category
    
    async def update_category(self, id: str, update_data: Dict[str, Any]) -> Optional[ConfigCategory]:
        """更新配置类别"""
        category = await self.get_category(id)
        if not category:
            return None
        
        # 更新字段
        for key, value in update_data.items():
            if hasattr(category, key):
                setattr(category, key, value)
        
        await self.db.flush()
        return category
    
    async def delete_category(self, id: str) -> bool:
        """删除配置类别"""
        category = await self.get_category(id)
        if not category:
            return False
        
        # 检查是否是系统类别
        if category.is_system:
            return False
        
        # 检查类别下是否有配置项
        result = await self.db.execute(select(SystemConfig).filter(SystemConfig.category_id == id))
        if result.scalar_one_or_none():
            return False
        
        await self.db.delete(category)
        await self.db.flush()
        return True
    
    # ============ 配置项管理 ============
    
    async def get_configs(self, category_id: Optional[str] = None, include_sensitive: bool = False) -> List[SystemConfig]:
        """获取配置项列表"""
        query = select(SystemConfig)
        
        if category_id:
            query = query.filter(SystemConfig.category_id == category_id)
        
        if not include_sensitive:
            query = query.filter(SystemConfig.is_sensitive == False)
        
        result = await self.db.execute(query.order_by(SystemConfig.key))
        return result.scalars().all()
    
    async def get_config(self, id: str) -> Optional[SystemConfig]:
        """通过ID获取配置项"""
        result = await self.db.execute(select(SystemConfig).filter(SystemConfig.id == id))
        return result.scalar_one_or_none()
    
    async def get_config_by_key(self, key: str) -> Optional[SystemConfig]:
        """通过键获取配置项"""
        result = await self.db.execute(select(SystemConfig).filter(SystemConfig.key == key))
        return result.scalar_one_or_none()
    
    async def get_config_value(self, key: str, default: Any = None) -> Any:
        """获取配置值，自动转换类型"""
        config = await self.get_config_by_key(key)
        if not config:
            return default
        
        string_value = config.value
        
        # 解密敏感值
        if config.is_sensitive and string_value and not string_value.startswith('[解密失败]'):
            string_value = ConfigEncryption.decrypt(string_value)
        
        # 转换值类型
        return self._string_to_value(string_value, config.value_type)
    
    async def create_config(self, key: str, value: Any, value_type: str, category_id: str,
                     description: str = None, default_value: Any = None,
                     is_system: bool = False, is_sensitive: bool = False,
                     validation_rules: Dict = None, visible_level: str = "all") -> SystemConfig:
        """创建配置项"""
        # 转换值为字符串
        string_value = self._value_to_string(value, value_type)
        string_default = self._value_to_string(default_value, value_type) if default_value is not None else None
        
        # 加密敏感值
        if is_sensitive and string_value:
            string_value = ConfigEncryption.encrypt(string_value)
        
        config = SystemConfig(
            key=key,
            value=string_value,
            value_type=value_type,
            category_id=category_id,
            description=description,
            default_value=string_default,
            is_system=is_system,
            is_sensitive=is_sensitive,
            validation_rules=validation_rules,
            visible_level=visible_level
        )
        
        self.db.add(config)
        await self.db.flush()
        
        # 记录创建历史
        await self._add_config_history(
            config_id=config.id,
            old_value=None,
            new_value=string_value,
            change_source="system",
            changed_by=None,
            change_notes="配置项创建"
        )
        
        return config
    
    async def update_config(self, id: str, update_data: Dict[str, Any], 
                     change_notes: str = None, change_source: str = "user",
                     changed_by: str = None) -> Optional[SystemConfig]:
        """更新配置项"""
        config = await self.get_config(id)
        if not config:
            return None
        
        old_value = config.value
        
        # 更新字段
        for key, value in update_data.items():
            if key == 'value':
                # 转换值为字符串
                string_value = self._value_to_string(value, config.value_type)
                
                # 加密敏感值
                if config.is_sensitive and string_value:
                    string_value = ConfigEncryption.encrypt(string_value)
                
                config.value = string_value
            elif hasattr(config, key):
                setattr(config, key, value)
        
        await self.db.flush()
        
        # 记录更新历史
        if 'value' in update_data and old_value != config.value:
            await self._add_config_history(
                config_id=config.id,
                old_value=old_value,
                new_value=config.value,
                change_source=change_source,
                changed_by=changed_by,
                change_notes=change_notes
            )
        
        return config
    
    async def delete_config(self, id: str) -> bool:
        """删除配置项"""
        config = await self.get_config(id)
        if not config:
            return False
        
        # 系统配置不允许删除
        if config.is_system:
            return False
        
        await self.db.delete(config)
        await self.db.flush()
        return True
    
    async def mark_config_overridden(self, key: str, source: str) -> None:
        """标记配置被覆盖"""
        config = await self.get_config_by_key(key)
        if not config:
            return
        
        await self._add_config_history(
            config_id=config.id,
            old_value=config.value,
            new_value=config.value,  # 值未变
            change_source=source,
            change_notes=f"配置被{source}方式覆盖"
        )
    
    async def get_config_history(self, config_id: str) -> List[ConfigHistory]:
        """获取配置历史记录"""
        result = await self.db.execute(
            select(ConfigHistory)
            .filter(ConfigHistory.config_id == config_id)
            .order_by(ConfigHistory.changed_at.desc())
        )
        return result.scalars().all()
    
    async def _add_config_history(self, config_id: str, old_value: str, new_value: str,
                          change_source: str, changed_by: str = None,
                          change_notes: str = None) -> ConfigHistory:
        """添加配置历史记录"""
        history = ConfigHistory(
            config_id=config_id,
            old_value=old_value,
            new_value=new_value,
            change_source=change_source,
            changed_by=changed_by,
            change_notes=change_notes
        )
        self.db.add(history)
        await self.db.flush()
        return history
    
    # ============ 服务健康检查 ============
    
    async def save_health_check_results(self, results: List[Dict]) -> None:
        """保存健康检查结果"""
        for result in results:
            await self.save_health_record(
                service_name=result.get("service"),
                status=result.get("status"),
                response_time_ms=result.get("response_time_ms"),
                error_message=result.get("error"),
                details=result.get("details")
            )
    
    async def save_health_record(self, service_name: str, status: bool, 
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
        await self.db.flush()
        return record
    
    async def get_latest_health_records(self) -> Dict[str, ServiceHealthRecord]:
        """获取最新的健康记录"""
        # 获取每个服务的最新记录
        result = {}
        
        # 获取所有不同的服务名
        services_result = await self.db.execute(
            select(ServiceHealthRecord.service_name).distinct()
        )
        services = services_result.scalars().all()
        
        # 对每个服务名获取最新记录
        for service_name in services:
            record_result = await self.db.execute(
                select(ServiceHealthRecord)
                .filter(ServiceHealthRecord.service_name == service_name)
                .order_by(ServiceHealthRecord.created_at.desc())
                .limit(1)
            )
            latest_record = record_result.scalar_one_or_none()
            if latest_record:
                result[service_name] = latest_record
        
        return result
    
    # ============ 配置导入导出 ============
    
    async def import_configs(self, config_dict: Dict[str, Any]) -> Dict[str, int]:
        """从字典导入配置"""
        imported = 0
        updated = 0
        failed = 0
        
        # 处理类别
        if "categories" in config_dict:
            for cat_data in config_dict["categories"]:
                try:
                    name = cat_data.get("name")
                    if not name:
                        continue
                    
                    existing = await self.get_category_by_name(name)
                    if existing:
                        # 更新现有类别
                        update_data = {
                            "description": cat_data.get("description", existing.description),
                            "order": cat_data.get("order", existing.order),
                        }
                        await self.update_category(existing.id, update_data)
                        updated += 1
                    else:
                        # 创建新类别
                        await self.create_category(
                            name=name,
                            description=cat_data.get("description"),
                            is_system=cat_data.get("is_system", False),
                            order=cat_data.get("order", 0)
                        )
                        imported += 1
                except Exception as e:
                    logger.error(f"导入配置类别失败: {str(e)}")
                    failed += 1
        
        # 处理配置项
        if "configs" in config_dict:
            for cfg_data in config_dict["configs"]:
                try:
                    key = cfg_data.get("key")
                    if not key:
                        continue
                    
                    # 查找或创建类别
                    category_name = cfg_data.get("category")
                    category_id = None
                    
                    if category_name:
                        category = await self.get_category_by_name(category_name)
                        if not category:
                            # 创建缺失的类别
                            category = await self.create_category(name=category_name)
                        category_id = category.id
                    
                    existing = await self.get_config_by_key(key)
                    if existing:
                        # 更新现有配置
                        update_data = {
                            "value": cfg_data.get("value", existing.value),
                            "description": cfg_data.get("description", existing.description),
                        }
                        
                        if category_id:
                            update_data["category_id"] = category_id
                        
                        await self.update_config(
                            existing.id, 
                            update_data, 
                            change_notes="自动导入", 
                            change_source="import"
                        )
                        updated += 1
                    else:
                        # 创建新配置
                        if not category_id:
                            # 使用默认类别
                            default_cat = await self.get_category_by_name("其他")
                            if not default_cat:
                                default_cat = await self.create_category(name="其他")
                            category_id = default_cat.id
                        
                        await self.create_config(
                            key=key,
                            value=cfg_data.get("value"),
                            value_type=cfg_data.get("value_type", "string"),
                            category_id=category_id,
                            description=cfg_data.get("description"),
                            default_value=cfg_data.get("default_value"),
                            is_system=cfg_data.get("is_system", False),
                            is_sensitive=cfg_data.get("is_sensitive", False),
                            validation_rules=cfg_data.get("validation_rules"),
                            visible_level=cfg_data.get("visible_level", "all")
                        )
                        imported += 1
                except Exception as e:
                    logger.error(f"导入配置项失败: {str(e)}")
                    failed += 1
        
        return {
            "imported": imported,
            "updated": updated,
            "failed": failed
        }
    
    async def export_configs(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """导出配置到字典"""
        result = {
            "categories": [],
            "configs": []
        }
        
        # 导出类别
        categories = await self.get_categories()
        for cat in categories:
            result["categories"].append({
                "name": cat.name,
                "description": cat.description,
                "is_system": cat.is_system,
                "order": cat.order
            })
        
        # 导出配置项
        configs = await self.get_configs(include_sensitive=include_sensitive)
        for cfg in configs:
            # 获取类别名称
            category_name = ""
            if cfg.category_id:
                category = await self.get_category(cfg.category_id)
                if category:
                    category_name = category.name
            
            # 解密敏感值
            value = cfg.value
            if cfg.is_sensitive and include_sensitive and value and not value.startswith('[解密失败]'):
                value = ConfigEncryption.decrypt(value)
            
            config_data = {
                "key": cfg.key,
                "value": value,
                "value_type": cfg.value_type,
                "category": category_name,
                "description": cfg.description,
                "is_system": cfg.is_system,
                "is_sensitive": cfg.is_sensitive,
                "visible_level": cfg.visible_level
            }
            
            if cfg.default_value:
                config_data["default_value"] = cfg.default_value
            
            if cfg.validation_rules:
                config_data["validation_rules"] = cfg.validation_rules
            
            result["configs"].append(config_data)
        
        return result
    
    # ============ 工具方法 ============
    
    def _value_to_string(self, value: Any, value_type: str) -> str:
        """将值转换为字符串存储"""
        if value is None:
            return ""
        
        if value_type == "json" or value_type == "dict" or value_type == "list":
            if isinstance(value, str):
                # 尝试解析JSON字符串
                try:
                    json.loads(value)
                    return value
                except:
                    pass
            return json.dumps(value, ensure_ascii=False)
        
        if value_type == "bool" and not isinstance(value, str):
            return "true" if value else "false"
        
        return str(value)
    
    def _string_to_value(self, string_value: str, value_type: str) -> Any:
        """将字符串值转换为实际类型"""
        if not string_value:
            return None
        
        if value_type == "int":
            try:
                return int(string_value)
            except:
                return 0
        
        if value_type == "float":
            try:
                return float(string_value)
            except:
                return 0.0
        
        if value_type == "bool":
            return string_value.lower() in ["true", "1", "yes", "y", "on"]
        
        if value_type == "json" or value_type == "dict" or value_type == "list":
            try:
                return json.loads(string_value)
            except:
                if value_type == "list":
                    return []
                return {}
        
        # 字符串直接返回
        return string_value
