"""
Agno Agent实现 - 使用正确的官方Agno Agent API
基于官方文档的真实Agno Agent接口，确保语法和方法调用的正确性
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, AsyncGenerator, Callable
from datetime import datetime

# 使用正确的Agno官方API导入
from agno.agent import Agent as AgnoAgent
from agno.team import Team as AgnoTeam
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.tools.reasoning import ReasoningTools
from agno.tools.yfinance import YFinanceTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.memory import Memory as AgnoMemory
from agno.storage import Storage as AgnoStorage

from app.frameworks.agno.core import AgnoLLMInterface, AgnoServiceContext

logger = logging.getLogger(__name__)

class AgnoKnowledgeAgent:
    """
    Agno知识代理 - 使用官方Agno Agent API
    为知识库查询和推理提供统一接口，保持与LlamaIndex的兼容性
    """
    
    def __init__(
        self,
        name: str = "Knowledge Agent",
        role: str = "AI Assistant",
        model: Optional[Union[str, AgnoLLMInterface]] = None,
        tools: Optional[List[Any]] = None,
        knowledge: Optional[Any] = None,
        memory: Optional[AgnoMemory] = None,
        storage: Optional[AgnoStorage] = None,
        instructions: Optional[Union[str, List[str]]] = None,
        description: Optional[str] = None,
        reasoning_enabled: bool = True,
        show_tool_calls: bool = False,
        markdown: bool = True,
        **kwargs
    ):
        self.name = name
        self.role = role
        self.reasoning_enabled = reasoning_enabled
        
        # 处理模型配置
        if isinstance(model, str):
            self._agno_model = self._create_model_from_string(model)
        elif isinstance(model, AgnoLLMInterface):
            self._agno_model = model.agno_model
        else:
            # 默认使用GPT-4o
            self._agno_model = OpenAIChat(id="gpt-4o")
        
        # 处理工具配置
        self._tools = self._prepare_tools(tools, reasoning_enabled)
        
        # 处理指令配置
        if isinstance(instructions, str):
            instructions = [instructions]
        elif instructions is None:
            instructions = [f"You are {name}, {role}. Provide helpful and accurate responses."]
        
        # 创建Agno Agent实例
        self._agno_agent = AgnoAgent(
            name=name,
            role=role,
            model=self._agno_model,
            tools=self._tools,
            knowledge=knowledge,
            memory=memory,
            storage=storage,
            instructions=instructions,
            description=description or f"An AI agent specialized in {role.lower()}",
            show_tool_calls=show_tool_calls,
            markdown=markdown,
            **kwargs
        )
        
        # 存储配置以便后续使用
        self._knowledge = knowledge
        self._memory = memory
        self._storage = storage
    
    def _create_model_from_string(self, model_name: str):
        """从字符串创建Agno模型实例"""
        if "claude" in model_name.lower():
            return Claude(id=model_name)
        else:
            return OpenAIChat(id=model_name)
    
    def _prepare_tools(self, tools: Optional[List[Any]], reasoning_enabled: bool) -> List[Any]:
        """准备工具列表"""
        agno_tools = []
        
        # 添加推理工具（如果启用）
        if reasoning_enabled:
            agno_tools.append(ReasoningTools(add_instructions=True))
        
        # 添加自定义工具
        if tools:
            agno_tools.extend(tools)
        
        return agno_tools
    
    @property
    def agno_agent(self) -> AgnoAgent:
        """获取底层Agno Agent实例"""
        return self._agno_agent
    
    def query(self, query_str: str, **kwargs) -> str:
        """
        执行查询 - 兼容LlamaIndex接口
        
        参数:
            query_str: 查询字符串
            **kwargs: 其他参数
            
        返回:
            响应字符串
        """
        try:
            # 使用Agno Agent的response方法
            response = self._agno_agent.response(query_str, **kwargs)
            
            # 处理响应格式
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"Agent query error: {e}")
            return f"Error processing query: {str(e)}"
    
    async def aquery(self, query_str: str, **kwargs) -> str:
        """异步查询"""
        return await asyncio.create_task(
            asyncio.to_thread(self.query, query_str, **kwargs)
        )
    
    def stream_query(self, query_str: str, **kwargs):
        """
        流式查询 - 生成器接口
        
        参数:
            query_str: 查询字符串
            **kwargs: 其他参数
            
        返回:
            响应生成器
        """
        try:
            # 使用Agno Agent的流式响应
            for chunk in self._agno_agent.response(query_str, stream=True, **kwargs):
                if hasattr(chunk, 'content'):
                    yield chunk.content
                else:
                    yield str(chunk)
        except Exception as e:
            logger.error(f"Agent stream query error: {e}")
            yield f"Error: {str(e)}"
    
    async def astream_query(self, query_str: str, **kwargs) -> AsyncGenerator[str, None]:
        """异步流式查询"""
        for chunk in self.stream_query(query_str, **kwargs):
            yield chunk
            await asyncio.sleep(0)  # 让出控制权
    
    def print_response(self, query_str: str, stream: bool = False, **kwargs):
        """
        打印响应 - 使用Agno原生方法
        
        参数:
            query_str: 查询字符串
            stream: 是否流式输出
            **kwargs: 其他参数
        """
        self._agno_agent.print_response(query_str, stream=stream, **kwargs)
    
    def add_tool(self, tool: Any):
        """添加工具到代理"""
        if hasattr(self._agno_agent, 'tools'):
            self._agno_agent.tools.append(tool)
        else:
            self._agno_agent.tools = [tool]
    
    def set_instructions(self, instructions: Union[str, List[str]]):
        """设置代理指令"""
        if isinstance(instructions, str):
            instructions = [instructions]
        self._agno_agent.instructions = instructions
    
    def get_session_history(self) -> List[Dict[str, Any]]:
        """获取会话历史"""
        if self._memory and hasattr(self._memory, 'get_messages'):
            return self._memory.get_messages()
        return []
    
    def clear_session(self):
        """清空会话"""
        if self._memory and hasattr(self._memory, 'clear'):
            self._memory.clear()

class AgnoTeam:
    """
    Agno团队 - 多代理协作系统
    使用官方Agno Team API实现多代理协作
    """
    
    def __init__(
        self,
        name: str = "Agent Team",
        agents: Optional[List[AgnoKnowledgeAgent]] = None,
        mode: str = "coordinate",  # coordinate, collaborate, route
        model: Optional[Union[str, AgnoLLMInterface]] = None,
        instructions: Optional[List[str]] = None,
        success_criteria: Optional[str] = None,
        show_tool_calls: bool = True,
        markdown: bool = True,
        **kwargs
    ):
        self.name = name
        self.mode = mode
        
        # 处理模型配置
        if isinstance(model, str):
            team_model = self._create_model_from_string(model)
        elif isinstance(model, AgnoLLMInterface):
            team_model = model.agno_model
        else:
            team_model = OpenAIChat(id="gpt-4o")
        
        # 提取Agno Agent实例
        agno_agents = []
        if agents:
            for agent in agents:
                if isinstance(agent, AgnoKnowledgeAgent):
                    agno_agents.append(agent.agno_agent)
                else:
                    agno_agents.append(agent)
        
        # 创建Agno Team实例
        if mode == "team":
            # 使用Agent的team参数创建团队
            self._agno_team = AgnoAgent(
                team=agno_agents,
                model=team_model,
                instructions=instructions or [f"Coordinate with team members to provide comprehensive responses"],
                show_tool_calls=show_tool_calls,
                markdown=markdown,
                **kwargs
            )
        else:
            # 使用Team类创建团队
            self._agno_team = AgnoTeam(
                mode=mode,
                members=agno_agents,
                model=team_model,
                success_criteria=success_criteria or "Provide comprehensive and accurate responses through team collaboration",
                instructions=instructions or [f"Work together as a team to provide the best possible response"],
                show_tool_calls=show_tool_calls,
                markdown=markdown,
                **kwargs
            )
        
        self._agents = agents or []
    
    def _create_model_from_string(self, model_name: str):
        """从字符串创建Agno模型实例"""
        if "claude" in model_name.lower():
            return Claude(id=model_name)
        else:
            return OpenAIChat(id=model_name)
    
    @property
    def agno_team(self):
        """获取底层Agno Team实例"""
        return self._agno_team
    
    def query(self, query_str: str, **kwargs) -> str:
        """团队查询"""
        try:
            response = self._agno_team.response(query_str, **kwargs)
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
        except Exception as e:
            logger.error(f"Team query error: {e}")
            return f"Error processing team query: {str(e)}"
    
    async def aquery(self, query_str: str, **kwargs) -> str:
        """异步团队查询"""
        return await asyncio.create_task(
            asyncio.to_thread(self.query, query_str, **kwargs)
        )
    
    def stream_query(self, query_str: str, **kwargs):
        """团队流式查询"""
        try:
            for chunk in self._agno_team.response(query_str, stream=True, **kwargs):
                if hasattr(chunk, 'content'):
                    yield chunk.content
                else:
                    yield str(chunk)
        except Exception as e:
            logger.error(f"Team stream query error: {e}")
            yield f"Error: {str(e)}"
    
    def print_response(self, query_str: str, stream: bool = False, **kwargs):
        """团队打印响应"""
        self._agno_team.print_response(query_str, stream=stream, **kwargs)
    
    def add_agent(self, agent: AgnoKnowledgeAgent):
        """添加代理到团队"""
        self._agents.append(agent)
        # 注意：Agno Team的成员在创建后通常不能动态修改
        # 这里仅更新内部列表，实际功能可能需要重新创建团队
    
    def get_agents(self) -> List[AgnoKnowledgeAgent]:
        """获取所有代理"""
        return self._agents.copy()

# 便利函数 - 创建常用的代理和团队
def create_knowledge_agent(
    name: str = "Knowledge Agent",
    model: str = "gpt-4o",
    knowledge_base: Optional[Any] = None,
    tools: Optional[List[Any]] = None,
    reasoning: bool = True,
    **kwargs
) -> AgnoKnowledgeAgent:
    """创建知识代理"""
    return AgnoKnowledgeAgent(
        name=name,
        model=model,
        knowledge=knowledge_base,
        tools=tools,
        reasoning_enabled=reasoning,
        **kwargs
    )

def create_research_agent(
    name: str = "Research Agent",
    model: str = "gpt-4o",
    **kwargs
) -> AgnoKnowledgeAgent:
    """创建研究代理"""
    tools = [
        DuckDuckGoTools(),  # 网络搜索
        ReasoningTools(add_instructions=True)  # 推理工具
    ]
    
    return AgnoKnowledgeAgent(
        name=name,
        role="Research and Analysis Specialist",
        model=model,
        tools=tools,
        instructions=[
            "You are a research specialist who excels at finding and analyzing information",
            "Use web search to gather current information when needed",
            "Apply reasoning tools to provide well-structured analysis",
            "Always cite sources and provide evidence-based responses"
        ],
        **kwargs
    )

def create_finance_agent(
    name: str = "Finance Agent",
    model: str = "gpt-4o",
    **kwargs
) -> AgnoKnowledgeAgent:
    """创建金融分析代理"""
    tools = [
        YFinanceTools(
            stock_price=True,
            analyst_recommendations=True,
            company_info=True,
            company_news=True
        ),
        ReasoningTools(add_instructions=True)
    ]
    
    return AgnoKnowledgeAgent(
        name=name,
        role="Financial Analysis Specialist",
        model=model,
        tools=tools,
        instructions=[
            "You are a financial analysis expert",
            "Use financial data tools to provide accurate market information",
            "Present data in clear tables and charts when possible",
            "Provide reasoned analysis based on available data"
        ],
        **kwargs
    )

def create_multi_agent_team(
    agents: List[AgnoKnowledgeAgent],
    name: str = "Multi-Agent Team",
    model: str = "gpt-4o",
    mode: str = "coordinate",
    **kwargs
) -> AgnoTeam:
    """创建多代理团队"""
    return AgnoTeam(
        name=name,
        agents=agents,
        model=model,
        mode=mode,
        **kwargs
    )

# LlamaIndex兼容性别名
KnowledgeAgent = AgnoKnowledgeAgent
AgentTeam = AgnoTeam

# 导出主要组件
__all__ = [
    "AgnoKnowledgeAgent",
    "AgnoTeam",
    "create_knowledge_agent",
    "create_research_agent", 
    "create_finance_agent",
    "create_multi_agent_team",
    "KnowledgeAgent",
    "AgentTeam"
]
