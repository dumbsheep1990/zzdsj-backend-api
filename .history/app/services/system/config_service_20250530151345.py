"""
系统配置服务 - 管理系统配置的持久化存储和操作
重构版本：调用core层业务逻辑，符合分层架构原则
"""
from app.utils.service_decorators import register_service
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.orm import Session

# 导入core层业务逻辑
from core.system_config import SystemConfigManager

# 导入模型类型（仅用于类型提示）
from app.models.system_config import SystemConfig, ConfigCategory, ConfigHistory, ServiceHealthRecord

logger = logging.getLogger(__name__)


@register_service(service_type="system-config", priority="critical", description="系统配置管理服务")
class SystemConfigService:
    """系统配置服务 - Services层，调用Core层业务逻辑"""
    
    def __init__(self, db: Session):
        """初始化配置服务"""
        self.db = db
        # 使用core层的SystemConfigManager
        self.config_manager = SystemConfigManager(db)
    
    # ============ 配置类别管理 ============
    
    async def get_categories(self) -> List[Dict[str, Any]]:
        """获取所有配置类别"""
        result = await self.config_manager.get_categories()
        if result["success"]:
            return result["data"]
        else:
            logger.error(f"获取配置类别失败: {result.get('error')}")
            return []
    
    async def get_category(self, id: str) -> Optional[Dict[str, Any]]:
        """通过ID获取配置类别"""
        categories = await self.get_categories()
        for category in categories:
            if category["id"] == id:
                return category
        return None
    
    async def get_category_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """通过名称获取配置类别"""
        categories = await self.get_categories()
        for category in categories:
            if category["name"] == name:
                return category
        return None
    
    async def create_category(self, name: str, description: str = None, 
                            is_system: bool = False, order: int = 0) -> Optional[Dict[str, Any]]:
        """创建配置类别"""
        result = await self.config_manager.create_category(
            name=name,
            description=description,
            is_system=is_system,
            order=order
        )
        if result["success"]:
            return result["data"]
        else:
            logger.error(f"创建配置类别失败: {result.get('error')}")
            return None
    
    async def update_category(self, id: str, name: str = None, description: str = None,
                            order: int = None) -> Optional[Dict[str, Any]]:
        """更新配置类别"""
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if order is not None:
            updates["order"] = order
        
        if not updates:
            return await self.get_category(id)
        
        result = await self.config_manager.update_category(id, **updates)
        if result["success"]:
            return result["data"]
        else:
            logger.error(f"更新配置类别失败: {result.get('error')}")
            return None
    
    async def delete_category(self, id: str) -> bool:
        """删除配置类别"""
        # Core层暂未实现删除方法，返回False
        logger.warning("配置类别删除功能尚未在core层实现")
        return False
    
    # ============ 配置项管理 ============
    
    async def get_configs(self, category_id: str = None, include_sensitive: bool = False) -> List[Dict[str, Any]]:
        """获取配置项列表"""
        if category_id:
            # 获取指定类别的配置项
            # Core层暂未实现按类别获取，这里需要扩展
            logger.warning("按类别获取配置功能需要扩展core层")
            return []
        else:
            # 获取所有配置项
            result = await self.config_manager.export_configs(include_sensitive=include_sensitive)
            if result["success"]:
                # 转换格式
                configs = []
                for key, data in result["data"].items():
                    configs.append({
                        "key": key,
                        "value": data["value"],
                        "value_type": data["type"],
                        "category_name": data["category"],
                        "description": data["description"],
                        "is_system": data["is_system"],
                        "is_sensitive": data["is_sensitive"],
                        "is_overridden": data["is_overridden"],
                        "override_source": data["override_source"]
                    })
                return configs
            else:
                logger.error(f"获取配置项失败: {result.get('error')}")
                return []
    
    async def get_config(self, id: str) -> Optional[Dict[str, Any]]:
        """通过ID获取配置项"""
        # Core层使用key而不是id，这里需要适配
        logger.warning("通过ID获取配置功能需要扩展core层")
        return None
    
    async def get_config_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """通过键获取配置项"""
        value = await self.config_manager.get_config_value(key)
        if value is not None:
            # 简化返回，实际应用中可能需要更多字段
            return {
                "key": key,
                "value": value
            }
        return None
    
    async def get_config_value(self, key: str, default: Any = None) -> Any:
        """获取配置值，自动转换类型"""
        return await self.config_manager.get_config_value(key, default)
    
    async def create_config(self, key: str, value: Any, value_type: str, category_id: str,
                          description: str = None, default_value: Any = None,
                          is_system: bool = False, is_sensitive: bool = False,
                          validation_rules: Dict = None, visible_level: str = "all") -> Optional[Dict[str, Any]]:
        """创建配置项"""
        result = await self.config_manager.create_config(
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
        if result["success"]:
            return result["data"]
        else:
            logger.error(f"创建配置项失败: {result.get('error')}")
            return None
    
    async def update_config(self, id: str = None, key: str = None, value: Any = None, 
                          description: str = None, is_sensitive: bool = None, 
                          validation_rules: Dict = None, visible_level: str = None, 
                          change_source: str = "user", changed_by: str = None, 
                          change_notes: str = None) -> Optional[Dict[str, Any]]:
        """更新配置项"""
        # 如果提供了key，直接使用
        if key:
            config_key = key
        else:
            # 如果只有id，需要先查找key（需要扩展core层）
            logger.warning("通过ID更新配置功能需要扩展core层")
            return None
        
        if value is not None:
            result = await self.config_manager.update_config_value(
                key=config_key,
                value=value,
                change_source=change_source,
                changed_by=changed_by,
                change_notes=change_notes
            )
            if result["success"]:
                return result["data"]
            else:
                logger.error(f"更新配置项失败: {result.get('error')}")
                return None
        
        return None
    
    async def delete_config(self, id: str) -> bool:
        """删除配置项"""
        # Core层暂未实现删除方法
        logger.warning("配置项删除功能尚未在core层实现")
        return False
    
    async def mark_config_overridden(self, key: str, source: str) -> bool:
        """标记配置被覆盖"""
        # Core层暂未实现此方法
        logger.warning("标记配置覆盖功能尚未在core层实现")
        return False
    
    # ============ 配置历史管理 ============
    
    async def get_config_history(self, config_id: str) -> List[Dict[str, Any]]:
        """获取配置历史记录"""
        # Core层暂未实现历史查询方法
        logger.warning("配置历史查询功能尚未在core层实现")
        return []
    
    # ============ 健康记录管理 ============
    
    async def save_health_record(self, service_name: str, status: bool, 
                               response_time_ms: int = None, error_message: str = None,
                               details: Dict = None) -> Optional[Dict[str, Any]]:
        """保存服务健康记录"""
        result = await self.config_manager.record_service_health(
            service_name=service_name,
            status=status,
            response_time_ms=response_time_ms,
            error_message=error_message,
            details=details
        )
        if result["success"]:
            return result["data"]
        else:
            logger.error(f"保存健康记录失败: {result.get('error')}")
            return None
    
    async def get_latest_health_records(self) -> Dict[str, Dict[str, Any]]:
        """获取最新的健康记录"""
        result = await self.config_manager.get_system_health_summary()
        if result["success"]:
            return result["data"]["services"]
        else:
            logger.error(f"获取健康记录失败: {result.get('error')}")
            return {}
    
    # ============ 批量操作 ============
    
    async def import_configs_from_dict(self, config_dict: Dict[str, Any], 
                                     change_source: str = "import") -> Tuple[int, int, List[str]]:
        """从字典导入配置"""
        result = await self.config_manager.import_configs(config_dict, change_source)
        if result["success"]:
            return result["created"], result["updated"], result["errors"]
        else:
            logger.error(f"导入配置失败: {result.get('error')}")
            return 0, 0, [result.get("error", "导入失败")]
    
    async def export_configs_to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """导出配置到字典"""
        result = await self.config_manager.export_configs(include_sensitive)
        if result["success"]:
            return result["data"]
        else:
            logger.error(f"导出配置失败: {result.get('error')}")
            return {}
    
    # ============ 初始化功能 ============
    
    async def sync_from_settings(self, settings_obj, prefix: str = "", only_missing: bool = True) -> Tuple[int, int]:
        """从设置对象同步配置到数据库"""
        created = 0
        updated = 0
        
        try:
            # 构建配置字典
            config_dict = {}
            
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
                
                # 检查是否敏感配置
                is_sensitive = any(kw in key.lower() for kw in 
                                ["password", "secret", "key", "token", "api_key"])
                
                config_dict[key] = {
                    "value": value,
                    "type": value_type,
                    "category": "系统配置",
                    "description": f"从设置自动导入: {attr_name}",
                    "is_system": True,
                    "is_sensitive": is_sensitive
                }
            
            # 导入配置
            if config_dict:
                created, updated, errors = await self.import_configs_from_dict(
                    config_dict, "system_sync"
                )
                
                if errors:
                    logger.warning(f"同步设置时发生错误: {errors}")
            
        except Exception as e:
            logger.error(f"从设置对象同步配置失败: {str(e)}")
        
        return created, updated
    
    async def initialize_default_categories(self) -> List[Dict[str, Any]]:
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
            # 检查是否已存在
            existing = await self.get_category_by_name(cat_data["name"])
            if not existing:
                category = await self.create_category(
                    name=cat_data["name"],
                    description=cat_data["description"],
                    is_system=cat_data["is_system"],
                    order=cat_data["order"]
                )
                if category:
                    created_categories.append(category)
            else:
                created_categories.append(existing)
        
        return created_categories
    
    # ============ 同步方法（兼容原有API） ============
    
    def get_categories_sync(self) -> List[Dict[str, Any]]:
        """同步获取配置类别（兼容方法）"""
        import asyncio
        return asyncio.run(self.get_categories())
    
    def get_config_value_sync(self, key: str, default: Any = None) -> Any:
        """同步获取配置值（兼容方法）"""
        import asyncio
        return asyncio.run(self.get_config_value(key, default))
    
    def create_config_sync(self, **kwargs) -> Optional[Dict[str, Any]]:
        """同步创建配置（兼容方法）"""
        import asyncio
        return asyncio.run(self.create_config(**kwargs))
