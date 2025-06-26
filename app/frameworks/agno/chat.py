"""
Agno聊天模块动态实现
基于系统配置和用户权限的动态聊天功能，与ZZDSJ聊天管理器集成
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator, Union
from datetime import datetime
import uuid

from app.frameworks.agno.dynamic_agent_factory import get_agent_factory
from app.frameworks.agno.config import get_user_agno_config, get_system_agno_config
from app.frameworks.agno.model_config_adapter import get_model_adapter, ModelType

# 动态导入Agno组件
try:
    from agno.agent import Agent as AgnoAgent
    from agno.memory import Memory as AgnoMemory
    from agno.storage import Storage as AgnoStorage
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False
    AgnoAgent = object
    AgnoMemory = object
    AgnoStorage = object

logger = logging.getLogger(__name__)

class DynamicAgnoChatManager:
    """
    动态Agno聊天管理器 - 基于系统配置
    与ZZDSJ聊天系统集成，支持动态模型和工具配置
    """
    
    def __init__(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        chat_config: Optional[Dict[str, Any]] = None
    ):
        self.user_id = user_id
        self.session_id = session_id or str(uuid.uuid4())
        self.chat_config = chat_config or {}
        
        # 动态组件
        self._agent_factory = get_agent_factory()
        self._model_adapter = get_model_adapter()
        self._current_agent = None
        self._is_initialized = False
        
        # 聊天状态
        self._conversation_history: List[Dict[str, Any]] = []
        self._agent_config: Optional[Dict[str, Any]] = None
    
    async def initialize(self):
        """初始化聊天管理器"""
        if self._is_initialized:
            return
        
        try:
            # 获取配置
            if self.user_id:
                agno_config = await get_user_agno_config(self.user_id)
            else:
                agno_config = await get_system_agno_config()
            
            # 构建默认Agent配置
            self._agent_config = await self._build_chat_agent_config(agno_config)
            
            # 创建默认聊天Agent
            await self._create_chat_agent()
            
            self._is_initialized = True
            logger.info(f"聊天管理器初始化成功 - Session: {self.session_id}")
            
        except Exception as e:
            logger.error(f"聊天管理器初始化失败: {str(e)}")
    
    async def _build_chat_agent_config(self, agno_config) -> Dict[str, Any]:
        """构建聊天Agent配置"""
        return {
            "name": self.chat_config.get("agent_name", "Chat Assistant"),
            "role": self.chat_config.get("agent_role", "AI Assistant"),
            "description": "A conversational AI assistant",
            "instructions": [
                "You are a helpful AI assistant",
                "Provide accurate and helpful responses",
                "Maintain conversation context",
                "Use available tools when necessary"
            ],
            "model_config": {
                "model_id": agno_config.models.default_chat_model,
                "type": "chat",
                "temperature": agno_config.models.temperature,
                "max_tokens": agno_config.models.max_tokens
            },
            "tools": await self._get_enabled_tools(agno_config),
            "knowledge_bases": self.chat_config.get("knowledge_bases", []),
            "show_tool_calls": agno_config.features.show_tool_calls,
            "markdown": agno_config.features.markdown,
            "memory_config": {
                "type": agno_config.memory.memory_type,
                "max_size": agno_config.memory.max_memory_size
            }
        }
    
    async def _get_enabled_tools(self, agno_config) -> List[Dict[str, Any]]:
        """获取启用的工具"""
        tools = []
        
        try:
            if self.user_id:
                # 获取用户权限的工具
                from app.services.tools.tool_service import ToolService
                from app.utils.core.database import get_db
                
                db = next(get_db())
                tool_service = ToolService(db)
                
                for tool_id in agno_config.tools.enabled_tools:
                    has_permission = await tool_service.check_tool_permission(
                        self.user_id, tool_id
                    )
                    if has_permission:
                        tools.append({"tool_id": tool_id, "params": {}})
            else:
                # 系统级别工具
                for tool_id in agno_config.tools.enabled_tools:
                    tools.append({"tool_id": tool_id, "params": {}})
            
            return tools
            
        except Exception as e:
            logger.error(f"获取启用工具失败: {str(e)}")
            return []
    
    async def _create_chat_agent(self):
        """创建聊天Agent"""
        try:
            from app.frameworks.agno.dynamic_agent_factory import create_dynamic_agent
            
            self._current_agent = await create_dynamic_agent(
                agent_config=self._agent_config,
                user_id=self.user_id or "system",
                session_id=self.session_id
            )
            
            if self._current_agent:
                logger.info(f"聊天Agent创建成功")
            else:
                logger.error(f"聊天Agent创建失败")
                
        except Exception as e:
            logger.error(f"创建聊天Agent失败: {str(e)}")
    
    async def send_message(
        self,
        message: str,
        stream: bool = False,
        include_history: bool = True,
        **kwargs
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        发送消息到聊天Agent
        
        Args:
            message: 用户消息
            stream: 是否流式响应
            include_history: 是否包含历史上下文
            **kwargs: 其他参数
            
        Returns:
            响应结果或流式生成器
        """
        if not self._is_initialized:
            await self.initialize()
        
        if not self._current_agent:
            return "Error: Chat agent not available"
        
        try:
            # 构建完整的对话上下文
            if include_history and self._conversation_history:
                # 构建包含历史的提示
                context_prompt = self._build_context_prompt(message)
            else:
                context_prompt = message
            
            # 记录用户消息
            user_message = {
                "role": "user",
                "content": message,
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id
            }
            self._conversation_history.append(user_message)
            
            # 获取Agent响应
            if stream:
                return self._stream_chat_response(context_prompt, **kwargs)
            else:
                response = await self._get_chat_response(context_prompt, **kwargs)
                
                # 记录Agent响应
                agent_message = {
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now().isoformat(),
                    "session_id": self.session_id
                }
                self._conversation_history.append(agent_message)
                
                return response
                
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
            return f"Error processing message: {str(e)}"
    
    def _build_context_prompt(self, current_message: str) -> str:
        """构建包含历史的上下文提示"""
        try:
            # 获取最近的几条对话
            recent_history = self._conversation_history[-10:]  # 最近10条
            
            context_parts = ["Previous conversation context:"]
            for msg in recent_history:
                role = "User" if msg["role"] == "user" else "Assistant"
                context_parts.append(f"{role}: {msg['content']}")
            
            context_parts.append(f"\nCurrent message:\nUser: {current_message}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"构建上下文提示失败: {str(e)}")
            return current_message
    
    async def _get_chat_response(self, prompt: str, **kwargs) -> str:
        """获取聊天响应"""
        try:
            # 使用Agent处理消息
            if hasattr(self._current_agent, 'aquery'):
                response = await self._current_agent.aquery(prompt, **kwargs)
            elif hasattr(self._current_agent, 'query'):
                response = await asyncio.create_task(
                    asyncio.to_thread(self._current_agent.query, prompt, **kwargs)
                )
            else:
                response = "Error: Agent does not support querying"
            
            return str(response)
            
        except Exception as e:
            logger.error(f"获取聊天响应失败: {str(e)}")
            return f"Error generating response: {str(e)}"
    
    async def _stream_chat_response(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """流式聊天响应"""
        try:
            if hasattr(self._current_agent, 'astream_query'):
                # 收集所有响应内容用于历史记录
                response_content = ""
                
                async for chunk in self._current_agent.astream_query(prompt, **kwargs):
                    chunk_str = str(chunk)
                    response_content += chunk_str
                    yield chunk_str
                
                # 记录完整响应到历史
                agent_message = {
                    "role": "assistant",
                    "content": response_content,
                    "timestamp": datetime.now().isoformat(),
                    "session_id": self.session_id
                }
                self._conversation_history.append(agent_message)
                
            else:
                # 兜底：非流式响应
                response = await self._get_chat_response(prompt, **kwargs)
                yield response
                
        except Exception as e:
            logger.error(f"流式响应失败: {str(e)}")
            yield f"Error: {str(e)}"
    
    async def update_agent_config(self, config_updates: Dict[str, Any]):
        """更新Agent配置"""
        try:
            # 更新配置
            if self._agent_config:
                self._agent_config.update(config_updates)
            
            # 重新创建Agent
            await self._create_chat_agent()
            
            logger.info(f"Agent配置更新成功")
            
        except Exception as e:
            logger.error(f"更新Agent配置失败: {str(e)}")
    
    async def switch_model(self, model_id: str):
        """切换聊天模型"""
        try:
            config_updates = {
                "model_config": {
                    "model_id": model_id,
                    "type": "chat"
                }
            }
            await self.update_agent_config(config_updates)
            
        except Exception as e:
            logger.error(f"切换模型失败: {str(e)}")
    
    async def add_tools(self, tool_ids: List[str]):
        """添加工具到当前Agent"""
        try:
            # 验证工具权限
            validated_tools = []
            
            if self.user_id:
                from app.services.tools.tool_service import ToolService
                from app.utils.core.database import get_db
                
                db = next(get_db())
                tool_service = ToolService(db)
                
                for tool_id in tool_ids:
                    has_permission = await tool_service.check_tool_permission(
                        self.user_id, tool_id
                    )
                    if has_permission:
                        validated_tools.append({"tool_id": tool_id, "params": {}})
            else:
                validated_tools = [{"tool_id": tid, "params": {}} for tid in tool_ids]
            
            # 更新配置
            current_tools = self._agent_config.get("tools", [])
            updated_tools = current_tools + validated_tools
            
            config_updates = {"tools": updated_tools}
            await self.update_agent_config(config_updates)
            
            logger.info(f"成功添加 {len(validated_tools)} 个工具")
            
        except Exception as e:
            logger.error(f"添加工具失败: {str(e)}")
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """获取对话历史"""
        return self._conversation_history.copy()
    
    def clear_conversation_history(self):
        """清空对话历史"""
        self._conversation_history.clear()
        logger.info(f"会话历史已清空 - Session: {self.session_id}")
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """获取Agent状态"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "is_initialized": self._is_initialized,
            "agent_available": self._current_agent is not None,
            "agent_config": self._agent_config,
            "conversation_length": len(self._conversation_history),
            "last_activity": self._conversation_history[-1]["timestamp"] if self._conversation_history else None
        }

class DynamicAgnoChatSession:
    """动态Agno聊天会话"""
    
    def __init__(self, user_id: str, session_id: Optional[str] = None):
        self.user_id = user_id
        self.session_id = session_id or str(uuid.uuid4())
        self.chat_manager = DynamicAgnoChatManager(user_id, self.session_id)
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
    
    async def send(self, message: str, **kwargs) -> str:
        """发送消息"""
        self.last_activity = datetime.now()
        return await self.chat_manager.send_message(message, **kwargs)
    
    async def stream(self, message: str, **kwargs) -> AsyncGenerator[str, None]:
        """流式发送消息"""
        self.last_activity = datetime.now()
        async for chunk in await self.chat_manager.send_message(message, stream=True, **kwargs):
            yield chunk
    
    def get_history(self) -> List[Dict[str, Any]]:
        """获取历史记录"""
        return self.chat_manager.get_conversation_history()
    
    def clear_history(self):
        """清空历史记录"""
        self.chat_manager.clear_conversation_history()

# 会话管理器
class DynamicAgnoChatSessionManager:
    """动态Agno聊天会话管理器"""
    
    def __init__(self):
        self._sessions: Dict[str, DynamicAgnoChatSession] = {}
    
    async def create_session(self, user_id: str, session_id: Optional[str] = None) -> DynamicAgnoChatSession:
        """创建聊天会话"""
        session = DynamicAgnoChatSession(user_id, session_id)
        await session.chat_manager.initialize()
        
        self._sessions[session.session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[DynamicAgnoChatSession]:
        """获取聊天会话"""
        return self._sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """删除聊天会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def get_user_sessions(self, user_id: str) -> List[DynamicAgnoChatSession]:
        """获取用户的所有会话"""
        return [session for session in self._sessions.values() if session.user_id == user_id]

# 全局会话管理器
_global_session_manager: Optional[DynamicAgnoChatSessionManager] = None

def get_session_manager() -> DynamicAgnoChatSessionManager:
    """获取全局会话管理器"""
    global _global_session_manager
    if _global_session_manager is None:
        _global_session_manager = DynamicAgnoChatSessionManager()
    return _global_session_manager

# 便利函数
async def create_chat_session(user_id: str, session_id: Optional[str] = None) -> DynamicAgnoChatSession:
    """创建聊天会话"""
    manager = get_session_manager()
    return await manager.create_session(user_id, session_id)

async def create_simple_chat(user_id: Optional[str] = None, **kwargs) -> DynamicAgnoChatManager:
    """创建简单聊天实例"""
    chat_manager = DynamicAgnoChatManager(user_id=user_id, **kwargs)
    await chat_manager.initialize()
    return chat_manager

# 兼容性别名
AgnoChatEngine = DynamicAgnoChatManager
AgnoContextChatEngine = DynamicAgnoChatManager
ChatEngine = DynamicAgnoChatManager
ContextChatEngine = DynamicAgnoChatManager

# 导出主要组件
__all__ = [
    "DynamicAgnoChatManager",
    "DynamicAgnoChatSession",
    "DynamicAgnoChatSessionManager",
    "get_session_manager",
    "create_chat_session",
    "create_simple_chat",
    "AgnoChatEngine",
    "AgnoContextChatEngine",
    "ChatEngine",
    "ContextChatEngine"
] 