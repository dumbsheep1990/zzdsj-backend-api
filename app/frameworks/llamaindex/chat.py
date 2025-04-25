"""
LlamaIndex聊天模块: 提供与LLM的交互功能
替代LangChain的聊天功能
"""

from typing import List, Dict, Any, Optional
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core import Settings
from app.frameworks.llamaindex.core import get_llm, get_service_context, format_prompt

def create_chat_engine(
    memory: Optional[ChatMemoryBuffer] = None,
    system_prompt: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None
) -> SimpleChatEngine:
    """
    创建聊天引擎，替代LangChain的聊天功能
    
    参数:
        memory: 聊天记忆
        system_prompt: 系统提示
        model_name: 模型名称
        temperature: 温度参数
        
    返回:
        聊天引擎
    """
    # 获取LLM
    llm = get_llm(model_name, temperature)
    
    # 创建记忆
    if memory is None:
        memory = ChatMemoryBuffer.from_defaults(token_limit=4096)
    
    # 创建聊天引擎
    chat_engine = SimpleChatEngine.from_defaults(
        llm=llm,
        memory=memory,
        system_prompt=system_prompt
    )
    
    return chat_engine

async def generate_response(
    system_prompt: str, 
    conversation_history: List[Dict[str, str]],
    references: Optional[List[Dict[str, Any]]] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None
) -> str:
    """
    使用LlamaIndex生成响应，替代LangChain的生成响应
    
    参数:
        system_prompt: 系统提示
        conversation_history: 对话历史
        references: 参考文档
        model_name: 模型名称
        temperature: 温度参数
        
    返回:
        生成的响应
    """
    # 处理参考资料
    if references:
        reference_text = "\n\n知识库中的相关信息:"
        for i, ref in enumerate(references):
            reference_text += f"\n\n文档 {i+1}:\n{ref.get('content', '')}"
        
        system_prompt += reference_text
    
    # 创建聊天引擎
    chat_engine = create_chat_engine(
        system_prompt=system_prompt,
        model_name=model_name,
        temperature=temperature
    )
    
    # 添加对话历史
    for message in conversation_history:
        if message["role"] == "user":
            chat_engine.memory.put({"role": "user", "content": message["content"]})
        elif message["role"] == "assistant":
            chat_engine.memory.put({"role": "assistant", "content": message["content"]})
    
    # 获取最后一条用户消息
    last_user_message = None
    for message in reversed(conversation_history):
        if message["role"] == "user":
            last_user_message = message["content"]
            break
    
    # 生成响应
    if last_user_message:
        response = await chat_engine.aquery(last_user_message)
        return response.response
    else:
        raise ValueError("对话历史中没有用户消息")
