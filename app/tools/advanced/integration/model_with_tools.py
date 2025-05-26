"""
模型工具集成中间件
将模型和工具能力集成，提供统一的函数调用接口
"""

import logging
from typing import List, Dict, Any, Optional, Union, Tuple

from llama_index.core.llms import LLM, ChatMessage, MessageRole
from llama_index.core.tools import BaseTool
from llama_index.core.callbacks import CallbackManager

from app.config import settings
from app.tools.base.function_calling.adapter import (
    FunctionCallingAdapter, 
    FunctionCallingConfig,
    FunctionCallingStrategy,
    create_function_calling_adapter
)
from app.tools.base.utils.tool_utils import get_all_tools

logger = logging.getLogger(__name__)

class ModelWithTools:
    """将LLM与工具能力集成的包装类"""
    
    def __init__(
        self,
        llm: LLM,
        tools: Optional[List[BaseTool]] = None,
        function_calling_config: Optional[Dict[str, Any]] = None,
        callback_manager: Optional[CallbackManager] = None
    ):
        """
        初始化模型工具集成
        
        参数:
            llm: 语言模型实例
            tools: 工具列表，如果为None则使用get_all_tools获取
            function_calling_config: 函数调用配置
            callback_manager: 回调管理器
        """
        self.llm = llm
        self.tools = tools if tools is not None else get_all_tools()
        self.function_calling_adapter = create_function_calling_adapter(
            llm=llm,
            tools=self.tools,
            config=function_calling_config,
            callback_manager=callback_manager
        )
    
    async def arun(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        异步执行对话并处理工具调用
        
        参数:
            messages: 消息列表，格式为[{"role": "user", "content": "..."}]
            **kwargs: 传递给底层适配器的参数
            
        返回:
            包含响应和工具调用结果的字典
        """
        # 转换为ChatMessage格式
        chat_messages = [
            ChatMessage(
                role=MessageRole(msg["role"]),
                content=msg["content"]
            )
            for msg in messages
        ]
        
        # 使用适配器处理函数调用
        function_result = await self.function_calling_adapter.arun(chat_messages, **kwargs)
        
        return function_result
    
    def run(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        同步执行对话并处理工具调用（包装异步方法）
        
        参数:
            messages: 消息列表，格式为[{"role": "user", "content": "..."}]
            **kwargs: 传递给底层适配器的参数
            
        返回:
            包含响应和工具调用结果的字典
        """
        import asyncio
        return asyncio.run(self.arun(messages, **kwargs))
    
    def __repr__(self) -> str:
        return f"ModelWithTools(llm={self.llm}, tools_count={len(self.tools)})"


def create_model_with_tools(
    llm: LLM,
    function_calling_strategy: str = "auto",
    verbose: bool = False,
    max_iterations: int = 10,
    tools: Optional[List[BaseTool]] = None,
    callback_manager: Optional[CallbackManager] = None
) -> ModelWithTools:
    """
    创建ModelWithTools实例
    
    参数:
        llm: 语言模型实例
        function_calling_strategy: 函数调用策略，可选值: "auto", "native", "chain"
        verbose: 是否输出详细日志
        max_iterations: 最大迭代次数
        tools: 工具列表
        callback_manager: 回调管理器
        
    返回:
        ModelWithTools: 实例
    """
    # 创建函数调用配置
    function_calling_config = {
        "strategy": function_calling_strategy,
        "verbose": verbose,
        "max_iterations": max_iterations
    }
    
    # 创建并返回ModelWithTools实例
    return ModelWithTools(
        llm=llm,
        tools=tools,
        function_calling_config=function_calling_config,
        callback_manager=callback_manager
    )
