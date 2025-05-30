import uuid
from sqlalchemy import Column, String, JSON, ForeignKey, Boolean, Text, DateTime
from sqlalchemy.sql import func
from app.models.database import Base
from typing import Dict, Any, Optional

class Tool(Base):
    """工具定义模型"""
    __tablename__ = 'tools'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    function_def = Column(JSON, nullable=False)  # 函数定义(JSONSchema格式)
    implementation_type = Column(String(50), default='python')  # 实现类型(python, api, mcp, model)
    implementation = Column(Text)  # 实现代码或URL
    is_system = Column(Boolean, default=False)  # 是否系统工具
    category = Column(String(50))  # 分类
    framework = Column(String(50))  # 关联框架(llamaindex, owl, lightrag等)
    permission_level = Column(String(50), default='standard')  # 权限级别
    parameter_schema = Column(JSON)  # 参数验证模式
    version = Column(String(20), default='1.0.0')  # 版本
    
    # 新增缺失的字段
    tool_type = Column(String(50), comment="工具类型")
    module_path = Column(Text, comment="模块路径")
    class_name = Column(String(100), comment="类名称")
    
    # 保留有用的扩展字段
    creator_id = Column(String(36), ForeignKey('users.id'))
    tags = Column(JSON)  # 工具标签
    input_format = Column(JSON)  # 输入格式定义(可选)
    output_format = Column(JSON)  # 输出格式定义(可选)
    
    # 统一使用DateTime类型并自动生成时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "function_def": self.function_def,
            "implementation_type": self.implementation_type,
            "implementation": self.implementation,
            "tool_type": self.tool_type,
            "module_path": self.module_path,
            "class_name": self.class_name,
            "creator_id": self.creator_id,
            "is_system": self.is_system,
            "category": self.category,
            "framework": self.framework,
            "permission_level": self.permission_level,
            "parameter_schema": self.parameter_schema,
            "version": self.version,
            "input_format": self.input_format,
            "output_format": self.output_format,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
