# Agno AgenticSearch 封装管理器
from typing import Dict, Any, List, Optional
from agno.tools import AgenticSearch

class AgnoSearchManager:
    """Agno搜索工具管理器 - 直接使用Agno框架的AgenticSearch"""
    
    def __init__(self, search_engine: str = "google", max_results: int = 10, **kwargs):
        """
        初始化Agno搜索工具管理器
        
        Args:
            search_engine: 搜索引擎
            max_results: 最大结果数
            **kwargs: 其他Agno AgenticSearch参数
        """
        # 直接使用Agno框架的AgenticSearch
        self.search_tools = AgenticSearch(
            search_engine=search_engine,
            max_results=max_results,
            **kwargs
        )
        self.name = "agno_search"
        self.description = "基于Agno框架的智能搜索工具"
    
    async def search(self, query: str, engine: Optional[str] = None, max_results: Optional[int] = None) -> Dict[str, Any]:
        """
        执行搜索
        
        Args:
            query: 搜索查询
            engine: 指定搜索引擎
            max_results: 最大结果数
            
        Returns:
            搜索结果
        """
        try:
            # 使用Agno AgenticSearch进行搜索
            search_params = {'query': query}
            if engine:
                search_params['engine'] = engine
            if max_results:
                search_params['max_results'] = max_results
                
            result = await self.search_tools.search(**search_params)
            
            return {
                'tool': 'agno_search',
                'action': 'search',
                'query': query,
                'engine': engine or 'default',
                'result': result,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_search',
                'action': 'search',
                'query': query,
                'error': str(e),
                'status': 'error'
            }
    
    async def agentic_search(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行智能搜索（带上下文理解）
        
        Args:
            query: 搜索查询
            context: 搜索上下文
            
        Returns:
            智能搜索结果
        """
        try:
            # 使用Agno AgenticSearch的智能搜索功能
            result = await self.search_tools.agentic_search(query, context=context)
            
            return {
                'tool': 'agno_search',
                'action': 'agentic_search',
                'query': query,
                'context': context,
                'result': result,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_search',
                'action': 'agentic_search',
                'query': query,
                'error': str(e),
                'status': 'error'
            }
    
    async def filter_results(self, results: List[Dict], criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        过滤搜索结果
        
        Args:
            results: 搜索结果列表
            criteria: 过滤条件
            
        Returns:
            过滤后的结果
        """
        try:
            # 使用Agno AgenticSearch的结果过滤功能
            filtered_results = await self.search_tools.filter(results, criteria=criteria)
            
            return {
                'tool': 'agno_search',
                'action': 'filter',
                'original_count': len(results),
                'filtered_count': len(filtered_results),
                'criteria': criteria,
                'result': filtered_results,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_search',
                'action': 'filter',
                'error': str(e),
                'status': 'error'
            }
    
    async def rank_results(self, results: List[Dict], ranking_criteria: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        对搜索结果进行排序
        
        Args:
            results: 搜索结果列表
            ranking_criteria: 排序条件
            
        Returns:
            排序后的结果
        """
        try:
            # 使用Agno AgenticSearch的结果排序功能
            ranked_results = await self.search_tools.rank(results, criteria=ranking_criteria)
            
            return {
                'tool': 'agno_search',
                'action': 'rank',
                'result_count': len(ranked_results),
                'ranking_criteria': ranking_criteria,
                'result': ranked_results,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_search',
                'action': 'rank',
                'error': str(e),
                'status': 'error'
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取搜索工具能力"""
        return {
            'tool_name': self.name,
            'description': self.description,
            'capabilities': [
                'web_search',
                'agentic_search',
                'result_filtering',
                'result_ranking',
                'context_aware_search'
            ],
            'framework': 'agno'
        } 