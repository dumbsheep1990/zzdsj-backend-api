"""
文档处理器 - 核心业务逻辑
提供文档上传、处理、解析等核心功能
"""

import os
import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

# 导入数据访问层
from app.repositories.knowledge import DocumentRepository, DocumentChunkRepository

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """文档处理器 - 核心业务逻辑类"""
    
    def __init__(self, db: Session):
        """初始化文档处理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.doc_repository = DocumentRepository(db)
        self.chunk_repository = DocumentChunkRepository(db)
        
    # ============ 文档管理方法 ============
    
    async def create_document(
        self,
        kb_id: str,
        name: str,
        content: str = None,
        file_path: str = None,
        mime_type: str = "text/plain",
        metadata: Dict[str, Any] = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """创建文档
        
        Args:
            kb_id: 知识库ID
            name: 文档名称
            content: 文档内容（可选）
            file_path: 文件路径（可选）
            mime_type: MIME类型
            metadata: 元数据
            user_id: 创建者ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证输入
            if not name or not name.strip():
                return {
                    "success": False,
                    "error": "文档名称不能为空",
                    "error_code": "INVALID_NAME"
                }
            
            if not content and not file_path:
                return {
                    "success": False,
                    "error": "必须提供文档内容或文件路径",
                    "error_code": "NO_CONTENT"
                }
            
            # 如果提供了文件路径但没有内容，尝试提取内容
            if file_path and not content:
                content = await self._extract_content_from_file(file_path, mime_type)
                if not content:
                    return {
                        "success": False,
                        "error": "无法从文件中提取内容",
                        "error_code": "EXTRACT_FAILED"
                    }
            
            # 准备文档数据
            doc_data = {
                "id": str(uuid.uuid4()),
                "kb_id": kb_id,
                "name": name.strip(),
                "content": content,
                "file_path": file_path,
                "mime_type": mime_type,
                "metadata": metadata or {},
                "status": "pending",  # pending, processing, completed, failed
                "created_by": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # 创建文档
            doc = await self.doc_repository.create(doc_data)
            
            logger.info(f"文档创建成功: {doc.id} - {doc.name}")
            
            return {
                "success": True,
                "data": {
                    "id": doc.id,
                    "kb_id": doc.kb_id,
                    "name": doc.name,
                    "mime_type": doc.mime_type,
                    "status": doc.status,
                    "created_at": doc.created_at,
                    "updated_at": doc.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"创建文档失败: {str(e)}")
            return {
                "success": False,
                "error": f"创建文档失败: {str(e)}",
                "error_code": "CREATE_FAILED"
            }
    
    async def process_document(self, doc_id: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> Dict[str, Any]:
        """处理文档（分块和向量化）
        
        Args:
            doc_id: 文档ID
            chunk_size: 分块大小
            chunk_overlap: 分块重叠
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 获取文档
            doc = await self.doc_repository.get_by_id(doc_id)
            if not doc:
                return {
                    "success": False,
                    "error": "文档不存在",
                    "error_code": "DOC_NOT_FOUND"
                }
            
            # 更新状态为处理中
            await self.doc_repository.update(doc_id, {
                "status": "processing",
                "updated_at": datetime.utcnow()
            })
            
            # 获取文档内容
            content = doc.content
            if not content and doc.file_path:
                content = await self._extract_content_from_file(doc.file_path, doc.mime_type)
            
            if not content:
                await self.doc_repository.update(doc_id, {
                    "status": "failed",
                    "updated_at": datetime.utcnow()
                })
                return {
                    "success": False,
                    "error": "无法获取文档内容",
                    "error_code": "NO_CONTENT"
                }
            
            # 分块文档
            chunks = await self._chunk_document(content, doc.mime_type, chunk_size, chunk_overlap)
            
            # 删除现有分块（如果重新处理）
            await self.chunk_repository.delete_by_document(doc_id)
            
            # 创建新分块
            chunk_ids = []
            for i, (chunk_content, chunk_metadata) in enumerate(chunks):
                chunk_data = {
                    "id": str(uuid.uuid4()),
                    "document_id": doc_id,
                    "kb_id": doc.kb_id,
                    "content": chunk_content,
                    "metadata": {
                        **chunk_metadata,
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    },
                    "created_at": datetime.utcnow()
                }
                
                chunk = await self.chunk_repository.create(chunk_data)
                chunk_ids.append(chunk.id)
            
            # 更新文档状态为完成
            await self.doc_repository.update(doc_id, {
                "status": "completed",
                "updated_at": datetime.utcnow()
            })
            
            logger.info(f"文档处理成功: {doc_id}, 生成 {len(chunks)} 个分块")
            
            return {
                "success": True,
                "data": {
                    "document_id": doc_id,
                    "chunks_created": len(chunks),
                    "chunk_ids": chunk_ids
                }
            }
            
        except Exception as e:
            logger.error(f"处理文档失败: {str(e)}")
            
            # 更新状态为失败
            try:
                await self.doc_repository.update(doc_id, {
                    "status": "failed",
                    "updated_at": datetime.utcnow()
                })
            except:
                pass
            
            return {
                "success": False,
                "error": f"处理文档失败: {str(e)}",
                "error_code": "PROCESS_FAILED"
            }
    
    async def get_document(self, doc_id: str) -> Dict[str, Any]:
        """获取文档详情
        
        Args:
            doc_id: 文档ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            doc = await self.doc_repository.get_by_id(doc_id)
            if not doc:
                return {
                    "success": False,
                    "error": "文档不存在",
                    "error_code": "DOC_NOT_FOUND"
                }
            
            # 获取分块数量
            chunk_count = await self.chunk_repository.count_by_document(doc_id)
            
            return {
                "success": True,
                "data": {
                    "id": doc.id,
                    "kb_id": doc.kb_id,
                    "name": doc.name,
                    "mime_type": doc.mime_type,
                    "status": doc.status,
                    "metadata": doc.metadata,
                    "chunk_count": chunk_count,
                    "created_at": doc.created_at,
                    "updated_at": doc.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"获取文档失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取文档失败: {str(e)}",
                "error_code": "GET_FAILED"
            }
    
    async def list_documents(
        self,
        kb_id: str,
        status: str = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """获取文档列表
        
        Args:
            kb_id: 知识库ID
            status: 状态过滤
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 构建过滤条件
            filters = {"kb_id": kb_id}
            if status:
                filters["status"] = status
            
            # 获取文档列表
            docs = await self.doc_repository.list_with_filters(filters, skip, limit)
            total = await self.doc_repository.count_with_filters(filters)
            
            # 为每个文档添加分块数量
            doc_list = []
            for doc in docs:
                chunk_count = await self.chunk_repository.count_by_document(doc.id)
                doc_data = {
                    "id": doc.id,
                    "kb_id": doc.kb_id,
                    "name": doc.name,
                    "mime_type": doc.mime_type,
                    "status": doc.status,
                    "chunk_count": chunk_count,
                    "created_at": doc.created_at,
                    "updated_at": doc.updated_at
                }
                doc_list.append(doc_data)
            
            return {
                "success": True,
                "data": {
                    "documents": doc_list,
                    "total": total,
                    "skip": skip,
                    "limit": limit
                }
            }
            
        except Exception as e:
            logger.error(f"获取文档列表失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取文档列表失败: {str(e)}",
                "error_code": "LIST_FAILED"
            }
    
    async def delete_document(self, doc_id: str) -> Dict[str, Any]:
        """删除文档
        
        Args:
            doc_id: 文档ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查文档是否存在
            doc = await self.doc_repository.get_by_id(doc_id)
            if not doc:
                return {
                    "success": False,
                    "error": "文档不存在",
                    "error_code": "DOC_NOT_FOUND"
                }
            
            # 删除所有分块
            await self.chunk_repository.delete_by_document(doc_id)
            
            # 删除文档
            success = await self.doc_repository.delete(doc_id)
            
            if success:
                logger.info(f"文档删除成功: {doc_id}")
                return {
                    "success": True,
                    "data": {"deleted_doc_id": doc_id}
                }
            else:
                return {
                    "success": False,
                    "error": "删除文档失败",
                    "error_code": "DELETE_FAILED"
                }
            
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return {
                "success": False,
                "error": f"删除文档失败: {str(e)}",
                "error_code": "DELETE_FAILED"
            }
    
    # ============ 辅助方法 ============
    
    async def _extract_content_from_file(self, file_path: str, mime_type: str) -> Optional[str]:
        """从文件中提取文本内容
        
        Args:
            file_path: 文件路径
            mime_type: MIME类型
            
        Returns:
            Optional[str]: 提取的文本内容
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return None
            
            # 简单文本文件处理
            if mime_type.startswith("text/"):
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            
            # PDF处理
            elif mime_type == "application/pdf":
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(file_path)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text
                except Exception as e:
                    logger.error(f"PDF文本提取失败: {e}")
                    return None
            
            # DOCX处理
            elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                try:
                    import docx
                    doc = docx.Document(file_path)
                    return "\n".join([para.text for para in doc.paragraphs])
                except Exception as e:
                    logger.error(f"DOCX文本提取失败: {e}")
                    return None
            
            # 其他类型暂不支持
            else:
                logger.warning(f"不支持的文件类型: {mime_type}")
                return None
                
        except Exception as e:
            logger.error(f"文件内容提取失败: {str(e)}")
            return None
    
    async def _chunk_document(
        self, 
        content: str, 
        mime_type: str, 
        chunk_size: int = 1000, 
        chunk_overlap: int = 200
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """将文档内容分块
        
        Args:
            content: 文档内容
            mime_type: MIME类型
            chunk_size: 分块大小
            chunk_overlap: 分块重叠
            
        Returns:
            List[Tuple[str, Dict[str, Any]]]: 分块列表，每个元素为(内容, 元数据)
        """
        try:
            chunks = []
            
            # 对于文本文件，按段落优先分块
            if mime_type.startswith("text/"):
                paragraphs = content.split("\n\n")
                current_chunk = ""
                current_position = 0
                
                for para in paragraphs:
                    if len(current_chunk) + len(para) <= chunk_size:
                        current_chunk += para + "\n\n"
                    else:
                        # 添加当前分块
                        if current_chunk:
                            chunks.append((
                                current_chunk.strip(),
                                {"position": current_position, "type": "paragraph"}
                            ))
                            current_position += 1
                        
                        # 处理超长段落
                        if len(para) > chunk_size:
                            for i in range(0, len(para), chunk_size - chunk_overlap):
                                sub_chunk = para[i:i + chunk_size]
                                chunks.append((
                                    sub_chunk.strip(),
                                    {"position": current_position, "type": "paragraph_segment"}
                                ))
                                current_position += 1
                        else:
                            current_chunk = para + "\n\n"
                
                # 添加最后一个分块
                if current_chunk:
                    chunks.append((
                        current_chunk.strip(),
                        {"position": current_position, "type": "paragraph"}
                    ))
            else:
                # 其他文档类型使用简单重叠分块
                for i in range(0, len(content), chunk_size - chunk_overlap):
                    chunk_content = content[i:i + chunk_size]
                    if chunk_content.strip():
                        chunks.append((
                            chunk_content.strip(),
                            {"position": i // (chunk_size - chunk_overlap), "type": "segment"}
                        ))
            
            return chunks
            
        except Exception as e:
            logger.error(f"文档分块失败: {str(e)}")
            return []
