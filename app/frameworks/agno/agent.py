"""
Agno Agent动态实现 - 基于系统配置的动态Agent
与动态Agent工厂集成，支持从前端配置和系统配置动态创建Agent
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, AsyncGenerator

from app.frameworks.agno.dynamic_agent_factory import get_agent_factory, create_dynamic_agent
from app.frameworks.agno.config import get_user_agno_config, get_system_agno_config
from app.frameworks.agno.model_config_adapter import get_model_adapter, ModelType

# 动态导入Agno组件
try:
    from agno.agent import Agent as AgnoAgent
    from agno.team import Team as AgnoTeam
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False
    AgnoAgent = object
    AgnoTeam = object

logger = logging.getLogger(__name__)

class DynamicAgnoKnowledgeAgent:
    """
    动态Agno知识代理 - 基于系统配置
    不再使用硬编码的模型和工具，而是从系统配置和用户配置动态获取
    """
    
    def __init__(
        self,
        name: str = "Knowledge Agent",
        role: str = "AI Assistant", 
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ):
        self.name = name
        self.role = role
        self.user_id = user_id
        self.session_id = session_id
        self.kwargs = kwargs
        
        # 动态创建的Agent实例
        self._agent_instance: Optional[AgnoAgent] = None
        self._is_initialized = False
    
    async def initialize(self):
        """异步初始化Agent"""
        if self._is_initialized:
            return
        
        try:
            # 从系统配置创建Agent配置
            agent_config = await self._build_agent_config()
            
            # 使用动态工厂创建Agent
            self._agent_instance = await create_dynamic_agent(
                agent_config=agent_config,
                user_id=self.user_id or "system",
                session_id=self.session_id
            )
            
            if self._agent_instance:
                self._is_initialized = True
                logger.info(f"成功初始化动态Agent: {self.name}")
            else:
                logger.error(f"初始化动态Agent失败: {self.name}")
                
        except Exception as e:
            logger.error(f"初始化Agent失败: {str(e)}", exc_info=True)
    
    async def _build_agent_config(self) -> Dict[str, Any]:
        """构建Agent配置"""
        try:
            # 获取用户配置或系统配置
            if self.user_id:
                agno_config = await get_user_agno_config(self.user_id)
            else:
                agno_config = await get_system_agno_config()
            
            # 构建基础配置
            agent_config = {
                "name": self.name,
                "role": self.role,
                "description": self.kwargs.get("description", f"A {self.role} assistant"),
                "instructions": self.kwargs.get("instructions", []),
                "model_config": {
                    "model_id": agno_config.models.default_chat_model,
                    "type": "chat"
                },
                "tools": await self._get_enabled_tools(agno_config),
                "knowledge_bases": self.kwargs.get("knowledge_bases", []),
                "show_tool_calls": agno_config.features.show_tool_calls,
                "markdown": agno_config.features.markdown,
                "max_loops": self.kwargs.get("max_loops", 10)
            }
            
            return agent_config
            
        except Exception as e:
            logger.error(f"构建Agent配置失败: {str(e)}")
            # 返回最小配置
            return {
                "name": self.name,
                "role": self.role,
                "model_config": {"type": "chat"},
                "tools": [],
                "knowledge_bases": []
            }
    
    async def _get_enabled_tools(self, agno_config) -> List[Dict[str, Any]]:
        """获取启用的工具配置"""
        tools = []
        
        try:
            # 从系统配置获取启用的工具
            enabled_tool_ids = agno_config.tools.enabled_tools
            
            if self.user_id:
                # 获取用户有权限的工具
                from app.services.tools.tool_service import ToolService
                from app.utils.core.database import get_db
                
                db = next(get_db())
                tool_service = ToolService(db)
                
                for tool_id in enabled_tool_ids:
                    has_permission = await tool_service.check_tool_permission(
                        self.user_id, tool_id
                    )
                    if has_permission:
                        tools.append({
                            "tool_id": tool_id,
                            "params": {}
                        })
            else:
                # 系统级别，直接使用所有启用的工具
                for tool_id in enabled_tool_ids:
                    tools.append({
                        "tool_id": tool_id,
                        "params": {}
                    })
            
            logger.info(f"为Agent {self.name} 配置了 {len(tools)} 个工具")
            return tools
            
        except Exception as e:
            logger.error(f"获取启用工具失败: {str(e)}")
            return []
    
    @property
    async def agno_agent(self) -> Optional[AgnoAgent]:
        """获取底层Agno Agent实例"""
        if not self._is_initialized:
            await self.initialize()
        return self._agent_instance
    
    async def query(self, query_str: str, **kwargs) -> str:
        """
        执行查询 - 兼容原接口
        """
        agent = await self.agno_agent
        if not agent:
            return "Error: Agent not initialized"
        
        try:
            # 使用动态Agent执行查询
            if hasattr(agent, 'aquery'):
                response = await agent.aquery(query_str, **kwargs)
            else:
                # 兼容同步接口
                response = await asyncio.create_task(
                    asyncio.to_thread(agent.query, query_str, **kwargs)
                )
            
            return str(response)
                
        except Exception as e:
            logger.error(f"Agent查询失败: {str(e)}")
            return f"Error processing query: {str(e)}"
    
    async def aquery(self, query_str: str, **kwargs) -> str:
        """异步查询"""
        return await self.query(query_str, **kwargs)
    
    async def stream_query(self, query_str: str, **kwargs) -> AsyncGenerator[str, None]:
        """
        流式查询 - 生成器接口
        """
        agent = await self.agno_agent
        if not agent:
            yield "Error: Agent not initialized"
            return
        
        try:
            # 使用动态Agent的流式查询
            if hasattr(agent, 'astream_query'):
                async for chunk in agent.astream_query(query_str, **kwargs):
                    yield str(chunk)
            else:
                # 兜底方案
                response = await self.query(query_str, **kwargs)
                yield response
                
        except Exception as e:
            logger.error(f"Agent流式查询失败: {str(e)}")
            yield f"Error: {str(e)}"

class DynamicAgnoTeam:
    """
    动态Agno团队 - 基于系统配置
    支持动态创建多Agent协作团队
    """
    
    def __init__(
        self,
        name: str = "Agent Team",
        agents_config: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        **kwargs
    ):
        self.name = name
        self.agents_config = agents_config or []
        self.user_id = user_id
        self.kwargs = kwargs
        
        self._team_instance: Optional[AgnoTeam] = None
        self._agents: List[DynamicAgnoKnowledgeAgent] = []
        self._is_initialized = False
    
    async def initialize(self):
        """初始化团队"""
        if self._is_initialized:
            return
        
        try:
            # 创建团队成员
            for agent_config in self.agents_config:
                agent = DynamicAgnoKnowledgeAgent(
                    name=agent_config.get("name", "Team Member"),
                    role=agent_config.get("role", "Assistant"),
                    user_id=self.user_id,
                    **agent_config
                )
                await agent.initialize()
                self._agents.append(agent)
            
            # 创建团队配置
            team_config = await self._build_team_config()
            
            # 使用动态工厂创建团队
            factory = get_agent_factory()
            self._team_instance = await factory.create_team_from_config(
                team_config, self.user_id or "system"
            )
            
            if self._team_instance:
                self._is_initialized = True
                logger.info(f"成功初始化动态团队: {self.name}")
            
        except Exception as e:
            logger.error(f"初始化团队失败: {str(e)}", exc_info=True)
    
    async def _build_team_config(self) -> Dict[str, Any]:
        """构建团队配置"""
        return {
            "name": self.name,
            "agents": self.agents_config,
            "model_config": {"type": "chat"},
            "mode": self.kwargs.get("mode", "sequential"),
            "instructions": self.kwargs.get("instructions", []),
            "success_criteria": self.kwargs.get("success_criteria")
        }
    
    async def query(self, query_str: str, **kwargs) -> str:
        """团队查询"""
        if not self._is_initialized:
            await self.initialize()
        
        if not self._team_instance:
            return "Error: Team not initialized"
        
        try:
            if hasattr(self._team_instance, 'aquery'):
                response = await self._team_instance.aquery(query_str, **kwargs)
            else:
                response = await asyncio.create_task(
                    asyncio.to_thread(self._team_instance.query, query_str, **kwargs)
                )
            return str(response)
            
        except Exception as e:
            logger.error(f"团队查询失败: {str(e)}")
            return f"Error processing team query: {str(e)}"

# 动态Agent创建函数
async def create_dynamic_knowledge_agent(
    name: str = "Knowledge Agent",
    role: str = "AI Assistant",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs
) -> DynamicAgnoKnowledgeAgent:
    """创建动态知识Agent"""
    agent = DynamicAgnoKnowledgeAgent(
        name=name,
        role=role, 
        user_id=user_id,
        session_id=session_id,
        **kwargs
    )
    await agent.initialize()
    return agent

async def create_dynamic_research_agent(
    name: str = "Research Agent",
    user_id: Optional[str] = None,
    **kwargs
) -> DynamicAgnoKnowledgeAgent:
    """创建动态研究Agent"""
    # 从系统配置获取研究相关的工具
    if user_id:
        agno_config = await get_user_agno_config(user_id)
    else:
        agno_config = await get_system_agno_config()
    
    # 过滤出搜索和推理相关的工具
    research_tools = []
    for tool_id in agno_config.tools.enabled_tools:
        # 这里可以根据工具类别过滤
        if "search" in tool_id.lower() or "reasoning" in tool_id.lower():
            research_tools.append(tool_id)
    
    return await create_dynamic_knowledge_agent(
        name=name,
        role="Research and Analysis Specialist",
        user_id=user_id,
        instructions=[
            "You are a research specialist who excels at finding and analyzing information",
            "Use available search tools to gather current information when needed",
            "Apply reasoning tools to provide well-structured analysis",
            "Always cite sources and provide evidence-based responses"
        ],
        **kwargs
    )

async def create_dynamic_assistant_agent(
    name: str = "AI Assistant",
    user_id: Optional[str] = None,
    **kwargs
) -> DynamicAgnoKnowledgeAgent:
    """创建动态助手Agent"""
    return await create_dynamic_knowledge_agent(
        name=name,
        role="General AI Assistant",
        user_id=user_id,
        instructions=[
            "You are a helpful AI assistant",
            "Provide accurate and helpful responses",
            "Use available tools when necessary",
            "Be friendly and professional"
        ],
        **kwargs
    )

async def create_dynamic_multi_agent_team(
    agents_config: List[Dict[str, Any]],
    name: str = "Multi-Agent Team",
    user_id: Optional[str] = None,
    **kwargs
) -> DynamicAgnoTeam:
    """创建动态多Agent团队"""
    team = DynamicAgnoTeam(
        name=name,
        agents_config=agents_config,
        user_id=user_id,
        **kwargs
    )
    await team.initialize()
    return team

# 兼容性别名
AgnoKnowledgeAgent = DynamicAgnoKnowledgeAgent
AgnoTeam = DynamicAgnoTeam
KnowledgeAgent = DynamicAgnoKnowledgeAgent
AgentTeam = DynamicAgnoTeam

# 导出主要组件
__all__ = [
    "DynamicAgnoKnowledgeAgent",
    "DynamicAgnoTeam",
    "create_dynamic_knowledge_agent",
    "create_dynamic_research_agent", 
    "create_dynamic_assistant_agent",
    "create_dynamic_multi_agent_team",
    "AgnoKnowledgeAgent",
    "AgnoTeam",
    "KnowledgeAgent",
    "AgentTeam"
]
