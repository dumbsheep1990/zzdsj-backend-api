"""
统一知识库管理工具
基于Agno框架提供完整的知识库管理功能，包括创建、配置、文档管理等
"""

from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio
from datetime import datetime
import uuid
from sqlalchemy.orm import Session

# 导入Agno框架
from app.frameworks.agno.knowledge_base import (
    get_knowledge_base,
    create_knowledge_base as agno_create_kb,
    list_knowledge_bases as agno_list_kbs,
    KnowledgeBaseProcessor
)

# 导入统一切分工具
from app.tools.base.document_chunking import (
    ChunkingConfig,
    DocumentChunk,
    ChunkingResult
)

# 导入数据库模型
from app.models.knowledge import KnowledgeBase, Document, DocumentChunk as DBDocumentChunk
from app.utils.database import get_db

logger = logging.getLogger(__name__)

class KnowledgeBaseStatus(str, Enum):
    """知识库状态枚举"""
    CREATING = "creating"
    ACTIVE = "active"
    INACTIVE = "inactive"
    UPDATING = "updating"
    ERROR = "error"

@dataclass
class KnowledgeBaseConfig:
    """知识库配置类"""
    name: str
    description: str = ""
    chunking_strategy: str = "sentence"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    language: str = "zh"
    embedding_model: str = "text-embedding-ada-002"
    vector_store: str = "agno"  # agno, elasticsearch, milvus
    is_active: bool = True
    
    # Agno特定配置
    agno_config: Dict[str, Any] = field(default_factory=dict)
    
    # 权限配置
    public_read: bool = False
    public_write: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "chunking_strategy": self.chunking_strategy,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "language": self.language,
            "embedding_model": self.embedding_model,
            "vector_store": self.vector_store,
            "is_active": self.is_active,
            "agno_config": self.agno_config,
            "public_read": self.public_read,
            "public_write": self.public_write
        }

@dataclass
class DocumentProcessingConfig:
    """文档处理配置"""
    auto_chunk: bool = True
    auto_vectorize: bool = True
    auto_index: bool = True
    chunk_config: Optional[ChunkingConfig] = None
    metadata_extraction: bool = True
    progress_callback: Optional[Callable] = None

