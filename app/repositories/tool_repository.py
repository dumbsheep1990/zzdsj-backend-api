from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from app.models.tool import Tool

class ToolRepository:
    """工具仓库"""
    
    def __init__(self, db: Session):
        """初始化工具仓库
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    async def create(self, data: Dict[str, Any]) -> Tool:
        """创建工具
        
        Args:
            data: 创建数据
            
        Returns:
            Tool: 创建的工具
        """
        tool = Tool(**data)
        self.db.add(tool)
        await self.db.commit()
        await self.db.refresh(tool)
        return tool
    
    async def get_by_id(self, tool_id: int) -> Optional[Tool]:
        """通过ID获取工具
        
        Args:
            tool_id: 工具ID
            
        Returns:
            Optional[Tool]: 工具，不存在则返回None
        """
        query = select(Tool).where(Tool.id == tool_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_all(
        self, skip: int = 0, limit: int = 100, 
        creator_id: Optional[int] = None, is_system: Optional[bool] = None,
        category: Optional[str] = None, tool_type: Optional[str] = None
    ) -> List[Tool]:
        """获取所有工具
        
        Args:
            skip: 跳过数量
            limit: 限制数量
            creator_id: 创建者ID筛选
            is_system: 是否系统工具筛选
            category: 分类筛选
            tool_type: 工具类型筛选
            
        Returns:
            List[Tool]: 工具列表
        """
        query = select(Tool)
        
        # 应用筛选条件
        if creator_id is not None:
            query = query.where(Tool.creator_id == creator_id)
        if is_system is not None:
            query = query.where(Tool.is_system == is_system)
        if category is not None:
            query = query.where(Tool.category == category)
        if tool_type is not None:
            query = query.where(Tool.tool_type == tool_type)
            
        # 应用分页
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_name(self, name: str) -> Optional[Tool]:
        """通过名称获取工具
        
        Args:
            name: 工具名称
            
        Returns:
            Optional[Tool]: 工具，不存在则返回None
        """
        query = select(Tool).where(Tool.name == name)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def list_with_filters(
        self, filters: Dict[str, Any], skip: int = 0, limit: int = 100
    ) -> List[Tool]:
        """根据过滤条件获取工具列表
        
        Args:
            filters: 过滤条件字典
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            List[Tool]: 符合条件的工具列表
        """
        query = select(Tool)
        
        # 应用过滤条件
        for key, value in filters.items():
            if hasattr(Tool, key):
                query = query.where(getattr(Tool, key) == value)
        
        # 应用分页
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def list_by_toolkit(self, toolkit_name: str) -> List[Tool]:
        """通过工具包名称获取工具列表
        
        Args:
            toolkit_name: 工具包名称
            
        Returns:
            List[Tool]: 属于该工具包的工具列表
        """
        query = select(Tool).where(Tool.category == toolkit_name)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update(
        self, tool_id: int, data: Dict[str, Any]
    ) -> Optional[Tool]:
        """更新工具
        
        Args:
            tool_id: 工具ID
            data: 更新数据
            
        Returns:
            Optional[Tool]: 更新后的工具，不存在则返回None
        """
        tool = await self.get_by_id(tool_id)
        if not tool:
            return None
            
        for key, value in data.items():
            if hasattr(tool, key):
                setattr(tool, key, value)
                
        await self.db.commit()
        await self.db.refresh(tool)
        return tool
    
    async def delete(self, tool_id: int) -> bool:
        """删除工具
        
        Args:
            tool_id: 工具ID
            
        Returns:
            bool: 是否成功删除
        """
        tool = await self.get_by_id(tool_id)
        if not tool:
            return False
            
        await self.db.delete(tool)
        await self.db.commit()
        return True
    
    async def search_by_tags(
        self, tags: List[str], skip: int = 0, limit: int = 100
    ) -> List[Tool]:
        """通过标签搜索工具
        
        Args:
            tags: 标签列表
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            List[Tool]: 符合条件的工具列表
        """
        # 注意：这里使用JSON包含操作符，具体实现可能需要根据数据库类型调整
        query = select(Tool).where(Tool.tags.contains(tags))
        
        # 应用分页
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
