from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.future import select
from app.models.agent_definition import AgentDefinition, agent_tool_association
from app.models.tool import Tool

class AgentDefinitionRepository:
    """智能体定义仓库"""
    
    async def create(self, data: Dict[str, Any], db: Session) -> AgentDefinition:
        """创建智能体定义
        
        Args:
            data: 创建数据
            db: 数据库会话
            
        Returns:
            AgentDefinition: 创建的智能体定义
        """
        # 提取工具配置
        tools_data = data.pop("tools", []) if "tools" in data else []
        
        # 创建智能体定义
        definition = AgentDefinition(**data)
        db.add(definition)
        await db.flush()
        
        # 添加工具关联
        if tools_data:
            await self._add_tools_to_definition(definition, tools_data, db)
        
        await db.commit()
        await db.refresh(definition)
        return definition
    
    async def get_by_id(self, definition_id: int, db: Session) -> Optional[AgentDefinition]:
        """通过ID获取智能体定义
        
        Args:
            definition_id: 智能体定义ID
            db: 数据库会话
            
        Returns:
            Optional[AgentDefinition]: 智能体定义，不存在则返回None
        """
        query = select(AgentDefinition).options(
            joinedload(AgentDefinition.tools)
        ).where(AgentDefinition.id == definition_id)
        
        result = await db.execute(query)
        return result.scalars().first()
    
    async def get_all(
        self, db: Session, skip: int = 0, limit: int = 100, 
        creator_id: Optional[int] = None, is_public: Optional[bool] = None,
        is_system: Optional[bool] = None
    ) -> List[AgentDefinition]:
        """获取所有智能体定义
        
        Args:
            db: 数据库会话
            skip: 跳过数量
            limit: 限制数量
            creator_id: 创建者ID筛选
            is_public: 是否公开筛选
            is_system: 是否系统筛选
            
        Returns:
            List[AgentDefinition]: 智能体定义列表
        """
        query = select(AgentDefinition).options(
            joinedload(AgentDefinition.tools)
        )
        
        # 应用筛选条件
        if creator_id is not None:
            query = query.where(AgentDefinition.creator_id == creator_id)
        if is_public is not None:
            query = query.where(AgentDefinition.is_public == is_public)
        if is_system is not None:
            query = query.where(AgentDefinition.is_system == is_system)
            
        # 应用分页
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def update(
        self, definition_id: int, data: Dict[str, Any], db: Session
    ) -> Optional[AgentDefinition]:
        """更新智能体定义
        
        Args:
            definition_id: 智能体定义ID
            data: 更新数据
            db: 数据库会话
            
        Returns:
            Optional[AgentDefinition]: 更新后的智能体定义，不存在则返回None
        """
        # 获取要更新的定义
        definition = await self.get_by_id(definition_id, db)
        if not definition:
            return None
            
        # 提取工具配置
        tools_data = data.pop("tools", None)
        
        # 更新基本字段
        for key, value in data.items():
            if hasattr(definition, key):
                setattr(definition, key, value)
                
        # 如果提供了工具数据，更新工具关联
        if tools_data is not None:
            # 清除现有工具关联
            await db.execute(
                agent_tool_association.delete().where(
                    agent_tool_association.c.agent_definition_id == definition_id
                )
            )
            
            # 添加新的工具关联
            await self._add_tools_to_definition(definition, tools_data, db)
        
        await db.commit()
        await db.refresh(definition)
        return definition
    
    async def delete(self, definition_id: int, db: Session) -> bool:
        """删除智能体定义
        
        Args:
            definition_id: 智能体定义ID
            db: 数据库会话
            
        Returns:
            bool: 是否成功删除
        """
        definition = await self.get_by_id(definition_id, db)
        if not definition:
            return False
            
        await db.delete(definition)
        await db.commit()
        return True
    
    async def _add_tools_to_definition(
        self, definition: AgentDefinition, tools_data: List[Dict[str, Any]], db: Session
    ) -> None:
        """为智能体定义添加工具
        
        Args:
            definition: 智能体定义
            tools_data: 工具配置列表
            db: 数据库会话
        """
        for i, tool_data in enumerate(tools_data):
            tool_id = tool_data.get("id")
            if not tool_id:
                continue
                
            # 查询工具是否存在
            tool = await db.get(Tool, tool_id)
            if not tool:
                continue
                
            # 创建关联
            order = tool_data.get("order", i)
            condition = tool_data.get("condition")
            parameters = tool_data.get("parameters")
            
            # 添加到关联表
            await db.execute(
                agent_tool_association.insert().values(
                    agent_definition_id=definition.id,
                    tool_id=tool_id,
                    order=order,
                    condition=condition,
                    parameters=parameters
                )
            )
