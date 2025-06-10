"""
Agno搜索工具：基于Agno框架的Web搜索工具
替代LlamaIndex版本，提供更清洁的Agno原生实现
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field

from core.searxng_manager import get_searxng_manager

logger = logging.getLogger(__name__)

class AgnoSearchQuery(BaseModel):
    """Agno搜索查询参数模型"""
    query: str = Field(..., description="搜索查询")
    engines: Optional[List[str]] = Field(None, description="要使用的搜索引擎列表，如不指定则使用默认引擎")
    language: str = Field("zh-CN", description="搜索语言")
    max_results: int = Field(5, description="最大返回结果数")

class AgnoSearchResult(BaseModel):
    """Agno搜索结果模型"""
    title: str = Field(..., description="结果标题")
    url: str = Field(..., description="结果URL")
    content: str = Field(..., description="结果内容摘要")
    source: str = Field(..., description="结果来源/搜索引擎")
    score: float = Field(0.0, description="结果评分")
    published_date: Optional[str] = Field(None, description="发布日期")

class AgnoWebSearchTool:
    """Agno Web搜索工具，基于SearxNG，使用Agno原生实现"""
    
    def __init__(self, name: str = "web_search"):
        """
        初始化Agno Web搜索工具
        
        参数:
            name: 工具名称
        """
        self.name = name
        self.searxng_manager = get_searxng_manager()
        self.description = (
            "使用SearxNG搜索互联网以获取有关查询的实时信息。"
            "对于需要最新信息、事实验证或未在知识库中包含的数据特别有用。"
        )
    
    def search_web(
        self, 
        query: str, 
        engines: Optional[List[str]] = None, 
        language: str = "zh-CN", 
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        搜索Web获取实时信息 - Agno工具方法
        
        参数:
            query: 搜索查询
            engines: 搜索引擎列表，可选值：google, bing, baidu, wikipedia等，默认为None（使用所有可用引擎）
            language: 搜索语言，默认为zh-CN
            max_results: 最大结果数，默认为5
            
        返回:
            包含搜索结果的字典
        """
        try:
            results = asyncio.run(self._async_search(query, engines, language, max_results))
            
            if not results:
                return {
                    "success": False,
                    "message": f"未找到关于 '{query}' 的搜索结果。",
                    "results": [],
                    "count": 0,
                    "query": query
                }
            
            # 格式化结果
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "title": result['title'],
                    "url": result['url'],
                    "content": result['content'],
                    "source": result['source'],
                    "published_date": result.get('published_date'),
                    "score": result.get('score', 0.0)
                })
            
            # 构建文本摘要
            text_summary = "搜索结果：\n\n"
            for i, result in enumerate(formatted_results, 1):
                text_summary += f"{i}. {result['title']}\n"
                text_summary += f"   URL: {result['url']}\n"
                text_summary += f"   摘要: {result['content']}\n"
                if result.get('published_date'):
                    text_summary += f"   发布日期: {result['published_date']}\n"
                text_summary += f"   来源: {result['source']}\n\n"
            
            return {
                "success": True,
                "message": f"成功找到 {len(formatted_results)} 个搜索结果",
                "results": formatted_results,
                "count": len(formatted_results),
                "query": query,
                "text_summary": text_summary
            }
            
        except Exception as e:
            logger.error(f"执行Web搜索时出错: {str(e)}")
            return {
                "success": False,
                "message": f"执行搜索时出错: {str(e)}",
                "results": [],
                "count": 0,
                "query": query,
                "error": str(e)
            }
    
    async def _async_search(
        self, 
        query: str, 
        engines: Optional[List[str]] = None,
        language: str = "zh-CN", 
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        异步执行搜索
        
        参数:
            query: 搜索查询
            engines: 搜索引擎列表
            language: 搜索语言
            max_results: 最大结果数
            
        返回:
            搜索结果列表
        """
        return await self.searxng_manager.search(
            query=query,
            engines=engines,
            language=language,
            max_results=max_results
        )
    
    def get_search_engines(self) -> List[str]:
        """
        获取可用的搜索引擎列表
        
        返回:
            可用搜索引擎列表
        """
        return [
            "google", "bing", "baidu", "duckduckgo", 
            "wikipedia", "yandex", "yahoo", "startpage"
        ]
    
    def validate_query(self, query: str) -> bool:
        """
        验证搜索查询
        
        参数:
            query: 搜索查询
            
        返回:
            是否有效
        """
        if not query or not query.strip():
            return False
        
        # 检查查询长度
        if len(query) > 500:
            return False
            
        return True

# 创建工具实例的工厂函数
def create_agno_web_search_tool(name: str = "web_search") -> AgnoWebSearchTool:
    """
    创建Agno Web搜索工具实例
    
    参数:
        name: 工具名称
        
    返回:
        配置好的Agno搜索工具
    """
    return AgnoWebSearchTool(name=name)

# 获取工具实例的便捷函数
def get_agno_search_tool() -> AgnoWebSearchTool:
    """
    获取Agno搜索工具实例
    
    返回:
        配置好的Agno搜索工具
    """
    return AgnoWebSearchTool()

# 兼容性：提供类似LlamaIndex的接口
class AgnoSearchToolWrapper:
    """Agno搜索工具包装器，提供与LlamaIndex兼容的接口"""
    
    def __init__(self):
        self.tool = AgnoWebSearchTool()
    
    def search(self, query: str, **kwargs) -> str:
        """
        搜索接口，返回文本格式结果
        
        参数:
            query: 搜索查询
            **kwargs: 其他参数
            
        返回:
            搜索结果的文本表示
        """
        result = self.tool.search_web(
            query=query,
            engines=kwargs.get('engines'),
            language=kwargs.get('language', 'zh-CN'),
            max_results=kwargs.get('max_results', 5)
        )
        
        if result['success']:
            return result['text_summary']
        else:
            return result['message']

# 导出主要组件
__all__ = [
    "AgnoWebSearchTool",
    "AgnoSearchQuery", 
    "AgnoSearchResult",
    "create_agno_web_search_tool",
    "get_agno_search_tool",
    "AgnoSearchToolWrapper"
] 