"""
LlamaIndex聊天模块: 提供与LLM的交互功能
替代LangChain的聊天功能
"""

from typing import List, Dict, Any, Optional
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core import Settings
from llama_index.core.llms import ChatMessage, MessageRole
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
    # 获取LLM
    llm = get_llm(model_name, temperature)
    
    # 处理参考资料
    if references:
        reference_text = "\n\n知识库中的相关信息:"
        for i, ref in enumerate(references):
            reference_text += f"\n\n文档 {i+1}:\n{ref.get('content', '')}"
        
        system_prompt += reference_text
    
    # 创建消息列表
    messages = []
    
    # 添加系统消息
    messages.append(ChatMessage(role=MessageRole.SYSTEM, content=system_prompt))
    
    # 添加对话历史
    for message in conversation_history:
        if message["role"] == "user":
            messages.append(ChatMessage(role=MessageRole.USER, content=message["content"]))
        elif message["role"] == "assistant":
            messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=message["content"]))
    
    # 生成响应
    response = await llm.achat(messages)
    
    return response.message.content

def create_prompt_template(template_name: str, **kwargs) -> str:
    """
    从模板创建提示，与现有LangChain的功能保持相同接口
    """
    # 定义模板
    templates = {
        "qa": (
            "你是一个根据提供的上下文回答问题的助手。\n"
            "如果答案不在上下文中，请说你不知道。\n"
            "上下文: {context}\n\n"
            "问题: {question}"
        ),
        "summarize": (
            "以简洁的方式总结以下文本:\n\n{text}"
        ),
        "assistant": (
            "你是{assistant_name}，{assistant_description}\n"
            "根据以下能力，以有帮助和准确的方式回应用户:\n"
            "{capabilities}"
        )
    }
    
    # 获取模板
    if template_name not in templates:
        raise ValueError(f"未找到模板 '{template_name}'")
    
    template = templates[template_name]
    
    # 用提供的值填充模板
    return template.format(**kwargs)
