# Agno ChunkingTools 封装管理器
from typing import Dict, Any, List, Optional
from agno.tools import ChunkingTools

class AgnoChunkingManager:
    """Agno分块工具管理器 - 直接使用Agno框架的ChunkingTools"""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200, **kwargs):
        """
        初始化Agno分块工具管理器
        
        Args:
            chunk_size: 分块大小
            overlap: 重叠大小
            **kwargs: 其他Agno ChunkingTools参数
        """
        # 直接使用Agno框架的ChunkingTools
        self.chunking_tools = ChunkingTools(
            chunk_size=chunk_size,
            overlap=overlap,
            **kwargs
        )
        self.name = "agno_chunking"
        self.description = "基于Agno框架的文档分块工具"
    
    async def chunk_text(self, text: str, chunk_strategy: str = "recursive") -> Dict[str, Any]:
        """
        对文本进行分块
        
        Args:
            text: 待分块文本
            chunk_strategy: 分块策略
            
        Returns:
            分块结果
        """
        try:
            # 使用Agno ChunkingTools进行文本分块
            chunks = await self.chunking_tools.chunk_text(text, strategy=chunk_strategy)
            
            return {
                'tool': 'agno_chunking',
                'action': 'chunk_text',
                'original_length': len(text),
                'chunk_count': len(chunks),
                'chunk_strategy': chunk_strategy,
                'chunks': chunks,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_chunking',
                'action': 'chunk_text',
                'text_length': len(text),
                'error': str(e),
                'status': 'error'
            }
    
    async def chunk_document(self, document: Any, doc_type: str = "auto") -> Dict[str, Any]:
        """
        对文档进行分块
        
        Args:
            document: 待分块文档
            doc_type: 文档类型
            
        Returns:
            分块结果
        """
        try:
            # 使用Agno ChunkingTools进行文档分块
            chunks = await self.chunking_tools.chunk_document(document, type=doc_type)
            
            return {
                'tool': 'agno_chunking',
                'action': 'chunk_document',
                'doc_type': doc_type,
                'chunk_count': len(chunks),
                'chunks': chunks,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_chunking',
                'action': 'chunk_document',
                'doc_type': doc_type,
                'error': str(e),
                'status': 'error'
            }
    
    async def smart_chunk(self, content: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        智能分块（基于上下文）
        
        Args:
            content: 待分块内容
            context: 分块上下文
            
        Returns:
            智能分块结果
        """
        try:
            # 使用Agno ChunkingTools的智能分块功能
            chunks = await self.chunking_tools.smart_chunk(content, context=context)
            
            return {
                'tool': 'agno_chunking',
                'action': 'smart_chunk',
                'chunk_count': len(chunks),
                'context': context,
                'chunks': chunks,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_chunking',
                'action': 'smart_chunk',
                'error': str(e),
                'status': 'error'
            }
    
    async def merge_chunks(self, chunks: List[Any], merge_criteria: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        合并分块
        
        Args:
            chunks: 分块列表
            merge_criteria: 合并条件
            
        Returns:
            合并结果
        """
        try:
            # 使用Agno ChunkingTools的分块合并功能
            merged_chunks = await self.chunking_tools.merge_chunks(chunks, criteria=merge_criteria)
            
            return {
                'tool': 'agno_chunking',
                'action': 'merge_chunks',
                'original_count': len(chunks),
                'merged_count': len(merged_chunks),
                'merge_criteria': merge_criteria,
                'result': merged_chunks,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_chunking',
                'action': 'merge_chunks',
                'original_count': len(chunks),
                'error': str(e),
                'status': 'error'
            }
    
    def get_chunk_info(self, chunks: List[Any]) -> Dict[str, Any]:
        """
        获取分块信息统计
        
        Args:
            chunks: 分块列表
            
        Returns:
            分块统计信息
        """
        try:
            total_length = sum(len(str(chunk)) for chunk in chunks)
            avg_length = total_length / len(chunks) if chunks else 0
            
            return {
                'tool': 'agno_chunking',
                'action': 'get_info',
                'chunk_count': len(chunks),
                'total_length': total_length,
                'average_length': avg_length,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_chunking',
                'action': 'get_info',
                'error': str(e),
                'status': 'error'
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取分块工具能力"""
        return {
            'tool_name': self.name,
            'description': self.description,
            'capabilities': [
                'text_chunking',
                'document_chunking',
                'smart_chunking',
                'chunk_merging',
                'chunk_analysis'
            ],
            'framework': 'agno'
        }
 