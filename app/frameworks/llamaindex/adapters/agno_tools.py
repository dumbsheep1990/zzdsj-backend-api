"""
Agno适配器模块: 将Agno代理包装为LlamaIndex工具
实现SOLID原则中的接口隔离和单一职责
"""

from typing import Any, Dict, Optional, List, Union
from llama_index.core.tools import BaseTool, ToolMetadata
from llama_index.core.query_engine import ToolCallbackQueryEngine
from app.frameworks.agno.agent import AgnoAgent

class AgnoAgentTool(BaseTool):
    """
    将Agno代理包装为LlamaIndex工具
    遵循适配器设计模式，将Agno框架的能力集成到LlamaIndex工具链中
    """
    
    def __init__(
        self, 
        agent: AgnoAgent, 
        name: str, 
        description: str
    ):
        """
        初始化Agno代理工具
        
        参数:
            agent: Agno代理实例
            name: 工具名称
            description: 工具描述
        """
        self.agent = agent
        self._metadata = ToolMetadata(name=name, description=description)
    
    @property
    def metadata(self) -> ToolMetadata:
        """返回工具元数据"""
        return self._metadata
    
    async def __call__(
        self, 
        query: str, 
        **kwargs
    ) -> str:
        """
        调用Agno代理执行查询
        
        参数:
            query: 用户查询
            **kwargs: 额外参数，支持conversation_id等
            
        返回:
            代理响应文本
        """
        conversation_id = kwargs.get("conversation_id")
        response = await self.agent.query(query, conversation_id)
        return response.get("response", "无响应")
    
    def as_query_engine(
        self, 
        **kwargs
    ) -> ToolCallbackQueryEngine:
        """
        将工具转换为查询引擎
        
        参数:
            **kwargs: 传递给查询引擎的参数
            
        返回:
            配置好的查询引擎
        """
        return ToolCallbackQueryEngine.from_defaults(
            tool=self,
            **kwargs
        )


def create_agno_tool(
    knowledge_base_ids: List[int] = None,
    name: str = "knowledge_reasoning",
    description: str = "复杂知识推理和多步骤问答",
    model: str = None
) -> AgnoAgentTool:
    """
    创建Agno代理工具的工厂函数
    
    参数:
        knowledge_base_ids: 知识库ID列表
        name: 工具名称
        description: 工具描述
        model: 模型名称
        
    返回:
        配置好的Agno代理工具
    """
    # 转换为字符串列表
    from app.frameworks.agno.agent import create_knowledge_agent
    
    kb_ids = [str(kb_id) for kb_id in knowledge_base_ids] if knowledge_base_ids else []
    
    # 创建知识代理
    agent = create_knowledge_agent(kb_ids, agent_name=name)
    
    # 创建并返回工具
    return AgnoAgentTool(
        agent=agent,
        name=name,
        description=description
    )
