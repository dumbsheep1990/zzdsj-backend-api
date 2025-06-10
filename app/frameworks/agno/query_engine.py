"""
Agno查询引擎 - 使用正确的官方Agno API
基于Agno的Agent和Knowledge系统实现查询处理功能
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, AsyncGenerator, Callable
from datetime import datetime

# 使用正确的Agno官方API导入
from agno.agent import Agent as AgnoAgent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.tools.reasoning import ReasoningTools

from app.frameworks.agno.core import AgnoLLMInterface, AgnoServiceContext
from app.frameworks.agno.agent import AgnoKnowledgeAgent

logger = logging.getLogger(__name__)

class AgnoQueryEngine:
    """
    Agno查询引擎 - 使用官方Agno Agent API
    提供多种查询模式和响应格式
    """
    
    def __init__(
        self,
        agent: Optional[Union[AgnoAgent, AgnoKnowledgeAgent]] = None,
        knowledge_base: Optional[Any] = None,
        model: Optional[Union[str, AgnoLLMInterface]] = None,
        instructions: Optional[Union[str, List[str]]] = None,
        query_mode: str = "default",  # default, reasoning, context
        response_mode: str = "compact",  # compact, tree_summarize, refine
        similarity_threshold: float = 0.7,
        top_k: int = 5,
        **kwargs
    ):
        self.query_mode = query_mode
        self.response_mode = response_mode
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k
        
        # 如果没有提供agent，创建默认agent
        if agent is None:
            # 处理模型配置
            if isinstance(model, str):
                agno_model = self._create_model_from_string(model)
            elif isinstance(model, AgnoLLMInterface):
                agno_model = model.agno_model
            else:
                agno_model = OpenAIChat(id="gpt-4o")
            
            # 准备工具
            tools = []
            if query_mode == "reasoning":
                tools.append(ReasoningTools(add_instructions=True))
            
            # 处理指令配置
            if isinstance(instructions, str):
                instructions = [instructions]
            elif instructions is None:
                instructions = [
                    "You are a helpful AI assistant that provides accurate and informative responses.",
                    "Use available knowledge and reasoning capabilities to answer questions thoroughly."
                ]
            
            # 创建Agno Agent
            self._agno_agent = AgnoAgent(
                model=agno_model,
                knowledge=knowledge_base,
                tools=tools,
                instructions=instructions,
                search_knowledge=True if knowledge_base else False,
                markdown=True,
                show_tool_calls=False,
                **kwargs
            )
        else:
            # 使用提供的agent
            if isinstance(agent, AgnoKnowledgeAgent):
                self._agno_agent = agent.agno_agent
            else:
                self._agno_agent = agent
        
        self.knowledge_base = knowledge_base
    
    def _create_model_from_string(self, model_name: str):
        """从字符串创建Agno模型实例"""
        if "claude" in model_name.lower():
            return Claude(id=model_name)
        else:
            return OpenAIChat(id=model_name)
    
    @property
    def agno_agent(self) -> AgnoAgent:
        """获取底层Agno Agent实例"""
        return self._agno_agent
    
    def query(self, query_str: str, **kwargs) -> Dict[str, Any]:
        """
        执行查询并返回结构化响应
        
        参数:
            query_str: 查询字符串
            **kwargs: 其他参数
            
        返回:
            结构化查询响应
        """
        try:
            # 使用Agno Agent处理查询
            start_time = datetime.now()
            response = self._agno_agent.response(query_str, **kwargs)
            end_time = datetime.now()
            
            # 提取响应内容
            response_content = response.content if hasattr(response, 'content') else str(response)
            
            # 构建结构化响应
            result = {
                "response": response_content,
                "metadata": {
                    "query": query_str,
                    "query_mode": self.query_mode,
                    "response_mode": self.response_mode,
                    "execution_time": (end_time - start_time).total_seconds(),
                    "timestamp": end_time.isoformat()
                },
                "sources": [],
                "tool_calls": []
            }
            
            # 提取工具调用信息（如果可用）
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    result["tool_calls"].append({
                        "tool_name": getattr(tool_call, 'name', 'unknown'),
                        "arguments": getattr(tool_call, 'arguments', {}),
                        "result": getattr(tool_call, 'result', None)
                    })
            
            # 提取源信息（如果可用）
            if hasattr(response, 'sources') and response.sources:
                for source in response.sources:
                    result["sources"].append({
                        "content": source.get("content", ""),
                        "metadata": source.get("metadata", {}),
                        "score": source.get("score", 1.0),
                        "node_id": source.get("id", "")
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return {
                "response": f"Error processing query: {str(e)}",
                "metadata": {
                    "query": query_str,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                },
                "sources": [],
                "tool_calls": []
            }
    
    async def aquery(self, query_str: str, **kwargs) -> Dict[str, Any]:
        """异步查询"""
        return await asyncio.create_task(
            asyncio.to_thread(self.query, query_str, **kwargs)
        )
    
    def stream_query(self, query_str: str, **kwargs):
        """
        流式查询
        
        参数:
            query_str: 查询字符串
            **kwargs: 其他参数
            
        返回:
            响应流生成器
        """
        try:
            # 使用Agno Agent的流式响应
            for chunk in self._agno_agent.response(query_str, stream=True, **kwargs):
                chunk_content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                yield {
                    "type": "content",
                    "content": chunk_content,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Stream query error: {e}")
            yield {
                "type": "error",
                "content": f"Error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def astream_query(self, query_str: str, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """异步流式查询"""
        for chunk in self.stream_query(query_str, **kwargs):
            yield chunk
            await asyncio.sleep(0)  # 让出控制权
    
    def synthesize(self, query_str: str, contexts: List[str], **kwargs) -> str:
        """
        合成响应 - 基于提供的上下文
        
        参数:
            query_str: 查询字符串
            contexts: 上下文列表
            **kwargs: 其他参数
            
        返回:
            合成的响应
        """
        try:
            # 构建包含上下文的查询
            context_text = "\n\n".join([f"Context {i+1}: {ctx}" for i, ctx in enumerate(contexts)])
            full_query = f"""Based on the following contexts, please answer the question.

