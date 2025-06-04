#!/usr/bin/env python3
"""
知识库文档集成示例
展示如何在现有的知识库系统中使用新的文档管理器
实现统一的文件ID管理和关联删除功能
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import UploadFile, HTTPException
from datetime import datetime

from document_manager import get_document_manager, DocumentManager

logger = logging.getLogger(__name__)

class KnowledgeDocumentService:
    """知识库文档服务"""
    
    def __init__(self):
        self.doc_manager = get_document_manager()
    
    async def upload_knowledge_document(self,
                                      file: UploadFile,
                                      kb_id: str,
                                      title: str = None,
                                      category: str = None,
                                      tags: List[str] = None,
                                      auto_vectorize: bool = True) -> Dict[str, Any]:
        """
        上传知识库文档
        
        Args:
            file: 上传的文件
            kb_id: 知识库ID
            title: 文档标题
            category: 文档分类
            tags: 文档标签
            auto_vectorize: 是否自动向量化
            
        Returns:
            Dict[str, Any]: 上传结果
        """
        try:
            # 准备文档元数据
            metadata = {
                "title": title or file.filename,
                "category": category or "general",
                "tags": tags or [],
                "auto_vectorize": auto_vectorize,
                "uploaded_at": datetime.now().isoformat()
            }
            
            # 使用文档管理器上传文件
            upload_result = await self.doc_manager.upload_document(
                file=file,
                kb_id=kb_id,
                metadata=metadata
            )
            
            if not upload_result["success"]:
                raise HTTPException(status_code=400, detail="文档上传失败")
            
            file_id = upload_result["file_id"]
            
            # 如果需要自动向量化，启动向量化任务
            if auto_vectorize and not upload_result.get("exists", False):
                await self._start_vectorization_task(file_id, kb_id, metadata)
            
            return {
                "success": True,
                "file_id": file_id,
                "filename": upload_result["filename"],
                "title": metadata["title"],
                "category": metadata["category"],
                "file_size": upload_result["file_size"],
                "exists": upload_result.get("exists", False),
                "message": "知识库文档上传成功"
            }
            
        except Exception as e:
            logger.error(f"知识库文档上传失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"知识库文档上传失败: {str(e)}")
    
    async def batch_upload_knowledge_documents(self,
                                             files: List[UploadFile],
                                             kb_id: str,
                                             default_category: str = "batch_upload",
                                             auto_vectorize: bool = True) -> Dict[str, Any]:
        """
        批量上传知识库文档
        
        Args:
            files: 文件列表
            kb_id: 知识库ID
            default_category: 默认分类
            auto_vectorize: 是否自动向量化
            
        Returns:
            Dict[str, Any]: 批量上传结果
        """
        try:
            # 准备文件列表
            file_items = []
            for file in files:
                file_items.append({
                    "file": file,
                    "filename": file.filename,
                    "metadata": {
                        "title": file.filename,
                        "category": default_category,
                        "auto_vectorize": auto_vectorize,
                        "uploaded_at": datetime.now().isoformat()
                    }
                })
            
            # 使用文档管理器批量上传
            batch_result = await self.doc_manager.batch_upload_documents(
                files=file_items,
                kb_id=kb_id
            )
            
            # 为成功上传的文档启动向量化任务
            if auto_vectorize:
                vectorization_tasks = []
                for result in batch_result["results"]:
                    if result["status"] == "success" and not result["result"].get("exists", False):
                        file_id = result["result"]["file_id"]
                        vectorization_tasks.append(
                            self._start_vectorization_task(file_id, kb_id, {})
                        )
                
                # 异步启动所有向量化任务
                if vectorization_tasks:
                    import asyncio
                    await asyncio.gather(*vectorization_tasks, return_exceptions=True)
            
            return {
                "success": batch_result["success"],
                "total_files": batch_result["total_files"],
                "success_count": batch_result["success_count"],
                "error_count": batch_result["error_count"],
                "results": batch_result["results"],
                "message": f"批量上传完成: 成功{batch_result['success_count']}个，失败{batch_result['error_count']}个"
            }
            
        except Exception as e:
            logger.error(f"批量上传知识库文档失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"批量上传失败: {str(e)}")
    
    async def delete_knowledge_document(self,
                                      file_id: str,
                                      kb_id: str = None,
                                      force: bool = False) -> Dict[str, Any]:
        """
        删除知识库文档（关联删除）
        
        Args:
            file_id: 文件ID
            kb_id: 知识库ID（可选，用于验证）
            force: 是否强制删除
            
        Returns:
            Dict[str, Any]: 删除结果
        """
        try:
            # 验证文档是否属于指定知识库
            if kb_id:
                doc_info = self.doc_manager.get_document_info(file_id)
                if not doc_info or doc_info.get("kb_id") != kb_id:
                    raise HTTPException(status_code=404, detail="文档不存在或不属于指定知识库")
            
            # 使用文档管理器删除文档
            delete_result = await self.doc_manager.delete_document(file_id, force=force)
            
            return {
                "success": delete_result["success"],
                "file_id": file_id,
                "filename": delete_result.get("filename"),
                "deletion_details": delete_result.get("deletion_results", {}),
                "message": delete_result["message"]
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"删除知识库文档失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"删除知识库文档失败: {str(e)}")
    
    def list_knowledge_documents(self,
                                kb_id: str,
                                category: str = None,
                                limit: int = 50,
                                offset: int = 0) -> Dict[str, Any]:
        """
        列出知识库文档
        
        Args:
            kb_id: 知识库ID
            category: 文档分类过滤
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            Dict[str, Any]: 文档列表
        """
        try:
            # 获取文档列表
            result = self.doc_manager.list_documents(kb_id, limit, offset)
            
            if not result["success"]:
                return result
            
            # 如果指定了分类，进行过滤
            documents = result["documents"]
            if category:
                filtered_docs = []
                for doc in documents:
                    try:
                        import json
                        metadata = json.loads(doc.get("metadata", "{}"))
                        if metadata.get("category") == category:
                            filtered_docs.append(doc)
                    except:
                        # 如果解析失败，跳过该文档
                        continue
                documents = filtered_docs
            
            # 格式化文档信息
            formatted_docs = []
            for doc in documents:
                try:
                    import json
                    metadata = json.loads(doc.get("metadata", "{}"))
                    
                    formatted_docs.append({
                        "file_id": doc["file_id"],
                        "filename": doc["filename"],
                        "title": metadata.get("title", doc["filename"]),
                        "category": metadata.get("category", "general"),
                        "tags": metadata.get("tags", []),
                        "file_size": doc["file_size"],
                        "upload_time": doc["upload_time"],
                        "status": doc["status"],
                        "storage_backend": doc["storage_backend"]
                    })
                except:
                    # 如果解析失败，使用基本信息
                    formatted_docs.append({
                        "file_id": doc["file_id"],
                        "filename": doc["filename"],
                        "title": doc["filename"],
                        "category": "unknown",
                        "tags": [],
                        "file_size": doc["file_size"],
                        "upload_time": doc["upload_time"],
                        "status": doc["status"],
                        "storage_backend": doc["storage_backend"]
                    })
            
            return {
                "success": True,
                "documents": formatted_docs,
                "total": len(formatted_docs) if category else result["total"],
                "limit": limit,
                "offset": offset,
                "kb_id": kb_id,
                "category_filter": category
            }
            
        except Exception as e:
            logger.error(f"列出知识库文档失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "documents": [],
                "total": 0
            }
    
    def get_knowledge_document_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        获取知识库文档详细信息
        
        Args:
            file_id: 文件ID
            
        Returns:
            Optional[Dict[str, Any]]: 文档信息
        """
        try:
            doc_info = self.doc_manager.get_document_info(file_id)
            
            if not doc_info:
                return None
            
            # 解析元数据
            try:
                import json
                metadata = json.loads(doc_info.get("metadata", "{}"))
            except:
                metadata = {}
            
            return {
                "file_id": doc_info["file_id"],
                "filename": doc_info["filename"],
                "title": metadata.get("title", doc_info["filename"]),
                "category": metadata.get("category", "general"),
                "tags": metadata.get("tags", []),
                "content_type": doc_info["content_type"],
                "file_size": doc_info["file_size"],
                "file_hash": doc_info["file_hash"],
                "storage_backend": doc_info["storage_backend"],
                "storage_path": doc_info["storage_path"],
                "upload_time": doc_info["upload_time"],
                "kb_id": doc_info["kb_id"],
                "doc_id": doc_info["doc_id"],
                "status": doc_info["status"],
                "auto_vectorize": metadata.get("auto_vectorize", False),
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"获取知识库文档信息失败: {str(e)}")
            return None
    
    async def _start_vectorization_task(self,
                                       file_id: str,
                                       kb_id: str,
                                       metadata: Dict[str, Any]):
        """
        启动文档向量化任务
        
        Args:
            file_id: 文件ID
            kb_id: 知识库ID
            metadata: 文档元数据
        """
        try:
            # TODO: 这里应该调用实际的向量化服务
            # 例如：
            # 1. 从MinIO下载文件内容
            # 2. 进行文本提取和分块
            # 3. 生成向量嵌入
            # 4. 存储到向量数据库
            # 5. 注册向量关联关系
            
            logger.info(f"开始为文档{file_id}启动向量化任务")
            
            # 模拟向量化过程
            vector_ids = [f"vec_{file_id}_{i}" for i in range(3)]  # 假设分成3个向量
            collection = f"kb_{kb_id}"
            
            # 注册向量关联
            for i, vector_id in enumerate(vector_ids):
                chunk_id = f"chunk_{file_id}_{i}"
                self.doc_manager.register_vector_data(
                    file_id=file_id,
                    vector_id=vector_id,
                    chunk_id=chunk_id,
                    collection=collection
                )
            
            logger.info(f"文档{file_id}向量化完成，生成{len(vector_ids)}个向量")
            
        except Exception as e:
            logger.error(f"文档{file_id}向量化失败: {str(e)}")

