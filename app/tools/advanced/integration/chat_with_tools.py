"""
聊天工具集成中间件
提供带工具能力的聊天接口，支持不同模型的函数调用能力
"""

import json
import logging
from typing import List, Dict, Any, Optional, Union, Tuple, Callable

from llama_index.core.llms import LLM, ChatMessage, MessageRole
from llama_index.core.tools import BaseTool
from llama_index.core.callbacks import CallbackManager

from app.config import settings
from app.tools.advanced.integration.model_with_tools import ModelWithTools, create_model_with_tools
from app.tools.base.utils.tool_utils import get_all_tools, get_web_search_tool

logger = logging.getLogger(__name__)

class ChatWithTools:
    """带工具能力的聊天管理器"""
    
    def __init__(
        self,
        llm: LLM,
        tools: Optional[List[BaseTool]] = None,
        function_calling_strategy: str = "auto",
        verbose: bool = False,
        max_iterations: int = 10,
        callback_manager: Optional[CallbackManager] = None
    ):
        """
        初始化带工具的聊天管理器
        
        参数:
            llm: 语言模型实例
            tools: 工具列表，如果为None则使用get_all_tools获取
            function_calling_strategy: 函数调用策略，可选值: "auto", "native", "chain"
            verbose: 是否输出详细日志
            max_iterations: 最大迭代次数
            callback_manager: 回调管理器
        """
        self.llm = llm
        self.tools = tools if tools is not None else get_all_tools()
        self.model_with_tools = create_model_with_tools(
            llm=llm,
            function_calling_strategy=function_calling_strategy,
            verbose=verbose,
            max_iterations=max_iterations,
            tools=self.tools,
            callback_manager=callback_manager
        )
        self.callback_manager = callback_manager
        self.verbose = verbose
    
    async def achat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        enable_tools: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        异步聊天，支持流式输出和工具调用
        
        参数:
            messages: 消息列表，格式为[{"role": "user", "content": "..."}]
            stream: 是否启用流式输出
            enable_tools: 是否启用工具调用
            **kwargs: 其他参数
            
        返回:
            聊天响应
        """
        try:
            if self.verbose:
                logger.info(f"Processing chat with {len(messages)} messages")
                
            # 获取工具调用参数
            # 如果启用工具，则传递工具配置
            tool_args = {
                "max_iterations": kwargs.pop("max_iterations", 10),
                "tool_choice": kwargs.pop("tool_choice", "auto"),
            } if enable_tools else {
                "tool_choice": "none"
            }
            
            # 合并所有参数
            combined_args = {**kwargs, **tool_args}
            
            # 如果使用流式输出
            if stream:
                # 流式响应处理
                async def astream_response():
                    # 由于当前函数调用适配器不支持流式工具调用
                    # 先完整获取结果，然后模拟流式输出
                    result = await self.model_with_tools.arun(messages, **combined_args)
                    
                    # 提取文本内容
                    content = result.get("response", "")
                    
                    # 逐字符返回结果 (这只是模拟，实际应当实现真正的流式)
                    for i in range(len(content)):
                        chunk = content[i]
                        yield {"response": chunk, "done": i == len(content) - 1}
                    
                    # 工具调用结果
                    if enable_tools and "tool_calls" in result and result["tool_calls"]:
                        yield {
                            "response": "",
                            "tool_calls": result["tool_calls"],
                            "done": True
                        }
                
                # 返回异步生成器
                return astream_response()
            
            # 非流式输出
            result = await self.model_with_tools.arun(messages, **combined_args)
            
            # 添加元数据
            if "metadata" not in result:
                result["metadata"] = {}
            
            # 添加工具信息
            if enable_tools and self.tools:
                result["metadata"]["available_tools"] = [
                    {
                        "name": tool.metadata.get("name", tool.name),
                        "description": tool.metadata.get("description", "")
                    }
                    for tool in self.tools
                ]
            
            return result
        
        except Exception as e:
            logger.error(f"Chat with tools error: {str(e)}")
            # 返回错误信息
            return {
                "response": f"处理请求时出错: {str(e)}",
                "error": str(e),
                "success": False
            }
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        enable_tools: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        同步聊天，支持流式输出和工具调用
        
        参数:
            messages: 消息列表，格式为[{"role": "user", "content": "..."}]
            stream: 是否启用流式输出
            enable_tools: 是否启用工具调用
            **kwargs: 其他参数
            
        返回:
            聊天响应
        """
        import asyncio
        return asyncio.run(self.achat(
            messages=messages,
            stream=stream,
            enable_tools=enable_tools,
            **kwargs
        ))
    
    def format_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        将内部响应格式化为API响应格式
        
        参数:
            result: 内部响应结果
            
        返回:
            API响应格式
        """
        if not result:
            return {
                "response": "",
                "success": False,
                "error": "Empty result"
            }
        
        # 提取响应内容
        response = result.get("response", "")
        
        # 提取工具调用
        tool_calls = result.get("tool_calls", [])
        tool_results = result.get("tool_results", [])
        
        # 格式化响应
        formatted_response = {
            "response": response,
            "success": True
        }
        
        # 如果有工具调用，添加工具调用信息
        if tool_calls:
            formatted_response["tool_calls"] = tool_calls
            
        # 如果有工具调用结果，添加结果信息
        if tool_results:
            formatted_response["tool_results"] = tool_results
            
        # 添加元数据
        if "metadata" in result:
            formatted_response["metadata"] = result["metadata"]
            
        return formatted_response


def create_chat_with_tools(
    llm: LLM,
    function_calling_strategy: str = "auto",
    verbose: bool = False,
    max_iterations: int = 10,
    tools: Optional[List[BaseTool]] = None,
    callback_manager: Optional[CallbackManager] = None
) -> ChatWithTools:
    """
    创建ChatWithTools实例
    
    参数:
        llm: 语言模型实例
        function_calling_strategy: 函数调用策略，可选值: "auto", "native", "chain"
        verbose: 是否输出详细日志
        max_iterations: 最大迭代次数
        tools: 工具列表
        callback_manager: 回调管理器
        
    返回:
        ChatWithTools: 实例
    """
    return ChatWithTools(
        llm=llm,
        tools=tools,
        function_calling_strategy=function_calling_strategy,
        verbose=verbose,
        max_iterations=max_iterations,
        callback_manager=callback_manager
    )
