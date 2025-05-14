from typing import Any, Dict, List, Optional, Union, Callable
import asyncio
import json
import inspect
import aiohttp
from functools import wraps

from app.utils.logger import get_logger

logger = get_logger(__name__)

class CustomTool:
    """自定义工具类，封装函数或API为可调用工具"""
    
    def __init__(self, name: str, description: str, function: Optional[Callable] = None, 
                 api_endpoint: Optional[str] = None, is_async: bool = False):
        """初始化自定义工具
        
        Args:
            name: 工具名称
            description: 工具描述
            function: 本地函数
            api_endpoint: API端点，远程工具使用
            is_async: 是否为异步工具
        """
        self.name = name
        self.description = description
        self.function = function
        self.api_endpoint = api_endpoint
        self.is_async = is_async
        self.function_def = None
        
    async def __call__(self, **kwargs) -> Dict[str, Any]:
        """调用工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            Dict[str, Any]: 工具执行结果
        """
        try:
            # 如果是本地函数
            if self.function:
                if self.is_async:
                    # 异步函数直接调用
                    return await self.function(**kwargs)
                else:
                    # 同步函数使用线程池执行
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, lambda: self.function(**kwargs))
                    
            # 如果是远程API
            elif self.api_endpoint:
                return await self._call_api(**kwargs)
            else:
                raise ValueError("工具未正确配置，缺少函数或API端点")
                
        except Exception as e:
            logger.error(f"工具 '{self.name}' 执行失败: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _call_api(self, **kwargs) -> Dict[str, Any]:
        """调用远程API
        
        Args:
            **kwargs: API参数
            
        Returns:
            Dict[str, Any]: API响应
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_endpoint, json=kwargs) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        return {
                            "status": "error",
                            "error": f"API调用失败，状态码: {response.status}，错误: {error_text}"
                        }
                    return await response.json()
        except Exception as e:
            return {
                "status": "error",
                "error": f"API调用异常: {str(e)}"
            }
            
    def to_dict(self) -> Dict[str, Any]:
        """将工具转换为字典表示
        
        Returns:
            Dict[str, Any]: 工具字典表示
        """
        result = {
            "name": self.name,
            "description": self.description,
            "is_async": self.is_async
        }
        
        if self.function_def:
            result["function_def"] = self.function_def
            
        if self.api_endpoint:
            result["api_endpoint"] = self.api_endpoint
            
        return result
            
    def set_function_def(self, function_def: Dict[str, Any]) -> None:
        """设置函数定义
        
        Args:
            function_def: 函数定义
        """
        self.function_def = function_def


async def create_custom_tool(name: str, description: str, function_def: Dict[str, Any],
                            api_endpoint: Optional[str] = None, is_async: bool = False) -> CustomTool:
    """创建自定义工具
    
    Args:
        name: 工具名称
        description: 工具描述
        function_def: 函数定义
        api_endpoint: API端点
        is_async: 是否为异步工具
        
    Returns:
        CustomTool: 创建的工具
    """
    # 创建工具
    tool = CustomTool(
        name=name,
        description=description,
        api_endpoint=api_endpoint,
        is_async=is_async
    )
    
    # 设置函数定义
    tool.set_function_def(function_def)
    
    # 如果是本地函数，生成实际的函数对象
    if not api_endpoint:
        # 这里仅用于示例，实际实现可能需要根据function_def动态生成函数
        # 这是一个简化实现，仅支持基本的函数生成
        async def generated_function(**kwargs):
            # 在实际实现中，这里应该根据function_def解析参数并执行逻辑
            logger.info(f"执行自定义工具 '{name}', 参数: {kwargs}")
            return {
                "status": "success",
                "message": f"工具 '{name}' 执行成功",
                "params": kwargs
            }
            
        tool.function = generated_function
    
    return tool
