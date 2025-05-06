"""
搜索工具中间件：整合SearxNG搜索引擎服务
提供Web搜索工具，作为独立中间件服务供所有组件使用
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable
from pydantic import BaseModel, Field

from llama_index.core.tools import BaseTool, FunctionTool
from llama_index.core.response_synthesizers import ResponseMode
from app.core.searxng_manager import get_searxng_manager

logger = logging.getLogger(__name__)

class SearchQuery(BaseModel):
    """搜索查询参数模型"""
    query: str = Field(..., description="搜索查询")
    engines: Optional[List[str]] = Field(None, description="要使用的搜索引擎列表，如不指定则使用默认引擎")
    language: str = Field("zh-CN", description="搜索语言")
    max_results: int = Field(5, description="最大返回结果数")

class SearchResult(BaseModel):
    """搜索结果模型"""
    title: str = Field(..., description="结果标题")
    url: str = Field(..., description="结果URL")
    content: str = Field(..., description="结果内容摘要")
    source: str = Field(..., description="结果来源/搜索引擎")
    score: float = Field(0.0, description="结果评分")
    published_date: Optional[str] = Field(None, description="发布日期")

class WebSearchTool(BaseTool):
    """Web搜索工具，基于SearxNG"""
    
    def __init__(self, name: str = "web_search"):
        """
        初始化Web搜索工具
        
        参数:
            name: 工具名称
        """
        super().__init__(name=name)
        self.searxng_manager = get_searxng_manager()
        self.description = (
            "使用SearxNG搜索互联网以获取有关查询的实时信息。"
            "对于需要最新信息、事实验证或未在知识库中包含的数据特别有用。"
        )
    
    async def _arun(self, query: str, engines: Optional[List[str]] = None, 
                 language: str = "zh-CN", max_results: int = 5) -> str:
        """
        异步执行搜索
        
        参数:
            query: 搜索查询
            engines: 搜索引擎列表，默认为None（使用所有可用引擎）
            language: 搜索语言，默认为zh-CN
            max_results: 最大结果数，默认为5
            
        返回:
            搜索结果的字符串表示
        """
        try:
            results = await self.searxng_manager.search(
                query=query,
                engines=engines,
                language=language,
                max_results=max_results
            )
            
            if not results:
                return f"未找到关于 '{query}' 的搜索结果。"
            
            # 格式化结果为结构化文本
            formatted_results = "搜索结果：\n\n"
            for i, result in enumerate(results, 1):
                formatted_results += f"{i}. {result['title']}\n"
                formatted_results += f"   URL: {result['url']}\n"
                formatted_results += f"   摘要: {result['content']}\n"
                if result.get('published_date'):
                    formatted_results += f"   发布日期: {result['published_date']}\n"
                formatted_results += f"   来源: {result['source']}\n\n"
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"执行Web搜索时出错: {str(e)}")
            return f"执行搜索时出错: {str(e)}"
    
    def _run(self, query: str, engines: Optional[List[str]] = None, 
           language: str = "zh-CN", max_results: int = 5) -> str:
        """
        同步执行搜索（包装异步方法）
        
        参数:
            query: 搜索查询
            engines: 搜索引擎列表，默认为None（使用所有可用引擎）
            language: 搜索语言，默认为zh-CN
            max_results: 最大结果数，默认为5
            
        返回:
            搜索结果的字符串表示
        """
        return asyncio.run(self._arun(query, engines, language, max_results))

def get_search_tool() -> BaseTool:
    """
    获取搜索工具实例
    
    返回:
        配置好的搜索工具
    """
    return WebSearchTool()

def create_search_function_tool() -> FunctionTool:
    """
    创建基于函数的搜索工具
    
    返回:
        配置好的函数工具
    """
    async def search_web(query: str, engines: Optional[List[str]] = None, 
                        language: str = "zh-CN", max_results: int = 5) -> str:
        """
        搜索Web获取实时信息
        
        参数:
            query: 搜索查询
            engines: 搜索引擎列表，可选值：google, bing, baidu, wikipedia等，默认为None（使用所有可用引擎）
            language: 搜索语言，默认为zh-CN
            max_results: 最大结果数，默认为5
            
        返回:
            搜索结果的字符串表示
        """
        searxng_manager = get_searxng_manager()
        results = await searxng_manager.search(
            query=query,
            engines=engines,
            language=language,
            max_results=max_results
        )
        
        if not results:
            return f"未找到关于 '{query}' 的搜索结果。"
        
        # 格式化结果为结构化文本
        formatted_results = "搜索结果：\n\n"
        for i, result in enumerate(results, 1):
            formatted_results += f"{i}. {result['title']}\n"
            formatted_results += f"   URL: {result['url']}\n"
            formatted_results += f"   摘要: {result['content']}\n"
            if result.get('published_date'):
                formatted_results += f"   发布日期: {result['published_date']}\n"
            formatted_results += f"   来源: {result['source']}\n\n"
        
        return formatted_results
    
    # 将异步函数包装为同步函数
    def sync_search_web(query: str, engines: Optional[List[str]] = None, 
                       language: str = "zh-CN", max_results: int = 5) -> str:
        return asyncio.run(search_web(query, engines, language, max_results))
    
    return FunctionTool.from_defaults(
        fn=sync_search_web,
        name="web_search",
        description=(
            "使用SearxNG搜索互联网以获取有关查询的实时信息。"
            "对于需要最新信息、事实验证或未在知识库中包含的数据特别有用。"
        )
    )
