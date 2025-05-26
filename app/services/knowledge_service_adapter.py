"""
知识库服务适配器
提供向后兼容的API，同时在底层使用新的统一知识库管理工具
"""

from typing import List, Dict, Any, Optional, Union
from sqlalchemy.orm import Session
from datetime import datetime
import logging

# 导入现有的数据模型和schema
from app.models.knowledge import KnowledgeBase, Document, DocumentChunk
from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    DocumentCreate,
    DocumentUpdate,
    KnowledgeBaseStats
)

# 导入统一的管理工具
from app.tools.base.knowledge_management import (
    get_knowledge_manager,
    KnowledgeBaseConfig,
    DocumentProcessingConfig
)

# 导入统一的切分工具
from app.tools.base.document_chunking import (
    get_chunking_tool,
    ChunkingConfig,
    DocumentChunk as UnifiedDocumentChunk
)

logger = logging.getLogger(__name__)

class KnowledgeServiceAdapter:
    """
    知识库服务适配器
    兼容现有的 KnowledgeService 接口，底层使用统一的管理工具
    """
    
    def __init__(self, db: Session):
        """
        初始化适配器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.unified_manager = get_knowledge_manager(db)
        self.chunking_tool = get_chunking_tool()
        
        logger.info("知识库服务适配器初始化完成")
    
    # ========== 知识库管理方法 ==========
    
    async def get_knowledge_bases(
        self, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取知识库列表（兼容原API）
        """
        try:
            # 使用统一管理器获取知识库
            all_kbs = await self.unified_manager.list_knowledge_bases()
            
            # 应用过滤条件
            filtered_kbs = []
            for kb in all_kbs:
                # 状态过滤
                if is_active is not None and kb.get("is_active") != is_active:
                    continue
                
                # 搜索过滤
                if search and search.lower() not in kb.get("name", "").lower():
                    continue
                
                filtered_kbs.append(kb)
            
            # 分页
            start = skip
            end = skip + limit
            paginated_kbs = filtered_kbs[start:end]
            
            # 转换为兼容格式
            result = []
            for kb in paginated_kbs:
                kb_dict = {
                    "id": kb["kb_id"],
                    "name": kb["name"],
                    "description": kb["description"],
                    "is_active": kb.get("is_active", True),
                    "created_at": kb.get("created_at"),
                    "updated_at": kb.get("last_updated"),
                    "embedding_model": kb.get("embedding_model", "text-embedding-ada-002"),
                    "stats": {
                        "document_count": kb.get("document_count", 0),
                        "chunk_count": kb.get("chunk_count", 0),
                        "language_distribution": {},  # 可以扩展
                        "total_characters": kb.get("total_characters", 0)
                    }
                }
                result.append(kb_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"获取知识库列表失败: {str(e)}")
            return []
    
    async def create_knowledge_base(self, kb_data: Union[KnowledgeBaseCreate, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        创建知识库（兼容原API）
        """
        try:
            if isinstance(kb_data, KnowledgeBaseCreate):
                kb_dict = kb_data.dict()
            else:
                kb_dict = kb_data
            
            # 转换为统一配置
            kb_config = KnowledgeBaseConfig(
                name=kb_dict["name"],
                description=kb_dict.get("description", ""),
                embedding_model=kb_dict.get("embedding_model", "text-embedding-ada-002"),
                is_active=kb_dict.get("is_active", True),
                chunking_strategy=kb_dict.get("chunking_strategy", "sentence"),
                chunk_size=kb_dict.get("chunk_size", 1000),
                chunk_overlap=kb_dict.get("chunk_overlap", 200)
            )
            
            # 使用统一管理器创建
            result = await self.unified_manager.create_knowledge_base(kb_config)
            
            if result.get("status") == "error":
                return None
            
            # 转换为兼容格式
            return {
                "id": result["kb_id"],
                "name": result["name"],
                "description": result["description"],
                "is_active": True,
                "created_at": result["created_at"],
                "embedding_model": kb_config.embedding_model
            }
            
        except Exception as e:
            logger.error(f"创建知识库失败: {str(e)}")
            return None
    
    async def get_knowledge_base(self, kb_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个知识库（兼容原API）
        """
        try:
            kb_info = await self.unified_manager.get_knowledge_base(kb_id)
            
            if not kb_info:
                return None
            
            # 转换为兼容格式
            return {
                "id": kb_info["kb_id"],
                "name": kb_info["name"],
                "description": kb_info["description"],
                "is_active": kb_info.get("is_active", True),
                "created_at": kb_info.get("created_at"),
                "updated_at": kb_info.get("last_updated"),
                "embedding_model": kb_info.get("embedding_model", "text-embedding-ada-002"),
                "stats": {
                    "document_count": kb_info.get("document_count", 0),
                    "chunk_count": kb_info.get("chunk_count", 0),
                    "total_characters": kb_info.get("total_characters", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"获取知识库失败: {str(e)}")
            return None
    
    async def update_knowledge_base(self, kb_id: str, update_data: Union[KnowledgeBaseUpdate, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        更新知识库（兼容原API）
        """
        try:
            if isinstance(update_data, KnowledgeBaseUpdate):
                updates = update_data.dict(exclude_unset=True)
            else:
                updates = update_data
            
            result = await self.unified_manager.update_knowledge_base(kb_id, updates)
            
            if result["status"] != "success":
                return None
            
            # 获取更新后的知识库信息
            return await self.get_knowledge_base(kb_id)
            
        except Exception as e:
            logger.error(f"更新知识库失败: {str(e)}")
            return None
    
    async def delete_knowledge_base(self, kb_id: str) -> bool:
        """
        删除知识库（兼容原API）
        """
        try:
            result = await self.unified_manager.delete_knowledge_base(kb_id)
            return result["status"] == "success"
            
        except Exception as e:
            logger.error(f"删除知识库失败: {str(e)}")
            return False
    
    # ========== 文档管理方法 ==========
    
    async def add_document(self, kb_id: str, doc_data: Union[DocumentCreate, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        添加文档（兼容原API）
        """
        try:
            if isinstance(doc_data, DocumentCreate):
                doc_dict = doc_data.dict()
            else:
                doc_dict = doc_data
            
            # 转换为统一格式
            document = {
                "title": doc_dict.get("title", "Untitled"),
                "content": doc_dict.get("content", ""),
                "metadata": doc_dict.get("metadata", {})
            }
            
            # 使用统一管理器添加文档
            result = await self.unified_manager.add_document(kb_id, document)
            
            if result["status"] != "success":
                return None
            
            # 转换为兼容格式
            return {
                "id": result["document_id"],
                "knowledge_base_id": kb_id,
                "title": document["title"],
                "content": document["content"],
                "metadata": document["metadata"],
                "status": "indexed",
                "chunk_count": result["chunks"],
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            return None
    
    async def add_document_chunks(self, doc_id: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        添加文档分块（兼容原API）
        """
        try:
            # 这个方法在新的架构中由统一管理器自动处理
            # 这里提供一个兼容的接口
            logger.info(f"文档切片由统一管理器自动处理: {doc_id}")
            
            # 返回兼容格式的响应
            created_chunks = []
            for i, chunk in enumerate(chunks):
                chunk_dict = {
                    "id": f"{doc_id}_chunk_{i}",
                    "document_id": doc_id,
                    "content": chunk["content"],
                    "chunk_index": i,
                    "metadata": chunk.get("metadata", {}),
                    "created_at": datetime.now().isoformat()
                }
                created_chunks.append(chunk_dict)
            
            return created_chunks
            
        except Exception as e:
            logger.error(f"添加文档分块失败: {str(e)}")
            return []
    
    async def search(self, kb_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索知识库（兼容原API）
        """
        try:
            results = await self.unified_manager.search_documents(kb_id, query, None, top_k)
            
            # 转换为兼容格式
            formatted_results = []
            for result in results:
                formatted_result = {
                    "id": result.get("chunk_id"),
                    "content": result["content"],
                    "score": result["score"],
                    "document": {
                        "id": result.get("document_id"),
                        "file_name": result.get("metadata", {}).get("file_name"),
                        "content_type": result.get("metadata", {}).get("file_type")
                    },
                    "metadata": result.get("metadata", {})
                }
                formatted_results.append(formatted_result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            return []
    
    # ========== 文档切分方法 ==========
    
    def chunk_document(self, content: str, chunk_size: int = 1000, chunk_overlap: int = 200, strategy: str = "sentence") -> List[Dict[str, Any]]:
        """
        文档切分（兼容原API）
        """
        try:
            # 创建切分配置
            config = ChunkingConfig(
                strategy=strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            # 执行切分
            result = self.chunking_tool.chunk_document(content, config)
            
            # 转换为兼容格式
            chunks = []
            for chunk in result.chunks:
                chunk_dict = {
                    "content": chunk.content,
                    "metadata": chunk.metadata
                }
                chunks.append(chunk_dict)
            
            return chunks
            
        except Exception as e:
            logger.error(f"文档切分失败: {str(e)}")
            return []
    
    # ========== 统计信息方法 ==========
    
    async def get_knowledge_base_stats(self, kb_id: str) -> Dict[str, Any]:
        """
        获取知识库统计信息（兼容原API）
        """
        try:
            kb_info = await self.unified_manager.get_knowledge_base(kb_id)
            
            if not kb_info:
                return {}
            
            return {
                "document_count": kb_info.get("document_count", 0),
                "chunk_count": kb_info.get("chunk_count", 0),
                "language_distribution": {},  # 可以扩展
                "total_characters": kb_info.get("total_characters", 0)
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {}

# ========== 混合搜索服务适配器 ==========

class HybridSearchServiceAdapter:
    """
    混合搜索服务适配器
    在原有的 HybridSearchService 基础上集成统一的知识库管理
    """
    
    def __init__(self):
        """初始化适配器"""
        from app.services.hybrid_search_service import get_hybrid_search_service
        self.original_service = get_hybrid_search_service()
        self.unified_manager = get_knowledge_manager()
        
        logger.info("混合搜索服务适配器初始化完成")
    
    async def index_document(
        self,
        kb_id: str,
        doc_id: str,
        chunk_id: str,
        title: str,
        content: str,
        vector: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        索引文档（兼容原API，同时同步到统一管理器）
        """
        try:
            # 调用原有的索引方法
            original_result = await self.original_service.index_document(
                kb_id, doc_id, chunk_id, title, content, vector, metadata
            )
            
            # 同步到统一管理器（如果原索引成功）
            if original_result:
                try:
                    # 构建文档数据
                    document = {
                        "id": doc_id,
                        "title": title,
                        "content": content,
                        "metadata": metadata
                    }
                    
                    # 检查知识库是否存在于统一管理器中
                    kb_info = await self.unified_manager.get_knowledge_base(kb_id)
                    if not kb_info:
                        # 创建知识库
                        from app.tools.base.knowledge_management import KnowledgeBaseConfig
                        kb_config = KnowledgeBaseConfig(
                            name=f"Migrated KB {kb_id}",
                            description="从混合搜索服务迁移的知识库"
                        )
                        await self.unified_manager.create_knowledge_base(kb_config)
                    
                    # 添加文档到统一管理器
                    await self.unified_manager.add_document(kb_id, document)
                    
                except Exception as sync_error:
                    logger.warning(f"同步到统一管理器失败: {str(sync_error)}")
                    # 不影响原有功能
            
            return original_result
            
        except Exception as e:
            logger.error(f"索引文档失败: {str(e)}")
            return False
    
    async def batch_index_documents(self, kb_id: str, documents: List[Dict[str, Any]]) -> bool:
        """
        批量索引文档（兼容原API，同时同步到统一管理器）
        """
        try:
            # 调用原有的批量索引方法
            original_result = await self.original_service.batch_index_documents(kb_id, documents)
            
            # 同步到统一管理器
            if original_result:
                try:
                    # 检查知识库是否存在
                    kb_info = await self.unified_manager.get_knowledge_base(kb_id)
                    if not kb_info:
                        # 创建知识库
                        from app.tools.base.knowledge_management import KnowledgeBaseConfig
                        kb_config = KnowledgeBaseConfig(
                            name=f"Migrated KB {kb_id}",
                            description="从混合搜索服务迁移的知识库"
                        )
                        await self.unified_manager.create_knowledge_base(kb_config)
                    
                    # 批量添加文档
                    unified_documents = []
                    for doc in documents:
                        unified_doc = {
                            "id": doc.get("doc_id"),
                            "title": doc.get("title", ""),
                            "content": doc.get("content", ""),
                            "metadata": doc.get("metadata", {})
                        }
                        unified_documents.append(unified_doc)
                    
                    # 这里可以使用批量添加方法（如果有的话）
                    for doc in unified_documents:
                        await self.unified_manager.add_document(kb_id, doc)
                    
                except Exception as sync_error:
                    logger.warning(f"批量同步到统一管理器失败: {str(sync_error)}")
            
            return original_result
            
        except Exception as e:
            logger.error(f"批量索引文档失败: {str(e)}")
            return False

# ========== 全局适配器实例 ==========

def get_knowledge_service_adapter(db: Session) -> KnowledgeServiceAdapter:
    """获取知识库服务适配器实例"""
    return KnowledgeServiceAdapter(db)

def get_hybrid_search_adapter() -> HybridSearchServiceAdapter:
    """获取混合搜索服务适配器实例"""
    return HybridSearchServiceAdapter() 