# 全局服务实例
_knowledge_document_service = None

def get_knowledge_document_service() -> KnowledgeDocumentService:
    """获取知识库文档服务实例"""
    global _knowledge_document_service
    if _knowledge_document_service is None:
        _knowledge_document_service = KnowledgeDocumentService()
    return _knowledge_document_service

# FastAPI 路由示例
from fastapi import APIRouter, File, Form, Depends
from typing import List

router = APIRouter(prefix="/api/knowledge", tags=["knowledge_documents"])

@router.post("/{kb_id}/documents/upload")
async def upload_knowledge_document(
    kb_id: str,
    file: UploadFile = File(...),
    title: str = Form(None),
    category: str = Form("general"),
    tags: str = Form("[]"),  # JSON字符串
    auto_vectorize: bool = Form(True),
    service: KnowledgeDocumentService = Depends(get_knowledge_document_service)
):
    """上传知识库文档"""
    try:
        import json
        tags_list = json.loads(tags) if tags else []
    except:
        tags_list = []
    
    result = await service.upload_knowledge_document(
        file=file,
        kb_id=kb_id,
        title=title,
        category=category,
        tags=tags_list,
        auto_vectorize=auto_vectorize
    )
    
    return result

@router.post("/{kb_id}/documents/batch-upload")
async def batch_upload_knowledge_documents(
    kb_id: str,
    files: List[UploadFile] = File(...),
    category: str = Form("batch_upload"),
    auto_vectorize: bool = Form(True),
    service: KnowledgeDocumentService = Depends(get_knowledge_document_service)
):
    """批量上传知识库文档"""
    result = await service.batch_upload_knowledge_documents(
        files=files,
        kb_id=kb_id,
        default_category=category,
        auto_vectorize=auto_vectorize
    )
    
    return result

