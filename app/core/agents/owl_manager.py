"""
OWL智能体管理器
处理OWL框架特定的智能体、链定义、执行和消息管理的核心业务逻辑
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from sqlalchemy.orm import Session
import uuid
import logging
from datetime import datetime

from app.repositories.owl_agent_repository import OwlAgentRepository

logger = logging.getLogger(__name__)


class OwlAgentManager:
    """OWL智能体管理器"""
    
    def __init__(self, db: Session):
        """初始化OWL智能体管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.repository = OwlAgentRepository(db)
    
    # ============ Agent定义相关方法 ============
    
    async def create_agent(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """创建Agent定义
        
        Args:
            agent_config: Agent配置
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 处理能力列表
            if "capabilities" in agent_config and isinstance(agent_config["capabilities"], list):
                capabilities_data = []
                for capability in agent_config["capabilities"]:
                    if hasattr(capability, 'to_dict'):
                        capabilities_data.append(capability.to_dict())
                    elif isinstance(capability, dict):
                        capabilities_data.append(capability)
                    else:
                        capabilities_data.append(dict(capability))
                agent_config["capabilities"] = capabilities_data
            
            # 创建Agent
            agent = await self.repository.create_agent(agent_config)
            
            return {
                "success": True,
                "data": agent.to_dict() if hasattr(agent, 'to_dict') else agent
            }
            
        except Exception as e:
            logger.error(f"创建Agent时出错: {str(e)}")
            return {
                "success": False,
                "error": f"创建Agent失败: {str(e)}",
                "error_code": "CREATE_AGENT_FAILED"
            }
    
    async def get_agent(self, agent_id: int) -> Dict[str, Any]:
        """获取Agent定义
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            agent = await self.repository.get_agent(agent_id)
            if not agent:
                return {
                    "success": False,
                    "error": "Agent不存在",
                    "error_code": "AGENT_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": agent.to_dict() if hasattr(agent, 'to_dict') else agent
            }
            
        except Exception as e:
            logger.error(f"获取Agent时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取Agent失败: {str(e)}",
                "error_code": "GET_AGENT_FAILED"
            }
    
    async def get_agent_by_name(self, name: str) -> Dict[str, Any]:
        """通过名称获取Agent定义
        
        Args:
            name: Agent名称
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            agent = await self.repository.get_agent_by_name(name)
            if not agent:
                return {
                    "success": False,
                    "error": "Agent不存在",
                    "error_code": "AGENT_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": agent.to_dict() if hasattr(agent, 'to_dict') else agent
            }
            
        except Exception as e:
            logger.error(f"通过名称获取Agent时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取Agent失败: {str(e)}",
                "error_code": "GET_AGENT_BY_NAME_FAILED"
            }
    
    async def list_agents(self, 
                         limit: int = 100, 
                         offset: int = 0,
                         is_active: Optional[bool] = None) -> Dict[str, Any]:
        """获取Agent定义列表
        
        Args:
            limit: 限制数量
            offset: 偏移量
            is_active: 活跃状态过滤
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            agents, total = await self.repository.list_agents(limit, offset, is_active)
            
            agent_list = []
            for agent in agents:
                agent_data = agent.to_dict() if hasattr(agent, 'to_dict') else agent
                agent_list.append(agent_data)
            
            return {
                "success": True,
                "data": {
                    "agents": agent_list,
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }
            }
            
        except Exception as e:
            logger.error(f"获取Agent列表时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取Agent列表失败: {str(e)}",
                "error_code": "LIST_AGENTS_FAILED"
            }
    
    async def update_agent(self, 
                          agent_id: int, 
                          agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """更新Agent定义
        
        Args:
            agent_id: Agent ID
            agent_config: Agent配置
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 处理能力列表
            if "capabilities" in agent_config and isinstance(agent_config["capabilities"], list):
                capabilities_data = []
                for capability in agent_config["capabilities"]:
                    if hasattr(capability, 'to_dict'):
                        capabilities_data.append(capability.to_dict())
                    elif isinstance(capability, dict):
                        capabilities_data.append(capability)
                    else:
                        capabilities_data.append(dict(capability))
                agent_config["capabilities"] = capabilities_data
            
            # 更新Agent
            agent = await self.repository.update_agent(agent_id, agent_config)
            if not agent:
                return {
                    "success": False,
                    "error": "Agent不存在或更新失败",
                    "error_code": "UPDATE_AGENT_FAILED"
                }
            
            return {
                "success": True,
                "data": agent.to_dict() if hasattr(agent, 'to_dict') else agent
            }
            
        except Exception as e:
            logger.error(f"更新Agent时出错: {str(e)}")
            return {
                "success": False,
                "error": f"更新Agent失败: {str(e)}",
                "error_code": "UPDATE_AGENT_FAILED"
            }
    
    async def delete_agent(self, agent_id: int) -> Dict[str, Any]:
        """删除Agent定义
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            success = await self.repository.delete_agent(agent_id)
            if not success:
                return {
                    "success": False,
                    "error": "Agent不存在或删除失败",
                    "error_code": "DELETE_AGENT_FAILED"
                }
            
            return {
                "success": True,
                "data": {
                    "message": "Agent已成功删除",
                    "agent_id": agent_id
                }
            }
            
        except Exception as e:
            logger.error(f"删除Agent时出错: {str(e)}")
            return {
                "success": False,
                "error": f"删除Agent失败: {str(e)}",
                "error_code": "DELETE_AGENT_FAILED"
            }
    
    # ============ Agent链定义相关方法 ============
    
    async def create_chain_definition(self, chain_definition: Dict[str, Any]) -> Dict[str, Any]:
        """创建链定义
        
        Args:
            chain_definition: 链定义
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 处理步骤列表
            if "steps" in chain_definition and isinstance(chain_definition["steps"], list):
                steps_data = []
                for step in chain_definition["steps"]:
                    if hasattr(step, 'to_dict'):
                        steps_data.append(step.to_dict())
                    elif isinstance(step, dict):
                        steps_data.append(step)
                    else:
                        steps_data.append(dict(step))
                chain_definition["steps"] = steps_data
            
            # 确保有链ID
            if not chain_definition.get("chain_id"):
                chain_definition["chain_id"] = f"chain-{uuid.uuid4()}"
            
            # 创建链定义
            chain = await self.repository.create_chain_definition(chain_definition)
            
            return {
                "success": True,
                "data": chain.to_dict() if hasattr(chain, 'to_dict') else chain
            }
            
        except Exception as e:
            logger.error(f"创建链定义时出错: {str(e)}")
            return {
                "success": False,
                "error": f"创建链定义失败: {str(e)}",
                "error_code": "CREATE_CHAIN_DEFINITION_FAILED"
            }
    
    async def get_chain_definition(self, chain_id: Union[int, str]) -> Dict[str, Any]:
        """获取链定义
        
        Args:
            chain_id: 链ID，可以是数字ID或字符串链ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            chain = await self.repository.get_chain_definition(chain_id)
            if not chain:
                return {
                    "success": False,
                    "error": "链定义不存在",
                    "error_code": "CHAIN_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": chain.to_dict() if hasattr(chain, 'to_dict') else chain
            }
            
        except Exception as e:
            logger.error(f"获取链定义时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取链定义失败: {str(e)}",
                "error_code": "GET_CHAIN_DEFINITION_FAILED"
            }
    
    async def list_chain_definitions(self, 
                                   limit: int = 100, 
                                   offset: int = 0,
                                   is_active: Optional[bool] = None) -> Dict[str, Any]:
        """获取链定义列表
        
        Args:
            limit: 限制数量
            offset: 偏移量
            is_active: 活跃状态过滤
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            chains, total = await self.repository.list_chain_definitions(limit, offset, is_active)
            
            chain_list = []
            for chain in chains:
                chain_data = chain.to_dict() if hasattr(chain, 'to_dict') else chain
                chain_list.append(chain_data)
            
            return {
                "success": True,
                "data": {
                    "chains": chain_list,
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }
            }
            
        except Exception as e:
            logger.error(f"获取链定义列表时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取链定义列表失败: {str(e)}",
                "error_code": "LIST_CHAIN_DEFINITIONS_FAILED"
            }
    
    async def update_chain_definition(self, 
                                    chain_id: Union[int, str], 
                                    chain_definition: Dict[str, Any]) -> Dict[str, Any]:
        """更新链定义
        
        Args:
            chain_id: 链ID，可以是数字ID或字符串链ID
            chain_definition: 链定义
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 处理步骤列表
            if "steps" in chain_definition and isinstance(chain_definition["steps"], list):
                steps_data = []
                for step in chain_definition["steps"]:
                    if hasattr(step, 'to_dict'):
                        steps_data.append(step.to_dict())
                    elif isinstance(step, dict):
                        steps_data.append(step)
                    else:
                        steps_data.append(dict(step))
                chain_definition["steps"] = steps_data
            
            # 更新链定义
            chain = await self.repository.update_chain_definition(chain_id, chain_definition)
            if not chain:
                return {
                    "success": False,
                    "error": "链定义不存在或更新失败",
                    "error_code": "UPDATE_CHAIN_DEFINITION_FAILED"
                }
            
            return {
                "success": True,
                "data": chain.to_dict() if hasattr(chain, 'to_dict') else chain
            }
            
        except Exception as e:
            logger.error(f"更新链定义时出错: {str(e)}")
            return {
                "success": False,
                "error": f"更新链定义失败: {str(e)}",
                "error_code": "UPDATE_CHAIN_DEFINITION_FAILED"
            }
    
    async def delete_chain_definition(self, chain_id: Union[int, str]) -> Dict[str, Any]:
        """删除链定义
        
        Args:
            chain_id: 链ID，可以是数字ID或字符串链ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            success = await self.repository.delete_chain_definition(chain_id)
            if not success:
                return {
                    "success": False,
                    "error": "链定义不存在或删除失败",
                    "error_code": "DELETE_CHAIN_DEFINITION_FAILED"
                }
            
            return {
                "success": True,
                "data": {
                    "message": "链定义已成功删除",
                    "chain_id": chain_id
                }
            }
            
        except Exception as e:
            logger.error(f"删除链定义时出错: {str(e)}")
            return {
                "success": False,
                "error": f"删除链定义失败: {str(e)}",
                "error_code": "DELETE_CHAIN_DEFINITION_FAILED"
            }
    
    # ============ Agent链执行相关方法 ============
    
    async def create_chain_execution(self,
                                   chain_id: Union[int, str],
                                   input_message: str,
                                   user_id: Optional[int] = None,
                                   context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建链执行记录
        
        Args:
            chain_id: 链ID
            input_message: 输入消息
            user_id: 用户ID
            context: 上下文
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 获取链定义
            chain_result = await self.get_chain_definition(chain_id)
            if not chain_result["success"]:
                return chain_result
            
            chain = chain_result["data"]
            
            # 创建执行记录
            execution_id = f"exec-{uuid.uuid4()}"
            execution_data = {
                "execution_id": execution_id,
                "chain_id": chain.get("id") if isinstance(chain, dict) else chain.id,
                "input_message": input_message,
                "status": "pending",
                "context": context or {},
                "user_id": user_id,
                "start_time": datetime.now()
            }
            
            # 创建执行记录
            execution = await self.repository.create_chain_execution(execution_data)
            
            return {
                "success": True,
                "data": execution.to_dict() if hasattr(execution, 'to_dict') else execution
            }
            
        except Exception as e:
            logger.error(f"创建链执行记录时出错: {str(e)}")
            return {
                "success": False,
                "error": f"创建链执行记录失败: {str(e)}",
                "error_code": "CREATE_CHAIN_EXECUTION_FAILED"
            }
    
    async def update_chain_execution_status(self,
                                          execution_id: Union[int, str],
                                          status: str,
                                          result_content: Optional[str] = None,
                                          error: Optional[str] = None,
                                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """更新链执行状态
        
        Args:
            execution_id: 执行ID
            status: 状态
            result_content: 结果内容
            error: 错误信息
            metadata: 元数据
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
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
                execution_result = await self.get_chain_execution(execution_id)
                if execution_result["success"]:
                    execution = execution_result["data"]
                    current_metadata = execution.get("metadata", {}) if isinstance(execution, dict) else (execution.metadata or {})
                    current_metadata.update(metadata)
                    execution_data["metadata"] = current_metadata
                else:
                    execution_data["metadata"] = metadata
            
            # 更新执行记录
            execution = await self.repository.update_chain_execution(execution_id, execution_data)
            if not execution:
                return {
                    "success": False,
                    "error": "执行记录不存在或更新失败",
                    "error_code": "UPDATE_CHAIN_EXECUTION_FAILED"
                }
            
            return {
                "success": True,
                "data": execution.to_dict() if hasattr(execution, 'to_dict') else execution
            }
            
        except Exception as e:
            logger.error(f"更新链执行状态时出错: {str(e)}")
            return {
                "success": False,
                "error": f"更新链执行状态失败: {str(e)}",
                "error_code": "UPDATE_CHAIN_EXECUTION_STATUS_FAILED"
            }
    
    async def get_chain_execution(self, execution_id: Union[int, str]) -> Dict[str, Any]:
        """获取链执行记录
        
        Args:
            execution_id: 执行ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            execution = await self.repository.get_chain_execution(execution_id)
            if not execution:
                return {
                    "success": False,
                    "error": "执行记录不存在",
                    "error_code": "EXECUTION_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": execution.to_dict() if hasattr(execution, 'to_dict') else execution
            }
            
        except Exception as e:
            logger.error(f"获取链执行记录时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取链执行记录失败: {str(e)}",
                "error_code": "GET_CHAIN_EXECUTION_FAILED"
            }
    
    async def list_chain_executions(self,
                                   limit: int = 100, 
                                   offset: int = 0,
                                   user_id: Optional[int] = None,
                                   chain_id: Optional[Union[int, str]] = None,
                                   status: Optional[str] = None) -> Dict[str, Any]:
        """获取链执行记录列表
        
        Args:
            limit: 限制数量
            offset: 偏移量
            user_id: 用户ID过滤
            chain_id: 链ID过滤
            status: 状态过滤
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            executions, total = await self.repository.list_chain_executions(
                limit, offset, user_id, chain_id, status
            )
            
            execution_list = []
            for execution in executions:
                execution_data = execution.to_dict() if hasattr(execution, 'to_dict') else execution
                execution_list.append(execution_data)
            
            return {
                "success": True,
                "data": {
                    "executions": execution_list,
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }
            }
            
        except Exception as e:
            logger.error(f"获取链执行记录列表时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取链执行记录列表失败: {str(e)}",
                "error_code": "LIST_CHAIN_EXECUTIONS_FAILED"
            }
    
    # ============ Agent消息相关方法 ============
    
    async def create_agent_message(self,
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
                                 tool_calls: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
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
            Dict[str, Any]: 操作结果
        """
        try:
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
            
            return {
                "success": True,
                "data": message.to_dict() if hasattr(message, 'to_dict') else message
            }
            
        except Exception as e:
            logger.error(f"创建Agent消息时出错: {str(e)}")
            return {
                "success": False,
                "error": f"创建Agent消息失败: {str(e)}",
                "error_code": "CREATE_AGENT_MESSAGE_FAILED"
            }
    
    async def get_agent_message(self, message_id: Union[int, str]) -> Dict[str, Any]:
        """获取Agent消息
        
        Args:
            message_id: 消息ID，可以是数字ID或字符串消息ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            message = await self.repository.get_agent_message(message_id)
            if not message:
                return {
                    "success": False,
                    "error": "消息不存在",
                    "error_code": "MESSAGE_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": message.to_dict() if hasattr(message, 'to_dict') else message
            }
            
        except Exception as e:
            logger.error(f"获取Agent消息时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取Agent消息失败: {str(e)}",
                "error_code": "GET_AGENT_MESSAGE_FAILED"
            }
    
    async def list_agent_messages(self,
                                 limit: int = 100, 
                                 offset: int = 0,
                                 user_id: Optional[int] = None,
                                 agent_id: Optional[int] = None,
                                 agent_execution_id: Optional[str] = None,
                                 conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """获取Agent消息列表
        
        Args:
            limit: 限制数量
            offset: 偏移量
            user_id: 用户ID过滤
            agent_id: Agent ID过滤
            agent_execution_id: 执行ID过滤
            conversation_id: 对话ID过滤
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            messages, total = await self.repository.list_agent_messages(
                limit, offset, user_id, agent_id, agent_execution_id, conversation_id
            )
            
            message_list = []
            for message in messages:
                message_data = message.to_dict() if hasattr(message, 'to_dict') else message
                message_list.append(message_data)
            
            return {
                "success": True,
                "data": {
                    "messages": message_list,
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }
            }
            
        except Exception as e:
            logger.error(f"获取Agent消息列表时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取Agent消息列表失败: {str(e)}",
                "error_code": "LIST_AGENT_MESSAGES_FAILED"
            } 