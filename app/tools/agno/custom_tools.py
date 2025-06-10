# ZZDSJ自定义工具 - 基于现有代码实现
from agno import tool
from typing import Dict, Any, Optional

class ZZDSJCustomTools:
    """ZZDSJ自定义工具集合 - 直接调用现有实现"""
    
    @tool
    async def policy_search(self, query: str, category: Optional[str] = None) -> Dict[str, Any]:
        """政策搜索工具 - 基于现有PolicySearchTool实现"""
        try:
            # 直接调用现有的政策搜索器实现
            from app.tools.advanced.research.policy_search_tool import PolicySearchTool
            
            policy_tool = PolicySearchTool()
            result = await policy_tool.search(query, category)
            
            return {
                'tool': 'policy_search',
                'query': query,
                'category': category,
                'result': result,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'policy_search',
                'query': query,
                'error': str(e),
                'status': 'error'
            }
    
    @tool
    async def knowledge_query(self, query: str, kb_name: Optional[str] = None) -> Dict[str, Any]:
        """知识库查询工具 - 基于现有知识库管理器"""
        try:
            # 调用现有知识库管理器适配器
            from app.frameworks.agno.knowledge_manager_adapter import AgnoKnowledgeManagerAdapter
            
            km_adapter = AgnoKnowledgeManagerAdapter()
            result = await km_adapter.search(query, kb_name)
            
            return {
                'tool': 'knowledge_query',
                'query': query,
                'knowledge_base': kb_name,
                'result': result,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'knowledge_query',
                'query': query,
                'error': str(e),
                'status': 'error'
            }
    
    @tool
    async def document_process(self, file_path: str, process_type: str = "extract") -> Dict[str, Any]:
        """文档处理工具 - 基于现有文档处理器"""
        try:
            # 调用现有文档处理器
            from app.frameworks.agno.document_processor import DocumentProcessor
            
            processor = DocumentProcessor()
            result = await processor.process(file_path, process_type)
            
            return {
                'tool': 'document_process',
                'file_path': file_path,
                'process_type': process_type,
                'result': result,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'document_process',
                'file_path': file_path,
                'error': str(e),
                'status': 'error'
            } 