"""
OWL框架数据格式处理装饰器
提供用于统一和转换Agent数据格式的装饰器函数
"""

import functools
import inspect
import json
from typing import Any, Callable, Dict, List, Optional, Union
import logging
from datetime import datetime

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AgentInput(BaseModel):
    """统一的Agent输入格式"""
    query: str
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    history: Optional[List[Dict[str, Any]]] = None
    source_agent_id: Optional[int] = None
    trace_id: Optional[str] = None


class AgentOutput(BaseModel):
    """统一的Agent输出格式"""
    content: str
    metadata: Dict[str, Any] = {}
    tool_calls: List[Dict[str, Any]] = []
    source_documents: List[Dict[str, Any]] = []
    timestamp: str = datetime.now().isoformat()
    error: Optional[str] = None
    raw_output: Optional[Any] = None


def format_agent_input(func):
    """将输入转换为统一的AgentInput格式
    
    如果输入已经是AgentInput类型，则直接使用
    否则尝试将输入转换为AgentInput格式
    
    Args:
        func: 要装饰的函数
        
    Returns:
        装饰后的函数，接收统一格式的输入
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # 检查函数签名获取参数名
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())
        
        # 找到输入参数位置
        input_arg = None
        input_index = None
        
        # 首先检查kwargs
        for param_name in ['input', 'agent_input', 'query']:
            if param_name in kwargs:
                input_arg = kwargs[param_name]
                input_param_name = param_name
                break
                
        # 如果没有在kwargs中找到，则检查args
        if input_arg is None and len(args) > 1:  # 第一个通常是self
            # 尝试在args中找到输入参数
            for i, param_name in enumerate(param_names):
                if param_name in ['input', 'agent_input', 'query'] and i < len(args):
                    input_arg = args[i]
                    input_index = i
                    break
        
        # 如果没有找到输入参数，则不做处理直接调用原函数
        if input_arg is None:
            return await func(*args, **kwargs)
            
        # 将输入转换为统一的AgentInput格式
        agent_input = None
        if isinstance(input_arg, AgentInput):
            # 已经是AgentInput格式，直接使用
            agent_input = input_arg
        elif isinstance(input_arg, dict):
            # 字典格式，转换为AgentInput
            try:
                agent_input = AgentInput(**input_arg)
            except Exception as e:
                logger.warning(f"将输入字典转换为AgentInput时出错: {str(e)}")
                # 尝试处理简单字典情况
                if 'query' in input_arg:
                    agent_input = AgentInput(query=input_arg['query'])
                elif 'text' in input_arg:
                    agent_input = AgentInput(query=input_arg['text'])
                elif 'content' in input_arg:
                    agent_input = AgentInput(query=input_arg['content'])
                else:
                    # 无法识别的字典格式，使用整个字典作为查询
                    agent_input = AgentInput(query=str(input_arg))
        elif isinstance(input_arg, str):
            # 字符串格式，作为查询
            agent_input = AgentInput(query=input_arg)
        else:
            # 其他格式，尝试转换为字符串
            try:
                agent_input = AgentInput(query=str(input_arg))
            except Exception as e:
                logger.error(f"无法将输入转换为AgentInput: {str(e)}")
                # 失败时返回错误信息
                return AgentOutput(
                    content="",
                    error=f"输入格式错误: {str(e)}",
                    metadata={"error_type": "input_format_error"}
                )
        
        # 替换参数并调用原函数
        if input_index is not None:
            # 替换args中的参数
            args_list = list(args)
            args_list[input_index] = agent_input
            return await func(*args_list, **kwargs)
        else:
            # 替换kwargs中的参数
            kwargs[input_param_name] = agent_input
            return await func(*args, **kwargs)
    
    return wrapper


def format_agent_output(func):
    """将输出转换为统一的AgentOutput格式
    
    如果输出已经是AgentOutput类型，则直接返回
    否则尝试将输出转换为AgentOutput格式
    
    Args:
        func: 要装饰的函数
        
    Returns:
        装饰后的函数，返回统一格式的输出
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # 调用原函数
        result = await func(*args, **kwargs)
        
        # 如果结果已经是AgentOutput格式，则直接返回
        if isinstance(result, AgentOutput):
            return result
            
        # 尝试转换结果为AgentOutput格式
        try:
            if isinstance(result, str):
                # 字符串结果，作为内容
                return AgentOutput(content=result)
            elif isinstance(result, dict):
                # 字典结果，尝试转换
                if 'content' in result:
                    # 包含content字段，可以直接转换
                    return AgentOutput(**result)
                elif 'answer' in result:
                    # 包含answer字段，作为内容
                    content = result.pop('answer')
                    return AgentOutput(content=content, metadata=result)
                elif 'text' in result:
                    # 包含text字段，作为内容
                    content = result.pop('text')
                    return AgentOutput(content=content, metadata=result)
                elif 'result' in result:
                    # 包含result字段，作为内容
                    content = result.pop('result')
                    return AgentOutput(content=content, metadata=result)
                else:
                    # 无法识别的字典格式，使用整个字典作为元数据
                    return AgentOutput(
                        content=str(result),
                        metadata={"raw_dict": result},
                        raw_output=result
                    )
            elif isinstance(result, tuple) and len(result) >= 2:
                # 元组结果，第一个元素作为内容，其余作为元数据
                content = result[0]
                if isinstance(content, str):
                    metadata = {}
                    if len(result) > 1 and isinstance(result[1], dict):
                        metadata = result[1]
                    return AgentOutput(content=content, metadata=metadata, raw_output=result)
                else:
                    # 第一个元素不是字符串，使用整个元组作为原始输出
                    return AgentOutput(
                        content=str(result),
                        metadata={"result_type": "tuple"},
                        raw_output=result
                    )
            else:
                # 其他格式，转换为字符串作为内容
                return AgentOutput(
                    content=str(result),
                    metadata={"result_type": type(result).__name__},
                    raw_output=result
                )
        except Exception as e:
            logger.error(f"将结果转换为AgentOutput时出错: {str(e)}")
            # 失败时返回错误信息
            return AgentOutput(
                content=str(result) if result is not None else "",
                error=f"输出格式转换错误: {str(e)}",
                metadata={"error_type": "output_format_error"},
                raw_output=result
            )
    
    return wrapper


