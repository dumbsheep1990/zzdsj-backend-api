"""
数据同步服务
确保PostgreSQL、Elasticsearch和Milvus之间的数据一致性
"""

import asyncio
import logging
import hashlib
import json
import time
from typing import Dict, Any, List, Optional, Set, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import uuid

logger = logging.getLogger(__name__)


class SyncJobStatus(str, Enum):
    """同步任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class SyncConflictResolution(str, Enum):
    """同步冲突解决策略"""
    SOURCE_WINS = "source_wins"          # 源数据优先
    TARGET_WINS = "target_wins"          # 目标数据优先
    LATEST_WINS = "latest_wins"          # 最新数据优先
    MERGE = "merge"                      # 合并数据
    MANUAL = "manual"                    # 手动解决


class SyncOperation(str, Enum):
    """同步操作类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BULK_CREATE = "bulk_create"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"


@dataclass
class SyncJobConfig:
    """同步任务配置"""
    job_id: str
    source_engine: str
    target_engine: str
    operation: SyncOperation
    data_type: str  # document, chunk, embedding等
    
    # 同步选项
    batch_size: int = 100
    max_retries: int = 3
    retry_delay: float = 5.0
    timeout: int = 300
    
    # 冲突解决
    conflict_resolution: SyncConflictResolution = SyncConflictResolution.LATEST_WINS
    
    # 过滤条件
    filters: Dict[str, Any] = field(default_factory=dict)
    
    # 回调函数
    on_progress: Optional[Callable[[int, int], None]] = None
    on_complete: Optional[Callable[[bool, str], None]] = None
    on_error: Optional[Callable[[Exception], None]] = None


