"""
系统配置持久化存储模型
"""
from sqlalchemy import Column, String, Text, JSON, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.core.database import Base
import uuid

class ConfigCategory(Base):
    """配置类别"""
    __tablename__ = "config_categories"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)  # 类别名称
    description = Column(Text, nullable=True)  # 类别描述
    order = Column(Integer, default=0)  # 排序
    is_system = Column(Boolean, default=False)  # 是否系统类别（不可删除）
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    configs = relationship("SystemConfig", back_populates="category", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ConfigCategory {self.name}>"


class SystemConfig(Base):
    """系统配置项"""
    __tablename__ = "system_configs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String(255), nullable=False, unique=True)  # 配置键
    value = Column(Text, nullable=True)  # 配置值
    value_type = Column(String(50), nullable=False)  # 值类型: string, number, boolean, json
    default_value = Column(Text, nullable=True)  # 默认值
    category_id = Column(String(36), ForeignKey("config_categories.id"), nullable=False)
    description = Column(Text, nullable=True)  # 配置描述
    is_system = Column(Boolean, default=False)  # 是否系统配置（不可删除）
    is_sensitive = Column(Boolean, default=False)  # 是否敏感信息（如密钥）
    is_encrypted = Column(Boolean, default=False)  # 是否加密存储
    validation_rules = Column(JSON, nullable=True)  # 验证规则
    is_overridden = Column(Boolean, default=False)  # 是否被配置文件或环境变量覆盖
    override_source = Column(String(255), nullable=True)  # 覆盖来源：file, env
    visible_level = Column(String(50), default="all")  # 可见级别: all, admin, system
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    category = relationship("ConfigCategory", back_populates="configs")
    history = relationship("ConfigHistory", back_populates="config", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SystemConfig {self.key}>"


class ConfigHistory(Base):
    """配置修改历史"""
    __tablename__ = "config_history"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    config_id = Column(String(36), ForeignKey("system_configs.id"), nullable=False)
    old_value = Column(Text, nullable=True)  # 修改前的值
    new_value = Column(Text, nullable=True)  # 修改后的值
    change_source = Column(String(50), nullable=False)  # 修改来源: user, system, import, startup
    changed_by = Column(String(100), nullable=True)  # 修改人
    change_notes = Column(Text, nullable=True)  # 修改备注
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    config = relationship("SystemConfig", back_populates="history")
    
    def __repr__(self):
        return f"<ConfigHistory {self.id}>"


class ServiceHealthRecord(Base):
    """服务健康状态记录"""
    __tablename__ = "service_health_records"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    service_name = Column(String(100), nullable=False)  # 服务名称
    status = Column(Boolean, default=False)  # 状态: True=健康, False=不健康
    check_time = Column(DateTime, server_default=func.now())  # 检查时间
    response_time_ms = Column(Integer, nullable=True)  # 响应时间(毫秒)
    error_message = Column(Text, nullable=True)  # 错误信息
    details = Column(JSON, nullable=True)  # 详细信息
    
    def __repr__(self):
        return f"<ServiceHealthRecord {self.service_name} @ {self.check_time}>"
