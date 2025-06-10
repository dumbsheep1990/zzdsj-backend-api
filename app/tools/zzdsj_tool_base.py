"""
ZZDSJ工具基类
为所有ZZDSJ自研工具提供统一的基础实现
注意：这是ZZDSJ自研的工具基类，不是Agno框架的工具
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union, Type
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError
import inspect

from app.tools.zzdsj_tool_registry import ToolMetadata, ToolCategory

logger = logging.getLogger(__name__)


class ZZDSJToolParameter(BaseModel):
    """ZZDSJ工具参数定义"""
    name: str = Field(..., description="参数名称")
    type: str = Field(..., description="参数类型")
    description: str = Field(..., description="参数描述")
    required: bool = Field(True, description="是否必须")
    default: Any = Field(None, description="默认值")
    
    
class ZZDSJToolSchema(BaseModel):
    """ZZDSJ工具模式定义"""
    parameters: List[ZZDSJToolParameter] = Field(..., description="参数列表")
    returns: Dict[str, str] = Field(..., description="返回值描述")
    examples: List[Dict[str, Any]] = Field(default_factory=list, description="使用示例")


class ZZDSJToolBase(ABC):
    """
    ZZDSJ工具基类（自研）
    
    所有ZZDSJ自研工具都应该继承此基类，并实现相应的抽象方法。
    基类提供了统一的执行框架、错误处理、日志记录等功能。
    
    注意：这不是Agno框架的工具基类，而是ZZDSJ项目自研的工具基类
    """
    
    def __init__(self, name: str, description: str, category: ToolCategory):
        """
        初始化ZZDSJ工具基类
        
        Args:
            name: 工具名称
            description: 工具描述
            category: 工具分类
        """
        self.name = name
        self.description = description
        self.category = category
        self.metadata = self._get_metadata()
        self._initialized = False
        self._execution_count = 0
        self._total_execution_time = 0.0
        
        # 初始化工具
        self._initialize()
    
    def _initialize(self):
        """初始化工具"""
        try:
            self._init_dependencies()
            self._initialized = True
            logger.info(f"Tool {self.name} initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize tool {self.name}: {str(e)}")
            self._initialized = False
    
    @abstractmethod
    def _init_dependencies(self):
        """初始化工具依赖（子类实现）"""
        pass
    
    @abstractmethod
    def _get_metadata(self) -> ToolMetadata:
        """获取工具元数据（子类实现）"""
        pass
    
    @abstractmethod
    def _get_schema(self) -> AgnoToolSchema:
        """获取工具模式定义（子类实现）"""
        pass
    
    @abstractmethod
    async def _execute_async(self, **kwargs) -> Dict[str, Any]:
        """异步执行工具核心逻辑（子类实现）"""
        pass
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        同步执行工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            执行结果
        """
        # 创建新的事件循环来运行异步方法
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已有运行中的循环，创建任务
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._execute_with_wrapper(**kwargs))
                    return future.result()
            else:
                # 没有运行中的循环，直接运行
                return loop.run_until_complete(self._execute_with_wrapper(**kwargs))
        except RuntimeError:
            # 没有事件循环，创建新的
            return asyncio.run(self._execute_with_wrapper(**kwargs))
    
    async def execute_async(self, **kwargs) -> Dict[str, Any]:
        """
        异步执行工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            执行结果
        """
        return await self._execute_with_wrapper(**kwargs)
    
    async def _execute_with_wrapper(self, **kwargs) -> Dict[str, Any]:
        """执行工具的包装方法，处理通用逻辑"""
        start_time = datetime.now()
        
        try:
            # 检查初始化状态
            if not self._initialized:
                raise RuntimeError(f"Tool {self.name} is not initialized")
            
            # 验证输入参数
            validated_params = self.validate_input(**kwargs)
            
            # 记录执行开始
            logger.debug(f"Executing tool {self.name} with params: {validated_params}")
            
            # 执行核心逻辑
            result = await self._execute_async(**validated_params)
            
            # 格式化输出
            formatted_result = self.format_output(result)
            
            # 记录执行成功
            execution_time = (datetime.now() - start_time).total_seconds()
            self._record_execution(execution_time, True)
            
            return formatted_result
            
        except ValidationError as e:
            # 参数验证错误
            error_msg = f"Parameter validation failed: {str(e)}"
            logger.error(f"Tool {self.name} - {error_msg}")
            return self._error_response(error_msg, "VALIDATION_ERROR")
            
        except Exception as e:
            # 其他错误
            error_msg = f"Execution failed: {str(e)}"
            logger.error(f"Tool {self.name} - {error_msg}", exc_info=True)
            execution_time = (datetime.now() - start_time).total_seconds()
            self._record_execution(execution_time, False)
            return self._error_response(error_msg, "EXECUTION_ERROR")
    
    def validate_input(self, **kwargs) -> Dict[str, Any]:
        """
        验证输入参数
        
        Args:
            **kwargs: 原始参数
            
        Returns:
            验证后的参数
        """
        schema = self._get_schema()
        validated_params = {}
        
        # 检查必需参数
        for param in schema.parameters:
            if param.required and param.name not in kwargs:
                if param.default is not None:
                    validated_params[param.name] = param.default
                else:
                    raise ValidationError(f"Required parameter '{param.name}' is missing")
            elif param.name in kwargs:
                # 这里可以添加类型检查逻辑
                validated_params[param.name] = kwargs[param.name]
        
        return validated_params
    
    def format_output(self, result: Any) -> Dict[str, Any]:
        """
        格式化输出结果
        
        Args:
            result: 原始结果
            
        Returns:
            格式化后的结果
        """
        return {
            "success": True,
            "tool_name": self.name,
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "execution_count": self._execution_count,
            "metadata": {
                "category": self.category.value,
                "version": self.metadata.version if self.metadata else "1.0.0"
            }
        }
    
    def _error_response(self, error_msg: str, error_type: str) -> Dict[str, Any]:
        """生成错误响应"""
        return {
            "success": False,
            "tool_name": self.name,
            "error": error_msg,
            "error_type": error_type,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "category": self.category.value,
                "version": self.metadata.version if self.metadata else "1.0.0"
            }
        }
    
    def _record_execution(self, execution_time: float, success: bool):
        """记录执行统计"""
        self._execution_count += 1
        self._total_execution_time += execution_time
        
        # 这里可以添加更多的统计记录，如成功率、平均执行时间等
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取工具执行统计"""
        avg_time = self._total_execution_time / self._execution_count if self._execution_count > 0 else 0
        
        return {
            "execution_count": self._execution_count,
            "total_execution_time": self._total_execution_time,
            "average_execution_time": avg_time,
            "initialized": self._initialized
        }
    
    def get_tool_info(self) -> Dict[str, Any]:
        """获取工具信息"""
        schema = self._get_schema()
        
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "metadata": self.metadata.__dict__ if self.metadata else {},
            "schema": {
                "parameters": [p.dict() for p in schema.parameters],
                "returns": schema.returns,
                "examples": schema.examples
            },
            "statistics": self.get_statistics()
        }
    
    @classmethod
    def create_from_function(cls, func: callable, name: str = None, 
                           description: str = None, category: ToolCategory = ToolCategory.CUSTOM) -> 'AgnoToolBase':
        """
        从函数创建工具
        
        Args:
            func: 要包装的函数
            name: 工具名称
            description: 工具描述
            category: 工具分类
            
        Returns:
            工具实例
        """
        # 动态创建工具类
        class FunctionTool(AgnoToolBase):
            def __init__(self):
                func_name = name or func.__name__
                func_desc = description or func.__doc__ or f"Function tool: {func.__name__}"
                super().__init__(func_name, func_desc, category)
                self.func = func
            
            def _init_dependencies(self):
                pass
            
            def _get_metadata(self) -> ToolMetadata:
                return ToolMetadata(
                    name=self.name,
                    description=self.description,
                    category=self.category,
                    version="1.0.0",
                    capabilities=["function_wrapper"],
                    tags=["function", "dynamic"]
                )
            
            def _get_schema(self) -> AgnoToolSchema:
                # 从函数签名推断参数
                sig = inspect.signature(self.func)
                parameters = []
                
                for param_name, param in sig.parameters.items():
                    param_type = "any"
                    if param.annotation != inspect.Parameter.empty:
                        param_type = str(param.annotation)
                    
                    parameters.append(AgnoToolParameter(
                        name=param_name,
                        type=param_type,
                        description=f"Parameter {param_name}",
                        required=param.default == inspect.Parameter.empty,
                        default=None if param.default == inspect.Parameter.empty else param.default
                    ))
                
                return AgnoToolSchema(
                    parameters=parameters,
                    returns={"type": "any", "description": "Function result"},
                    examples=[]
                )
            
            async def _execute_async(self, **kwargs) -> Any:
                if asyncio.iscoroutinefunction(self.func):
                    return await self.func(**kwargs)
                else:
                    return self.func(**kwargs)
        
        return FunctionTool()


# 工具装饰器
def agno_tool(name: str = None, description: str = None, 
              category: ToolCategory = ToolCategory.CUSTOM):
    """
    Agno工具装饰器
    
    使用示例:
    ```python
    @agno_tool(name="my_tool", description="My custom tool", category=ToolCategory.CUSTOM)
    def my_function(param1: str, param2: int) -> str:
        return f"Result: {param1}, {param2}"
    ```
    """
    def decorator(func):
        # 创建工具实例
        tool = AgnoToolBase.create_from_function(
            func, name=name, description=description, category=category
        )
        
        # 保留原函数的属性
        tool.original_function = func
        
        return tool
    
    return decorator 