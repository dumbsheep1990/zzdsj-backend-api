"""
数据同步服务
确保PostgreSQL、Elasticsearch、Milvus间的数据一致性，提供增量同步和全量同步功能
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib

logger = logging.getLogger(__name__)


class SyncOperation(str, Enum):
    """同步操作类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    REINDEX = "reindex"


class SyncStatus(str, Enum):
    """同步状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class SyncRecord:
    """同步记录"""
    id: str
    operation: SyncOperation
    source_table: str
    target_engines: List[str]
    data_id: str
    data_hash: str
    status: SyncStatus = SyncStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncStats:
    """同步统计"""
    total_records: int = 0
    success_count: int = 0
    failed_count: int = 0
    pending_count: int = 0
    sync_duration: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_records == 0:
            return 0.0
        return self.success_count / self.total_records


class DataSyncService:
    """数据同步服务"""
    
    def __init__(self):
        """初始化数据同步服务"""
        self._sync_queue: List[SyncRecord] = []
        self._is_running = False
        self._max_retry_count = 3
        self._batch_size = 100
        self._sync_interval = 30  # 秒
        self._last_sync_time = datetime.now()
        self._sync_stats = SyncStats()
        
    async def start_sync_daemon(self):
        """启动同步守护进程"""
        if self._is_running:
            logger.warning("同步守护进程已在运行")
            return
        
        self._is_running = True
        logger.info("启动数据同步守护进程")
        
        try:
            while self._is_running:
                await self._process_sync_queue()
                await asyncio.sleep(self._sync_interval)
                
        except Exception as e:
            logger.error(f"同步守护进程异常: {str(e)}")
        finally:
            self._is_running = False
            logger.info("同步守护进程已停止")
    
    def stop_sync_daemon(self):
        """停止同步守护进程"""
        self._is_running = False
        logger.info("正在停止同步守护进程...")
    
    async def sync_document_chunk(
        self, 
        chunk_id: str, 
        operation: SyncOperation,
        target_engines: Optional[List[str]] = None
    ) -> bool:
        """
        同步文档块数据
        
        Args:
            chunk_id: 文档块ID
            operation: 同步操作类型
            target_engines: 目标引擎列表，None表示同步到所有引擎
            
        Returns:
            是否成功添加到同步队列
        """
        try:
            # 获取文档块数据
            chunk_data = await self._get_chunk_data(chunk_id)
            if not chunk_data:
                logger.error(f"未找到文档块数据: {chunk_id}")
                return False
            
            # 计算数据哈希
            data_hash = self._calculate_data_hash(chunk_data)
            
            # 确定目标引擎
            if target_engines is None:
                target_engines = await self._get_available_engines()
            
            # 创建同步记录
            sync_record = SyncRecord(
                id=f"{chunk_id}_{operation.value}_{datetime.now().timestamp()}",
                operation=operation,
                source_table="document_chunks",
                target_engines=target_engines,
                data_id=chunk_id,
                data_hash=data_hash,
                metadata={"chunk_data": chunk_data}
            )
            
            # 添加到队列
            self._sync_queue.append(sync_record)
            logger.info(f"已添加同步任务: {sync_record.id}")
            
            return True
            
        except Exception as e:
            logger.error(f"添加同步任务失败: {str(e)}")
            return False
    
    async def sync_knowledge_base(
        self, 
        kb_id: str, 
        operation: SyncOperation,
        include_documents: bool = True
    ) -> bool:
        """
        同步知识库数据
        
        Args:
            kb_id: 知识库ID
            operation: 同步操作类型
            include_documents: 是否包含文档数据
            
        Returns:
            是否成功
        """
        try:
            if operation == SyncOperation.DELETE:
                # 删除操作需要级联删除所有相关数据
                return await self._cascade_delete_knowledge_base(kb_id)
            
            # 同步知识库元数据
            kb_success = await self.sync_document_chunk(
                kb_id, operation, ["elasticsearch"]
            )
            
            if not kb_success:
                return False
            
            # 如果需要，同步相关文档
            if include_documents:
                documents = await self._get_knowledge_base_documents(kb_id)
                for doc_id in documents:
                    await self._sync_document_and_chunks(doc_id, operation)
            
            return True
            
        except Exception as e:
            logger.error(f"同步知识库失败: {str(e)}")
            return False
    
    async def _sync_document_and_chunks(self, doc_id: str, operation: SyncOperation):
        """同步文档及其所有块"""
        try:
            # 获取文档的所有块
            chunks = await self._get_document_chunks(doc_id)
            
            # 批量同步块
            sync_tasks = [
                self.sync_document_chunk(chunk_id, operation)
                for chunk_id in chunks
            ]
            
            results = await asyncio.gather(*sync_tasks, return_exceptions=True)
            
            success_count = sum(1 for r in results if r is True)
            logger.info(f"文档 {doc_id} 同步完成: {success_count}/{len(chunks)} 个块成功")
            
        except Exception as e:
            logger.error(f"同步文档块失败: {str(e)}")
    
    async def _process_sync_queue(self):
        """处理同步队列"""
        if not self._sync_queue:
            return
        
        logger.info(f"开始处理同步队列，待处理: {len(self._sync_queue)} 个任务")
        
        # 按批次处理
        batch_start = 0
        while batch_start < len(self._sync_queue):
            batch_end = min(batch_start + self._batch_size, len(self._sync_queue))
            batch = self._sync_queue[batch_start:batch_end]
            
            # 并发处理批次
            tasks = [self._process_sync_record(record) for record in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            processed_records = []
            for i, result in enumerate(results):
                record = batch[i]
                if isinstance(result, Exception):
                    logger.error(f"同步记录处理异常: {record.id}, {str(result)}")
                    record.status = SyncStatus.FAILED
                    record.error_message = str(result)
                else:
                    if result:
                        record.status = SyncStatus.SUCCESS
                        processed_records.append(record)
                    else:
                        record.status = SyncStatus.FAILED
                
                record.updated_at = datetime.now()
            
            # 移除已处理的记录
            for record in processed_records:
                if record in self._sync_queue:
                    self._sync_queue.remove(record)
            
            batch_start = batch_end
        
        # 重试失败的记录
        await self._retry_failed_records()
        
        logger.info(f"同步队列处理完成，剩余: {len(self._sync_queue)} 个任务")
    
    async def _process_sync_record(self, record: SyncRecord) -> bool:
        """处理单个同步记录"""
        try:
            record.status = SyncStatus.RUNNING
            
            # 根据操作类型执行同步
            if record.operation == SyncOperation.CREATE:
                return await self._sync_create(record)
            elif record.operation == SyncOperation.UPDATE:
                return await self._sync_update(record)
            elif record.operation == SyncOperation.DELETE:
                return await self._sync_delete(record)
            elif record.operation == SyncOperation.REINDEX:
                return await self._sync_reindex(record)
            else:
                logger.error(f"未知的同步操作: {record.operation}")
                return False
                
        except Exception as e:
            logger.error(f"处理同步记录失败: {record.id}, {str(e)}")
            record.error_message = str(e)
            return False
    
    async def _sync_create(self, record: SyncRecord) -> bool:
        """执行创建同步"""
        try:
            chunk_data = record.metadata.get("chunk_data")
            if not chunk_data:
                logger.error(f"缺少文档块数据: {record.id}")
                return False
            
            success_count = 0
            
            # 同步到各个引擎
            for engine in record.target_engines:
                try:
                    if engine == "elasticsearch":
                        success = await self._sync_to_elasticsearch(chunk_data, "create")
                    elif engine == "milvus":
                        success = await self._sync_to_milvus(chunk_data, "create")
                    else:
                        logger.warning(f"不支持的引擎: {engine}")
                        continue
                    
                    if success:
                        success_count += 1
                        
                except Exception as e:
                    logger.error(f"同步到 {engine} 失败: {str(e)}")
            
            # 至少有一个引擎同步成功才算成功
            return success_count > 0
            
        except Exception as e:
            logger.error(f"创建同步失败: {str(e)}")
            return False
    
    async def _sync_update(self, record: SyncRecord) -> bool:
        """执行更新同步"""
        try:
            chunk_data = record.metadata.get("chunk_data")
            if not chunk_data:
                return False
            
            success_count = 0
            
            for engine in record.target_engines:
                try:
                    if engine == "elasticsearch":
                        success = await self._sync_to_elasticsearch(chunk_data, "update")
                    elif engine == "milvus":
                        success = await self._sync_to_milvus(chunk_data, "update")
                    else:
                        continue
                    
                    if success:
                        success_count += 1
                        
                except Exception as e:
                    logger.error(f"更新同步到 {engine} 失败: {str(e)}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"更新同步失败: {str(e)}")
            return False
    
    async def _sync_delete(self, record: SyncRecord) -> bool:
        """执行删除同步"""
        try:
            success_count = 0
            
            for engine in record.target_engines:
                try:
                    if engine == "elasticsearch":
                        success = await self._delete_from_elasticsearch(record.data_id)
                    elif engine == "milvus":
                        success = await self._delete_from_milvus(record.data_id)
                    else:
                        continue
                    
                    if success:
                        success_count += 1
                        
                except Exception as e:
                    logger.error(f"从 {engine} 删除失败: {str(e)}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"删除同步失败: {str(e)}")
            return False
    
    async def _sync_reindex(self, record: SyncRecord) -> bool:
        """执行重新索引"""
        try:
            # 重新索引通常需要先删除再创建
            delete_success = await self._sync_delete(record)
            if delete_success:
                # 短暂延迟以确保删除完成
                await asyncio.sleep(1)
                return await self._sync_create(record)
            return False
            
        except Exception as e:
            logger.error(f"重新索引失败: {str(e)}")
            return False
    
    async def _sync_to_elasticsearch(self, chunk_data: Dict[str, Any], action: str) -> bool:
        """同步数据到Elasticsearch"""
        try:
            logger.info(f"同步到Elasticsearch: {action}, chunk_id: {chunk_data.get('id')}")
            
            # 模拟ES同步逻辑
            es_doc = {
                "id": chunk_data.get("id"),
                "content": chunk_data.get("content", ""),
                "metadata": chunk_data.get("metadata", {}),
                "embedding": chunk_data.get("embedding"),
                "knowledge_base_id": chunk_data.get("knowledge_base_id"),
                "document_id": chunk_data.get("document_id"),
                "created_at": chunk_data.get("created_at"),
                "updated_at": datetime.now().isoformat()
            }
            
            # 实际应该调用ES的索引API
            return True
            
        except Exception as e:
            logger.error(f"同步到Elasticsearch失败: {str(e)}")
            return False
    
    async def _sync_to_milvus(self, chunk_data: Dict[str, Any], action: str) -> bool:
        """同步数据到Milvus"""
        try:
            logger.info(f"同步到Milvus: {action}, chunk_id: {chunk_data.get('id')}")
            
            if not chunk_data.get("embedding"):
                logger.warning(f"文档块缺少向量数据: {chunk_data.get('id')}")
                return False
            
            # 模拟Milvus同步逻辑
            milvus_entity = {
                "id": chunk_data.get("id"),
                "vector": chunk_data.get("embedding"),
                "metadata": json.dumps(chunk_data.get("metadata", {}))
            }
            
            # 实际应该调用Milvus的插入API
            return True
            
        except Exception as e:
            logger.error(f"同步到Milvus失败: {str(e)}")
            return False
    
    async def _delete_from_elasticsearch(self, doc_id: str) -> bool:
        """从Elasticsearch删除文档"""
        try:
            logger.info(f"从Elasticsearch删除: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"从Elasticsearch删除失败: {str(e)}")
            return False
    
    async def _delete_from_milvus(self, doc_id: str) -> bool:
        """从Milvus删除向量"""
        try:
            logger.info(f"从Milvus删除: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"从Milvus删除失败: {str(e)}")
            return False
    
    async def _retry_failed_records(self):
        """重试失败的记录"""
        failed_records = [
            record for record in self._sync_queue 
            if record.status == SyncStatus.FAILED and record.retry_count < self._max_retry_count
        ]
        
        if not failed_records:
            return
        
        logger.info(f"重试 {len(failed_records)} 个失败的同步记录")
        
        for record in failed_records:
            # 指数退避重试
            wait_time = 2 ** record.retry_count
            await asyncio.sleep(wait_time)
            
            record.retry_count += 1
            record.status = SyncStatus.PENDING
            record.error_message = None
            
            logger.info(f"重试同步记录: {record.id} (第 {record.retry_count} 次)")
    
    async def _get_chunk_data(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """从数据库获取文档块数据"""
        try:
            # 模拟实现，返回模拟数据
            return {
                "id": chunk_id,
                "content": f"Mock content for chunk {chunk_id}",
                "metadata": {"mock": True},
                "embedding": [0.1] * 768,  # 模拟向量
                "knowledge_base_id": "kb_001",
                "document_id": "doc_001",
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取文档块数据失败: {str(e)}")
            return None
    
    async def _get_available_engines(self) -> List[str]:
        """获取可用的搜索引擎列表"""
        try:
            engines = []
            
            # 检查Elasticsearch
            try:
                from app.utils.storage.detection import check_elasticsearch
                if check_elasticsearch():
                    engines.append("elasticsearch")
            except (ImportError, AttributeError):
                pass
            
            # 检查Milvus
            try:
                from app.utils.storage.detection import check_milvus
                if check_milvus():
                    engines.append("milvus")
            except (ImportError, AttributeError):
                pass
            
            return engines
            
        except Exception as e:
            logger.error(f"获取可用引擎失败: {str(e)}")
            return []
    
    async def _get_knowledge_base_documents(self, kb_id: str) -> List[str]:
        """获取知识库的所有文档ID"""
        try:
            # 模拟实现，实际应该查询数据库
            return [f"doc_{i}" for i in range(1, 6)]  # 返回5个模拟文档ID
            
        except Exception as e:
            logger.error(f"获取知识库文档失败: {str(e)}")
            return []
    
    async def _get_document_chunks(self, doc_id: str) -> List[str]:
        """获取文档的所有块ID"""
        try:
            # 模拟实现
            return [f"{doc_id}_chunk_{i}" for i in range(1, 11)]  # 返回10个模拟块ID
            
        except Exception as e:
            logger.error(f"获取文档块失败: {str(e)}")
            return []
    
    async def _cascade_delete_knowledge_base(self, kb_id: str) -> bool:
        """级联删除知识库及相关数据"""
        try:
            # 获取所有相关文档
            documents = await self._get_knowledge_base_documents(kb_id)
            
            # 删除所有文档块
            for doc_id in documents:
                chunks = await self._get_document_chunks(doc_id)
                for chunk_id in chunks:
                    await self.sync_document_chunk(chunk_id, SyncOperation.DELETE)
            
            logger.info(f"已安排删除知识库 {kb_id} 的所有相关数据")
            return True
            
        except Exception as e:
            logger.error(f"级联删除知识库失败: {str(e)}")
            return False
    
    def _calculate_data_hash(self, data: Dict[str, Any]) -> str:
        """计算数据哈希值"""
        try:
            # 移除时间戳等变化字段
            stable_data = {k: v for k, v in data.items() if k not in ["created_at", "updated_at"]}
            data_str = json.dumps(stable_data, sort_keys=True)
            return hashlib.md5(data_str.encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"计算数据哈希失败: {str(e)}")
            return ""
    
    def get_sync_stats(self) -> SyncStats:
        """获取同步统计信息"""
        try:
            stats = SyncStats()
            stats.total_records = len(self._sync_queue)
            
            for record in self._sync_queue:
                if record.status == SyncStatus.SUCCESS:
                    stats.success_count += 1
                elif record.status == SyncStatus.FAILED:
                    stats.failed_count += 1
                elif record.status == SyncStatus.PENDING:
                    stats.pending_count += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"获取同步统计失败: {str(e)}")
            return SyncStats()
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        try:
            return {
                "queue_size": len(self._sync_queue),
                "is_running": self._is_running,
                "last_sync_time": self._last_sync_time.isoformat(),
                "sync_interval": self._sync_interval,
                "batch_size": self._batch_size,
                "max_retry_count": self._max_retry_count
            }
            
        except Exception as e:
            logger.error(f"获取队列状态失败: {str(e)}")
            return {"error": str(e)}


# 全局数据同步服务实例
_sync_service: Optional[DataSyncService] = None


def get_data_sync_service() -> DataSyncService:
    """获取数据同步服务实例"""
    global _sync_service
    if _sync_service is None:
        _sync_service = DataSyncService()
    return _sync_service


async def sync_chunk_to_engines(chunk_id: str, operation: SyncOperation = SyncOperation.CREATE) -> bool:
    """便捷函数：同步文档块到所有引擎"""
    service = get_data_sync_service()
    return await service.sync_document_chunk(chunk_id, operation) 