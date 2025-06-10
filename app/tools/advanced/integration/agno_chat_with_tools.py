"""
Agno原生聊天工具集成
基于Agno框架提供带工具能力的聊天接口，无依赖LlamaIndex
"""

import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union, Callable, AsyncIterator
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class AgnoToolCall:
    """Agno工具调用封装"""
    
    def __init__(self, tool_name: str, tool_function: Callable, parameters: Dict[str, Any]):
        self.tool_name = tool_name
        self.tool_function = tool_function
        self.parameters = parameters
        self.call_id = str(uuid.uuid4())
        self.start_time = None
        self.end_time = None
        self.result = None
        self.error = None
    
    async def execute(self) -> Dict[str, Any]:
        """执行工具调用"""
        self.start_time = datetime.now()
        
        try:
            if asyncio.iscoroutinefunction(self.tool_function):
                self.result = await self.tool_function(**self.parameters)
            else:
                self.result = self.tool_function(**self.parameters)
            
            self.end_time = datetime.now()
            
            return {
                "call_id": self.call_id,
                "tool_name": self.tool_name,
                "result": self.result,
                "success": True,
                "execution_time": (self.end_time - self.start_time).total_seconds()
            }
            
        except Exception as e:
            self.error = str(e)
            self.end_time = datetime.now()
            
            logger.error(f"Tool {self.tool_name} execution failed: {str(e)}")
            
            return {
                "call_id": self.call_id,
                "tool_name": self.tool_name,
                "error": self.error,
                "success": False,
                "execution_time": (self.end_time - self.start_time).total_seconds() if self.start_time else 0
            }

class AgnoToolRegistry:
    """Agno工具注册表"""
    
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
    
    def register_tool(self, name: str, function: Callable, description: str = "", 
                     parameters: Dict[str, Any] = None) -> None:
        """注册工具"""
        self.tools[name] = {
            "function": function,
            "description": description,
            "parameters": parameters or {},
            "metadata": {
                "name": name,
                "description": description,
                "is_async": asyncio.iscoroutinefunction(function)
            }
        }
    
    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """获取工具"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有工具"""
        return [
            {
                "name": name,
                "description": tool["description"],
                "parameters": tool["parameters"],
                "metadata": tool["metadata"]
            }
            for name, tool in self.tools.items()
        ]

