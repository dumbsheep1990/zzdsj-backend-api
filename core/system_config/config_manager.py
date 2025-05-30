"""
系统配置管理核心业务逻辑
提供配置的业务层操作，封装数据访问和业务规则
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.system_config import SystemConfig, ConfigCategory, ConfigHistory, ServiceHealthRecord
from app.repositories.system_config_repository import SystemConfigRepository
from .config_validator import ConfigValidator
from .config_encryption import ConfigEncryption

logger = logging.getLogger(__name__)


class SystemConfigManager:
    """系统配置管理器 - Core层业务逻辑"""
    
    def __init__(self, db: Session):
        """初始化配置管理器"""
        self.db = db
        self.repository = SystemConfigRepository(db)
        self.validator = ConfigValidator()
        self.encryption = ConfigEncryption()
    
    # ============ 配置类别业务逻辑 ============
    
    async def create_category(self, name: str, description: str = None, 
                            is_system: bool = False, order: int = 0) -> Dict[str, Any]:
        """创建配置类别 - 业务逻辑层"""
        try:
            # 业务规则验证
            if await self.repository.get_category_by_name(name):
                return {
                    "success": False,
                    "error": f"配置类别名称 '{name}' 已存在",
                    "error_code": "CATEGORY_EXISTS"
                }
            
            # 名称验证
            if not self.validator.validate_category_name(name):
                return {
                    "success": False,
                    "error": "配置类别名称格式无效",
                    "error_code": "INVALID_NAME"
                }
            
            # 创建类别
            category = await self.repository.create_category(name, description, is_system, order)
            
            return {
                "success": True,
                "data": {
                    "id": category.id,
                    "name": category.name,
                    "description": category.description,
                    "is_system": category.is_system,
                    "order": category.order
                }
            }
            
        except Exception as e:
            logger.error(f"创建配置类别失败: {str(e)}")
            return {
                "success": False,
                "error": f"创建配置类别失败: {str(e)}",
                "error_code": "CREATE_FAILED"
            }
    
    async def get_categories(self) -> Dict[str, Any]:
        """获取所有配置类别"""
        try:
            categories = await self.repository.get_categories()
            
            return {
                "success": True,
                "data": [
                    {
                        "id": cat.id,
                        "name": cat.name,
                        "description": cat.description,
                        "is_system": cat.is_system,
                        "order": cat.order,
                        "config_count": await self.repository.get_category_config_count(cat.id)
                    }
                    for cat in categories
                ]
            }
            
        except Exception as e:
            logger.error(f"获取配置类别失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取配置类别失败: {str(e)}",
                "error_code": "GET_FAILED"
            }
    
    async def update_category(self, category_id: str, **updates) -> Dict[str, Any]:
        """更新配置类别 - 业务逻辑层"""
        try:
            category = await self.repository.get_category_by_id(category_id)
            if not category:
                return {
                    "success": False,
                    "error": "配置类别不存在",
                    "error_code": "CATEGORY_NOT_FOUND"
                }
            
            # 系统类别的业务规则
            if category.is_system and "name" in updates:
                return {
                    "success": False,
                    "error": "系统类别名称不允许修改",
                    "error_code": "SYSTEM_CATEGORY_READONLY"
                }
            
            # 名称重复检查
            if "name" in updates:
                existing = await self.repository.get_category_by_name(updates["name"])
                if existing and existing.id != category_id:
                    return {
                        "success": False,
                        "error": f"配置类别名称 '{updates['name']}' 已存在",
                        "error_code": "CATEGORY_EXISTS"
                    }
            
            # 执行更新
            updated_category = await self.repository.update_category(category_id, **updates)
            
            return {
                "success": True,
                "data": {
                    "id": updated_category.id,
                    "name": updated_category.name,
                    "description": updated_category.description,
                    "is_system": updated_category.is_system,
                    "order": updated_category.order
                }
            }
            
        except Exception as e:
            logger.error(f"更新配置类别失败: {str(e)}")
            return {
                "success": False,
                "error": f"更新配置类别失败: {str(e)}",
                "error_code": "UPDATE_FAILED"
            }
    
    # ============ 配置项业务逻辑 ============
    
    async def create_config(self, key: str, value: Any, value_type: str, category_id: str,
                          description: str = None, default_value: Any = None,
                          is_system: bool = False, is_sensitive: bool = False,
                          validation_rules: Dict = None, visible_level: str = "all") -> Dict[str, Any]:
        """创建配置项 - 业务逻辑层"""
        try:
            # 业务规则验证
            if await self.repository.get_config_by_key(key):
                return {
                    "success": False,
                    "error": f"配置键 '{key}' 已存在",
                    "error_code": "CONFIG_EXISTS"
                }
            
            # 验证类别存在
            category = await self.repository.get_category_by_id(category_id)
            if not category:
                return {
                    "success": False,
                    "error": "配置类别不存在",
                    "error_code": "CATEGORY_NOT_FOUND"
                }
            
            # 配置键格式验证
            if not self.validator.validate_config_key(key):
                return {
                    "success": False,
                    "error": "配置键格式无效",
                    "error_code": "INVALID_KEY"
                }
            
            # 值类型验证
            if not self.validator.validate_value_type(value, value_type):
                return {
                    "success": False,
                    "error": f"配置值与类型 '{value_type}' 不匹配",
                    "error_code": "VALUE_TYPE_MISMATCH"
                }
            
            # 验证规则检查
            if validation_rules:
                validation_result = self.validator.validate_config_value(value, validation_rules)
                if not validation_result["valid"]:
                    return {
                        "success": False,
                        "error": f"配置值验证失败: {validation_result['error']}",
                        "error_code": "VALIDATION_FAILED"
                    }
            
            # 创建配置
            config = await self.repository.create_config(
                key=key,
                value=value,
                value_type=value_type,
                category_id=category_id,
                description=description,
                default_value=default_value,
                is_system=is_system,
                is_sensitive=is_sensitive,
                validation_rules=validation_rules,
                visible_level=visible_level
            )
            
            return {
                "success": True,
                "data": {
                    "id": config.id,
                    "key": config.key,
                    "value": self._safe_get_value(config),
                    "value_type": config.value_type,
                    "category_id": config.category_id,
                    "description": config.description,
                    "is_system": config.is_system,
                    "is_sensitive": config.is_sensitive
                }
            }
            
        except Exception as e:
            logger.error(f"创建配置项失败: {str(e)}")
            return {
                "success": False,
                "error": f"创建配置项失败: {str(e)}",
                "error_code": "CREATE_FAILED"
            }
    
    async def get_config_value(self, key: str, default: Any = None) -> Any:
        """获取配置值 - 业务逻辑层"""
        try:
            config = await self.repository.get_config_by_key(key)
            if not config:
                return default
            
            # 解密和类型转换
            value = self._get_decrypted_value(config)
            return self._convert_value_type(value, config.value_type, default)
            
        except Exception as e:
            logger.error(f"获取配置值失败: {key}, 错误: {str(e)}")
            return default
    
    async def update_config_value(self, key: str, value: Any, 
                                change_source: str = "api", changed_by: str = None,
                                change_notes: str = None) -> Dict[str, Any]:
        """更新配置值 - 业务逻辑层"""
        try:
            config = await self.repository.get_config_by_key(key)
            if not config:
                return {
                    "success": False,
                    "error": f"配置项 '{key}' 不存在",
                    "error_code": "CONFIG_NOT_FOUND"
                }
            
            # 值类型验证
            if not self.validator.validate_value_type(value, config.value_type):
                return {
                    "success": False,
                    "error": f"配置值与类型 '{config.value_type}' 不匹配",
                    "error_code": "VALUE_TYPE_MISMATCH"
                }
            
            # 验证规则检查
            if config.validation_rules:
                validation_result = self.validator.validate_config_value(value, config.validation_rules)
                if not validation_result["valid"]:
                    return {
                        "success": False,
                        "error": f"配置值验证失败: {validation_result['error']}",
                        "error_code": "VALIDATION_FAILED"
                    }
            
            # 记录旧值用于历史记录
            old_value = self._get_decrypted_value(config)
            
            # 执行更新
            updated_config = await self.repository.update_config(
                config.id,
                value=value,
                change_source=change_source,
                changed_by=changed_by,
                change_notes=change_notes
            )
            
            return {
                "success": True,
                "data": {
                    "id": updated_config.id,
                    "key": updated_config.key,
                    "old_value": old_value,
                    "new_value": self._safe_get_value(updated_config),
                    "changed_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"更新配置值失败: {str(e)}")
            return {
                "success": False,
                "error": f"更新配置值失败: {str(e)}",
                "error_code": "UPDATE_FAILED"
            }
    
    # ============ 批量操作业务逻辑 ============
    
    async def import_configs(self, config_dict: Dict[str, Any], 
                           change_source: str = "import") -> Dict[str, Any]:
        """导入配置 - 业务逻辑层"""
        try:
            results = {
                "created": 0,
                "updated": 0,
                "errors": [],
                "success": True
            }
            
            for key, data in config_dict.items():
                try:
                    # 获取或创建类别
                    category_name = data.get("category", "导入配置")
                    category = await self._ensure_category(category_name)
                    
                    # 检查配置是否存在
                    existing_config = await self.repository.get_config_by_key(key)
                    
                    if existing_config:
                        # 更新现有配置
                        update_result = await self.update_config_value(
                            key=key,
                            value=data.get("value"),
                            change_source=change_source,
                            change_notes=f"从导入更新: {data.get('source', '未知')}"
                        )
                        
                        if update_result["success"]:
                            results["updated"] += 1
                        else:
                            results["errors"].append(f"{key}: {update_result['error']}")
                    else:
                        # 创建新配置
                        create_result = await self.create_config(
                            key=key,
                            value=data.get("value"),
                            value_type=data.get("type", "string"),
                            category_id=category.id,
                            description=data.get("description"),
                            default_value=data.get("default"),
                            is_system=data.get("is_system", False),
                            is_sensitive=data.get("is_sensitive", False)
                        )
                        
                        if create_result["success"]:
                            results["created"] += 1
                        else:
                            results["errors"].append(f"{key}: {create_result['error']}")
                            
                except Exception as e:
                    results["errors"].append(f"{key}: {str(e)}")
            
            if results["errors"]:
                results["success"] = False
            
            return results
            
        except Exception as e:
            logger.error(f"导入配置失败: {str(e)}")
            return {
                "success": False,
                "error": f"导入配置失败: {str(e)}",
                "error_code": "IMPORT_FAILED"
            }
    
    async def export_configs(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """导出配置 - 业务逻辑层"""
        try:
            categories = await self.repository.get_categories()
            result = {}
            
            for category in categories:
                configs = await self.repository.get_configs_by_category(
                    category.id, 
                    include_sensitive=include_sensitive
                )
                
                for config in configs:
                    value = self._get_decrypted_value(config) if include_sensitive else self._safe_get_value(config)
                    
                    result[config.key] = {
                        "value": self._convert_value_type(value, config.value_type),
                        "type": config.value_type,
                        "default": self._convert_value_type(config.default_value, config.value_type) if config.default_value else None,
                        "category": category.name,
                        "description": config.description,
                        "is_system": config.is_system,
                        "is_sensitive": config.is_sensitive,
                        "is_overridden": config.is_overridden,
                        "override_source": config.override_source
                    }
            
            return {
                "success": True,
                "data": result
            }
            
        except Exception as e:
            logger.error(f"导出配置失败: {str(e)}")
            return {
                "success": False,
                "error": f"导出配置失败: {str(e)}",
                "error_code": "EXPORT_FAILED"
            }
    
    # ============ 健康监控业务逻辑 ============
    
    async def record_service_health(self, service_name: str, status: bool,
                                  response_time_ms: int = None, 
                                  error_message: str = None,
                                  details: Dict = None) -> Dict[str, Any]:
        """记录服务健康状态 - 业务逻辑层"""
        try:
            # 业务规则验证
            if not self.validator.validate_service_name(service_name):
                return {
                    "success": False,
                    "error": "服务名称格式无效",
                    "error_code": "INVALID_SERVICE_NAME"
                }
            
            record = await self.repository.create_health_record(
                service_name=service_name,
                status=status,
                response_time_ms=response_time_ms,
                error_message=error_message,
                details=details
            )
            
            return {
                "success": True,
                "data": {
                    "id": record.id,
                    "service_name": record.service_name,
                    "status": record.status,
                    "check_time": record.check_time.isoformat(),
                    "response_time_ms": record.response_time_ms
                }
            }
            
        except Exception as e:
            logger.error(f"记录服务健康状态失败: {str(e)}")
            return {
                "success": False,
                "error": f"记录服务健康状态失败: {str(e)}",
                "error_code": "RECORD_FAILED"
            }
    
    async def get_system_health_summary(self) -> Dict[str, Any]:
        """获取系统健康状态摘要 - 业务逻辑层"""
        try:
            latest_records = await self.repository.get_latest_health_records()
            
            summary = {
                "total_services": len(latest_records),
                "healthy_services": 0,
                "unhealthy_services": 0,
                "services": {},
                "overall_status": "healthy"
            }
            
            for service_name, record in latest_records.items():
                if record.status:
                    summary["healthy_services"] += 1
                else:
                    summary["unhealthy_services"] += 1
                
                summary["services"][service_name] = {
                    "status": "healthy" if record.status else "unhealthy",
                    "last_check": record.check_time.isoformat(),
                    "response_time_ms": record.response_time_ms,
                    "error_message": record.error_message
                }
            
            # 计算整体状态
            if summary["unhealthy_services"] > 0:
                if summary["unhealthy_services"] >= summary["total_services"] * 0.5:
                    summary["overall_status"] = "critical"
                else:
                    summary["overall_status"] = "warning"
            
            return {
                "success": True,
                "data": summary
            }
            
        except Exception as e:
            logger.error(f"获取系统健康状态摘要失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取系统健康状态摘要失败: {str(e)}",
                "error_code": "GET_HEALTH_FAILED"
            }
    
    # ============ 私有辅助方法 ============
    
    def _get_decrypted_value(self, config: SystemConfig) -> str:
        """获取解密后的配置值"""
        if config.is_encrypted:
            return self.encryption.decrypt(config.value)
        return config.value
    
    def _safe_get_value(self, config: SystemConfig) -> str:
        """安全获取配置值（敏感值用占位符）"""
        if config.is_sensitive:
            return "[敏感信息]"
        return self._get_decrypted_value(config)
    
    def _convert_value_type(self, value: str, value_type: str, default: Any = None) -> Any:
        """转换配置值类型"""
        if not value:
            return default
        
        try:
            if value_type == "number":
                if "." in value:
                    return float(value)
                return int(value)
            elif value_type == "boolean":
                return value.lower() in ["true", "yes", "1"]
            elif value_type == "json":
                return json.loads(value)
            else:  # string
                return value
        except (ValueError, json.JSONDecodeError):
            logger.error(f"配置值类型转换失败: {value} -> {value_type}")
            return default
    
    async def _ensure_category(self, category_name: str) -> ConfigCategory:
        """确保配置类别存在，不存在则创建"""
        category = await self.repository.get_category_by_name(category_name)
        if not category:
            result = await self.create_category(category_name, f"自动创建的类别: {category_name}")
            if result["success"]:
                return await self.repository.get_category_by_id(result["data"]["id"])
            else:
                raise Exception(f"创建配置类别失败: {result['error']}")
        return category 