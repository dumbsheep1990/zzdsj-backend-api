"""
LlamaIndex核心模块: 提供统一入口点和路由功能
替代LangChain作为系统的主要协调框架
"""

from typing import List, Dict, Any, Optional, Union
from llama_index.core import Settings, ServiceContext
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.openai import OpenAI
from llama_index.core.response_synthesizers import ResponseMode
from app.config import settings

def get_llm(model_name: Optional[str] = None, temperature: Optional[float] = None):
    """获取LlamaIndex LLM实例，替代LangChain的ChatOpenAI"""
    model = model_name or settings.DEFAULT_MODEL
    temp = temperature or float(settings.get_config("llm", "temperature", default=0.7))
    
    return OpenAI(
        model=model,
        api_key=settings.OPENAI_API_KEY,
        temperature=temp
    )

def get_service_context(model_name: Optional[str] = None, temperature: Optional[float] = None):
    """创建LlamaIndex服务上下文，配置全局设置"""
    llm = get_llm(model_name, temperature)
    
    # 设置全局服务上下文
    service_context = ServiceContext.from_defaults(
        llm=llm,
        embed_model="local:BAAI/bge-small-zh-v1.5",  # 可以根据需要配置
        chunk_size=settings.LLAMAINDEX_CHUNK_SIZE,
        chunk_overlap=settings.LLAMAINDEX_CHUNK_OVERLAP
    )
    
    return service_context

def create_chat_memory():
    """创建聊天记忆缓冲，替代LangChain的对话历史管理"""
    return ChatMemoryBuffer.from_defaults(token_limit=4096)

def create_router(
    query_engines: List[Dict[str, Any]],
    service_context: Optional[ServiceContext] = None
) -> RouterQueryEngine:
    """
    创建查询路由器，作为系统的统一入口
    
    参数:
        query_engines: 查询引擎配置列表
        service_context: 服务上下文
        
    返回:
        路由查询引擎
    """
    # 确保有服务上下文
    if service_context is None:
        service_context = get_service_context()
    
    # 创建查询引擎工具
    query_engine_tools = []
    for engine_config in query_engines:
        query_engine_tools.append(
            QueryEngineTool(
                query_engine=engine_config["engine"],
                metadata=ToolMetadata(
                    name=engine_config["name"],
                    description=engine_config["description"]
                )
            )
        )
    
    # 创建路由引擎
    router = RouterQueryEngine.from_defaults(
        query_engine_tools=query_engine_tools,
        service_context=service_context,
        select_multi=True  # 允许选择多个引擎
    )
    
    return router

async def process_query(
    query: str,
    engine: Any,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    system_prompt: Optional[str] = None,
    stream: bool = False
) -> Dict[str, Any]:
    """
    统一查询处理，替代LangChain的生成响应
    
    参数:
        query: 用户查询
        engine: 查询引擎
        conversation_history: 对话历史
        system_prompt: 系统提示
        stream: 是否流式响应
        
    返回:
        包含答案和元数据的响应
    """
    # 处理系统提示
    if system_prompt and hasattr(engine, "update_prompts"):
        engine.update_prompts({"system_prompt": system_prompt})
    
    # 处理对话历史
    if conversation_history and hasattr(engine, "memory"):
        for message in conversation_history:
            if message["role"] == "user":
                engine.memory.put({"role": "user", "content": message["content"]})
            elif message["role"] == "assistant":
                engine.memory.put({"role": "assistant", "content": message["content"]})
    
    # 执行查询
    if stream:
        response = engine.stream_chat(query)
        # 处理流式响应
        return {"streaming": True, "response": response}
    else:
        response = await engine.aquery(query)
        
        # 准备结果
        result = {
            "answer": response.response,
            "metadata": {}
        }
        
        # 添加源文档(如果有)
        if hasattr(response, "source_nodes"):
            sources = []
            for node in response.source_nodes:
                sources.append({
                    "content": node.text,
                    "metadata": node.metadata,
                    "score": node.score if node.score is not None else 1.0,
                    "node_id": node.node_id
                })
            result["metadata"]["sources"] = sources
        
        return result

def format_prompt(template_name: str, **kwargs) -> str:
    """
    格式化提示，替代LangChain的提示模板
    
    参数:
        template_name: 模板名称
        **kwargs: 模板参数
        
    返回:
        格式化后的提示
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
    
    # 获取并填充模板
    if template_name not in templates:
        raise ValueError(f"未找到模板 '{template_name}'")
    
    template = templates[template_name]
    return template.format(**kwargs)