Contexts:
{context_text}

Question: {query_str}

Please provide a comprehensive answer based on the provided contexts."""
            
            # 使用Agent处理
            response = self._agno_agent.response(full_query, **kwargs)
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            return f"Error synthesizing response: {str(e)}"
    
    async def asynthesize(self, query_str: str, contexts: List[str], **kwargs) -> str:
        """异步合成响应"""
        return await asyncio.create_task(
            asyncio.to_thread(self.synthesize, query_str, contexts, **kwargs)
        )

class AgnoContextQueryEngine:
    """
    Agno上下文查询引擎 - 专门处理知识库查询
    结合知识检索和生成回答
    """
    
    def __init__(
        self,
        knowledge_base: Any,
        model: Optional[Union[str, AgnoLLMInterface]] = None,
        instructions: Optional[Union[str, List[str]]] = None,
        similarity_threshold: float = 0.7,
        top_k: int = 5,
        retrieval_mode: str = "hybrid",  # hybrid, vector, keyword
        **kwargs
    ):
        self.knowledge_base = knowledge_base
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k
        self.retrieval_mode = retrieval_mode
        
        # 处理模型配置
        if isinstance(model, str):
            agno_model = self._create_model_from_string(model)
        elif isinstance(model, AgnoLLMInterface):
            agno_model = model.agno_model
        else:
            agno_model = OpenAIChat(id="gpt-4o")
        
        # 处理指令配置
        if isinstance(instructions, str):
            instructions = [instructions]
        elif instructions is None:
            instructions = [
                "You are an expert assistant that provides accurate answers based on knowledge base information.",
                "Always prioritize information from the knowledge base when available.",
                "If the question cannot be answered from the knowledge base, clearly state this limitation."
            ]
        
        # 创建带知识库的Agent
        self._agno_agent = AgnoAgent(
            model=agno_model,
            knowledge=knowledge_base,
            instructions=instructions,
            search_knowledge=True,
            add_context=True,  # 自动添加上下文到提示
            markdown=True,
            show_tool_calls=True,
            **kwargs
        )
    
    def _create_model_from_string(self, model_name: str):
        """从字符串创建Agno模型实例"""
        if "claude" in model_name.lower():
            return Claude(id=model_name)
        else:
            return OpenAIChat(id=model_name)
    
    def query(self, query_str: str, **kwargs) -> Dict[str, Any]:
        """上下文感知查询"""
        try:
            start_time = datetime.now()
            response = self._agno_agent.response(query_str, **kwargs)
            end_time = datetime.now()
            
            response_content = response.content if hasattr(response, 'content') else str(response)
            
            return {
                "response": response_content,
                "metadata": {
                    "query": query_str,
                    "retrieval_mode": self.retrieval_mode,
                    "similarity_threshold": self.similarity_threshold,
                    "top_k": self.top_k,
                    "execution_time": (end_time - start_time).total_seconds(),
                    "timestamp": end_time.isoformat()
                },
                "sources": self._extract_sources(response),
                "tool_calls": self._extract_tool_calls(response)
            }
            
        except Exception as e:
            logger.error(f"Context query error: {e}")
            return {
                "response": f"Error processing context query: {str(e)}",
                "metadata": {
                    "query": query_str,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                },
                "sources": [],
                "tool_calls": []
            }
    
    def _extract_sources(self, response) -> List[Dict[str, Any]]:
        """提取源信息"""
        sources = []
        if hasattr(response, 'sources') and response.sources:
            for source in response.sources:
                sources.append({
                    "content": source.get("content", ""),
                    "metadata": source.get("metadata", {}),
                    "score": source.get("score", 1.0),
                    "node_id": source.get("id", "")
                })
        return sources
    
    def _extract_tool_calls(self, response) -> List[Dict[str, Any]]:
        """提取工具调用信息"""
        tool_calls = []
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_calls.append({
                    "tool_name": getattr(tool_call, 'name', 'unknown'),
                    "arguments": getattr(tool_call, 'arguments', {}),
                    "result": getattr(tool_call, 'result', None)
                })
        return tool_calls
    
    async def aquery(self, query_str: str, **kwargs) -> Dict[str, Any]:
        """异步上下文查询"""
        return await asyncio.create_task(
            asyncio.to_thread(self.query, query_str, **kwargs)
        )
    
    def stream_query(self, query_str: str, **kwargs):
        """流式上下文查询"""
        try:
            for chunk in self._agno_agent.response(query_str, stream=True, **kwargs):
                chunk_content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                yield {
                    "type": "content",
                    "content": chunk_content,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Stream context query error: {e}")
            yield {
                "type": "error",
                "content": f"Error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

# 便利函数 - 创建常用的查询引擎
def create_query_engine(
    agent: Optional[Union[AgnoAgent, AgnoKnowledgeAgent]] = None,
    model: str = "gpt-4o",
    query_mode: str = "default",
    **kwargs
) -> AgnoQueryEngine:
    """创建基础查询引擎"""
    return AgnoQueryEngine(
        agent=agent,
        model=model,
        query_mode=query_mode,
        **kwargs
    )

def create_context_query_engine(
    knowledge_base: Any,
    model: str = "gpt-4o",
    **kwargs
) -> AgnoContextQueryEngine:
    """创建上下文查询引擎"""
    return AgnoContextQueryEngine(
        knowledge_base=knowledge_base,
        model=model,
        **kwargs
    )

def create_reasoning_query_engine(
    knowledge_base: Optional[Any] = None,
    model: str = "gpt-4o",
    **kwargs
) -> AgnoQueryEngine:
    """创建推理查询引擎"""
    return AgnoQueryEngine(
        knowledge_base=knowledge_base,
        model=model,
        query_mode="reasoning",
        **kwargs
    )

# LlamaIndex兼容性别名
QueryEngine = AgnoQueryEngine
ContextQueryEngine = AgnoContextQueryEngine

# 导出主要组件
__all__ = [
    "AgnoQueryEngine",
    "AgnoContextQueryEngine",
    "create_query_engine",
    "create_context_query_engine", 
    "create_reasoning_query_engine",
    "QueryEngine",
    "ContextQueryEngine"
] 