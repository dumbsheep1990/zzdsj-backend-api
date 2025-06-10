"""
Agno框架聊天管理器适配器

将现有的ZZDSJ聊天管理器逻辑迁移到Agno框架，提供统一的聊天会话管理
根据Agno官方文档实现聊天代理和会话管理
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

# Agno核心导入 - 根据官方文档语法
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.memory.agent_memory import AgentMemory
from agno.storage.agent_storage import AgentStorage
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools

# ZZDSJ内部组件导入
from .core import ZZDSJAgnoCore
from .memory_adapter import ZZDSJMemoryAdapter

logger = logging.getLogger(__name__)


@dataclass
class ChatSession:
    """聊天会话数据结构"""
    session_id: str
    user_id: str
    agent_id: str
    created_at: str
    updated_at: str
    message_count: int
    status: str  # "active", "ended", "paused"
    metadata: Dict[str, Any] = None


@dataclass
class ChatMessage:
    """聊天消息数据结构"""
    message_id: str
    session_id: str
    role: str  # "user", "agent", "system"
    content: str
    timestamp: str
    agent_id: Optional[str] = None
    metadata: Dict[str, Any] = None


class ZZDSJAgnoChatManager:
    """ZZDSJ Agno聊天管理器适配器"""
    
    def __init__(self):
        """初始化聊天管理器"""
        self.agno_core = ZZDSJAgnoCore()
        self.memory_adapter = ZZDSJMemoryAdapter()
        
        # 导入模型配置适配器
        from .model_config_adapter import get_model_adapter
        self.model_adapter = get_model_adapter()
        
        # 会话存储
        self.sessions: Dict[str, ChatSession] = {}
        self.messages: Dict[str, List[ChatMessage]] = {}
        
        # 代理注册表
        self.chat_agents: Dict[str, Agent] = {}
        self.chat_teams: Dict[str, Team] = {}
        
        # 初始化默认聊天代理（延迟到第一次调用时执行）
        self._agents_initialized = False
        
        logger.info("Agno聊天管理器初始化完成")

    async def _setup_default_chat_agents(self):
        """设置默认聊天代理"""
        try:
            # 获取配置化的模型
            general_model = await self.model_adapter.create_agno_model()
            search_model = await self.model_adapter.create_agno_model()
            team_model = await self.model_adapter.create_agno_model()
            
            # 如果模型创建失败，使用默认回退
            if not general_model:
                general_model = OpenAIChat(id="gpt-4o")
            if not search_model:
                search_model = OpenAIChat(id="gpt-4o") 
            if not team_model:
                team_model = OpenAIChat(id="gpt-4o")
            
            # 通用聊天助手 - 根据Agno官方文档语法
            general_chat_agent = Agent(
                model=general_model,
                name="General Chat Assistant",
                description="通用聊天助手，可以进行各种日常对话",
                instructions=[
                    "作为一个友好、有用的AI助手",
                    "以自然、对话的方式回应用户",
                    "如果不确定某些信息，诚实地表达不确定性",
                    "保持对话的连贯性和上下文"
                ],
                markdown=True
            )
            self.chat_agents["general"] = general_chat_agent
            
            # 智能搜索助手
            search_chat_agent = Agent(
                model=search_model,
                name="Search Chat Assistant",
                description="具备搜索能力的聊天助手",
                tools=[DuckDuckGoTools()],
                instructions=[
                    "使用搜索工具获取最新信息回答用户问题",
                    "总是验证搜索结果的可靠性",
                    "在回答中包含信息来源",
                    "以对话的方式呈现搜索结果"
                ],
                show_tool_calls=True,
                markdown=True
            )
            self.chat_agents["search"] = search_chat_agent
            
            # 创建协作团队 - 根据Agno官方文档的Team语法
            collaborative_team = Team(
                mode="coordinate",
                members=[search_chat_agent],
                model=team_model,
                name="Collaborative Chat Team",
                instructions=[
                    "协调搜索能力",
                    "提供全面的信息和分析",
                    "确保回答的准确性和实用性",
                    "保持友好的对话风格"
                ],
                show_tool_calls=True,
                markdown=True
            )
            self.chat_teams["collaborative"] = collaborative_team
            
            self._agents_initialized = True
            logger.info("默认聊天代理设置完成")
            
        except Exception as e:
            logger.error(f"设置默认聊天代理失败: {e}")
            self._agents_initialized = False

    async def _ensure_agents_initialized(self):
        """确保代理已初始化"""
        if not self._agents_initialized:
            await self._setup_default_chat_agents()

    async def create_chat_session(
        self, 
        user_id: str, 
        agent_id: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """创建新的聊天会话"""
        try:
            # 确保代理已初始化
            await self._ensure_agents_initialized()
            
            session_id = str(uuid.uuid4())
            
            # 验证代理存在
            if agent_id not in self.chat_agents and agent_id not in self.chat_teams:
                raise ValueError(f"代理 {agent_id} 不存在")
            
            # 创建会话
            session = ChatSession(
                session_id=session_id,
                user_id=user_id,
                agent_id=agent_id,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                message_count=0,
                status="active",
                metadata=metadata or {}
            )
            
            self.sessions[session_id] = session
            self.messages[session_id] = []
            
            logger.info(f"创建聊天会话: {session_id}, 用户: {user_id}, 代理: {agent_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"创建聊天会话失败: {e}")
            raise

    async def send_message(
        self,
        session_id: str,
        content: str,
        role: str = "user",
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """发送聊天消息"""
        try:
            # 验证会话存在
            if session_id not in self.sessions:
                raise ValueError(f"会话 {session_id} 不存在")
            
            session = self.sessions[session_id]
            agent_id = session.agent_id
            
            # 记录用户消息
            user_message = ChatMessage(
                message_id=str(uuid.uuid4()),
                session_id=session_id,
                role=role,
                content=content,
                timestamp=datetime.now().isoformat(),
                agent_id=agent_id
            )
            self.messages[session_id].append(user_message)
            
            # 获取代理响应
            if agent_id in self.chat_agents:
                agent = self.chat_agents[agent_id]
                response = await self._get_agent_response(agent, content, stream)
            elif agent_id in self.chat_teams:
                team = self.chat_teams[agent_id]
                response = await self._get_team_response(team, content, stream)
            else:
                raise ValueError(f"代理 {agent_id} 不存在")
            
            # 处理响应
            if stream:
                # 流式响应
                async def stream_response():
                    response_content = ""
                    async for chunk in response:
                        response_content += chunk
                        yield chunk
                    
                    # 记录代理响应
                    agent_message = ChatMessage(
                        message_id=str(uuid.uuid4()),
                        session_id=session_id,
                        role="agent",
                        content=response_content,
                        timestamp=datetime.now().isoformat(),
                        agent_id=agent_id
                    )
                    self.messages[session_id].append(agent_message)
                    
                    # 更新会话
                    session.message_count += 2
                    session.updated_at = datetime.now().isoformat()
                
                return stream_response()
            else:
                # 非流式响应
                # 记录代理响应
                agent_message = ChatMessage(
                    message_id=str(uuid.uuid4()),
                    session_id=session_id,
                    role="agent",
                    content=response,
                    timestamp=datetime.now().isoformat(),
                    agent_id=agent_id
                )
                self.messages[session_id].append(agent_message)
                
                # 更新会话
                session.message_count += 2
                session.updated_at = datetime.now().isoformat()
                
                return response
                
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            raise

    async def _get_agent_response(
        self, 
        agent: Agent, 
        message: str, 
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """获取代理响应"""
        try:
            if stream:
                # 流式响应 - 根据Agno文档，使用print_response方法
                async def generate_stream():
                    response = agent.print_response(message, stream=True)
                    # 注意：实际的Agno流式响应可能需要不同的处理方式
                    if hasattr(response, '__aiter__'):
                        async for chunk in response:
                            yield str(chunk)
                    else:
                        yield str(response)
                
                return generate_stream()
            else:
                # 非流式响应
                response = agent.print_response(message, stream=False)
                return str(response)
                
        except Exception as e:
            logger.error(f"获取代理响应失败: {e}")
            raise

    async def _get_team_response(
        self, 
        team: Team, 
        message: str, 
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """获取团队响应"""
        try:
            if stream:
                # 流式响应
                async def generate_stream():
                    response = team.print_response(message, stream=True)
                    if hasattr(response, '__aiter__'):
                        async for chunk in response:
                            yield str(chunk)
                    else:
                        yield str(response)
                
                return generate_stream()
            else:
                # 非流式响应
                response = team.print_response(message, stream=False)
                return str(response)
                
        except Exception as e:
            logger.error(f"获取团队响应失败: {e}")
            raise

    async def get_chat_history(
        self, 
        session_id: str, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """获取聊天历史"""
        try:
            if session_id not in self.messages:
                return []
            
            messages = self.messages[session_id]
            if limit:
                messages = messages[-limit:]
            
            return [asdict(msg) for msg in messages]
            
        except Exception as e:
            logger.error(f"获取聊天历史失败: {e}")
            raise

    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        try:
            if session_id not in self.sessions:
                return None
            
            session = self.sessions[session_id]
            return asdict(session)
            
        except Exception as e:
            logger.error(f"获取会话信息失败: {e}")
            raise

    async def end_session(self, session_id: str) -> bool:
        """结束聊天会话"""
        try:
            if session_id not in self.sessions:
                return False
            
            self.sessions[session_id].status = "ended"
            self.sessions[session_id].updated_at = datetime.now().isoformat()
            
            logger.info(f"结束聊天会话: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"结束会话失败: {e}")
            return False

    async def list_user_sessions(
        self, 
        user_id: str, 
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """列出用户的会话"""
        try:
            user_sessions = [
                asdict(session) 
                for session in self.sessions.values() 
                if session.user_id == user_id and (not status or session.status == status)
            ]
            
            return sorted(user_sessions, key=lambda x: x['updated_at'], reverse=True)
            
        except Exception as e:
            logger.error(f"列出用户会话失败: {e}")
            raise

    async def cleanup_old_sessions(self, days: int = 7):
        """清理旧会话"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            sessions_to_remove = []
            for session_id, session in self.sessions.items():
                session_time = datetime.fromisoformat(session.updated_at)
                if session_time < cutoff_time:
                    sessions_to_remove.append(session_id)
            
            for session_id in sessions_to_remove:
                del self.sessions[session_id]
                if session_id in self.messages:
                    del self.messages[session_id]
            
            logger.info(f"清理了 {len(sessions_to_remove)} 个旧会话")
            return len(sessions_to_remove)
            
        except Exception as e:
            logger.error(f"清理旧会话失败: {e}")
            return 0

    async def get_agent_list(self) -> Dict[str, List[str]]:
        """获取可用代理列表"""
        try:
            return {
                "agents": list(self.chat_agents.keys()),
                "teams": list(self.chat_teams.keys())
            }
        except Exception as e:
            logger.error(f"获取代理列表失败: {e}")
            return {"agents": [], "teams": []}


# 全局聊天管理器实例
_chat_manager: Optional[ZZDSJAgnoChatManager] = None


def get_chat_manager() -> ZZDSJAgnoChatManager:
    """获取全局聊天管理器实例"""
    global _chat_manager
    if _chat_manager is None:
        _chat_manager = ZZDSJAgnoChatManager()
    return _chat_manager


async def init_chat_manager():
    """初始化聊天管理器"""
    global _chat_manager
    _chat_manager = ZZDSJAgnoChatManager()
    logger.info("Agno聊天管理器全局初始化完成") 