@router.delete("/{kb_id}/documents/{file_id}")
async def delete_knowledge_document(
    kb_id: str,
    file_id: str,
    force: bool = False,
    service: KnowledgeDocumentService = Depends(get_knowledge_document_service)
):
    """删除知识库文档"""
    result = await service.delete_knowledge_document(
        file_id=file_id,
        kb_id=kb_id,
        force=force
    )
    
    return result

@router.get("/{kb_id}/documents")
async def list_knowledge_documents(
    kb_id: str,
    category: str = None,
    limit: int = 50,
    offset: int = 0,
    service: KnowledgeDocumentService = Depends(get_knowledge_document_service)
):
    """列出知识库文档"""
    result = service.list_knowledge_documents(
        kb_id=kb_id,
        category=category,
        limit=limit,
        offset=offset
    )
    
    return result

@router.get("/{kb_id}/documents/{file_id}")
async def get_knowledge_document_info(
    kb_id: str,
    file_id: str,
    service: KnowledgeDocumentService = Depends(get_knowledge_document_service)
):
    """获取知识库文档详细信息"""
    result = service.get_knowledge_document_info(file_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 验证文档是否属于指定知识库
    if result.get("kb_id") != kb_id:
        raise HTTPException(status_code=404, detail="文档不属于指定知识库")
    
    return result 