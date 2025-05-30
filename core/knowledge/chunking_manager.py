"""
分块管理器 - 核心业务逻辑
提供文档分块的策略和管理功能
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

# 导入数据访问层
from app.repositories.knowledge import DocumentChunkRepository

logger = logging.getLogger(__name__)


class ChunkingManager:
    """分块管理器 - 核心业务逻辑类"""
    
    def __init__(self, db: Session):
        """初始化分块管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.chunk_repository = DocumentChunkRepository(db)
        
    # ============ 分块管理方法 ============
    
    async def get_document_chunks(
        self,
        doc_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """获取文档的分块列表
        
        Args:
            doc_id: 文档ID
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 获取分块列表
            chunks = await self.chunk_repository.list_by_document(doc_id, skip, limit)
            total = await self.chunk_repository.count_by_document(doc_id)
            
            # 转换为标准格式
            chunk_list = []
            for chunk in chunks:
                chunk_data = {
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "kb_id": chunk.kb_id,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "created_at": chunk.created_at
                }
                chunk_list.append(chunk_data)
            
            return {
                "success": True,
                "data": {
                    "chunks": chunk_list,
                    "total": total,
                    "skip": skip,
                    "limit": limit
                }
            }
            
        except Exception as e:
            logger.error(f"获取文档分块失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取文档分块失败: {str(e)}",
                "error_code": "GET_CHUNKS_FAILED"
            }
    
    async def get_knowledge_base_chunks(
        self,
        kb_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """获取知识库的所有分块
        
        Args:
            kb_id: 知识库ID
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 获取分块列表
            chunks = await self.chunk_repository.list_by_kb(kb_id, skip, limit)
            total = await self.chunk_repository.count_by_kb(kb_id)
            
            # 转换为标准格式
            chunk_list = []
            for chunk in chunks:
                chunk_data = {
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "kb_id": chunk.kb_id,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "created_at": chunk.created_at
                }
                chunk_list.append(chunk_data)
            
            return {
                "success": True,
                "data": {
                    "chunks": chunk_list,
                    "total": total,
                    "skip": skip,
                    "limit": limit
                }
            }
            
        except Exception as e:
            logger.error(f"获取知识库分块失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取知识库分块失败: {str(e)}",
                "error_code": "GET_KB_CHUNKS_FAILED"
            }
    
    async def get_chunk(self, chunk_id: str) -> Dict[str, Any]:
        """获取单个分块详情
        
        Args:
            chunk_id: 分块ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            chunk = await self.chunk_repository.get_by_id(chunk_id)
            if not chunk:
                return {
                    "success": False,
                    "error": "分块不存在",
                    "error_code": "CHUNK_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": {
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "kb_id": chunk.kb_id,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "created_at": chunk.created_at
                }
            }
            
        except Exception as e:
            logger.error(f"获取分块失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取分块失败: {str(e)}",
                "error_code": "GET_CHUNK_FAILED"
            }
    
    async def update_chunk_metadata(
        self,
        chunk_id: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新分块元数据
        
        Args:
            chunk_id: 分块ID
            metadata: 新的元数据
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查分块是否存在
            chunk = await self.chunk_repository.get_by_id(chunk_id)
            if not chunk:
                return {
                    "success": False,
                    "error": "分块不存在",
                    "error_code": "CHUNK_NOT_FOUND"
                }
            
            # 更新元数据
            updated_chunk = await self.chunk_repository.update(chunk_id, {"metadata": metadata})
            
            logger.info(f"分块元数据更新成功: {chunk_id}")
            
            return {
                "success": True,
                "data": {
                    "id": updated_chunk.id,
                    "document_id": updated_chunk.document_id,
                    "kb_id": updated_chunk.kb_id,
                    "content": updated_chunk.content,
                    "metadata": updated_chunk.metadata,
                    "created_at": updated_chunk.created_at
                }
            }
            
        except Exception as e:
            logger.error(f"更新分块元数据失败: {str(e)}")
            return {
                "success": False,
                "error": f"更新分块元数据失败: {str(e)}",
                "error_code": "UPDATE_METADATA_FAILED"
            }
    
    async def delete_chunk(self, chunk_id: str) -> Dict[str, Any]:
        """删除分块
        
        Args:
            chunk_id: 分块ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查分块是否存在
            chunk = await self.chunk_repository.get_by_id(chunk_id)
            if not chunk:
                return {
                    "success": False,
                    "error": "分块不存在",
                    "error_code": "CHUNK_NOT_FOUND"
                }
            
            # 删除分块
            success = await self.chunk_repository.delete(chunk_id)
            
            if success:
                logger.info(f"分块删除成功: {chunk_id}")
                return {
                    "success": True,
                    "data": {"deleted_chunk_id": chunk_id}
                }
            else:
                return {
                    "success": False,
                    "error": "删除分块失败",
                    "error_code": "DELETE_FAILED"
                }
            
        except Exception as e:
            logger.error(f"删除分块失败: {str(e)}")
            return {
                "success": False,
                "error": f"删除分块失败: {str(e)}",
                "error_code": "DELETE_FAILED"
            }
    
    # ============ 分块策略方法 ============
    
    def get_chunking_strategies(self) -> Dict[str, Any]:
        """获取可用的分块策略
        
        Returns:
            Dict[str, Any]: 分块策略列表
        """
        strategies = {
            "paragraph": {
                "name": "段落分块",
                "description": "按段落进行分块，适合结构化文档",
                "parameters": {
                    "chunk_size": {"type": "int", "default": 1000, "min": 100, "max": 4000},
                    "chunk_overlap": {"type": "int", "default": 200, "min": 0, "max": 500}
                }
            },
            "sentence": {
                "name": "句子分块",
                "description": "按句子进行分块，保持语义完整性",
                "parameters": {
                    "chunk_size": {"type": "int", "default": 800, "min": 100, "max": 2000},
                    "chunk_overlap": {"type": "int", "default": 100, "min": 0, "max": 300}
                }
            },
            "fixed": {
                "name": "固定长度分块",
                "description": "按固定字符数分块，简单高效",
                "parameters": {
                    "chunk_size": {"type": "int", "default": 1000, "min": 100, "max": 4000},
                    "chunk_overlap": {"type": "int", "default": 200, "min": 0, "max": 500}
                }
            },
            "semantic": {
                "name": "语义分块",
                "description": "基于语义相似度进行分块，保持主题一致性",
                "parameters": {
                    "similarity_threshold": {"type": "float", "default": 0.8, "min": 0.5, "max": 0.95},
                    "min_chunk_size": {"type": "int", "default": 200, "min": 50, "max": 1000},
                    "max_chunk_size": {"type": "int", "default": 2000, "min": 500, "max": 5000}
                }
            }
        }
        
        return {
            "success": True,
            "data": {"strategies": strategies}
        }
    
    def validate_chunking_config(self, strategy: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证分块配置
        
        Args:
            strategy: 分块策略
            parameters: 分块参数
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            strategies = self.get_chunking_strategies()["data"]["strategies"]
            
            if strategy not in strategies:
                return {
                    "success": False,
                    "error": f"不支持的分块策略: {strategy}",
                    "error_code": "INVALID_STRATEGY"
                }
            
            strategy_config = strategies[strategy]
            errors = []
            
            # 验证参数
            for param_name, param_config in strategy_config["parameters"].items():
                if param_name in parameters:
                    value = parameters[param_name]
                    param_type = param_config["type"]
                    
                    # 类型检查
                    if param_type == "int" and not isinstance(value, int):
                        errors.append(f"参数 {param_name} 必须是整数")
                    elif param_type == "float" and not isinstance(value, (int, float)):
                        errors.append(f"参数 {param_name} 必须是数字")
                    
                    # 范围检查
                    if "min" in param_config and value < param_config["min"]:
                        errors.append(f"参数 {param_name} 不能小于 {param_config['min']}")
                    if "max" in param_config and value > param_config["max"]:
                        errors.append(f"参数 {param_name} 不能大于 {param_config['max']}")
            
            if errors:
                return {
                    "success": False,
                    "error": "参数验证失败: " + "; ".join(errors),
                    "error_code": "INVALID_PARAMETERS"
                }
            
            return {
                "success": True,
                "data": {"validated": True}
            }
            
        except Exception as e:
            logger.error(f"验证分块配置失败: {str(e)}")
            return {
                "success": False,
                "error": f"验证分块配置失败: {str(e)}",
                "error_code": "VALIDATION_FAILED"
            }
    
    # ============ 统计方法 ============
    
    async def get_chunking_stats(self, kb_id: str = None, doc_id: str = None) -> Dict[str, Any]:
        """获取分块统计信息
        
        Args:
            kb_id: 知识库ID（可选）
            doc_id: 文档ID（可选）
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            stats = {}
            
            if doc_id:
                # 文档级别统计
                chunk_count = await self.chunk_repository.count_by_document(doc_id)
                chunks = await self.chunk_repository.list_by_document(doc_id)
                
                if chunks:
                    content_lengths = [len(chunk.content) for chunk in chunks]
                    stats = {
                        "document_id": doc_id,
                        "total_chunks": chunk_count,
                        "avg_chunk_length": sum(content_lengths) / len(content_lengths),
                        "min_chunk_length": min(content_lengths),
                        "max_chunk_length": max(content_lengths)
                    }
                else:
                    stats = {
                        "document_id": doc_id,
                        "total_chunks": 0,
                        "avg_chunk_length": 0,
                        "min_chunk_length": 0,
                        "max_chunk_length": 0
                    }
            
            elif kb_id:
                # 知识库级别统计
                chunk_count = await self.chunk_repository.count_by_kb(kb_id)
                chunks = await self.chunk_repository.list_by_kb(kb_id, 0, 1000)  # 取样本
                
                if chunks:
                    content_lengths = [len(chunk.content) for chunk in chunks]
                    stats = {
                        "kb_id": kb_id,
                        "total_chunks": chunk_count,
                        "avg_chunk_length": sum(content_lengths) / len(content_lengths),
                        "min_chunk_length": min(content_lengths),
                        "max_chunk_length": max(content_lengths)
                    }
                else:
                    stats = {
                        "kb_id": kb_id,
                        "total_chunks": 0,
                        "avg_chunk_length": 0,
                        "min_chunk_length": 0,
                        "max_chunk_length": 0
                    }
            
            return {
                "success": True,
                "data": stats
            }
            
        except Exception as e:
            logger.error(f"获取分块统计信息失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取分块统计信息失败: {str(e)}",
                "error_code": "STATS_FAILED"
            } 