from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Boolean
from app.utils.database import Base
from datetime import datetime
from typing import Dict, Any

class Tool(Base):
    """工具定义模型"""
    __tablename__ = 'tools'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    tool_type = Column(String, nullable=False)  # 工具类型
    creator_id = Column(Integer, ForeignKey('users.id'))
    is_system = Column(Boolean, default=False)  # 是否系统工具
    
    # 实现信息
    module_path = Column(String, nullable=False)  # 模块路径
    class_name = Column(String, nullable=False)   # 类名
    
    # 参数定义
    parameter_schema = Column(JSON)  # 参数模式定义
    
    # 输入输出格式
    input_format = Column(JSON)   # 输入格式定义
    output_format = Column(JSON)  # 输出格式定义
    
    # 标签和分类
    tags = Column(JSON)  # 工具标签
    category = Column(String)  # 工具分类
    
    # 创建和更新时间
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    updated_at = Column(String, default=lambda: datetime.now().isoformat(), onupdate=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tool_type": self.tool_type,
            "creator_id": self.creator_id,
            "is_system": self.is_system,
            "module_path": self.module_path,
            "class_name": self.class_name,
            "parameter_schema": self.parameter_schema,
            "input_format": self.input_format,
            "output_format": self.output_format,
            "tags": self.tags,
            "category": self.category,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
