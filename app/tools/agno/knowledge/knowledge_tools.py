# Agno KnowledgeTools 封装管理器
from typing import Dict, Any, Optional
from agno import KnowledgeTools

class AgnoKnowledgeManager:
    """Agno知识工具管理器 - 直接使用Agno框架的KnowledgeTools"""
    
    def __init__(self, knowledge_base=None, think: bool = True, search: bool = True, analyze: bool = True, **kwargs):
        """
        初始化Agno知识工具管理器
        
        Args:
            knowledge_base: 知识库实例
            think: 是否启用思考功能
            search: 是否启用搜索功能
            analyze: 是否启用分析功能
            **kwargs: 其他Agno KnowledgeTools参数
        """
        # 直接使用Agno框架的KnowledgeTools
        self.knowledge_tools = KnowledgeTools(
            knowledge_base=knowledge_base,
            think=think,
            search=search,
            analyze=analyze,
            **kwargs
        )
        self.name = "agno_knowledge"
        self.description = "基于Agno框架的知识库工具"
    
    async def search(self, query: str, kb_name: Optional[str] = None, max_results: int = 5) -> Dict[str, Any]:
        """
        搜索知识库
        
        Args:
            query: 搜索查询
            kb_name: 知识库名称
            max_results: 最大结果数
            
        Returns:
            搜索结果
        """
        try:
            # 使用Agno KnowledgeTools进行搜索
            result = await self.knowledge_tools.search(
                query, 
                knowledge_base=kb_name, 
                max_results=max_results
            )
            
            return {
                'tool': 'agno_knowledge',
                'action': 'search',
                'query': query,
                'knowledge_base': kb_name,
                'result': result,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_knowledge',
                'action': 'search',
                'query': query,
                'error': str(e),
                'status': 'error'
            }
    
    async def analyze(self, content: str, analysis_type: str = "general") -> Dict[str, Any]:
        """
        分析知识内容
        
        Args:
            content: 待分析内容
            analysis_type: 分析类型
            
        Returns:
            分析结果
        """
        try:
            # 使用Agno KnowledgeTools进行分析
            result = await self.knowledge_tools.analyze(content, type=analysis_type)
            
            return {
                'tool': 'agno_knowledge',
                'action': 'analyze',
                'content_length': len(content),
                'analysis_type': analysis_type,
                'result': result,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_knowledge',
                'action': 'analyze',
                'error': str(e),
                'status': 'error'
            }
    
    async def think(self, topic: str, knowledge_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        基于知识进行思考
        
        Args:
            topic: 思考主题
            knowledge_context: 知识上下文
            
        Returns:
            思考结果
        """
        try:
            # 使用Agno KnowledgeTools进行思考
            result = await self.knowledge_tools.think(topic, context=knowledge_context)
            
            return {
                'tool': 'agno_knowledge',
                'action': 'think',
                'topic': topic,
                'result': result,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_knowledge',
                'action': 'think',
                'topic': topic,
                'error': str(e),
                'status': 'error'
            }
    
    async def summarize(self, content: str, summary_type: str = "brief") -> Dict[str, Any]:
        """
        总结内容
        
        Args:
            content: 待总结内容
            summary_type: 总结类型
            
        Returns:
            总结结果
        """
        try:
            # 使用Agno KnowledgeTools进行总结
            result = await self.knowledge_tools.summarize(content, type=summary_type)
            
            return {
                'tool': 'agno_knowledge',
                'action': 'summarize',
                'content_length': len(content),
                'summary_type': summary_type,
                'result': result,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_knowledge',
                'action': 'summarize',
                'error': str(e),
                'status': 'error'
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取知识工具能力"""
        return {
            'tool_name': self.name,
            'description': self.description,
            'capabilities': [
                'knowledge_search',
                'content_analysis',
                'knowledge_thinking',
                'content_summarization'
            ],
            'framework': 'agno'
        } 