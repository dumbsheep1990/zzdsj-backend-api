"""
Agno Chat模块 - 使用正确的官方Agno API
基于Agno的Agent和Memory系统实现聊天功能
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Union, AsyncGenerator, Callable
from datetime import datetime

# 使用正确的Agno官方API导入
from agno.agent import Agent as AgnoAgent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.memory import Memory as AgnoMemory
from agno.storage import Storage as AgnoStorage

from app.frameworks.agno.core import AgnoLLMInterface, AgnoServiceContext

logger = logging.getLogger(__name__)

class AgnoChatEngine:
    """
    Agno聊天引擎 - 基于官方Agno Agent API
    提供完整的对话管理和流式响应功能
    """
    
    def __init__(
        self,
        agent: Optional[AgnoAgent] = None,
        model: Optional[Union[str, AgnoLLMInterface]] = None,
        memory: Optional[AgnoMemory] = None,
        storage: Optional[AgnoStorage] = None,
        instructions: Optional[Union[str, List[str]]] = None,
        system_prompt: Optional[str] = None,
        chat_mode: str = "best",  # best, context, simple
        session_id: Optional[str] = None,
        **kwargs
    ):
        self.chat_mode = chat_mode
        self.session_id = session_id or str(uuid.uuid4())
        
        # 如果没有提供agent，创建默认agent
        if agent is None:
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
                instructions = ["You are a helpful AI assistant. Provide clear, accurate, and helpful responses."]
            
            # 如果有系统提示，添加到指令中
            if system_prompt:
                instructions.insert(0, system_prompt)
            
            # 创建Agno Agent
            self._agno_agent = AgnoAgent(
                model=agno_model,
                memory=memory,
                storage=storage,
                instructions=instructions,
                markdown=True,
                show_tool_calls=False,
                **kwargs
            )
        else:
            self._agno_agent = agent
        
        # 存储会话信息
        self._chat_history = []
        self._memory = memory
        self._storage = storage
    
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
    
    def chat(self, message: str, **kwargs) -> str:
        """
        同步聊天方法
        
        参数:
            message: 用户消息
            **kwargs: 其他参数
            
        返回:
            AI响应
        """
        try:
            # 添加到聊天历史
            self._add_to_history("user", message)
            
            # 使用Agno Agent处理消息
            response = self._agno_agent.response(message, **kwargs)
            
            # 提取响应内容
            response_content = response.content if hasattr(response, 'content') else str(response)
            
            # 添加到聊天历史
            self._add_to_history("assistant", response_content)
            
            return response_content
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            error_response = f"Sorry, I encountered an error: {str(e)}"
            self._add_to_history("assistant", error_response)
            return error_response
    
    async def achat(self, message: str, **kwargs) -> str:
        """异步聊天方法"""
        return await asyncio.create_task(
            asyncio.to_thread(self.chat, message, **kwargs)
        )
    
    def stream_chat(self, message: str, **kwargs):
        """
        流式聊天方法
        
        参数:
            message: 用户消息
            **kwargs: 其他参数
            
        返回:
            响应生成器
        """
        try:
            # 添加到聊天历史
            self._add_to_history("user", message)
            
            # 收集完整响应
            full_response = ""
            
            # 使用Agno Agent的流式响应
            for chunk in self._agno_agent.response(message, stream=True, **kwargs):
                chunk_content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                full_response += chunk_content
                yield chunk_content
            
            # 添加完整响应到聊天历史
            self._add_to_history("assistant", full_response)
            
        except Exception as e:
            logger.error(f"Stream chat error: {e}")
            error_response = f"Error: {str(e)}"
            self._add_to_history("assistant", error_response)
            yield error_response
    
    async def astream_chat(self, message: str, **kwargs) -> AsyncGenerator[str, None]:
        """异步流式聊天方法"""
        for chunk in self.stream_chat(message, **kwargs):
            yield chunk
            await asyncio.sleep(0)  # 让出控制权
    
    def _add_to_history(self, role: str, content: str):
        """添加消息到聊天历史"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self._chat_history.append(message)
        
        # 如果有内存系统，也添加到内存中
        if self._memory:
            try:
                if hasattr(self._memory, 'add'):
                    self._memory.add(message)
                elif hasattr(self._memory, 'add_message'):
                    self._memory.add_message(message)
            except Exception as e:
                logger.debug(f"Failed to add message to memory: {e}")
    
    def get_chat_history(self) -> List[Dict[str, Any]]:
        """获取聊天历史"""
        return self._chat_history.copy()
    
    def clear_history(self):
        """清空聊天历史"""
        self._chat_history.clear()
        if self._memory and hasattr(self._memory, 'clear'):
            try:
                self._memory.clear()
            except Exception as e:
                logger.debug(f"Failed to clear memory: {e}")
    
    def set_system_prompt(self, system_prompt: str):
        """设置系统提示"""
        current_instructions = getattr(self._agno_agent, 'instructions', [])
        if isinstance(current_instructions, str):
            current_instructions = [current_instructions]
        elif not current_instructions:
            current_instructions = []
        
        # 将系统提示添加到指令开头
        new_instructions = [system_prompt] + current_instructions
        self._agno_agent.instructions = new_instructions
    
    def reset_conversation(self):
        """重置对话"""
        self.clear_history()
        self.session_id = str(uuid.uuid4())

