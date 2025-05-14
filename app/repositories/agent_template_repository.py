from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from app.models.agent_template import AgentTemplate

class AgentTemplateRepository:
    """智能体模板仓库"""
    
    async def create(self, data: Dict[str, Any], db: Session) -> AgentTemplate:
        """创建智能体模板
        
        Args:
            data: 创建数据
            db: 数据库会话
            
        Returns:
            AgentTemplate: 创建的智能体模板
        """
        template = AgentTemplate(**data)
        db.add(template)
        await db.commit()
        await db.refresh(template)
        return template
    
    async def get_by_id(self, template_id: int, db: Session) -> Optional[AgentTemplate]:
        """通过ID获取智能体模板
        
        Args:
            template_id: 模板ID
            db: 数据库会话
            
        Returns:
            Optional[AgentTemplate]: 智能体模板，不存在则返回None
        """
        query = select(AgentTemplate).where(AgentTemplate.id == template_id)
        result = await db.execute(query)
        return result.scalars().first()
    
    async def get_all(
        self, db: Session, skip: int = 0, limit: int = 100, 
        creator_id: Optional[int] = None, is_system: Optional[bool] = None,
        category: Optional[str] = None, base_agent_type: Optional[str] = None
    ) -> List[AgentTemplate]:
        """获取所有智能体模板
        
        Args:
            db: 数据库会话
            skip: 跳过数量
            limit: 限制数量
            creator_id: 创建者ID筛选
            is_system: 是否系统模板筛选
            category: 分类筛选
            base_agent_type: 基础智能体类型筛选
            
        Returns:
            List[AgentTemplate]: 智能体模板列表
        """
        query = select(AgentTemplate)
        
        # 应用筛选条件
        if creator_id is not None:
            query = query.where(AgentTemplate.creator_id == creator_id)
        if is_system is not None:
            query = query.where(AgentTemplate.is_system == is_system)
        if category is not None:
            query = query.where(AgentTemplate.category == category)
        if base_agent_type is not None:
            query = query.where(AgentTemplate.base_agent_type == base_agent_type)
            
        # 应用分页
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def update(
        self, template_id: int, data: Dict[str, Any], db: Session
    ) -> Optional[AgentTemplate]:
        """更新智能体模板
        
        Args:
            template_id: 模板ID
            data: 更新数据
            db: 数据库会话
            
        Returns:
            Optional[AgentTemplate]: 更新后的智能体模板，不存在则返回None
        """
        template = await self.get_by_id(template_id, db)
        if not template:
            return None
            
        for key, value in data.items():
            if hasattr(template, key):
                setattr(template, key, value)
                
        await db.commit()
        await db.refresh(template)
        return template
    
    async def delete(self, template_id: int, db: Session) -> bool:
        """删除智能体模板
        
        Args:
            template_id: 模板ID
            db: 数据库会话
            
        Returns:
            bool: 是否成功删除
        """
        template = await self.get_by_id(template_id, db)
        if not template:
            return False
            
        await db.delete(template)
        await db.commit()
        return True
