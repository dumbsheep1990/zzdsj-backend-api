"""
OWL框架Agent数据访问层
提供对Agent定义、链执行和消息集成相关的数据库操作
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from sqlalchemy import select, insert, update, delete, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.owl_agent import (
    OwlAgentDefinition, OwlAgentCapability, OwlAgentTool,
    OwlAgentChainDefinition, OwlAgentChainStep, 
    OwlAgentChainExecution, OwlAgentChainExecutionStep,
    OwlAgentMessage, OwlAgentMessageMapping, OwlAgentToolCall
)


class OwlAgentRepository:
    """OWL Agent数据访问仓库"""
    
    def __init__(self, db: AsyncSession):
        """初始化仓库
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    # ============ Agent定义相关方法 ============
    
    async def create_agent(self, agent_data: Dict[str, Any]) -> OwlAgentDefinition:
        """创建Agent定义
        
        Args:
            agent_data: Agent定义数据
            
        Returns:
            OwlAgentDefinition: 创建的Agent定义
        """
        # 提取能力和工具数据
        capabilities_data = agent_data.pop("capabilities", [])
        tools_data = agent_data.pop("tools", [])
        
        # 创建Agent定义
        stmt = insert(OwlAgentDefinition).values(**agent_data).returning(OwlAgentDefinition)
        result = await self.db.execute(stmt)
        agent = result.scalar_one()
        
        # 创建能力
        for capability_data in capabilities_data:
            capability_data["agent_id"] = agent.id
            stmt = insert(OwlAgentCapability).values(**capability_data)
            await self.db.execute(stmt)
        
        # 创建工具
        for tool_data in tools_data:
            tool_data["agent_id"] = agent.id
            stmt = insert(OwlAgentTool).values(**tool_data)
            await self.db.execute(stmt)
        
        await self.db.commit()
        
        # 重新加载Agent以获取关联数据
        stmt = select(OwlAgentDefinition).options(
            selectinload(OwlAgentDefinition.capabilities),
            selectinload(OwlAgentDefinition.tools)
        ).where(OwlAgentDefinition.id == agent.id)
        result = await self.db.execute(stmt)
        return result.scalar_one()
    
    async def get_agent(self, agent_id: int) -> Optional[OwlAgentDefinition]:
        """获取Agent定义
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Optional[OwlAgentDefinition]: Agent定义
        """
        stmt = select(OwlAgentDefinition).options(
            selectinload(OwlAgentDefinition.capabilities),
            selectinload(OwlAgentDefinition.tools)
        ).where(OwlAgentDefinition.id == agent_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_agent_by_name(self, name: str) -> Optional[OwlAgentDefinition]:
        """通过名称获取Agent定义
        
        Args:
            name: Agent名称
            
        Returns:
            Optional[OwlAgentDefinition]: Agent定义
        """
        stmt = select(OwlAgentDefinition).options(
            selectinload(OwlAgentDefinition.capabilities),
            selectinload(OwlAgentDefinition.tools)
        ).where(OwlAgentDefinition.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_agents(
        self, 
        limit: int = 100, 
        offset: int = 0,
        is_active: Optional[bool] = None
    ) -> Tuple[List[OwlAgentDefinition], int]:
        """获取Agent定义列表
        
        Args:
            limit: 限制数量
            offset: 偏移量
            is_active: 活跃状态过滤
            
        Returns:
            Tuple[List[OwlAgentDefinition], int]: Agent定义列表和总数
        """
        # 构建查询条件
        conditions = []
        if is_active is not None:
            conditions.append(OwlAgentDefinition.is_active == is_active)
        
        # 查询总数
        count_stmt = select(func.count()).select_from(OwlAgentDefinition)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = await self.db.execute(count_stmt)
        total = total.scalar()
        
        # 查询列表
        stmt = select(OwlAgentDefinition).options(
            selectinload(OwlAgentDefinition.capabilities),
            selectinload(OwlAgentDefinition.tools)
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(desc(OwlAgentDefinition.updated_at)).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return result.scalars().all(), total
    
    async def update_agent(self, agent_id: int, agent_data: Dict[str, Any]) -> Optional[OwlAgentDefinition]:
        """更新Agent定义
        
        Args:
            agent_id: Agent ID
            agent_data: Agent定义数据
            
        Returns:
            Optional[OwlAgentDefinition]: 更新后的Agent定义
        """
        # 提取能力和工具数据
        capabilities_data = agent_data.pop("capabilities", None)
        tools_data = agent_data.pop("tools", None)
        
        # 更新Agent定义
        stmt = update(OwlAgentDefinition).where(OwlAgentDefinition.id == agent_id).values(**agent_data)
        await self.db.execute(stmt)
        
        # 更新能力
        if capabilities_data is not None:
            # 删除现有能力
            delete_stmt = delete(OwlAgentCapability).where(OwlAgentCapability.agent_id == agent_id)
            await self.db.execute(delete_stmt)
            
            # 创建新能力
            for capability_data in capabilities_data:
                capability_data["agent_id"] = agent_id
                stmt = insert(OwlAgentCapability).values(**capability_data)
                await self.db.execute(stmt)
        
        # 更新工具
        if tools_data is not None:
            # 删除现有工具
            delete_stmt = delete(OwlAgentTool).where(OwlAgentTool.agent_id == agent_id)
            await self.db.execute(delete_stmt)
            
            # 创建新工具
            for tool_data in tools_data:
                tool_data["agent_id"] = agent_id
                stmt = insert(OwlAgentTool).values(**tool_data)
                await self.db.execute(stmt)
        
        await self.db.commit()
        
        # 重新加载Agent以获取关联数据
        return await self.get_agent(agent_id)
    
    async def delete_agent(self, agent_id: int) -> bool:
        """删除Agent定义
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否成功删除
        """
        stmt = delete(OwlAgentDefinition).where(OwlAgentDefinition.id == agent_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0
    
    # ============ Agent链定义相关方法 ============
    
    async def create_chain_definition(self, chain_data: Dict[str, Any]) -> OwlAgentChainDefinition:
        """创建链定义
        
        Args:
            chain_data: 链定义数据
            
        Returns:
            OwlAgentChainDefinition: 创建的链定义
        """
        # 提取步骤数据
        steps_data = chain_data.pop("steps", [])
        
        # 创建链定义
        stmt = insert(OwlAgentChainDefinition).values(**chain_data).returning(OwlAgentChainDefinition)
        result = await self.db.execute(stmt)
        chain = result.scalar_one()
        
        # 创建步骤
        for step_data in steps_data:
            step_data["chain_id"] = chain.id
            stmt = insert(OwlAgentChainStep).values(**step_data)
            await self.db.execute(stmt)
        
        await self.db.commit()
        
        # 重新加载链定义以获取关联数据
        stmt = select(OwlAgentChainDefinition).options(
            selectinload(OwlAgentChainDefinition.steps)
        ).where(OwlAgentChainDefinition.id == chain.id)
        result = await self.db.execute(stmt)
        return result.scalar_one()
    
    async def get_chain_definition(self, chain_id: Union[int, str]) -> Optional[OwlAgentChainDefinition]:
        """获取链定义
        
        Args:
            chain_id: 链ID，可以是数字ID或字符串链ID
            
        Returns:
            Optional[OwlAgentChainDefinition]: 链定义
        """
        if isinstance(chain_id, int):
            condition = OwlAgentChainDefinition.id == chain_id
        else:
            condition = OwlAgentChainDefinition.chain_id == chain_id
            
        stmt = select(OwlAgentChainDefinition).options(
            selectinload(OwlAgentChainDefinition.steps).joinedload(OwlAgentChainStep.agent)
        ).where(condition)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_chain_definitions(
        self, 
        limit: int = 100, 
        offset: int = 0,
        is_active: Optional[bool] = None
    ) -> Tuple[List[OwlAgentChainDefinition], int]:
        """获取链定义列表
        
        Args:
            limit: 限制数量
            offset: 偏移量
            is_active: 活跃状态过滤
            
        Returns:
            Tuple[List[OwlAgentChainDefinition], int]: 链定义列表和总数
        """
        # 构建查询条件
        conditions = []
        if is_active is not None:
            conditions.append(OwlAgentChainDefinition.is_active == is_active)
        
        # 查询总数
        count_stmt = select(func.count()).select_from(OwlAgentChainDefinition)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = await self.db.execute(count_stmt)
        total = total.scalar()
        
        # 查询列表
        stmt = select(OwlAgentChainDefinition).options(
            selectinload(OwlAgentChainDefinition.steps)
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(desc(OwlAgentChainDefinition.updated_at)).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return result.scalars().all(), total
    
    async def update_chain_definition(
        self, 
        chain_id: Union[int, str], 
        chain_data: Dict[str, Any]
    ) -> Optional[OwlAgentChainDefinition]:
        """更新链定义
        
        Args:
            chain_id: 链ID，可以是数字ID或字符串链ID
            chain_data: 链定义数据
            
        Returns:
            Optional[OwlAgentChainDefinition]: 更新后的链定义
        """
        # 获取数字ID
        if isinstance(chain_id, str):
            chain = await self.get_chain_definition(chain_id)
            if not chain:
                return None
            numeric_id = chain.id
        else:
            numeric_id = chain_id
        
        # 提取步骤数据
        steps_data = chain_data.pop("steps", None)
        
        # 更新链定义
        stmt = update(OwlAgentChainDefinition).where(OwlAgentChainDefinition.id == numeric_id).values(**chain_data)
        await self.db.execute(stmt)
        
        # 更新步骤
        if steps_data is not None:
            # 删除现有步骤
            delete_stmt = delete(OwlAgentChainStep).where(OwlAgentChainStep.chain_id == numeric_id)
            await self.db.execute(delete_stmt)
            
            # 创建新步骤
            for step_data in steps_data:
                step_data["chain_id"] = numeric_id
                stmt = insert(OwlAgentChainStep).values(**step_data)
                await self.db.execute(stmt)
        
        await self.db.commit()
        
        # 重新加载链定义以获取关联数据
        return await self.get_chain_definition(numeric_id)
    
    async def delete_chain_definition(self, chain_id: Union[int, str]) -> bool:
        """删除链定义
        
        Args:
            chain_id: 链ID，可以是数字ID或字符串链ID
            
        Returns:
            bool: 是否成功删除
        """
        if isinstance(chain_id, str):
            condition = OwlAgentChainDefinition.chain_id == chain_id
        else:
            condition = OwlAgentChainDefinition.id == chain_id
            
        stmt = delete(OwlAgentChainDefinition).where(condition)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0
    
    # ============ Agent链执行相关方法 ============
    
    async def create_chain_execution(self, execution_data: Dict[str, Any]) -> OwlAgentChainExecution:
        """创建链执行记录
        
        Args:
            execution_data: 执行记录数据
            
        Returns:
            OwlAgentChainExecution: 创建的执行记录
        """
        # 提取步骤数据
        steps_data = execution_data.pop("steps", [])
        
        # 创建执行记录
        stmt = insert(OwlAgentChainExecution).values(**execution_data).returning(OwlAgentChainExecution)
        result = await self.db.execute(stmt)
        execution = result.scalar_one()
        
        # 创建步骤记录
        for step_data in steps_data:
            step_data["execution_id"] = execution.id
            stmt = insert(OwlAgentChainExecutionStep).values(**step_data)
            await self.db.execute(stmt)
        
        await self.db.commit()
        
        # 重新加载执行记录以获取关联数据
        stmt = select(OwlAgentChainExecution).options(
            selectinload(OwlAgentChainExecution.steps)
        ).where(OwlAgentChainExecution.id == execution.id)
        result = await self.db.execute(stmt)
        return result.scalar_one()
    
    async def get_chain_execution(
        self, 
        execution_id: Union[int, str]
    ) -> Optional[OwlAgentChainExecution]:
        """获取链执行记录
        
        Args:
            execution_id: 执行ID，可以是数字ID或字符串执行ID
            
        Returns:
            Optional[OwlAgentChainExecution]: 执行记录
        """
        if isinstance(execution_id, int):
            condition = OwlAgentChainExecution.id == execution_id
        else:
            condition = OwlAgentChainExecution.execution_id == execution_id
            
        stmt = select(OwlAgentChainExecution).options(
            selectinload(OwlAgentChainExecution.steps)
        ).where(condition)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_chain_executions(
        self, 
        limit: int = 100, 
        offset: int = 0,
        user_id: Optional[int] = None,
        chain_id: Optional[Union[int, str]] = None,
        status: Optional[str] = None
    ) -> Tuple[List[OwlAgentChainExecution], int]:
        """获取链执行记录列表
        
        Args:
            limit: 限制数量
            offset: 偏移量
            user_id: 用户ID过滤
            chain_id: 链ID过滤
            status: 状态过滤
            
        Returns:
            Tuple[List[OwlAgentChainExecution], int]: 执行记录列表和总数
        """
        # 构建查询条件
        conditions = []
        if user_id is not None:
            conditions.append(OwlAgentChainExecution.user_id == user_id)
        if chain_id is not None:
            if isinstance(chain_id, int):
                conditions.append(OwlAgentChainExecution.chain_id == chain_id)
            else:
                # 获取链ID对应的数字ID
                chain = await self.get_chain_definition(chain_id)
                if chain:
                    conditions.append(OwlAgentChainExecution.chain_id == chain.id)
        if status is not None:
            conditions.append(OwlAgentChainExecution.status == status)
        
        # 查询总数
        count_stmt = select(func.count()).select_from(OwlAgentChainExecution)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = await self.db.execute(count_stmt)
        total = total.scalar()
        
        # 查询列表
        stmt = select(OwlAgentChainExecution)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(desc(OwlAgentChainExecution.created_at)).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return result.scalars().all(), total
    
    async def update_chain_execution(
        self, 
        execution_id: Union[int, str], 
        execution_data: Dict[str, Any]
    ) -> Optional[OwlAgentChainExecution]:
        """更新链执行记录
        
        Args:
            execution_id: 执行ID，可以是数字ID或字符串执行ID
            execution_data: 执行记录数据
            
        Returns:
            Optional[OwlAgentChainExecution]: 更新后的执行记录
        """
        # 获取数字ID
        if isinstance(execution_id, str):
            execution = await self.get_chain_execution(execution_id)
            if not execution:
                return None
            numeric_id = execution.id
        else:
            numeric_id = execution_id
        
        # 提取步骤数据
        steps_data = execution_data.pop("steps", None)
        
        # 更新执行记录
        stmt = update(OwlAgentChainExecution).where(
            OwlAgentChainExecution.id == numeric_id
        ).values(**execution_data)
        await self.db.execute(stmt)
        
        # 更新步骤记录
        if steps_data is not None:
            for step_data in steps_data:
                step_id = step_data.pop("id", None)
                if step_id:
                    # 更新现有步骤
                    stmt = update(OwlAgentChainExecutionStep).where(
                        OwlAgentChainExecutionStep.id == step_id
                    ).values(**step_data)
                    await self.db.execute(stmt)
                else:
                    # 创建新步骤
                    step_data["execution_id"] = numeric_id
                    stmt = insert(OwlAgentChainExecutionStep).values(**step_data)
                    await self.db.execute(stmt)
        
        await self.db.commit()
        
        # 重新加载执行记录以获取关联数据
        return await self.get_chain_execution(numeric_id)
    
    # ============ Agent消息相关方法 ============
    
    async def create_agent_message(self, message_data: Dict[str, Any]) -> OwlAgentMessage:
        """创建Agent消息
        
        Args:
            message_data: 消息数据
            
        Returns:
            OwlAgentMessage: 创建的消息
        """
        # 提取工具调用数据
        tool_calls_data = message_data.pop("tool_calls", [])
        
        # 创建消息
        stmt = insert(OwlAgentMessage).values(**message_data).returning(OwlAgentMessage)
        result = await self.db.execute(stmt)
        message = result.scalar_one()
        
        # 创建工具调用记录
        for tool_call_data in tool_calls_data:
            tool_call_data["message_id"] = message.id
            stmt = insert(OwlAgentToolCall).values(**tool_call_data)
            await self.db.execute(stmt)
        
        await self.db.commit()
        
        # 重新加载消息以获取关联数据
        stmt = select(OwlAgentMessage).options(
            selectinload(OwlAgentMessage.tool_calls)
        ).where(OwlAgentMessage.id == message.id)
        result = await self.db.execute(stmt)
        return result.scalar_one()
    
    async def get_agent_message(
        self, 
        message_id: Union[int, str]
    ) -> Optional[OwlAgentMessage]:
        """获取Agent消息
        
        Args:
            message_id: 消息ID，可以是数字ID或字符串消息ID
            
        Returns:
            Optional[OwlAgentMessage]: 消息
        """
        if isinstance(message_id, int):
            condition = OwlAgentMessage.id == message_id
        else:
            condition = OwlAgentMessage.message_id == message_id
            
        stmt = select(OwlAgentMessage).options(
            selectinload(OwlAgentMessage.tool_calls),
            selectinload(OwlAgentMessage.mappings)
        ).where(condition)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_agent_messages(
        self, 
        limit: int = 100, 
        offset: int = 0,
        user_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        agent_execution_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> Tuple[List[OwlAgentMessage], int]:
        """获取Agent消息列表
        
        Args:
            limit: 限制数量
            offset: 偏移量
            user_id: 用户ID过滤
            agent_id: Agent ID过滤
            agent_execution_id: 执行ID过滤
            conversation_id: 对话ID过滤
            
        Returns:
            Tuple[List[OwlAgentMessage], int]: 消息列表和总数
        """
        # 构建查询条件
        conditions = []
        if user_id is not None:
            conditions.append(OwlAgentMessage.user_id == user_id)
        if agent_id is not None:
            conditions.append(OwlAgentMessage.agent_id == agent_id)
        if agent_execution_id is not None:
            conditions.append(OwlAgentMessage.agent_execution_id == agent_execution_id)
        if conversation_id is not None:
            conditions.append(OwlAgentMessage.conversation_id == conversation_id)
        
        # 查询总数
        count_stmt = select(func.count()).select_from(OwlAgentMessage)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = await self.db.execute(count_stmt)
        total = total.scalar()
        
        # 查询列表
        stmt = select(OwlAgentMessage)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(asc(OwlAgentMessage.timestamp)).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return result.scalars().all(), total
    
    async def create_message_mapping(self, mapping_data: Dict[str, Any]) -> OwlAgentMessageMapping:
        """创建消息映射
        
        Args:
            mapping_data: 映射数据
            
        Returns:
            OwlAgentMessageMapping: 创建的映射
        """
        stmt = insert(OwlAgentMessageMapping).values(**mapping_data).returning(OwlAgentMessageMapping)
        result = await self.db.execute(stmt)
        mapping = result.scalar_one()
        await self.db.commit()
        return mapping
    
    async def get_message_by_external_id(self, external_message_id: str) -> Optional[OwlAgentMessage]:
        """通过外部消息ID获取内部消息
        
        Args:
            external_message_id: 外部消息ID
            
        Returns:
            Optional[OwlAgentMessage]: 内部消息
        """
        stmt = select(OwlAgentMessage).join(
            OwlAgentMessageMapping, 
            OwlAgentMessage.id == OwlAgentMessageMapping.internal_message_id
        ).where(OwlAgentMessageMapping.external_message_id == external_message_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_tool_call(self, tool_call_data: Dict[str, Any]) -> OwlAgentToolCall:
        """创建工具调用记录
        
        Args:
            tool_call_data: 工具调用数据
            
        Returns:
            OwlAgentToolCall: 创建的工具调用记录
        """
        stmt = insert(OwlAgentToolCall).values(**tool_call_data).returning(OwlAgentToolCall)
        result = await self.db.execute(stmt)
        tool_call = result.scalar_one()
        await self.db.commit()
        return tool_call
    
    async def update_tool_call(
        self, 
        tool_call_id: int, 
        tool_call_data: Dict[str, Any]
    ) -> Optional[OwlAgentToolCall]:
        """更新工具调用记录
        
        Args:
            tool_call_id: 工具调用ID
            tool_call_data: 工具调用数据
            
        Returns:
            Optional[OwlAgentToolCall]: 更新后的工具调用记录
        """
        stmt = update(OwlAgentToolCall).where(
            OwlAgentToolCall.id == tool_call_id
        ).values(**tool_call_data).returning(OwlAgentToolCall)
        result = await self.db.execute(stmt)
        tool_call = result.scalar_one_or_none()
        await self.db.commit()
        return tool_call