class UnifiedKnowledgeBaseManager:
    """统一知识库管理器"""
    
    def __init__(self, db: Optional[Session] = None):
        """
        初始化知识库管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self._agno_kbs: Dict[str, KnowledgeBaseProcessor] = {}
        
        logger.info("初始化统一知识库管理器")
    
    async def create_knowledge_base(self, config: KnowledgeBaseConfig, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        创建知识库
        
        Args:
            config: 知识库配置
            user_id: 创建者ID
            
        Returns:
            创建结果
        """
        try:
            # 1. 生成知识库ID
            kb_id = str(uuid.uuid4())
            
            logger.info(f"创建知识库: {config.name} (ID: {kb_id})")
            
            # 2. 在数据库中创建记录
            db_kb = None
            if self.db:
                db_kb = KnowledgeBase(
                    id=kb_id,
                    name=config.name,
                    description=config.description,
                    is_active=config.is_active,
                    embedding_model=config.embedding_model,
                    settings=config.to_dict(),
                    type="agno",
                    agno_kb_id=f"agno_{kb_id}"
                )
                self.db.add(db_kb)
                self.db.commit()
                self.db.refresh(db_kb)
            
            # 3. 创建Agno知识库
            agno_config = {
                "chunking_strategy": config.chunking_strategy,
                "chunk_size": config.chunk_size,
                "chunk_overlap": config.chunk_overlap,
                "language": config.language,
                "embedding_model": config.embedding_model,
                **config.agno_config
            }
            
            agno_kb = await agno_create_kb(kb_id, config.name, agno_config)
            self._agno_kbs[kb_id] = agno_kb
            
            # 4. 创建响应
            result = {
                "kb_id": kb_id,
                "name": config.name,
                "description": config.description,
                "agno_kb_id": f"agno_{kb_id}",
                "status": KnowledgeBaseStatus.ACTIVE.value,
                "created_at": datetime.now().isoformat(),
                "config": config.to_dict(),
                "stats": {
                    "document_count": 0,
                    "chunk_count": 0,
                    "total_characters": 0
                }
            }
            
            if db_kb:
                result["db_id"] = db_kb.id
            
            logger.info(f"知识库 {config.name} 创建成功")
            return result
            
        except Exception as e:
            logger.error(f"创建知识库失败: {str(e)}")
            # 回滚数据库操作
            if self.db and db_kb:
                self.db.rollback()
            
            return {
                "status": "error",
                "error": str(e),
                "kb_id": kb_id if 'kb_id' in locals() else None
            }
    
    async def get_knowledge_base(self, kb_id: str) -> Optional[Dict[str, Any]]:
        """
        获取知识库信息
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            知识库信息
        """
        try:
            # 从Agno获取
            agno_kb = self._get_agno_kb(kb_id)
            if not agno_kb:
                return None
            
            stats = agno_kb.get_stats()
            
            # 从数据库获取额外信息
            db_info = {}
            if self.db:
                db_kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
                if db_kb:
                    db_info = {
                        "db_id": db_kb.id,
                        "created_at": db_kb.created_at.isoformat() if db_kb.created_at else None,
                        "updated_at": db_kb.updated_at.isoformat() if db_kb.updated_at else None,
                        "is_active": db_kb.is_active,
                        "settings": db_kb.settings or {}
                    }
            
            # 合并信息
            result = {
                **stats,
                **db_info,
                "status": KnowledgeBaseStatus.ACTIVE.value
            }
            
            return result
            
        except Exception as e:
            logger.error(f"获取知识库失败: {str(e)}")
            return None
    
    async def list_knowledge_bases(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出知识库
        
        Args:
            user_id: 用户ID（用于权限过滤）
            
        Returns:
            知识库列表
        """
        try:
            # 从Agno获取所有知识库
            agno_stats = agno_list_kbs()
            
            # 从数据库获取额外信息
            db_kbs = {}
            if self.db:
                db_kb_list = self.db.query(KnowledgeBase).all()
                for db_kb in db_kb_list:
                    db_kbs[db_kb.id] = {
                        "db_id": db_kb.id,
                        "created_at": db_kb.created_at.isoformat() if db_kb.created_at else None,
                        "updated_at": db_kb.updated_at.isoformat() if db_kb.updated_at else None,
                        "is_active": db_kb.is_active,
                        "settings": db_kb.settings or {}
                    }
            
            # 合并信息
            result = []
            for stats in agno_stats:
                kb_id = stats["kb_id"]
                kb_info = {
                    **stats,
                    **db_kbs.get(kb_id, {}),
                    "status": KnowledgeBaseStatus.ACTIVE.value
                }
                result.append(kb_info)
            
            return result
            
        except Exception as e:
            logger.error(f"列出知识库失败: {str(e)}")
            return []
    
    async def update_knowledge_base(self, kb_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新知识库
        
        Args:
            kb_id: 知识库ID
            updates: 更新内容
            
        Returns:
            更新结果
        """
        try:
            # 更新Agno知识库
            agno_kb = self._get_agno_kb(kb_id)
            if not agno_kb:
                return {"status": "error", "error": "Knowledge base not found"}
            
            agno_kb.update_config(updates)
            
            # 更新数据库记录
            if self.db:
                db_kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
                if db_kb:
                    # 更新允许的字段
                    if "name" in updates:
                        db_kb.name = updates["name"]
                    if "description" in updates:
                        db_kb.description = updates["description"]
                    if "is_active" in updates:
                        db_kb.is_active = updates["is_active"]
                    if "embedding_model" in updates:
                        db_kb.embedding_model = updates["embedding_model"]
                    
                    # 更新设置
                    current_settings = db_kb.settings or {}
                    current_settings.update(updates)
                    db_kb.settings = current_settings
                    
                    db_kb.updated_at = datetime.now()
                    self.db.commit()
            
            logger.info(f"知识库 {kb_id} 更新成功")
            return {
                "status": "success",
                "kb_id": kb_id,
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"更新知识库失败: {str(e)}")
            if self.db:
                self.db.rollback()
            return {"status": "error", "error": str(e)}
    
    async def delete_knowledge_base(self, kb_id: str) -> Dict[str, Any]:
        """
        删除知识库
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            删除结果
        """
        try:
            # 从Agno中移除
            if kb_id in self._agno_kbs:
                del self._agno_kbs[kb_id]
            
            # 从数据库中删除
            if self.db:
                # 删除相关的文档和切片
                db_kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
                if db_kb:
                    # 删除文档块
                    chunks = self.db.query(DBDocumentChunk).join(Document).filter(
                        Document.knowledge_base_id == db_kb.id
                    ).all()
                    for chunk in chunks:
                        self.db.delete(chunk)
                    
                    # 删除文档
                    documents = self.db.query(Document).filter(
                        Document.knowledge_base_id == db_kb.id
                    ).all()
                    for doc in documents:
                        self.db.delete(doc)
                    
                    # 删除知识库
                    self.db.delete(db_kb)
                    self.db.commit()
            
            logger.info(f"知识库 {kb_id} 删除成功")
            return {"status": "success", "kb_id": kb_id}
            
        except Exception as e:
            logger.error(f"删除知识库失败: {str(e)}")
            if self.db:
                self.db.rollback()
            return {"status": "error", "error": str(e)}
    
    async def add_document(self, kb_id: str, document: Dict[str, Any], 
                          config: Optional[DocumentProcessingConfig] = None) -> Dict[str, Any]:
        """
        向知识库添加文档
        
        Args:
            kb_id: 知识库ID
            document: 文档数据
            config: 处理配置
            
        Returns:
            添加结果
        """
        try:
            config = config or DocumentProcessingConfig()
            
            # 获取Agno知识库
            agno_kb = self._get_agno_kb(kb_id)
            if not agno_kb:
                return {"status": "error", "error": "Knowledge base not found"}
            
            # 设置进度回调
            if config.progress_callback:
                # 这里可以设置进度回调，但Agno的add_document是同步的
                pass
            
            # 添加到Agno知识库
            result = await agno_kb.add_document(document)
            
            # 同步到数据库
            if result["status"] == "success" and self.db:
                await self._sync_document_to_db(kb_id, document, result)
            
            return result
            
        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def search_documents(self, kb_id: str, query: str, 
                             filter_criteria: Optional[Dict[str, Any]] = None,
                             top_k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索文档
        
        Args:
            kb_id: 知识库ID
            query: 查询文本
            filter_criteria: 过滤条件
            top_k: 返回数量
            
        Returns:
            搜索结果
        """
        try:
            agno_kb = self._get_agno_kb(kb_id)
            if not agno_kb:
                return []
            
            return await agno_kb.search(query, filter_criteria, top_k)
            
        except Exception as e:
            logger.error(f"搜索文档失败: {str(e)}")
            return []
    
    async def remove_document(self, kb_id: str, document_id: str) -> Dict[str, Any]:
        """
        删除文档
        
        Args:
            kb_id: 知识库ID
            document_id: 文档ID
            
        Returns:
            删除结果
        """
        try:
            agno_kb = self._get_agno_kb(kb_id)
            if not agno_kb:
                return {"status": "error", "error": "Knowledge base not found"}
            
            # 从Agno删除
            result = await agno_kb.remove_document(document_id)
            
            # 从数据库删除
            if result["status"] == "success" and self.db:
                db_doc = self.db.query(Document).filter(Document.id == document_id).first()
                if db_doc:
                    # 删除相关切片
                    chunks = self.db.query(DBDocumentChunk).filter(
                        DBDocumentChunk.document_id == db_doc.id
                    ).all()
                    for chunk in chunks:
                        self.db.delete(chunk)
                    
                    # 删除文档
                    self.db.delete(db_doc)
                    self.db.commit()
            
            return result
            
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def _get_agno_kb(self, kb_id: str) -> Optional[KnowledgeBaseProcessor]:
        """获取Agno知识库实例"""
        if kb_id not in self._agno_kbs:
            # 尝试从全局获取
            try:
                agno_kb = get_knowledge_base(kb_id)
                self._agno_kbs[kb_id] = agno_kb
                return agno_kb
            except:
                return None
        return self._agno_kbs[kb_id]
    
    async def _sync_document_to_db(self, kb_id: str, document: Dict[str, Any], agno_result: Dict[str, Any]):
        """同步文档到数据库"""
        if not self.db:
            return
        
        try:
            # 获取知识库
            db_kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not db_kb:
                return
            
            # 创建文档记录
            db_doc = Document(
                knowledge_base_id=db_kb.id,
                title=document.get("title", "Untitled"),
                content=document.get("content", ""),
                metadata=document.get("metadata", {}),
                status="indexed"
            )
            self.db.add(db_doc)
            self.db.flush()  # 获取ID
            
            # 创建切片记录（如果有）
            chunk_ids = agno_result.get("chunk_ids", [])
            for i, chunk_id in enumerate(chunk_ids):
                db_chunk = DBDocumentChunk(
                    document_id=db_doc.id,
                    content=f"Chunk {i+1}",  # 实际内容需要从Agno获取
                    metadata={"chunk_id": chunk_id, "chunk_index": i}
                )
                self.db.add(db_chunk)
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"同步文档到数据库失败: {str(e)}")
            self.db.rollback()

# 全局管理器实例
_knowledge_manager = None

def get_knowledge_manager(db: Optional[Session] = None) -> UnifiedKnowledgeBaseManager:
    """获取知识库管理器实例"""
    global _knowledge_manager
    if _knowledge_manager is None:
        _knowledge_manager = UnifiedKnowledgeBaseManager(db)
    return _knowledge_manager

# 便利函数
async def create_kb(name: str, description: str = "", config: Optional[Dict[str, Any]] = None, 
                   user_id: Optional[str] = None) -> Dict[str, Any]:
    """创建知识库的便利函数"""
    kb_config = KnowledgeBaseConfig(
        name=name,
        description=description,
        **(config or {})
    )
    manager = get_knowledge_manager()
    return await manager.create_knowledge_base(kb_config, user_id)

async def add_document_to_kb(kb_id: str, content: str, metadata: Optional[Dict[str, Any]] = None,
                           title: str = "Untitled") -> Dict[str, Any]:
    """向知识库添加文档的便利函数"""
    document = {
        "content": content,
        "metadata": metadata or {},
        "title": title
    }
    manager = get_knowledge_manager()
    return await manager.add_document(kb_id, document)

async def search_kb(kb_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """搜索知识库的便利函数"""
    manager = get_knowledge_manager()
    return await manager.search_documents(kb_id, query, top_k=top_k) 