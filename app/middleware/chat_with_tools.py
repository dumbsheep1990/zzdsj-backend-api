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
from app.middleware.model_with_tools import ModelWithTools, create_model_with_tools
from app.middleware.tool_utils import get_all_tools, get_web_search_tool

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
        self.chat_history: List[ChatMessage] = []
        self.verbose = verbose
        self.tool_usage_metrics: Dict[str, int] = {}  # 工具使用统计
    
    def reset(self):
        """重置聊天历史"""
        self.chat_history = []
        
    def add_message(self, role: str, content: str):
        """
        添加消息到聊天历史
        
        参数:
            role: 消息角色，"user", "assistant", "system"
            content: 消息内容
        """
        if role == "user":
            message_role = MessageRole.USER
        elif role == "assistant":
            message_role = MessageRole.ASSISTANT
        elif role == "system":
            message_role = MessageRole.SYSTEM
        else:
            message_role = MessageRole.USER
            
        self.chat_history.append(ChatMessage(role=message_role, content=content))
    
    def get_chat_history(self) -> List[Dict[str, str]]:
        """
        获取聊天历史
        
        返回:
            List[Dict[str, str]]: 聊天历史记录
        """
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in self.chat_history
        ]
    
    async def achat(
        self,
        message: str,
        system_message: Optional[str] = None,
        use_tools: bool = True,
        selected_tools: Optional[List[str]] = None,
        include_history: bool = True,
    ) -> Dict[str, Any]:
        """
        异步执行聊天，支持工具调用
        
        参数:
            message: 用户消息
            system_message: 系统消息，如果为None则不添加
            use_tools: 是否使用工具
            selected_tools: 选择使用的工具名称列表
            include_history: 是否包含历史消息
            
        返回:
            Dict[str, Any]: 响应信息，包含文本和工具调用信息
        """
        # 构建消息列表
        messages = []
        
        # 添加系统消息
        if system_message:
            messages.append(ChatMessage(role=MessageRole.SYSTEM, content=system_message))
        
        # 添加历史消息
        if include_history and self.chat_history:
            messages.extend(self.chat_history)
        
        # 添加当前用户消息
        messages.append(ChatMessage(role=MessageRole.USER, content=message))
        
        # 过滤选择的工具
        active_tools = None
        if selected_tools and use_tools:
            tool_map = {tool.metadata.name: tool for tool in self.tools}
            active_tools = [
                tool_map[name] for name in selected_tools
                if name in tool_map
            ]
            
            if not active_tools:
                logger.warning(f"未找到指定的工具: {selected_tools}，将使用所有可用工具")
                active_tools = None
        
        # 调用模型
        response_text, tool_results = await self.model_with_tools.achat(
            messages=messages,
            use_tools=use_tools,
            tools=active_tools
        )
        
        # 更新聊天历史
        self.add_message("user", message)
        self.add_message("assistant", response_text)
        
        # 更新工具使用统计
        if tool_results:
            for tool_name in tool_results:
                self.tool_usage_metrics[tool_name] = self.tool_usage_metrics.get(tool_name, 0) + 1
        
        # 构建响应
        result = {
            "response": response_text,
            "has_tool_calls": bool(tool_results),
            "tool_calls": [],
            "tool_metrics": dict(self.tool_usage_metrics)
        }
        
        # 添加工具调用信息
        if tool_results:
            for tool_name, tool_result in tool_results.items():
                result["tool_calls"].append({
                    "tool": tool_name,
                    "result": tool_result
                })
        
        return result
    
    def chat(
        self,
        message: str,
        system_message: Optional[str] = None,
        use_tools: bool = True,
        selected_tools: Optional[List[str]] = None,
        include_history: bool = True,
    ) -> Dict[str, Any]:
        """
        同步执行聊天，支持工具调用
        
        参数:
            message: 用户消息
            system_message: 系统消息，如果为None则不添加
            use_tools: 是否使用工具
            selected_tools: 选择使用的工具名称列表
            include_history: 是否包含历史消息
            
        返回:
            Dict[str, Any]: 响应信息，包含文本和工具调用信息
        """
        import asyncio
        return asyncio.run(self.achat(
            message=message,
            system_message=system_message,
            use_tools=use_tools,
            selected_tools=selected_tools,
            include_history=include_history
        ))
    
    @classmethod
    def from_llm(
        cls,
        llm: LLM,
        function_calling_strategy: str = "auto",
        verbose: bool = False,
        max_iterations: int = 10,
        callback_manager: Optional[CallbackManager] = None
    ) -> "ChatWithTools":
        """
        从LLM创建ChatWithTools实例
        
        参数:
            llm: 语言模型实例
            function_calling_strategy: 函数调用策略，可选值: "auto", "native", "chain"
            verbose: 是否输出详细日志
            max_iterations: 最大迭代次数
            callback_manager: 回调管理器
            
        返回:
            ChatWithTools: 实例
        """
        return cls(
            llm=llm,
            function_calling_strategy=function_calling_strategy,
            verbose=verbose,
            max_iterations=max_iterations,
            callback_manager=callback_manager
        )


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
