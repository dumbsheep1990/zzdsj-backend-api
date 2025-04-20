"""
LangChain聊天模块: 处理与LLM的基于聊天的交互
使用LangChain强大的聊天模型和提示模板
"""

from typing import List, Dict, Any, Optional
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from app.config import settings

def get_chat_model(model_name: Optional[str] = None, temperature: Optional[float] = None):
    """获取LangChain聊天模型实例"""
    model = model_name or settings.DEFAULT_MODEL
    temp = temperature or float(settings.get_config("llm", "temperature", default=0.7))
    
    return ChatOpenAI(
        model_name=model,
        openai_api_key=settings.OPENAI_API_KEY,
        temperature=temp
    )

async def generate_response(
    system_prompt: str, 
    conversation_history: List[Dict[str, str]],
    references: Optional[List[Dict[str, Any]]] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None
) -> str:
    """
    使用LangChain的聊天模型生成响应
    
    参数:
        system_prompt: 给LLM的系统指令
        conversation_history: 消息字典列表，包含'role'和'content'键
        references: 可选的参考文档列表，包含在上下文中
        model_name: 可选的模型名称覆盖
        temperature: 可选的温度参数覆盖
        
    返回:
        生成的响应文本
    """
    # 初始化聊天模型
    chat = get_chat_model(model_name, temperature)
    
    # 准备消息
    messages = []
    
    # 如果有参考资料，添加带参考的系统消息
    if references:
        reference_text = "\n\n知识库中的相关信息:"
        for i, ref in enumerate(references):
            reference_text += f"\n\n文档 {i+1}:\n{ref.get('content', '')}"
        
        system_prompt += reference_text
    
    messages.append(SystemMessage(content=system_prompt))
    
    # 添加对话历史
    for message in conversation_history:
        if message["role"] == "user":
            messages.append(HumanMessage(content=message["content"]))
        elif message["role"] == "assistant":
            messages.append(AIMessage(content=message["content"]))
    
    # 生成响应
    response = await chat.ainvoke(messages)
    
    return response.content

def create_prompt_template(template_name: str, **kwargs) -> str:
    """
    从模板创建提示
    
    此函数加载预定义模板并用提供的值填充它们
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
