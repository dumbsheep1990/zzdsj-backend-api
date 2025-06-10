"""
Agno Core Integration - 使用正确的官方Agno API语法
基于官方文档的真实Agno接口实现，确保语法正确性
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, AsyncGenerator, Generator
from contextlib import asynccontextmanager

# 使用正确的Agno官方API导入
from agno.agent import Agent as AgnoAgent
from agno.models.openai import OpenAIChat  # 正确的OpenAI模型类名
from agno.models.anthropic import Claude
from agno.tools.reasoning import ReasoningTools
from agno.memory import Memory as AgnoMemory
from agno.storage import Storage as AgnoStorage

logger = logging.getLogger(__name__)

class AgnoLLMInterface:
    """
    Agno LLM统一接口 - 使用官方Agno API
    提供与LlamaIndex兼容的接口，底层使用Agno原生实现
    """
    
    def __init__(
        self,
        model_name: str = "gpt-4o",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        self.model_name = model_name
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.kwargs = kwargs
        
        # 根据模型名称创建正确的Agno模型实例
        self._agno_model = self._create_agno_model()
    
    def _create_agno_model(self):
        """创建Agno模型实例"""
        if "gpt" in self.model_name or "o1" in self.model_name:
            return OpenAIChat(
                id=self.model_name,
                api_key=self.api_key,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **self.kwargs
            )
        elif "claude" in self.model_name:
            return Claude(
                id=self.model_name,
                api_key=self.api_key,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **self.kwargs
            )
        else:
            # 默认使用OpenAI
            return OpenAIChat(
                id=self.model_name,
                api_key=self.api_key,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **self.kwargs
            )
    
    @property
    def agno_model(self):
        """获取Agno原生模型实例"""
        return self._agno_model
    
    def complete(self, prompt: str, **kwargs) -> str:
        """兼容LlamaIndex的complete方法"""
        # 创建临时Agent来处理completion
        temp_agent = AgnoAgent(model=self._agno_model, markdown=False)
        response = temp_agent.response(prompt, **kwargs)
        return response.content if hasattr(response, 'content') else str(response)
    
    async def acomplete(self, prompt: str, **kwargs) -> str:
        """异步completion"""
        return await asyncio.create_task(
            asyncio.to_thread(self.complete, prompt, **kwargs)
        )

class AgnoServiceContext:
    """
    Agno服务上下文 - 兼容LlamaIndex接口
    管理LLM、内存和其他服务组件
    """
    
    def __init__(
        self,
        llm: Optional[AgnoLLMInterface] = None,
        memory: Optional[Any] = None,
        storage: Optional[Any] = None,
        chunk_size: int = 1024,
        chunk_overlap: int = 200,
        **kwargs
    ):
        self.llm = llm or AgnoLLMInterface()
        self.memory = memory
        self.storage = storage
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.kwargs = kwargs
    
    @classmethod
    def from_defaults(
        cls,
        llm: Optional[Union[str, AgnoLLMInterface]] = None,
        **kwargs
    ) -> "AgnoServiceContext":
        """从默认配置创建服务上下文"""
        if isinstance(llm, str):
            llm = AgnoLLMInterface(model_name=llm)
        elif llm is None:
            llm = AgnoLLMInterface()
        
        return cls(llm=llm, **kwargs)

class AgnoChatMemory:
    """
    Agno聊天记忆管理 - 使用Agno原生Memory
    """
    
    def __init__(self, storage: Optional[AgnoStorage] = None):
        self.storage = storage
        self._agno_memory = AgnoMemory(storage=storage) if storage else None
        self._messages = []
    
    def add_message(self, message: Dict[str, Any]):
        """添加消息到记忆"""
        self._messages.append(message)
        if self._agno_memory:
            self._agno_memory.add(message)
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """获取所有消息"""
        return self._messages.copy()
    
    def clear(self):
        """清空记忆"""
        self._messages.clear()
        if self._agno_memory:
            self._agno_memory.clear()

class AgnoQueryProcessor:
    """
    Agno查询处理器 - 提供流式和非流式处理
    """
    
    def __init__(self, agent: AgnoAgent):
        self.agent = agent
    
    def process_query(
        self,
        query: str,
        stream: bool = False,
        **kwargs
    ) -> Union[str, Generator[str, None, None]]:
        """处理查询请求"""
        if stream:
            return self._stream_response(query, **kwargs)
        else:
            response = self.agent.response(query, **kwargs)
            return response.content if hasattr(response, 'content') else str(response)
    
    async def aprocess_query(
        self,
        query: str,
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncGenerator[str, None]]:
        """异步处理查询请求"""
        if stream:
            return self._astream_response(query, **kwargs)
        else:
            return await asyncio.create_task(
                asyncio.to_thread(self.process_query, query, stream=False, **kwargs)
            )
    
    def _stream_response(self, query: str, **kwargs) -> Generator[str, None, None]:
        """流式响应生成器"""
        try:
            # 使用Agno的流式响应
            for chunk in self.agent.response(query, stream=True, **kwargs):
                if hasattr(chunk, 'content'):
                    yield chunk.content
                else:
                    yield str(chunk)
        except Exception as e:
            logger.error(f"Error in stream response: {e}")
            yield f"Error: {str(e)}"
    
    async def _astream_response(self, query: str, **kwargs) -> AsyncGenerator[str, None]:
        """异步流式响应生成器"""
        for chunk in self._stream_response(query, **kwargs):
            yield chunk
            await asyncio.sleep(0)  # 让出控制权

class AgnoPromptTemplate:
    """
    Agno提示模板 - 扩展的模板功能
    """
    
    def __init__(self, template: str, **kwargs):
        self.template = template
        self.kwargs = kwargs
    
    def format(self, **format_kwargs) -> str:
        """格式化模板"""
        combined_kwargs = {**self.kwargs, **format_kwargs}
        return self.template.format(**combined_kwargs)
    
    @classmethod
    def from_template(cls, template: str, **kwargs) -> "AgnoPromptTemplate":
        """从模板字符串创建"""
        return cls(template=template, **kwargs)

# LlamaIndex兼容性别名 - 保持现有代码兼容性
LLM = AgnoLLMInterface
ServiceContext = AgnoServiceContext
ChatMemory = AgnoChatMemory
QueryProcessor = AgnoQueryProcessor
PromptTemplate = AgnoPromptTemplate

# 工厂函数 - 便于创建常用组件
def create_openai_llm(model_name: str = "gpt-4o", **kwargs) -> AgnoLLMInterface:
    """创建OpenAI LLM实例"""
    return AgnoLLMInterface(model_name=model_name, **kwargs)

def create_claude_llm(model_name: str = "claude-3-5-sonnet-20241022", **kwargs) -> AgnoLLMInterface:
    """创建Claude LLM实例"""
    return AgnoLLMInterface(model_name=model_name, **kwargs)

def create_service_context(
    llm: Optional[Union[str, AgnoLLMInterface]] = None,
    **kwargs
) -> AgnoServiceContext:
    """创建服务上下文"""
    return AgnoServiceContext.from_defaults(llm=llm, **kwargs)

@asynccontextmanager
async def create_async_context(llm: Optional[AgnoLLMInterface] = None):
    """创建异步上下文管理器"""
    service_context = create_service_context(llm=llm)
    try:
        yield service_context
    finally:
        # 清理资源
        pass

# 导出主要组件
__all__ = [
    "AgnoLLMInterface",
    "AgnoServiceContext", 
    "AgnoChatMemory",
    "AgnoQueryProcessor",
    "AgnoPromptTemplate",
    "LLM",
    "ServiceContext",
    "ChatMemory",
    "QueryProcessor",
    "PromptTemplate",
    "create_openai_llm",
    "create_claude_llm",
    "create_service_context",
    "create_async_context"
] 