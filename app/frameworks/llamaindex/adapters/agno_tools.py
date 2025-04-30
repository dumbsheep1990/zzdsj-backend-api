"""
Agno适配器模块: 将Agno代理包装为LlamaIndex工具
实现SOLID原则中的接口隔离和单一职责
"""

from typing import Any, Dict, Optional, List, Union
from llama_index.core.tools import BaseTool, ToolMetadata
from llama_index.core.query_engine import BaseQueryEngine
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
        
        metadata = ToolMetadata(
            name=name,
            description=description
        )
        
        super().__init__(metadata=metadata)
    
    async def __call__(self, query: str, **kwargs):
        """
        异步调用方法，处理查询
        
        参数:
            query: 查询文本
            **kwargs: 额外参数
            
        返回:
            代理响应文本
        """
        conversation_id = kwargs.get("conversation_id")
        response = await self.agent.query(query, conversation_id)
        return response.get("response", "无响应")
    
    def as_query_engine(self) -> BaseQueryEngine:
        """
        将工具转换为查询引擎
        
        返回:
            配置好的查询引擎
        """
        # 创建一个自定义查询引擎类
        class AgnoQueryEngine(BaseQueryEngine):
            def __init__(self, tool: AgnoAgentTool):
                self.tool = tool
                super().__init__()
            
            async def aquery(self, query_str: str):
                from llama_index.core.response.schema import Response
                result = await self.tool(query_str)
                return Response(response=result)
            
            def query(self, query_str: str):
                import asyncio
                return asyncio.run(self.aquery(query_str))
        
        # 返回查询引擎实例
        return AgnoQueryEngine(self)


from app.frameworks.agno.agent import create_knowledge_agent

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
    # 创建知识代理
    agent = create_knowledge_agent(
        knowledge_base_ids=knowledge_base_ids,
        model=model
    )
    
    # 创建工具
    return AgnoAgentTool(
        agent=agent,
        name=name,
        description=description
    )
