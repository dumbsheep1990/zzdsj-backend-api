from typing import Any, Dict, List, Optional, Tuple, Union
import json
import logging
import asyncio

# 正式导入CAMEL库
from camel.agents import ChatAgent
from camel.types import ModelType
from camel.configs import ChatGPTConfig
from camel.tools import BaseTool, ToolMessage

from app.utils.logging import get_logger

logger = get_logger(__name__)

class BaseAgent:
    """基础智能体，扩展OWL的ChatAgent，提供工具调用和任务处理能力"""
    
    def __init__(self, model_config: Dict[str, Any], system_message: Optional[str] = None):
        """初始化基础智能体
        
        Args:
            model_config: 模型配置，包含model_name、temperature、max_tokens等参数
            system_message: 系统消息，用于设置智能体的角色和行为
        """
        # 提取模型配置
        model_name = model_config.get("model_name", "gpt-4")
        temperature = model_config.get("temperature", 0.7)
        max_tokens = model_config.get("max_tokens", 1500)
        
        # 映射模型名称到ModelType
        model_mapping = {
            "gpt-4": ModelType.GPT_4,
            "gpt-4-turbo": ModelType.GPT_4_TURBO,
            "gpt-3.5-turbo": ModelType.GPT_3_5_TURBO,
            "qwen-turbo": ModelType.QWEN_TURBO,
            "qwen-plus": ModelType.QWEN_PLUS,
            "claude-3-opus": ModelType.CLAUDE_3_OPUS,
            "claude-3-sonnet": ModelType.CLAUDE_3_SONNET,
            "claude-3-haiku": ModelType.CLAUDE_3_HAIKU
        }
        
        model_type = model_mapping.get(model_name, ModelType.GPT_4)
        
        # 创建配置对象
        config = ChatGPTConfig(
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # 创建智能体实例
        self.agent = ChatAgent(
            model_type=model_type,
            system_message=system_message or "",
            config=config
        )
        
        # 初始化属性
        self.tools = []
        self.tool_map = {}  # 工具名称到实例的映射
        self.model_config = model_config
        self.system_message = system_message
        self.workflow = None
        self.chat_history = []  # 记录聊天历史
        self.token_usage = {"prompt": 0, "completion": 0, "total": 0}  # 记录token使用情况
        
    def add_tools(self, tools: List[Any]) -> None:
        """添加工具到智能体
        
        Args:
            tools: 要添加的工具列表
        """
        for tool in tools:
            if not hasattr(tool, 'name') or not hasattr(tool, '__call__'):
                logger.warning(f"忽略无效工具: {tool}，该工具缺少name属性或不可调用")
                continue
                
            # 将工具包装为CAMEL的BaseTool格式（如果尚未包装）
            if not isinstance(tool, BaseTool):
                tool = self._wrap_as_camel_tool(tool)
                
            self.tools.append(tool)
            self.tool_map[tool.name] = tool
            
        # 更新智能体的工具集
        self.agent.set_tools(self.tools)
        
    def _wrap_as_camel_tool(self, tool: Any) -> BaseTool:
        """将普通工具包装为CAMEL格式的工具
        
        Args:
            tool: 要包装的工具
            
        Returns:
            BaseTool: 包装后的CAMEL工具
        """
        tool_name = getattr(tool, 'name', None) or str(id(tool))
        tool_description = getattr(tool, 'description', None) or f"工具 {tool_name}"
        
        # 创建CAMEL格式的工具
        class WrappedTool(BaseTool):
            def __init__(self, original_tool):
                super().__init__(name=tool_name, description=tool_description)
                self.original_tool = original_tool
                
            async def __call__(self, *args, **kwargs):
                try:
                    # 调用原始工具
                    if asyncio.iscoroutinefunction(self.original_tool.__call__):
                        result = await self.original_tool(*args, **kwargs)
                    else:
                        result = self.original_tool(*args, **kwargs)
                    
                    # 处理结果，确保返回ToolMessage
                    if isinstance(result, ToolMessage):
                        return result
                    elif isinstance(result, str):
                        return ToolMessage(content=result)
                    else:
                        try:
                            result_str = json.dumps(result, ensure_ascii=False)
                        except:
                            result_str = str(result)
                        return ToolMessage(content=result_str)
                except Exception as e:
                    logger.error(f"工具 {tool_name} 执行失败: {str(e)}")
                    return ToolMessage(content=f"错误: {str(e)}")
                    
        return WrappedTool(tool)
        
    def set_workflow(self, workflow_definition: Dict[str, Any]) -> None:
        """设置工作流定义
        
        Args:
            workflow_definition: 工作流定义，包含步骤和条件
        """
        self.workflow = workflow_definition
        
    async def chat(self, message: str) -> str:
        """与智能体交互
        
        Args:
            message: 用户消息
            
        Returns:
            str: 智能体回复
        """
        # 记录请求
        self.chat_history.append({"role": "user", "content": message})
        
        # 使用CAMEL的agent进行聊天
        response, token_info = await self.agent.chat(message, return_token_count=True)
        
        # 更新token使用记录
        if token_info:
            self.token_usage["prompt"] += token_info.get("prompt_tokens", 0)
            self.token_usage["completion"] += token_info.get("completion_tokens", 0)
            self.token_usage["total"] += token_info.get("total_tokens", 0)
            
        # 记录回复
        self.chat_history.append({"role": "assistant", "content": response})
        
        return response
        
    async def run_task(self, task: str, tools: List[Any] = None, **kwargs) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        """运行任务
        
        Args:
            task: 任务描述
            tools: 可用工具列表，如果为None，则使用已添加的工具
            **kwargs: 额外参数
            
        Returns:
            Tuple[str, List[Dict[str, Any]], Dict[str, Any]]: (回答, 交互历史, 元数据)
        """
        # 确保工具列表
        if tools:
            self.add_tools(tools)
            
        # 记录任务开始
        logger.info(f"开始执行任务: {task[:100]}...")
        
        # 执行任务
        try:
            # 调用智能体处理任务
            response = await self.chat(task)
            
            # 构建元数据
            metadata = {
                "token_usage": self.token_usage,
                "tool_calls": [],  # 可以在实际工具调用时填充
                "task_completed": True
            }
            
            return response, self.chat_history, metadata
            
        except Exception as e:
            logger.error(f"执行任务时出错: {str(e)}")
            error_response = f"执行任务时发生错误: {str(e)}"
            
            # 记录错误信息
            self.chat_history.append({"role": "system", "content": error_response})
            
            # 构建错误元数据
            error_metadata = {
                "token_usage": self.token_usage,
                "error": str(e),
                "task_completed": False
            }
            
            return error_response, self.chat_history, error_metadata
        
