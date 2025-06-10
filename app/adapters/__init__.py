"""
ZZDSJ框架适配器层
提供不同AI框架的统一适配接口
"""

from .base_adapter import BaseToolAdapter, AdapterError
from .agno_adapter import AgnoToolAdapter, AgnoFrameworkAdapter
from .llamaindex_adapter import LlamaIndexToolAdapter, LlamaIndexFrameworkAdapter
from .owl_adapter import OwlToolAdapter, OwlFrameworkAdapter
from .fastmcp_adapter import FastMCPToolAdapter, FastMCPFrameworkAdapter
from .haystack_adapter import HaystackToolAdapter, HaystackFrameworkAdapter

__all__ = [
    # 基础适配器
    "BaseToolAdapter",
    "AdapterError",
    
    # Agno适配器
    "AgnoToolAdapter",
    "AgnoFrameworkAdapter",
    
    # LlamaIndex适配器  
    "LlamaIndexToolAdapter",
    "LlamaIndexFrameworkAdapter",
    
    # OWL适配器
    "OwlToolAdapter", 
    "OwlFrameworkAdapter",
    
    # FastMCP适配器
    "FastMCPToolAdapter",
    "FastMCPFrameworkAdapter",
    
    # Haystack适配器
    "HaystackToolAdapter",
    "HaystackFrameworkAdapter",
]

__version__ = "1.0.0" 