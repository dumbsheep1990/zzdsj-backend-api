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
from app.middleware.function_calling import (
    FunctionCallingAdapter, 
    FunctionCallingConfig,
    FunctionCallingStrategy,
    create_function_calling_adapter
)
from app.middleware.tool_utils import get_all_tools

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
    
    async def achat(
        self,
        messages: List[ChatMessage],
        use_tools: bool = True,
        tools: Optional[List[BaseTool]] = None,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        异步执行聊天，支持工具调用
        
        参数:
            messages: 对话消息列表
            use_tools: 是否使用工具
            tools: 可选的工具列表，如果提供则覆盖初始化时的工具
            
        返回:
            Tuple[str, Optional[Dict[str, Any]]]: (响应文本, 工具调用结果)
        """
        if use_tools:
            active_tools = tools if tools is not None else self.tools
            return await self.function_calling_adapter.arun(messages, active_tools)
        else:
            # 不使用工具，直接调用模型
            response = await self.llm.achat(messages)
            return response.message.content, None
    
    def chat(
        self,
        messages: List[ChatMessage],
        use_tools: bool = True,
        tools: Optional[List[BaseTool]] = None,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        同步执行聊天，支持工具调用
        
        参数:
            messages: 对话消息列表
            use_tools: 是否使用工具
            tools: 可选的工具列表，如果提供则覆盖初始化时的工具
            
        返回:
            Tuple[str, Optional[Dict[str, Any]]]: (响应文本, 工具调用结果)
        """
        import asyncio
        return asyncio.run(self.achat(messages, use_tools, tools))
    
    @classmethod
    def from_llm(
        cls,
        llm: LLM,
        function_calling_strategy: str = "auto",
        verbose: bool = False,
        max_iterations: int = 10,
        tools: Optional[List[BaseTool]] = None,
        callback_manager: Optional[CallbackManager] = None
    ) -> "ModelWithTools":
        """
        从LLM创建ModelWithTools实例
        
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
        config = {
            "strategy": function_calling_strategy,
            "verbose": verbose,
            "max_iterations": max_iterations
        }
        
        return cls(
            llm=llm,
            tools=tools,
            function_calling_config=config,
            callback_manager=callback_manager
        )


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
    return ModelWithTools.from_llm(
        llm=llm,
        function_calling_strategy=function_calling_strategy,
        verbose=verbose,
        max_iterations=max_iterations,
        tools=tools,
        callback_manager=callback_manager
    )
