"""
OWL框架Agent服务层
提供Agent定义、链执行和消息集成的业务逻辑处理
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import uuid
import json
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.owl_agent_repository import OwlAgentRepository
from app.frameworks.owl.agents.interfaces import (
    AgentConfig, AgentInputSchema, AgentOutputSchema, 
    AgentChainDefinition, AgentChainStep
)
from app.frameworks.owl.utils.decorators import AgentInput, AgentOutput
from app.frameworks.owl.utils.message_adapter import AgentMessageAdapter, AgentChainMessageAdapter
from app.messaging.core.models import Message, MessageRole


class OwlAgentService:
    """OWL Agent服务"""
    
    def __init__(self, db: AsyncSession):
        """初始化服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.repository = OwlAgentRepository(db)
    
    # ============ Agent定义相关方法 ============
    
    async def create_agent(self, agent_config: Union[AgentConfig, Dict[str, Any]]) -> Dict[str, Any]:
        """创建Agent定义
        
        Args:
            agent_config: Agent配置
            
        Returns:
            Dict[str, Any]: 创建的Agent数据
        """
        # 转换为字典
        if hasattr(agent_config, 'to_dict'):
            agent_data = agent_config.to_dict()
        else:
            agent_data = dict(agent_config)
        
        # 处理能力列表
        if "capabilities" in agent_data and isinstance(agent_data["capabilities"], list):
            capabilities_data = []
            for capability in agent_data["capabilities"]:
                if hasattr(capability, 'to_dict'):
                    capabilities_data.append(capability.to_dict())
                else:
                    capabilities_data.append(dict(capability))
            agent_data["capabilities"] = capabilities_data
        
        # 创建Agent
        agent = await self.repository.create_agent(agent_data)
        return agent.to_dict()
    
    async def get_agent(self, agent_id: int) -> Optional[Dict[str, Any]]:
        """获取Agent定义
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Optional[Dict[str, Any]]: Agent数据
        """
        agent = await self.repository.get_agent(agent_id)
        if agent:
            return agent.to_dict()
        return None
    
    async def get_agent_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """通过名称获取Agent定义
        
        Args:
            name: Agent名称
            
        Returns:
            Optional[Dict[str, Any]]: Agent数据
        """
        agent = await self.repository.get_agent_by_name(name)
        if agent:
            return agent.to_dict()
        return None
    
    async def list_agents(
        self, 
        limit: int = 100, 
        offset: int = 0,
        is_active: Optional[bool] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """获取Agent定义列表
        
        Args:
            limit: 限制数量
            offset: 偏移量
            is_active: 活跃状态过滤
            
        Returns:
            Tuple[List[Dict[str, Any]], int]: Agent数据列表和总数
        """
        agents, total = await self.repository.list_agents(limit, offset, is_active)
        return [agent.to_dict() for agent in agents], total
    
    async def update_agent(
        self, 
        agent_id: int, 
        agent_config: Union[AgentConfig, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """更新Agent定义
        
        Args:
            agent_id: Agent ID
            agent_config: Agent配置
            
        Returns:
            Optional[Dict[str, Any]]: 更新后的Agent数据
        """
        # 转换为字典
        if hasattr(agent_config, 'to_dict'):
            agent_data = agent_config.to_dict()
        else:
            agent_data = dict(agent_config)
        
        # 处理能力列表
        if "capabilities" in agent_data and isinstance(agent_data["capabilities"], list):
            capabilities_data = []
            for capability in agent_data["capabilities"]:
                if hasattr(capability, 'to_dict'):
                    capabilities_data.append(capability.to_dict())
                else:
                    capabilities_data.append(dict(capability))
            agent_data["capabilities"] = capabilities_data
        
        # 更新Agent
        agent = await self.repository.update_agent(agent_id, agent_data)
        if agent:
            return agent.to_dict()
        return None
    
    async def delete_agent(self, agent_id: int) -> bool:
        """删除Agent定义
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否成功删除
        """
        return await self.repository.delete_agent(agent_id)
    
    # ============ Agent链定义相关方法 ============
    
    async def create_chain_definition(
        self, 
        chain_definition: Union[AgentChainDefinition, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """创建链定义
        
        Args:
            chain_definition: 链定义
            
        Returns:
            Dict[str, Any]: 创建的链数据
        """
        # 转换为字典
        if hasattr(chain_definition, 'to_dict'):
            chain_data = chain_definition.to_dict()
        else:
            chain_data = dict(chain_definition)
        
        # 处理步骤列表
        if "steps" in chain_data and isinstance(chain_data["steps"], list):
            steps_data = []
            for step in chain_data["steps"]:
                if hasattr(step, 'to_dict'):
                    steps_data.append(step.to_dict())
                else:
                    steps_data.append(dict(step))
            chain_data["steps"] = steps_data
        
        # 确保有链ID
        if not chain_data.get("chain_id"):
            chain_data["chain_id"] = f"chain-{uuid.uuid4()}"
        
        # 创建链定义
        chain = await self.repository.create_chain_definition(chain_data)
        return chain.to_dict()
    
    async def get_chain_definition(self, chain_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        """获取链定义
        
        Args:
            chain_id: 链ID，可以是数字ID或字符串链ID
            
        Returns:
            Optional[Dict[str, Any]]: 链数据
        """
        chain = await self.repository.get_chain_definition(chain_id)
        if chain:
            return chain.to_dict()
        return None
    
    async def list_chain_definitions(
        self, 
        limit: int = 100, 
        offset: int = 0,
        is_active: Optional[bool] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """获取链定义列表
        
        Args:
            limit: 限制数量
            offset: 偏移量
            is_active: 活跃状态过滤
            
        Returns:
            Tuple[List[Dict[str, Any]], int]: 链数据列表和总数
        """
        chains, total = await self.repository.list_chain_definitions(limit, offset, is_active)
        return [chain.to_dict() for chain in chains], total
    
    async def update_chain_definition(
        self, 
        chain_id: Union[int, str], 
        chain_definition: Union[AgentChainDefinition, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """更新链定义
        
        Args:
            chain_id: 链ID，可以是数字ID或字符串链ID
            chain_definition: 链定义
            
        Returns:
            Optional[Dict[str, Any]]: 更新后的链数据
        """
        # 转换为字典
        if hasattr(chain_definition, 'to_dict'):
            chain_data = chain_definition.to_dict()
        else:
            chain_data = dict(chain_definition)
        
        # 处理步骤列表
        if "steps" in chain_data and isinstance(chain_data["steps"], list):
            steps_data = []
            for step in chain_data["steps"]:
                if hasattr(step, 'to_dict'):
                    steps_data.append(step.to_dict())
                else:
                    steps_data.append(dict(step))
            chain_data["steps"] = steps_data
        
        # 更新链定义
        chain = await self.repository.update_chain_definition(chain_id, chain_data)
        if chain:
            return chain.to_dict()
        return None
    
    async def delete_chain_definition(self, chain_id: Union[int, str]) -> bool:
        """删除链定义
        
        Args:
            chain_id: 链ID，可以是数字ID或字符串链ID
            
        Returns:
            bool: 是否成功删除
        """
        return await self.repository.delete_chain_definition(chain_id)
    
    # ============ Agent链执行相关方法 ============
    
    async def create_chain_execution(
        self, 
        chain_id: Union[int, str],
        input_message: str,
        user_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建链执行记录
        
        Args:
            chain_id: 链ID
            input_message: 输入消息
            user_id: 用户ID
            context: 上下文
            
        Returns:
            Dict[str, Any]: 创建的执行记录数据
        """
        # 获取链定义
        chain = await self.repository.get_chain_definition(chain_id)
        if not chain:
            raise ValueError(f"链定义不存在: {chain_id}")
        
        # 创建执行记录
        execution_id = f"exec-{uuid.uuid4()}"
        execution_data = {
            "execution_id": execution_id,
            "chain_id": chain.id,
            "input_message": input_message,
            "status": "pending",
            "context": context or {},
            "user_id": user_id,
            "start_time": datetime.now()
        }
        
        # 创建执行记录
        execution = await self.repository.create_chain_execution(execution_data)
        return execution.to_dict()
    
    async def update_chain_execution_status(
        self, 
        execution_id: Union[int, str],
        status: str,
        result_content: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """更新链执行状态
        
        Args:
            execution_id: 执行ID
            status: 状态
            result_content: 结果内容
            error: 错误信息
            metadata: 元数据
            
        Returns:
            Optional[Dict[str, Any]]: 更新后的执行记录数据
        """
        # 准备更新数据
        execution_data = {
            "status": status
        }
        
        if status in ["completed", "failed"]:
            execution_data["end_time"] = datetime.now()
        
        if result_content is not None:
            execution_data["result_content"] = result_content
        
        if error is not None:
            execution_data["error"] = error
        
        if metadata is not None:
            # 获取现有元数据并合并
            execution = await self.repository.get_chain_execution(execution_id)
            if execution:
                current_metadata = execution.metadata or {}
                current_metadata.update(metadata)
                execution_data["metadata"] = current_metadata
            else:
                execution_data["metadata"] = metadata
        
        # 更新执行记录
        execution = await self.repository.update_chain_execution(execution_id, execution_data)
        if execution:
            return execution.to_dict()
        return None
    
    async def get_chain_execution(self, execution_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        """获取链执行记录
        
        Args:
            execution_id: 执行ID
            
        Returns:
            Optional[Dict[str, Any]]: 执行记录数据
        """
        execution = await self.repository.get_chain_execution(execution_id)
        if execution:
            return execution.to_dict()
        return None
    
    async def list_chain_executions(
        self, 
        limit: int = 100, 
        offset: int = 0,
        user_id: Optional[int] = None,
        chain_id: Optional[Union[int, str]] = None,
        status: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """获取链执行记录列表
        
        Args:
            limit: 限制数量
            offset: 偏移量
            user_id: 用户ID过滤
            chain_id: 链ID过滤
            status: 状态过滤
            
        Returns:
            Tuple[List[Dict[str, Any]], int]: 执行记录数据列表和总数
        """
        executions, total = await self.repository.list_chain_executions(
            limit, offset, user_id, chain_id, status
        )
        return [execution.to_dict() for execution in executions], total
    
    async def add_execution_step(
        self,
        execution_id: Union[int, str],
        agent_id: int,
        agent_name: str,
        position: int,
        status: str = "pending",
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        chain_step_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """添加执行步骤记录
        
        Args:
            execution_id: 执行ID
            agent_id: Agent ID
            agent_name: Agent名称
            position: 位置
            status: 状态
            input_data: 输入数据
            output_data: 输出数据
            error: 错误信息
            chain_step_id: 链步骤ID
            
        Returns:
            Optional[Dict[str, Any]]: 添加的步骤记录数据
        """
        # 获取执行记录
        execution = await self.repository.get_chain_execution(execution_id)
        if not execution:
            return None
        
        # 准备步骤数据
        step_data = {
            "execution_id": execution.id,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "position": position,
            "status": status,
            "input": input_data or {},
            "chain_step_id": chain_step_id
        }
        
        if status in ["completed", "failed", "skipped"]:
            step_data["start_time"] = datetime.now()
            step_data["end_time"] = datetime.now()
        else:
            step_data["start_time"] = datetime.now()
        
        if output_data is not None:
            step_data["output"] = output_data
        
        if error is not None:
            step_data["error"] = error
        
        # 更新执行记录
        execution_data = {
            "steps": [step_data]
        }
        
        execution = await self.repository.update_chain_execution(execution.id, execution_data)
        if execution and execution.steps:
            for step in execution.steps:
                if step.position == position:
                    return step.to_dict()
        
        return None
    
    async def update_execution_step(
        self,
        execution_id: Union[int, str],
        position: int,
        status: str,
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """更新执行步骤状态
        
        Args:
            execution_id: 执行ID
            position: 步骤位置
            status: 状态
            output_data: 输出数据
            error: 错误信息
            
        Returns:
            Optional[Dict[str, Any]]: 更新后的步骤记录数据
        """
        # 获取执行记录
        execution = await self.repository.get_chain_execution(execution_id)
        if not execution:
            return None
        
        # 查找步骤
        target_step = None
        for step in execution.steps:
            if step.position == position:
                target_step = step
                break
        
        if not target_step:
            return None
        
        # 准备更新数据
        step_data = {
            "id": target_step.id,
            "status": status
        }
        
        if status in ["completed", "failed", "skipped"]:
            step_data["end_time"] = datetime.now()
        
        if output_data is not None:
            step_data["output"] = output_data
        
        if error is not None:
            step_data["error"] = error
        
        # 更新执行记录
        execution_data = {
            "steps": [step_data]
        }
        
        execution = await self.repository.update_chain_execution(execution.id, execution_data)
        if execution and execution.steps:
            for step in execution.steps:
                if step.position == position:
                    return step.to_dict()
        
        return None
    
    # ============ Agent消息相关方法 ============
    
    async def create_agent_message(
        self,
        agent_id: Optional[int],
        message_type: str,
        role: str,
        content: Any,
        user_id: Optional[int] = None,
        agent_execution_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        parent_message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        content_format: str = "text",
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """创建Agent消息
        
        Args:
            agent_id: Agent ID
            message_type: 消息类型
            role: 角色
            content: 内容
            user_id: 用户ID
            agent_execution_id: 执行ID
            conversation_id: 对话ID
            parent_message_id: 父消息ID
            metadata: 元数据
            content_format: 内容格式
            tool_calls: 工具调用数据
            
        Returns:
            Dict[str, Any]: 创建的消息数据
        """
        # 准备消息数据
        message_id = f"msg-{uuid.uuid4()}"
        raw_content = {}
        
        # 处理内容
        if isinstance(content, dict):
            raw_content = content
            if content_format == "text" and "text" in content:
                content = content["text"]
            elif content_format == "text" and "content" in content:
                content = content["content"]
        elif not isinstance(content, str):
            try:
                content_str = str(content)
                raw_content = {"original": content}
                content = content_str
            except:
                content = ""
                raw_content = {"error": "无法转换内容为字符串"}
        
        # 创建消息数据
        message_data = {
            "message_id": message_id,
            "agent_id": agent_id,
            "agent_execution_id": agent_execution_id,
            "message_type": message_type,
            "role": role,
            "content": content,
            "content_format": content_format,
            "raw_content": raw_content,
            "metadata": metadata or {},
            "parent_message_id": parent_message_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "tool_calls": tool_calls or []
        }
        
        # 创建消息
        message = await self.repository.create_agent_message(message_data)
        return message.to_dict()
    
    async def create_message_from_agent_output(
        self,
        output: Union[AgentOutput, AgentOutputSchema, Dict[str, Any]],
        agent_id: Optional[int] = None,
        user_id: Optional[int] = None,
        agent_execution_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        parent_message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """从Agent输出创建消息
        
        Args:
            output: Agent输出
            agent_id: Agent ID
            user_id: 用户ID
            agent_execution_id: 执行ID
            conversation_id: 对话ID
            parent_message_id: 父消息ID
            
        Returns:
            Dict[str, Any]: 创建的消息数据
        """
        # 转换为字典
        if hasattr(output, 'to_dict'):
            output_data = output.to_dict()
        else:
            output_data = dict(output)
        
        # 准备消息数据
        message_type = "text"
        role = "assistant"
        content = output_data.get("content", "")
        metadata = output_data.get("metadata", {})
        tool_calls = output_data.get("tool_calls", [])
        
        # 检查是否有特殊内容类型
        if metadata.get("content_type") == "code":
            message_type = "code"
            content = {
                "code": content,
                "language": metadata.get("language", ""),
                "explanation": metadata.get("explanation", "")
            }
            content_format = "json"
        elif metadata.get("content_type") == "thinking":
            message_type = "thinking"
            role = "system"
            content_format = "text"
        elif metadata.get("content_type") == "error":
            message_type = "error"
            role = "system"
            content = {
                "message": output_data.get("error", "未知错误"),
                "details": metadata.get("error_details", "")
            }
            content_format = "json"
        else:
            content_format = "text"
        
        # 创建消息
        return await self.create_agent_message(
            agent_id=agent_id,
            message_type=message_type,
            role=role,
            content=content,
            user_id=user_id,
            agent_execution_id=agent_execution_id,
            conversation_id=conversation_id,
            parent_message_id=parent_message_id,
            metadata=metadata,
            content_format=content_format,
            tool_calls=tool_calls
        )
    
    async def create_mapping_from_message(
        self,
        internal_message_id: int,
        external_message: Message,
        mapping_type: str = "direct",
        mapping_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建消息映射
        
        Args:
            internal_message_id: 内部消息ID
            external_message: 外部消息
            mapping_type: 映射类型
            mapping_data: 映射数据
            
        Returns:
            Dict[str, Any]: 创建的映射数据
        """
        # 准备映射数据
        mapping_data = {
            "internal_message_id": internal_message_id,
            "external_message_id": external_message.id,
            "mapping_type": mapping_type,
            "mapping_data": mapping_data or {}
        }
        
        # 创建映射
        mapping = await self.repository.create_message_mapping(mapping_data)
        return mapping.to_dict()
    
    async def get_agent_message(self, message_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        """获取Agent消息
        
        Args:
            message_id: 消息ID，可以是数字ID或字符串消息ID
            
        Returns:
            Optional[Dict[str, Any]]: 消息数据
        """
        message = await self.repository.get_agent_message(message_id)
        if message:
            return message.to_dict()
        return None
    
    async def get_message_by_external_id(self, external_message_id: str) -> Optional[Dict[str, Any]]:
        """通过外部消息ID获取内部消息
        
        Args:
            external_message_id: 外部消息ID
            
        Returns:
            Optional[Dict[str, Any]]: 内部消息数据
        """
        message = await self.repository.get_message_by_external_id(external_message_id)
        if message:
            return message.to_dict()
        return None
    
    async def list_agent_messages(
        self, 
        limit: int = 100, 
        offset: int = 0,
        user_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        agent_execution_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """获取Agent消息列表
        
        Args:
            limit: 限制数量
            offset: 偏移量
            user_id: 用户ID过滤
            agent_id: Agent ID过滤
            agent_execution_id: 执行ID过滤
            conversation_id: 对话ID过滤
            
        Returns:
            Tuple[List[Dict[str, Any]], int]: 消息数据列表和总数
        """
        messages, total = await self.repository.list_agent_messages(
            limit, offset, user_id, agent_id, agent_execution_id, conversation_id
        )
        return [message.to_dict() for message in messages], total
    
    async def add_tool_call(
        self,
        message_id: Union[int, str],
        tool_name: str,
        tool_arguments: Dict[str, Any],
        tool_result: Optional[Dict[str, Any]] = None,
        status: str = "pending"
    ) -> Optional[Dict[str, Any]]:
        """添加工具调用记录
        
        Args:
            message_id: 消息ID
            tool_name: 工具名称
            tool_arguments: 工具参数
            tool_result: 工具结果
            status: 状态
            
        Returns:
            Optional[Dict[str, Any]]: 工具调用记录数据
        """
        # 获取消息
        if isinstance(message_id, str):
            message = await self.repository.get_agent_message(message_id)
            if not message:
                return None
            message_id = message.id
        
        # 准备工具调用数据
        tool_call_data = {
            "message_id": message_id,
            "tool_name": tool_name,
            "tool_arguments": tool_arguments,
            "status": status
        }
        
        if tool_result is not None:
            tool_call_data["tool_result"] = tool_result
            tool_call_data["status"] = "completed"
            tool_call_data["end_time"] = datetime.now()
        
        # 创建工具调用记录
        tool_call = await self.repository.create_tool_call(tool_call_data)
        return tool_call.to_dict()
    
    async def update_tool_call(
        self,
        tool_call_id: int,
        tool_result: Dict[str, Any],
        status: str = "completed",
        error: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """更新工具调用记录
        
        Args:
            tool_call_id: 工具调用ID
            tool_result: 工具结果
            status: 状态
            error: 错误信息
            
        Returns:
            Optional[Dict[str, Any]]: 更新后的工具调用记录数据
        """
        # 准备更新数据
        tool_call_data = {
            "tool_result": tool_result,
            "status": status,
            "end_time": datetime.now()
        }
        
        if error is not None:
            tool_call_data["error"] = error
            tool_call_data["status"] = "failed"
        
        # 更新工具调用记录
        tool_call = await self.repository.update_tool_call(tool_call_id, tool_call_data)
        if tool_call:
            return tool_call.to_dict()
        return None
