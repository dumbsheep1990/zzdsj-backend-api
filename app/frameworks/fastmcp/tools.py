"""
FastMCP工具管理模块
负责注册和管理MCP工具
"""

import logging
import inspect
from typing import Dict, Any, Optional, List, Callable, Type, Union
from pydantic import BaseModel
from fastmcp import FastMCP
from .server import get_mcp_server

logger = logging.getLogger(__name__)

# 工具元数据存储
_tool_registry = {}


def register_tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: str = "general",
    schema: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None
) -> Callable:
    """
    注册MCP工具的装饰器
    
    参数:
        name: 工具名称，如果不提供则使用函数名
        description: 工具描述，如果不提供则使用函数文档字符串
        category: 工具类别，用于分组展示
        schema: 工具参数和返回值的JSON Schema，如果不提供则自动生成
        tags: 工具标签，用于筛选
        
    返回:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        nonlocal name, description
        
        # 使用函数名作为默认名称
        if name is None:
            name = func.__name__
        
        # 使用函数文档作为默认描述
        if description is None and func.__doc__:
            description = func.__doc__.strip()
        elif description is None:
            description = f"{name} - MCP工具"
        
        # 获取MCP服务器实例
        mcp = get_mcp_server()
        
        # 注册为MCP工具
        decorated_func = mcp.tool()(func)
        
        # 存储工具元数据
        _tool_registry[name] = {
            "name": name,
            "description": description,
            "category": category,
            "tags": tags or [],
            "function": func,
            "decorated_function": decorated_func,
            "schema": schema
        }
        
        logger.info(f"注册MCP工具: {name}")
        return decorated_func
    
    return decorator


def list_tools(category: Optional[str] = None, tag: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    列出已注册的MCP工具
    
    参数:
        category: 可选，按类别筛选
        tag: 可选，按标签筛选
        
    返回:
        工具列表
    """
    tools = []
    
    for tool_name, tool_data in _tool_registry.items():
        # 按类别筛选
        if category and tool_data["category"] != category:
            continue
        
        # 按标签筛选
        if tag and tag not in tool_data["tags"]:
            continue
        
        # 添加到结果列表
        tools.append({
            "name": tool_data["name"],
            "description": tool_data["description"],
            "category": tool_data["category"],
            "tags": tool_data["tags"]
        })
    
    return tools


def get_tool(name: str) -> Optional[Dict[str, Any]]:
    """
    获取指定名称的工具详情
    
    参数:
        name: 工具名称
        
    返回:
        工具详情，如果不存在则返回None
    """
    return _tool_registry.get(name)


def get_tool_schema(name: str) -> Optional[Dict[str, Any]]:
    """
    获取工具的JSON Schema
    
    参数:
        name: 工具名称
        
    返回:
        工具的JSON Schema，如果不存在则返回None
    """
    tool_data = _tool_registry.get(name)
    if not tool_data:
        return None
    
    if tool_data.get("schema"):
        return tool_data["schema"]
    
    # 尝试自动生成Schema
    try:
        func = tool_data["function"]
        sig = inspect.signature(func)
        schema = {
            "name": tool_data["name"],
            "description": tool_data["description"],
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
        
        # 解析函数参数
        for param_name, param in sig.parameters.items():
            # 跳过self参数
            if param_name == "self":
                continue
                
            param_schema = _parse_parameter_type(param)
            
            # 如果参数没有默认值，标记为必需
            if param.default == inspect.Parameter.empty:
                schema["parameters"]["required"].append(param_name)
            
            schema["parameters"]["properties"][param_name] = param_schema
        
        return schema
    
    except Exception as e:
        logger.error(f"生成工具\"{name}\"的Schema时出错: {str(e)}")
        return None

def _parse_parameter_type(param: inspect.Parameter) -> Dict[str, Any]:
    """
    解析参数类型，生成对应的JSON Schema
    
    参数:
        param: 函数参数
        
    返回:
        参数的JSON Schema
    """
    param_schema = {"type": "string"}  # 默认类型
    
    # 如果有类型注解，尝试解析类型
    if param.annotation != inspect.Parameter.empty:
        annotation = param.annotation
        
        # 处理泛型类型
        if hasattr(annotation, "__origin__"):
            origin = annotation.__origin__
            args = getattr(annotation, "__args__", ())
            
            if origin is list or origin is List:
                param_schema = {"type": "array"}
                if args:
                    item_type = args[0]
                    param_schema["items"] = _get_type_schema(item_type)
            elif origin is dict or origin is Dict:
                param_schema = {"type": "object"}
                if len(args) >= 2:
                    # 如果值类型已知，添加值类型信息
                    value_type = args[1]
                    param_schema["additionalProperties"] = _get_type_schema(value_type)
            elif origin is Union:
                # 处理Union类型（如Optional）
                non_none_types = [arg for arg in args if arg is not type(None)]
                if len(non_none_types) == 1:
                    # Optional[T] 等价于 Union[T, None]
                    param_schema = _get_type_schema(non_none_types[0])
                else:
                    # 多种类型的Union，使用anyOf
                    param_schema = {
                        "anyOf": [_get_type_schema(arg) for arg in non_none_types]
                    }
        else:
            param_schema = _get_type_schema(annotation)
    
    # 如果有默认值，添加到schema中
    if param.default != inspect.Parameter.empty:
        if param.default is not None:
            param_schema["default"] = param.default
    
    return param_schema

def _get_type_schema(type_annotation: Any) -> Dict[str, Any]:
    """
    根据类型注解生成JSON Schema
    
    参数:
        type_annotation: 类型注解
        
    返回:
        对应的JSON Schema
    """
    if type_annotation == str:
        return {"type": "string"}
    elif type_annotation == int:
        return {"type": "integer"}
    elif type_annotation == float:
        return {"type": "number"}
    elif type_annotation == bool:
        return {"type": "boolean"}
    elif type_annotation == list:
        return {"type": "array"}
    elif type_annotation == dict:
        return {"type": "object"}
    elif type_annotation is type(None):
        return {"type": "null"}
    elif hasattr(type_annotation, "__bases__") and BaseModel in type_annotation.__bases__:
        # 处理Pydantic模型
        try:
            # 如果是Pydantic模型，尝试获取其schema
            if hasattr(type_annotation, "model_json_schema"):
                return type_annotation.model_json_schema()
            else:
                return {"type": "object"}
        except Exception:
            return {"type": "object"}
    else:
        # 未知类型，默认为字符串
        return {"type": "string"}