class AgnoChatWithTools:
    """Agno原生聊天工具管理器"""
    
    def __init__(self, 
                 llm_service,
                 tool_registry: Optional[AgnoToolRegistry] = None,
                 max_iterations: int = 10,
                 verbose: bool = False,
                 tool_choice: str = "auto"):
        """
        初始化Agno聊天工具管理器
        
        Args:
            llm_service: LLM服务实例
            tool_registry: 工具注册表
            max_iterations: 最大工具调用迭代次数
            verbose: 是否输出详细日志
            tool_choice: 工具选择策略 ("auto", "none", "required")
        """
        self.llm_service = llm_service
        self.tool_registry = tool_registry or AgnoToolRegistry()
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.tool_choice = tool_choice
        
        # 注册内置工具
        self._register_builtin_tools()
        
        if self.verbose:
            logger.info(f"Initialized AgnoChatWithTools with {len(self.tool_registry.tools)} tools")
    
    def _register_builtin_tools(self):
        """注册内置工具"""
        # 注册搜索工具
        try:
            from app.tools.base.search.agno_search_tool import get_agno_search_tool
            search_tool = get_agno_search_tool()
            
            self.tool_registry.register_tool(
                name="web_search",
                function=search_tool.search_web,
                description="搜索互联网获取实时信息",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索查询"
                        },
                        "max_results": {
                            "type": "integer", 
                            "description": "最大结果数",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            )
        except ImportError:
            logger.warning("Failed to import Agno search tool")
        
        # 注册推理工具
        try:
            from app.tools.advanced.reasoning.agno_cot_tool import get_agno_cot_tool
            cot_tool = get_agno_cot_tool()
            
            self.tool_registry.register_tool(
                name="chain_of_thought",
                function=cot_tool.reason_with_cot,
                description="使用思维链进行复杂推理",
                parameters={
                    "type": "object",
                    "properties": {
                        "problem": {
                            "type": "string",
                            "description": "需要推理的问题"
                        },
                        "steps": {
                            "type": "integer",
                            "description": "推理步骤数",
                            "default": 5
                        }
                    },
                    "required": ["problem"]
                }
            )
        except ImportError:
            logger.warning("Failed to import Agno CoT tool")
    
    async def chat(self, 
                   messages: List[Dict[str, str]], 
                   enable_tools: bool = True,
                   stream: bool = False,
                   **kwargs) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
        """
        执行聊天，支持工具调用
        
        Args:
            messages: 消息列表
            enable_tools: 是否启用工具调用
            stream: 是否流式输出
            **kwargs: 其他参数
            
        Returns:
            聊天响应或流式生成器
        """
        if stream:
            return self._stream_chat(messages, enable_tools, **kwargs)
        else:
            return await self._complete_chat(messages, enable_tools, **kwargs)
    
    async def _complete_chat(self, 
                           messages: List[Dict[str, str]], 
                           enable_tools: bool = True,
                           **kwargs) -> Dict[str, Any]:
        """完整聊天处理"""
        conversation_history = messages.copy()
        tool_calls_history = []
        iteration = 0
        
        while iteration < self.max_iterations:
            # 构建系统提示
            system_message = self._build_system_message(enable_tools)
            
            # 构建当前消息
            current_messages = [system_message] + conversation_history
            
            # 调用LLM
            try:
                response = await self.llm_service.chat_completion(
                    messages=current_messages,
                    **kwargs
                )
                
                response_content = response["choices"][0]["message"]["content"]
                
                if self.verbose:
                    logger.info(f"LLM response: {response_content[:200]}...")
                
            except Exception as e:
                logger.error(f"LLM call failed: {str(e)}")
                return {
                    "response": f"LLM调用失败: {str(e)}",
                    "success": False,
                    "error": str(e)
                }
            
            # 检查是否需要工具调用
            if enable_tools and self.tool_choice != "none":
                tool_calls = self._extract_tool_calls(response_content)
                
                if tool_calls:
                    # 执行工具调用
                    tool_results = await self._execute_tool_calls(tool_calls)
                    tool_calls_history.extend(tool_results)
                    
                    # 将工具结果添加到对话历史
                    conversation_history.append({
                        "role": "assistant",
                        "content": response_content
                    })
                    
                    # 添加工具结果
                    tool_result_message = self._format_tool_results(tool_results)
                    conversation_history.append({
                        "role": "system",
                        "content": tool_result_message
                    })
                    
                    iteration += 1
                    continue
            
            # 没有工具调用，返回最终结果
            return {
                "response": response_content,
                "success": True,
                "tool_calls": tool_calls_history,
                "iterations": iteration,
                "metadata": {
                    "tools_enabled": enable_tools,
                    "tool_choice": self.tool_choice,
                    "available_tools": len(self.tool_registry.tools)
                }
            }
        
        # 达到最大迭代次数
        return {
            "response": response_content if 'response_content' in locals() else "达到最大迭代次数",
            "success": True,
            "tool_calls": tool_calls_history,
            "iterations": iteration,
            "max_iterations_reached": True,
            "metadata": {
                "tools_enabled": enable_tools,
                "tool_choice": self.tool_choice,
                "available_tools": len(self.tool_registry.tools)
            }
        }
    
    async def _stream_chat(self, 
                          messages: List[Dict[str, str]], 
                          enable_tools: bool = True,
                          **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """流式聊天处理"""
        # 先获取完整结果，然后流式返回
        complete_result = await self._complete_chat(messages, enable_tools, **kwargs)
        
        response_text = complete_result.get("response", "")
        tool_calls = complete_result.get("tool_calls", [])
        
        # 逐步返回响应文本
        for i, char in enumerate(response_text):
            yield {
                "response_delta": char,
                "done": False,
                "metadata": {"position": i}
            }
            await asyncio.sleep(0.01)  # 模拟流式延迟
        
        # 返回工具调用结果
        if tool_calls:
            yield {
                "response_delta": "",
                "done": False,
                "tool_calls": tool_calls
            }
        
        # 最终完成
        yield {
            "response_delta": "",
            "done": True,
            "complete_result": complete_result
        }
    
    def _build_system_message(self, enable_tools: bool) -> Dict[str, str]:
        """构建系统消息"""
        system_content = "你是一个有用的AI助手。"
        
        if enable_tools and self.tool_choice != "none":
            tools_info = self.tool_registry.list_tools()
            system_content += f"\n\n你可以使用以下工具:\n"
            
            for tool in tools_info:
                system_content += f"- {tool['name']}: {tool['description']}\n"
            
            system_content += "\n如需使用工具，请按以下格式:\n"
            system_content += "```tool\n{\"tool_name\": \"工具名\", \"parameters\": {参数}}\n```"
        
        return {"role": "system", "content": system_content}
    
    def _extract_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """从响应中提取工具调用"""
        import re
        
        tool_calls = []
        
        # 查找工具调用模式
        pattern = r'```tool\s*\n(.*?)\n```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                tool_call = json.loads(match.strip())
                if "tool_name" in tool_call and "parameters" in tool_call:
                    tool_calls.append(tool_call)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse tool call: {match}")
        
        return tool_calls
    
    async def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """执行工具调用"""
        results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.get("tool_name")
            parameters = tool_call.get("parameters", {})
            
            tool_info = self.tool_registry.get_tool(tool_name)
            if not tool_info:
                results.append({
                    "tool_name": tool_name,
                    "error": f"Tool {tool_name} not found",
                    "success": False
                })
                continue
            
            # 创建工具调用实例
            agno_tool_call = AgnoToolCall(
                tool_name=tool_name,
                tool_function=tool_info["function"],
                parameters=parameters
            )
            
            # 执行工具调用
            result = await agno_tool_call.execute()
            results.append(result)
        
        return results
    
    def _format_tool_results(self, tool_results: List[Dict[str, Any]]) -> str:
        """格式化工具结果"""
        formatted_results = []
        
        for result in tool_results:
            if result["success"]:
                formatted_results.append(
                    f"工具 {result['tool_name']} 执行成功，结果: {json.dumps(result['result'], ensure_ascii=False)}"
                )
            else:
                formatted_results.append(
                    f"工具 {result['tool_name']} 执行失败，错误: {result['error']}"
                )
        
        return "工具执行结果:\n" + "\n".join(formatted_results)
    
    def add_tool(self, name: str, function: Callable, description: str = "", 
                parameters: Dict[str, Any] = None) -> None:
        """添加工具"""
        self.tool_registry.register_tool(name, function, description, parameters)
    
    def remove_tool(self, name: str) -> bool:
        """移除工具"""
        if name in self.tool_registry.tools:
            del self.tool_registry.tools[name]
            return True
        return False
    
    def list_available_tools(self) -> List[Dict[str, Any]]:
        """列出可用工具"""
        return self.tool_registry.list_tools()

# 工厂函数
def create_agno_chat_with_tools(llm_service,
                               max_iterations: int = 10,
                               verbose: bool = False,
                               tool_choice: str = "auto") -> AgnoChatWithTools:
    """创建Agno聊天工具管理器实例"""
    return AgnoChatWithTools(
        llm_service=llm_service,
        max_iterations=max_iterations,
        verbose=verbose,
        tool_choice=tool_choice
    )

# 单例获取
_agno_chat_with_tools = None

def get_agno_chat_with_tools(llm_service=None) -> AgnoChatWithTools:
    """获取Agno聊天工具管理器单例"""
    global _agno_chat_with_tools
    
    if _agno_chat_with_tools is None and llm_service:
        _agno_chat_with_tools = create_agno_chat_with_tools(llm_service)
    
    return _agno_chat_with_tools 