def agent_data_formatter(func):
    """Agent数据格式化装饰器
    
    将输入转换为统一的AgentInput格式，将输出转换为统一的AgentOutput格式
    
    Args:
        func: 要装饰的函数
        
    Returns:
        装饰后的函数，接收和返回统一格式的数据
    """
    # 组合输入和输出装饰器
    @format_agent_input
    @format_agent_output
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
        
    return wrapper


def tool_result_formatter(func):
    """工具结果格式化装饰器
    
    确保工具返回结果符合预期格式，处理异常情况
    
    Args:
        func: 要装饰的函数
        
    Returns:
        装饰后的函数，返回标准化的工具结果
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # 调用原始工具函数
            result = await func(*args, **kwargs) if inspect.iscoroutinefunction(func) else func(*args, **kwargs)
            
            # 标准化结果格式
            if result is None:
                return {"status": "success", "result": None}
            elif isinstance(result, dict) and ("result" in result or "error" in result):
                # 已经是标准格式，确保包含status字段
                if "status" not in result:
                    if "error" in result:
                        result["status"] = "error"
                    else:
                        result["status"] = "success"
                return result
            else:
                # 将结果包装为标准格式
                return {"status": "success", "result": result}
        except Exception as e:
            # 捕获异常并返回错误信息
            error_message = str(e)
            logger.error(f"工具执行错误: {error_message}")
            return {
                "status": "error",
                "error": error_message,
                "error_type": type(e).__name__
            }
    
    return wrapper


def agent_chain_input_formatter(func):
    """Agent链输入格式化装饰器
    
    确保在链式调用中的输入输出格式一致，保持上下文传递
    
    Args:
        func: 要装饰的函数
        
    Returns:
        装饰后的函数，处理Agent链的输入输出
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # 提取上下文和链信息
        chain_context = kwargs.get('context', {})
        chain_index = kwargs.get('chain_index', 0)
        chain_trace_id = kwargs.get('trace_id', None)
        
        # 增强上下文信息
        chain_context.update({
            "chain_position": chain_index,
            "chain_trace_id": chain_trace_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # 更新kwargs
        kwargs['context'] = chain_context
        
        # 调用原函数
        result = await func(*args, **kwargs)
        
        # 返回结果，确保格式符合链处理要求
        return result
    
    return wrapper
