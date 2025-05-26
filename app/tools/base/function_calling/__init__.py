"""
函数调用工具模块
提供Function Calling的工具实现，支持不同模型的函数调用适配
"""

from app.tools.base.function_calling.adapter import (
    FunctionCallingAdapter,
    FunctionCallingConfig,
    FunctionCallingStrategy,
    create_function_calling_adapter
)

__all__ = [
    "FunctionCallingAdapter",
    "FunctionCallingConfig", 
    "FunctionCallingStrategy",
    "create_function_calling_adapter"
]