@dataclass
class SyncJobResult:
    """同步任务结果"""
    job_id: str
    status: SyncJobStatus
    start_time: float
    end_time: Optional[float] = None
    
    # 统计信息
    total_items: int = 0
    processed_items: int = 0
    success_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0
    
    # 错误信息
    errors: List[str] = field(default_factory=list)
    
    # 性能指标
    throughput_per_second: float = 0.0
    avg_processing_time: float = 0.0
    
    def duration(self) -> float:
        """获取执行时长"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    def success_rate(self) -> float:
        """获取成功率"""
        if self.total_items == 0:
            return 0.0
        return self.success_items / self.total_items


@dataclass
class DataRecord:
    """数据记录"""
    record_id: str
    data_type: str
    content: Dict[str, Any]
    hash_value: str
    timestamp: float
    source_engine: str
    
    @classmethod
    def create(cls, record_id: str, data_type: str, content: Dict[str, Any], source_engine: str) -> 'DataRecord':
        """创建数据记录"""
        # 计算内容哈希
        content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
        hash_value = hashlib.sha256(content_str.encode('utf-8')).hexdigest()
        
        return cls(
            record_id=record_id,
            data_type=data_type,
            content=content,
            hash_value=hash_value,
            timestamp=time.time(),
            source_engine=source_engine
        )


class DataSyncService:
    """数据同步服务"""
    
    def __init__(self):
        """初始化同步服务"""
        self.active_jobs: Dict[str, SyncJobConfig] = {}
        self.job_results: Dict[str, SyncJobResult] = {}
        self.sync_queue: asyncio.Queue = asyncio.Queue()
        
        # 数据状态追踪
        self.data_checksums: Dict[str, Dict[str, str]] = defaultdict(dict)  # engine -> record_id -> hash
        self.sync_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        
        # 配置参数
        self.max_concurrent_jobs = 5
        self.heartbeat_interval = 30
        self.cleanup_interval = 3600  # 1小时
        self.max_job_history = 1000
        
        # 引擎连接器
        self.connectors: Dict[str, Any] = {}
        
        # 内部状态
        self._running = False
        self._worker_tasks: List[asyncio.Task] = []
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """初始化同步服务"""
        try:
            # 初始化引擎连接器
            await self._initialize_connectors()
            
            # 启动工作线程
            self._running = True
            for i in range(self.max_concurrent_jobs):
                task = asyncio.create_task(self._sync_worker(f"worker-{i}"))
                self._worker_tasks.append(task)
            
            # 启动心跳任务
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # 启动清理任务
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            logger.info(f"数据同步服务初始化成功，启动 {self.max_concurrent_jobs} 个工作线程")
            
        except Exception as e:
            logger.error(f"数据同步服务初始化失败: {str(e)}")
            raise
    
    async def _initialize_connectors(self) -> None:
        """初始化引擎连接器"""
        try:
            # PostgreSQL连接器
            self.connectors['postgresql'] = await self._create_postgresql_connector()
            
            # Elasticsearch连接器
            self.connectors['elasticsearch'] = await self._create_elasticsearch_connector()
            
            # Milvus连接器
            self.connectors['milvus'] = await self._create_milvus_connector()
            
            logger.info("引擎连接器初始化完成")
            
        except Exception as e:
            logger.error(f"引擎连接器初始化失败: {str(e)}")
            raise
    
    async def _create_postgresql_connector(self) -> Dict[str, Any]:
        """创建PostgreSQL连接器"""
        try:
            from app.config import get_db
            from app.repositories.knowledge import DocumentChunkRepository
            
            # 这里应该创建实际的数据库连接
            return {
                'type': 'postgresql',
                'status': 'connected',
                'last_ping': time.time()
            }
        except Exception as e:
            logger.warning(f"PostgreSQL连接器创建失败: {str(e)}")
            return {'type': 'postgresql', 'status': 'error', 'error': str(e)}
    
    async def _create_elasticsearch_connector(self) -> Dict[str, Any]:
        """创建Elasticsearch连接器"""
        try:
            from app.utils.storage.elasticsearch_adapter import ElasticsearchVectorStore
            
            # 这里应该创建实际的ES连接
            return {
                'type': 'elasticsearch',
                'status': 'connected',
                'last_ping': time.time()
            }
        except Exception as e:
            logger.warning(f"Elasticsearch连接器创建失败: {str(e)}")
            return {'type': 'elasticsearch', 'status': 'error', 'error': str(e)}
    
    async def _create_milvus_connector(self) -> Dict[str, Any]:
        """创建Milvus连接器"""
        try:
            # 这里应该创建实际的Milvus连接
            return {
                'type': 'milvus',
                'status': 'connected', 
                'last_ping': time.time()
            }
        except Exception as e:
            logger.warning(f"Milvus连接器创建失败: {str(e)}")
            return {'type': 'milvus', 'status': 'error', 'error': str(e)}
    
    async def submit_sync_job(self, config: SyncJobConfig) -> str:
        """提交同步任务"""
        try:
            # 生成任务ID
            if not config.job_id:
                config.job_id = f"sync_{uuid.uuid4().hex[:8]}_{int(time.time())}"
            
            # 验证配置
            await self._validate_sync_config(config)
            
            # 创建任务结果记录
            result = SyncJobResult(
                job_id=config.job_id,
                status=SyncJobStatus.PENDING,
                start_time=time.time()
            )
            
            # 注册任务
            self.active_jobs[config.job_id] = config
            self.job_results[config.job_id] = result
            
            # 添加到队列
            await self.sync_queue.put(config)
            
            logger.info(f"同步任务已提交: {config.job_id}")
            return config.job_id
            
        except Exception as e:
            logger.error(f"提交同步任务失败: {str(e)}")
            raise
    
    async def _validate_sync_config(self, config: SyncJobConfig) -> None:
        """验证同步配置"""
        # 检查引擎是否可用
        if config.source_engine not in self.connectors:
            raise ValueError(f"源引擎不支持: {config.source_engine}")
        
        if config.target_engine not in self.connectors:
            raise ValueError(f"目标引擎不支持: {config.target_engine}")
        
        # 检查连接状态
        source_status = self.connectors[config.source_engine].get('status')
        target_status = self.connectors[config.target_engine].get('status')
        
        if source_status != 'connected':
            raise ValueError(f"源引擎连接异常: {config.source_engine}")
        
        if target_status != 'connected':
            raise ValueError(f"目标引擎连接异常: {config.target_engine}")
        
        # 检查批次大小
        if config.batch_size <= 0 or config.batch_size > 1000:
            raise ValueError(f"批次大小必须在1-1000之间: {config.batch_size}")
    
    async def sync_document_chunks(
        self, 
        knowledge_base_id: str, 
        document_id: Optional[str] = None,
        force_full_sync: bool = False
    ) -> str:
        """同步文档分块数据"""
        
        filters = {'knowledge_base_id': knowledge_base_id}
        if document_id:
            filters['document_id'] = document_id
        
        config = SyncJobConfig(
            job_id=f"sync_chunks_{knowledge_base_id}_{int(time.time())}",
            source_engine='postgresql',
            target_engine='elasticsearch',
            operation=SyncOperation.BULK_UPDATE,
            data_type='document_chunk',
            filters=filters,
            batch_size=50
        )
        
        return await self.submit_sync_job(config)
    
    async def sync_embeddings(
        self, 
        knowledge_base_id: str, 
        chunk_ids: Optional[List[str]] = None
    ) -> str:
        """同步嵌入向量数据"""
        
        filters = {'knowledge_base_id': knowledge_base_id}
        if chunk_ids:
            filters['chunk_ids'] = chunk_ids
        
        config = SyncJobConfig(
            job_id=f"sync_embeddings_{knowledge_base_id}_{int(time.time())}",
            source_engine='postgresql',
            target_engine='milvus',
            operation=SyncOperation.BULK_UPDATE,
            data_type='embedding',
            filters=filters,
            batch_size=100
        )
        
        return await self.submit_sync_job(config)
    
    async def incremental_sync(
        self, 
        data_type: str, 
        last_sync_time: Optional[float] = None
    ) -> str:
        """增量同步"""
        
        if not last_sync_time:
            last_sync_time = time.time() - 3600  # 默认1小时内的变更
        
        filters = {
            'updated_after': last_sync_time,
            'data_type': data_type
        }
        
        config = SyncJobConfig(
            job_id=f"incremental_sync_{data_type}_{int(time.time())}",
            source_engine='postgresql',
            target_engine='elasticsearch',
            operation=SyncOperation.BULK_UPDATE,
            data_type=data_type,
            filters=filters,
            batch_size=100
        )
        
        return await self.submit_sync_job(config)
    
    async def _sync_worker(self, worker_id: str) -> None:
        """同步工作线程"""
        logger.info(f"同步工作线程启动: {worker_id}")
        
        while self._running:
            try:
                # 获取任务（带超时）
                config = await asyncio.wait_for(
                    self.sync_queue.get(), 
                    timeout=30
                )
                
                # 执行同步任务
                await self._execute_sync_job(config, worker_id)
                
                # 标记任务完成
                self.sync_queue.task_done()
                
            except asyncio.TimeoutError:
                # 超时是正常的，继续等待
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"同步工作线程 {worker_id} 出错: {str(e)}")
                await asyncio.sleep(5)
        
        logger.info(f"同步工作线程退出: {worker_id}")
    
    async def _execute_sync_job(self, config: SyncJobConfig, worker_id: str) -> None:
        """执行同步任务"""
        result = self.job_results[config.job_id]
        result.status = SyncJobStatus.RUNNING
        
        try:
            logger.info(f"工作线程 {worker_id} 开始执行同步任务: {config.job_id}")
            
            # 获取同步锁
            lock_key = f"{config.source_engine}_{config.target_engine}_{config.data_type}"
            async with self.sync_locks[lock_key]:
                
                # 根据操作类型执行同步
                if config.operation in [SyncOperation.BULK_CREATE, SyncOperation.BULK_UPDATE]:
                    await self._execute_bulk_sync(config, result)
                elif config.operation == SyncOperation.BULK_DELETE:
                    await self._execute_bulk_delete(config, result)
                else:
                    await self._execute_single_sync(config, result)
            
            # 更新结果状态
            result.status = SyncJobStatus.COMPLETED
            result.end_time = time.time()
            result.throughput_per_second = result.success_items / max(result.duration(), 1)
            
            # 调用完成回调
            if config.on_complete:
                try:
                    config.on_complete(True, "同步完成")
                except Exception as e:
                    logger.warning(f"完成回调执行失败: {str(e)}")
            
            logger.info(
                f"同步任务完成: {config.job_id}, "
                f"成功: {result.success_items}, 失败: {result.failed_items}, "
                f"耗时: {result.duration():.2f}s"
            )
            
        except Exception as e:
            # 更新错误状态
            result.status = SyncJobStatus.FAILED
            result.end_time = time.time()
            result.errors.append(str(e))
            
            # 调用错误回调
            if config.on_error:
                try:
                    config.on_error(e)
                except Exception as callback_error:
                    logger.warning(f"错误回调执行失败: {str(callback_error)}")
            
            logger.error(f"同步任务失败: {config.job_id}, 错误: {str(e)}")
            
            # 重试逻辑
            if result.failed_items < config.max_retries:
                logger.info(f"准备重试同步任务: {config.job_id}")
                result.status = SyncJobStatus.RETRYING
                await asyncio.sleep(config.retry_delay)
                await self.sync_queue.put(config)
        
        finally:
            # 清理活跃任务
            if config.job_id in self.active_jobs:
                del self.active_jobs[config.job_id]
    
    async def _execute_bulk_sync(self, config: SyncJobConfig, result: SyncJobResult) -> None:
        """执行批量同步"""
        # 获取源数据
        source_data = await self._fetch_source_data(config)
        result.total_items = len(source_data)
        
        if not source_data:
            logger.info(f"没有需要同步的数据: {config.job_id}")
            return
        
        # 分批处理
        batch_size = config.batch_size
        for i in range(0, len(source_data), batch_size):
            batch = source_data[i:i + batch_size]
            
            try:
                # 检测变更
                changed_records = await self._detect_changes(batch, config)
                
                if changed_records:
                    # 同步到目标引擎
                    success_count = await self._sync_batch_to_target(changed_records, config)
                    result.success_items += success_count
                    result.skipped_items += len(batch) - len(changed_records)
                else:
                    result.skipped_items += len(batch)
                
                result.processed_items += len(batch)
                
                # 调用进度回调
                if config.on_progress:
                    try:
                        config.on_progress(result.processed_items, result.total_items)
                    except Exception as e:
                        logger.warning(f"进度回调执行失败: {str(e)}")
                
                # 更新检查点
                await self._update_sync_checksums(changed_records, config.target_engine)
                
            except Exception as e:
                logger.error(f"批次同步失败: {str(e)}")
                result.failed_items += len(batch)
                result.errors.append(f"批次 {i//batch_size + 1}: {str(e)}")
    
    async def _fetch_source_data(self, config: SyncJobConfig) -> List[DataRecord]:
        """从源引擎获取数据"""
        try:
            if config.source_engine == 'postgresql':
                return await self._fetch_postgresql_data(config)
            elif config.source_engine == 'elasticsearch':
                return await self._fetch_elasticsearch_data(config)
            elif config.source_engine == 'milvus':
                return await self._fetch_milvus_data(config)
            else:
                raise ValueError(f"不支持的源引擎: {config.source_engine}")
                
        except Exception as e:
            logger.error(f"获取源数据失败: {str(e)}")
            return []
    
    async def _fetch_postgresql_data(self, config: SyncJobConfig) -> List[DataRecord]:
        """从PostgreSQL获取数据"""
        # 这里应该实现实际的数据库查询逻辑
        # 模拟数据
        mock_data = []
        for i in range(10):
            content = {
                'id': f"record_{i}",
                'content': f"测试内容 {i}",
                'metadata': {'index': i},
                'updated_at': time.time()
            }
            record = DataRecord.create(
                record_id=f"record_{i}",
                data_type=config.data_type,
                content=content,
                source_engine='postgresql'
            )
            mock_data.append(record)
        
        return mock_data
    
    async def _fetch_elasticsearch_data(self, config: SyncJobConfig) -> List[DataRecord]:
        """从Elasticsearch获取数据"""
        # 这里应该实现实际的ES查询逻辑
        return []
    
    async def _fetch_milvus_data(self, config: SyncJobConfig) -> List[DataRecord]:
        """从Milvus获取数据"""
        # 这里应该实现实际的Milvus查询逻辑
        return []
    
    async def _detect_changes(self, records: List[DataRecord], config: SyncJobConfig) -> List[DataRecord]:
        """检测数据变更"""
        changed_records = []
        target_checksums = self.data_checksums.get(config.target_engine, {})
        
        for record in records:
            existing_hash = target_checksums.get(record.record_id)
            
            if existing_hash != record.hash_value:
                # 数据有变更或者是新数据
                changed_records.append(record)
        
        logger.info(f"检测到 {len(changed_records)} 条变更记录，总计 {len(records)} 条")
        return changed_records
    
    async def _sync_batch_to_target(self, records: List[DataRecord], config: SyncJobConfig) -> int:
        """同步批次数据到目标引擎"""
        try:
            if config.target_engine == 'elasticsearch':
                return await self._sync_to_elasticsearch(records, config)
            elif config.target_engine == 'milvus':
                return await self._sync_to_milvus(records, config)
            elif config.target_engine == 'postgresql':
                return await self._sync_to_postgresql(records, config)
            else:
                raise ValueError(f"不支持的目标引擎: {config.target_engine}")
                
        except Exception as e:
            logger.error(f"同步到目标引擎失败: {str(e)}")
            return 0
    
    async def _sync_to_elasticsearch(self, records: List[DataRecord], config: SyncJobConfig) -> int:
        """同步到Elasticsearch"""
        # 这里应该实现实际的ES批量索引逻辑
        success_count = 0
        
        for record in records:
            try:
                # 模拟ES索引操作
                await asyncio.sleep(0.01)  # 模拟网络延迟
                success_count += 1
            except Exception as e:
                logger.warning(f"ES索引失败 {record.record_id}: {str(e)}")
        
        return success_count
    
    async def _sync_to_milvus(self, records: List[DataRecord], config: SyncJobConfig) -> int:
        """同步到Milvus"""
        # 这里应该实现实际的Milvus插入逻辑
        success_count = 0
        
        for record in records:
            try:
                # 模拟Milvus插入操作
                await asyncio.sleep(0.01)  # 模拟网络延迟
                success_count += 1
            except Exception as e:
                logger.warning(f"Milvus插入失败 {record.record_id}: {str(e)}")
        
        return success_count
    
    async def _sync_to_postgresql(self, records: List[DataRecord], config: SyncJobConfig) -> int:
        """同步到PostgreSQL"""
        # 这里应该实现实际的数据库插入/更新逻辑
        success_count = 0
        
        for record in records:
            try:
                # 模拟数据库操作
                await asyncio.sleep(0.005)  # 模拟数据库延迟
                success_count += 1
            except Exception as e:
                logger.warning(f"数据库操作失败 {record.record_id}: {str(e)}")
        
        return success_count
    
    async def _update_sync_checksums(self, records: List[DataRecord], target_engine: str) -> None:
        """更新同步检查点"""
        target_checksums = self.data_checksums[target_engine]
        
        for record in records:
            target_checksums[record.record_id] = record.hash_value
    
    async def _execute_bulk_delete(self, config: SyncJobConfig, result: SyncJobResult) -> None:
        """执行批量删除"""
        # 实现删除逻辑
        pass
    
    async def _execute_single_sync(self, config: SyncJobConfig, result: SyncJobResult) -> None:
        """执行单条记录同步"""
        # 实现单条同步逻辑
        pass
    
    async def get_job_status(self, job_id: str) -> Optional[SyncJobResult]:
        """获取任务状态"""
        return self.job_results.get(job_id)
    
    async def cancel_job(self, job_id: str) -> bool:
        """取消同步任务"""
        if job_id in self.active_jobs:
            result = self.job_results.get(job_id)
            if result and result.status in [SyncJobStatus.PENDING, SyncJobStatus.RUNNING]:
                result.status = SyncJobStatus.CANCELLED
                result.end_time = time.time()
                del self.active_jobs[job_id]
                logger.info(f"同步任务已取消: {job_id}")
                return True
        return False
    
    async def get_sync_statistics(self) -> Dict[str, Any]:
        """获取同步统计信息"""
        stats = {
            'active_jobs': len(self.active_jobs),
            'total_jobs': len(self.job_results),
            'queue_size': self.sync_queue.qsize(),
            'worker_count': len(self._worker_tasks),
            'connector_status': {},
            'job_statistics': {
                'completed': 0,
                'failed': 0,
                'running': 0,
                'pending': 0
            }
        }
        
        # 连接器状态
        for engine, connector in self.connectors.items():
            stats['connector_status'][engine] = connector.get('status', 'unknown')
        
        # 任务统计
        for result in self.job_results.values():
            stats['job_statistics'][result.status.value] += 1
        
        return stats
    
    async def _heartbeat_loop(self) -> None:
        """心跳循环，检查连接器状态"""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                # 检查连接器状态
                for engine, connector in self.connectors.items():
                    try:
                        # 这里应该实现实际的心跳检查
                        connector['last_ping'] = time.time()
                        if connector.get('status') == 'error':
                            # 尝试重新连接
                            logger.info(f"尝试重新连接 {engine}")
                            connector['status'] = 'connected'
                    except Exception as e:
                        logger.warning(f"引擎 {engine} 心跳检查失败: {str(e)}")
                        connector['status'] = 'error'
                        connector['error'] = str(e)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳循环出错: {str(e)}")
                await asyncio.sleep(60)
    
    async def _cleanup_loop(self) -> None:
        """清理循环，清理过期任务记录"""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                current_time = time.time()
                cutoff_time = current_time - (24 * 3600)  # 保留24小时内的记录
                
                # 清理过期任务记录
                expired_jobs = []
                for job_id, result in self.job_results.items():
                    if (result.end_time and result.end_time < cutoff_time and 
                        result.status in [SyncJobStatus.COMPLETED, SyncJobStatus.FAILED, SyncJobStatus.CANCELLED]):
                        expired_jobs.append(job_id)
                
                for job_id in expired_jobs:
                    if len(self.job_results) > self.max_job_history:
                        del self.job_results[job_id]
                
                logger.info(f"清理了 {len(expired_jobs)} 个过期任务记录")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理循环出错: {str(e)}")
                await asyncio.sleep(3600)
    
    async def cleanup(self) -> None:
        """清理资源"""
        self._running = False
        
        # 取消所有工作任务
        for task in self._worker_tasks:
            task.cancel()
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # 等待任务完成
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        
        if self._heartbeat_task:
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("数据同步服务清理完成")


# 全局同步服务实例
_sync_service: Optional[DataSyncService] = None


async def get_sync_service() -> DataSyncService:
    """获取全局同步服务实例"""
    global _sync_service
    
    if _sync_service is None:
        _sync_service = DataSyncService()
        await _sync_service.initialize()
    
    return _sync_service 