class AgnoContextChatEngine:
    """
    Agno上下文聊天引擎 - 支持知识库检索
    结合Agent和Knowledge Base实现上下文感知的聊天
    """
    
    def __init__(
        self,
        agent: Optional[AgnoAgent] = None,
        knowledge_base: Optional[Any] = None,
        model: Optional[Union[str, AgnoLLMInterface]] = None,
        memory: Optional[AgnoMemory] = None,
        system_prompt: Optional[str] = None,
        context_mode: str = "auto",  # auto, always, on_demand
        **kwargs
    ):
        self.knowledge_base = knowledge_base
        self.context_mode = context_mode
        
        # 如果没有提供agent，创建默认agent
        if agent is None:
            # 处理模型配置
            if isinstance(model, str):
                agno_model = self._create_model_from_string(model)
            elif isinstance(model, AgnoLLMInterface):
                agno_model = model.agno_model
            else:
                agno_model = OpenAIChat(id="gpt-4o")
            
            # 设置指令
            instructions = [
                system_prompt or "You are a helpful AI assistant with access to knowledge resources.",
                "Use your knowledge base to provide accurate and detailed responses when relevant.",
                "If information is not available in your knowledge base, use your general knowledge."
            ]
            
            # 创建Agno Agent with knowledge
            self._agno_agent = AgnoAgent(
                model=agno_model,
                knowledge=knowledge_base,
                memory=memory,
                instructions=instructions,
                search_knowledge=True,  # 启用知识库搜索
                markdown=True,
                show_tool_calls=True,
                **kwargs
            )
        else:
            self._agno_agent = agent
        
        # 创建基础聊天引擎
        self._chat_engine = AgnoChatEngine(
            agent=self._agno_agent,
            memory=memory,
            **kwargs
        )
    
    def _create_model_from_string(self, model_name: str):
        """从字符串创建Agno模型实例"""
        if "claude" in model_name.lower():
            return Claude(id=model_name)
        else:
            return OpenAIChat(id=model_name)
    
    def chat(self, message: str, **kwargs) -> str:
        """上下文感知聊天"""
        return self._chat_engine.chat(message, **kwargs)
    
    async def achat(self, message: str, **kwargs) -> str:
        """异步上下文感知聊天"""
        return await self._chat_engine.achat(message, **kwargs)
    
    def stream_chat(self, message: str, **kwargs):
        """流式上下文感知聊天"""
        return self._chat_engine.stream_chat(message, **kwargs)
    
    async def astream_chat(self, message: str, **kwargs) -> AsyncGenerator[str, None]:
        """异步流式上下文感知聊天"""
        async for chunk in self._chat_engine.astream_chat(message, **kwargs):
            yield chunk
    
    def get_chat_history(self) -> List[Dict[str, Any]]:
        """获取聊天历史"""
        return self._chat_engine.get_chat_history()
    
    def clear_history(self):
        """清空聊天历史"""
        self._chat_engine.clear_history()
    
    def reset_conversation(self):
        """重置对话"""
        self._chat_engine.reset_conversation()

# 便利函数 - 创建常用的聊天引擎
def create_chat_engine(
    model: str = "gpt-4o",
    system_prompt: Optional[str] = None,
    memory: bool = True,
    **kwargs
) -> AgnoChatEngine:
    """创建基础聊天引擎"""
    agno_memory = None
    if memory:
        # 创建简单的内存存储
        try:
            agno_memory = AgnoMemory()
        except Exception as e:
            logger.debug(f"Failed to create memory: {e}")
    
    return AgnoChatEngine(
        model=model,
        memory=agno_memory,
        system_prompt=system_prompt,
        **kwargs
    )

def create_context_chat_engine(
    model: str = "gpt-4o",
    knowledge_base: Optional[Any] = None,
    system_prompt: Optional[str] = None,
    memory: bool = True,
    **kwargs
) -> AgnoContextChatEngine:
    """创建上下文聊天引擎"""
    agno_memory = None
    if memory:
        try:
            agno_memory = AgnoMemory()
        except Exception as e:
            logger.debug(f"Failed to create memory: {e}")
    
    return AgnoContextChatEngine(
        model=model,
        knowledge_base=knowledge_base,
        memory=agno_memory,
        system_prompt=system_prompt,
        **kwargs
    )

def create_agent_chat_engine(
    agent: AgnoAgent,
    memory: bool = True,
    **kwargs
) -> AgnoChatEngine:
    """从现有Agent创建聊天引擎"""
    agno_memory = None
    if memory:
        try:
            agno_memory = AgnoMemory()
        except Exception as e:
            logger.debug(f"Failed to create memory: {e}")
    
    return AgnoChatEngine(
        agent=agent,
        memory=agno_memory,
        **kwargs
    )

# LlamaIndex兼容性别名
ChatEngine = AgnoChatEngine
ContextChatEngine = AgnoContextChatEngine

# 导出主要组件
__all__ = [
    "AgnoChatEngine",
    "AgnoContextChatEngine", 
    "create_chat_engine",
    "create_context_chat_engine",
    "create_agent_chat_engine",
    "ChatEngine",
    "ContextChatEngine"
] 