from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from app.models.tool import Tool

class ToolRepository:
    """工具仓库"""
    
    async def create(self, data: Dict[str, Any], db: Session) -> Tool:
        """创建工具
        
        Args:
            data: 创建数据
            db: 数据库会话
            
        Returns:
            Tool: 创建的工具
        """
        tool = Tool(**data)
        db.add(tool)
        await db.commit()
        await db.refresh(tool)
        return tool
    
    async def get_by_id(self, tool_id: int, db: Session) -> Optional[Tool]:
        """通过ID获取工具
        
        Args:
            tool_id: 工具ID
            db: 数据库会话
            
        Returns:
            Optional[Tool]: 工具，不存在则返回None
        """
        query = select(Tool).where(Tool.id == tool_id)
        result = await db.execute(query)
        return result.scalars().first()
    
    async def get_all(
        self, db: Session, skip: int = 0, limit: int = 100, 
        creator_id: Optional[int] = None, is_system: Optional[bool] = None,
        category: Optional[str] = None, tool_type: Optional[str] = None
    ) -> List[Tool]:
        """获取所有工具
        
        Args:
            db: 数据库会话
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
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def update(
        self, tool_id: int, data: Dict[str, Any], db: Session
    ) -> Optional[Tool]:
        """更新工具
        
        Args:
            tool_id: 工具ID
            data: 更新数据
            db: 数据库会话
            
        Returns:
            Optional[Tool]: 更新后的工具，不存在则返回None
        """
        tool = await self.get_by_id(tool_id, db)
        if not tool:
            return None
            
        for key, value in data.items():
            if hasattr(tool, key):
                setattr(tool, key, value)
                
        await db.commit()
        await db.refresh(tool)
        return tool
    
    async def delete(self, tool_id: int, db: Session) -> bool:
        """删除工具
        
        Args:
            tool_id: 工具ID
            db: 数据库会话
            
        Returns:
            bool: 是否成功删除
        """
        tool = await self.get_by_id(tool_id, db)
        if not tool:
            return False
            
        await db.delete(tool)
        await db.commit()
        return True
    
    async def search_by_tags(
        self, tags: List[str], db: Session, skip: int = 0, limit: int = 100
    ) -> List[Tool]:
        """通过标签搜索工具
        
        Args:
            tags: 标签列表
            db: 数据库会话
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            List[Tool]: 符合条件的工具列表
        """
        # 注意：这里使用JSON包含操作符，具体实现可能需要根据数据库类型调整
        query = select(Tool).where(Tool.tags.contains(tags))
        
        # 应用分页
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
