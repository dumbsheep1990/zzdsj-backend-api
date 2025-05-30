"""
系统配置Repository层
提供系统配置相关的数据访问操作
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from datetime import datetime

from app.models.system_config import SystemConfig, ConfigCategory, ConfigHistory, ServiceHealthRecord
from .base import BaseRepository


class SystemConfigRepository(BaseRepository):
    """系统配置Repository"""
    
    def __init__(self, db: Session):
        super().__init__(db)
    
    # ============ 配置类别数据访问 ============
    
    async def get_categories(self) -> List[ConfigCategory]:
        """获取所有配置类别"""
        return self.db.query(ConfigCategory).order_by(ConfigCategory.order).all()
    
    async def get_category_by_id(self, category_id: str) -> Optional[ConfigCategory]:
        """通过ID获取配置类别"""
        return self.db.query(ConfigCategory).filter(ConfigCategory.id == category_id).first()
    
    async def get_category_by_name(self, name: str) -> Optional[ConfigCategory]:
        """通过名称获取配置类别"""
        return self.db.query(ConfigCategory).filter(ConfigCategory.name == name).first()
    
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
        self.db.flush()
        return category
    
    async def update_category(self, category_id: str, **updates) -> ConfigCategory:
        """更新配置类别"""
        category = await self.get_category_by_id(category_id)
        if not category:
            raise ValueError(f"配置类别不存在: {category_id}")
        
        for field, value in updates.items():
            if hasattr(category, field):
                setattr(category, field, value)
        
        self.db.flush()
        return category
    
    async def delete_category(self, category_id: str) -> bool:
        """删除配置类别"""
        category = await self.get_category_by_id(category_id)
        if not category:
            return False
        
        # 检查是否有关联配置
        config_count = await self.get_category_config_count(category_id)
        if config_count > 0:
            raise ValueError("不能删除包含配置项的类别")
        
        self.db.delete(category)
        self.db.flush()
        return True
    
    async def get_category_config_count(self, category_id: str) -> int:
        """获取类别下的配置项数量"""
        return self.db.query(func.count(SystemConfig.id)).filter(
            SystemConfig.category_id == category_id
        ).scalar()
    
    # ============ 配置项数据访问 ============
    
    async def get_configs_by_category(self, category_id: str, 
                                    include_sensitive: bool = False) -> List[SystemConfig]:
        """获取指定类别的配置项"""
        query = self.db.query(SystemConfig).filter(SystemConfig.category_id == category_id)
        
        if not include_sensitive:
            query = query.filter(SystemConfig.is_sensitive == False)
        
        return query.all()
    
    async def get_config_by_id(self, config_id: str) -> Optional[SystemConfig]:
        """通过ID获取配置项"""
        return self.db.query(SystemConfig).filter(SystemConfig.id == config_id).first()
    
    async def get_config_by_key(self, key: str) -> Optional[SystemConfig]:
        """通过键获取配置项"""
        return self.db.query(SystemConfig).filter(SystemConfig.key == key).first()
    
    async def create_config(self, key: str, value: Any, value_type: str, category_id: str,
                          description: str = None, default_value: Any = None,
                          is_system: bool = False, is_sensitive: bool = False,
                          validation_rules: Dict = None, visible_level: str = "all") -> SystemConfig:
        """创建配置项"""
        from core.system_config.config_encryption import ConfigEncryption
        
        # 将值转换为字符串
        str_value = self._value_to_string(value, value_type)
        str_default = self._value_to_string(default_value, value_type) if default_value is not None else None
        
        # 加密敏感数据
        is_encrypted = is_sensitive
        if is_encrypted and str_value:
            encryption = ConfigEncryption()
            str_value = encryption.encrypt(str_value)
        
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
    
    async def update_config(self, config_id: str, value: Any = None, 
                          description: str = None, is_sensitive: bool = None,
                          validation_rules: Dict = None, visible_level: str = None,
                          change_source: str = "user", changed_by: str = None,
                          change_notes: str = None) -> SystemConfig:
        """更新配置项"""
        from core.system_config.config_encryption import ConfigEncryption
        
        config = await self.get_config_by_id(config_id)
        if not config:
            raise ValueError(f"配置项不存在: {config_id}")
        
        # 记录旧值
        old_value = config.value
        if config.is_encrypted:
            encryption = ConfigEncryption()
            old_value = encryption.decrypt(config.value)
        
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
                    encryption = ConfigEncryption()
                    str_value = encryption.encrypt(str_value)
                # 如果不再敏感，解密旧值
                elif config.is_encrypted:
                    config.is_encrypted = False
            # 处理现有敏感配置
            elif config.is_encrypted:
                encryption = ConfigEncryption()
                str_value = encryption.encrypt(str_value)
            
            config.value = str_value
        
        # 更新其他字段
        if description is not None:
            config.description = description
        if validation_rules is not None:
            config.validation_rules = validation_rules
        if visible_level is not None:
            config.visible_level = visible_level
        
        # 添加历史记录
        new_value = config.value
        if config.is_encrypted:
            encryption = ConfigEncryption()
            new_value = encryption.decrypt(config.value)
        
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
    
    async def delete_config(self, config_id: str) -> bool:
        """删除配置项"""
        config = await self.get_config_by_id(config_id)
        if not config:
            return False
        
        # 系统配置不允许删除
        if config.is_system:
            raise ValueError("系统配置不允许删除")
        
        self.db.delete(config)
        self.db.flush()
        return True
    
    async def mark_config_overridden(self, key: str, source: str) -> bool:
        """标记配置被覆盖"""
        config = await self.get_config_by_key(key)
        if not config:
            return False
        
        config.is_overridden = True
        config.override_source = source
        self.db.flush()
        return True
    
    # ============ 配置历史数据访问 ============
    
    async def get_config_history(self, config_id: str, limit: int = 50) -> List[ConfigHistory]:
        """获取配置历史记录"""
        return self.db.query(ConfigHistory).filter(
            ConfigHistory.config_id == config_id
        ).order_by(ConfigHistory.created_at.desc()).limit(limit).all()
    
    async def get_recent_changes(self, days: int = 7, limit: int = 100) -> List[ConfigHistory]:
        """获取最近的配置变更"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        return self.db.query(ConfigHistory).filter(
            ConfigHistory.created_at >= cutoff_date
        ).order_by(ConfigHistory.created_at.desc()).limit(limit).all()
    
    # ============ 健康记录数据访问 ============
    
    async def create_health_record(self, service_name: str, status: bool,
                                 response_time_ms: int = None, error_message: str = None,
                                 details: Dict = None) -> ServiceHealthRecord:
        """创建服务健康记录"""
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
    
    async def get_latest_health_records(self) -> Dict[str, ServiceHealthRecord]:
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
    
    async def get_service_health_history(self, service_name: str, 
                                       hours: int = 24, limit: int = 100) -> List[ServiceHealthRecord]:
        """获取服务健康历史"""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return self.db.query(ServiceHealthRecord).filter(
            ServiceHealthRecord.service_name == service_name,
            ServiceHealthRecord.check_time >= cutoff_time
        ).order_by(ServiceHealthRecord.check_time.desc()).limit(limit).all()
    
    async def cleanup_old_health_records(self, days: int = 30) -> int:
        """清理旧的健康记录"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        count = self.db.query(ServiceHealthRecord).filter(
            ServiceHealthRecord.check_time < cutoff_date
        ).count()
        
        self.db.query(ServiceHealthRecord).filter(
            ServiceHealthRecord.check_time < cutoff_date
        ).delete()
        
        self.db.flush()
        return count
    
    # ============ 辅助方法 ============
    
    def _value_to_string(self, value: Any, value_type: str) -> str:
        """将值转换为字符串"""
        if value is None:
            return ""
        
        if value_type == "json":
            import json
            return json.dumps(value, ensure_ascii=False)
        else:
            return str(value)
    
    def _string_to_value(self, str_value: str, value_type: str) -> Any:
        """将字符串转换为指定类型的值"""
        if not str_value:
            return None
        
        try:
            if value_type == "number":
                if "." in str_value:
                    return float(str_value)
                return int(str_value)
            elif value_type == "boolean":
                return str_value.lower() in ["true", "yes", "1"]
            elif value_type == "json":
                import json
                return json.loads(str_value)
            else:  # string
                return str_value
        except (ValueError, json.JSONDecodeError):
            return str_value 