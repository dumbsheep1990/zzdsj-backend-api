"""
OWL框架工具存储库
处理OWL框架工具和工具包的数据访问
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete

from app.models.owl_tool import OwlTool, OwlToolkit

class OwlToolRepository:
    """OWL框架工具存储库"""
    
    async def create(self, tool_data: Dict[str, Any], db: Session) -> OwlTool:
        """创建工具
        
        Args:
            tool_data: 工具数据
            db: 数据库会话
            
        Returns:
            OwlTool: 创建的工具实例
        """
        tool = OwlTool(**tool_data)
        db.add(tool)
        await db.commit()
        await db.refresh(tool)
        return tool
    
    async def get_by_id(self, tool_id: str, db: Session) -> Optional[OwlTool]:
        """通过ID获取工具
        
        Args:
            tool_id: 工具ID
            db: 数据库会话
            
        Returns:
            Optional[OwlTool]: 获取的工具实例或None
        """
        query = select(OwlTool).where(OwlTool.id == tool_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str, db: Session) -> Optional[OwlTool]:
        """通过名称获取工具
        
        Args:
            name: 工具名称
            db: 数据库会话
            
        Returns:
            Optional[OwlTool]: 获取的工具实例或None
        """
        query = select(OwlTool).where(OwlTool.name == name)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_all(self, skip: int = 0, limit: int = 100, db: Session = None) -> List[OwlTool]:
        """获取工具列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            db: 数据库会话
            
        Returns:
            List[OwlTool]: 工具列表
        """
        query = select(OwlTool).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def list_by_toolkit(self, toolkit_name: str, db: Session) -> List[OwlTool]:
        """获取指定工具包的工具列表
        
        Args:
            toolkit_name: 工具包名称
            db: 数据库会话
            
        Returns:
            List[OwlTool]: 工具列表
        """
        query = select(OwlTool).where(OwlTool.toolkit_name == toolkit_name)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def list_enabled(self, db: Session) -> List[OwlTool]:
        """获取已启用的工具列表
        
        Args:
            db: 数据库会话
            
        Returns:
            List[OwlTool]: 已启用的工具列表
        """
        query = select(OwlTool).where(OwlTool.is_enabled == True)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def update(self, tool_id: str, update_data: Dict[str, Any], db: Session) -> Optional[OwlTool]:
        """更新工具
        
        Args:
            tool_id: 工具ID
            update_data: 更新数据
            db: 数据库会话
            
        Returns:
            Optional[OwlTool]: 更新后的工具实例或None
        """
        stmt = update(OwlTool).where(OwlTool.id == tool_id).values(**update_data).returning(OwlTool)
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one_or_none()
    
    async def delete(self, tool_id: str, db: Session) -> bool:
        """删除工具
        
        Args:
            tool_id: 工具ID
            db: 数据库会话
            
        Returns:
            bool: 是否成功删除
        """
        stmt = delete(OwlTool).where(OwlTool.id == tool_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0


class OwlToolkitRepository:
    """OWL框架工具包存储库"""
    
    async def create(self, toolkit_data: Dict[str, Any], db: Session) -> OwlToolkit:
        """创建工具包
        
        Args:
            toolkit_data: 工具包数据
            db: 数据库会话
            
        Returns:
            OwlToolkit: 创建的工具包实例
        """
        toolkit = OwlToolkit(**toolkit_data)
        db.add(toolkit)
        await db.commit()
        await db.refresh(toolkit)
        return toolkit
    
    async def get_by_id(self, toolkit_id: str, db: Session) -> Optional[OwlToolkit]:
        """通过ID获取工具包
        
        Args:
            toolkit_id: 工具包ID
            db: 数据库会话
            
        Returns:
            Optional[OwlToolkit]: 获取的工具包实例或None
        """
        query = select(OwlToolkit).where(OwlToolkit.id == toolkit_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str, db: Session) -> Optional[OwlToolkit]:
        """通过名称获取工具包
        
        Args:
            name: 工具包名称
            db: 数据库会话
            
        Returns:
            Optional[OwlToolkit]: 获取的工具包实例或None
        """
        query = select(OwlToolkit).where(OwlToolkit.name == name)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_all(self, skip: int = 0, limit: int = 100, db: Session = None) -> List[OwlToolkit]:
        """获取工具包列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            db: 数据库会话
            
        Returns:
            List[OwlToolkit]: 工具包列表
        """
        query = select(OwlToolkit).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def list_enabled(self, db: Session) -> List[OwlToolkit]:
        """获取已启用的工具包列表
        
        Args:
            db: 数据库会话
            
        Returns:
            List[OwlToolkit]: 已启用的工具包列表
        """
        query = select(OwlToolkit).where(OwlToolkit.is_enabled == True)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def update(self, toolkit_id: str, update_data: Dict[str, Any], db: Session) -> Optional[OwlToolkit]:
        """更新工具包
        
        Args:
            toolkit_id: 工具包ID
            update_data: 更新数据
            db: 数据库会话
            
        Returns:
            Optional[OwlToolkit]: 更新后的工具包实例或None
        """
        stmt = update(OwlToolkit).where(OwlToolkit.id == toolkit_id).values(**update_data).returning(OwlToolkit)
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one_or_none()
    
    async def delete(self, toolkit_id: str, db: Session) -> bool:
        """删除工具包
        
        Args:
            toolkit_id: 工具包ID
            db: 数据库会话
            
        Returns:
            bool: 是否成功删除
        """
        stmt = delete(OwlToolkit).where(OwlToolkit.id == toolkit_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0
