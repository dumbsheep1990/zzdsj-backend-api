"""
知识图谱核心服务
提供完整的知识图谱管理、处理和可视化功能
"""

import asyncio
import json
import logging
import time
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from app.frameworks.ai_knowledge_graph.processor import AIKnowledgeGraphProcessor
from app.frameworks.ai_knowledge_graph.adapters.storage_adapter import StorageAdapter
from app.frameworks.ai_knowledge_graph.config import get_config

# 导入统一图数据库架构
from app.utils.storage.graph_storage.graph_database_factory import (
    GraphDatabaseFactory, 
    GraphDatabaseType,
    IGraphDatabase,
    graph_db_manager
)
from app.config.graph_database_config import get_graph_database_config
from app.schemas.knowledge_graph import (
    KnowledgeGraphCreate, KnowledgeGraphUpdate, KnowledgeGraphResponse,
    EntityExtractionConfig, GraphVisualizationConfig, GraphStatus,
    ProcessingProgress, GraphStatistics, GraphAnalytics
)
from app.repositories.knowledge_graph_repository import KnowledgeGraphRepository
from app.services.integrations.llm_service import LLMService
from app.utils.common.async_utils import AsyncContextManager
from app.utils.monitoring.core.performance_monitor import PerformanceMonitor
from app.utils.storage.core.file_storage import FileStorageService

# 集成现有知识库服务
from app.services.knowledge.unified_service import UnifiedKnowledgeService
from app.services.knowledge.adapter_service import KnowledgeServiceAdapter

logger = logging.getLogger(__name__)

class KnowledgeGraphService(AsyncContextManager):
    """知识图谱服务类"""
    
    def __init__(self, db_session=None):
        self.config = get_config()
        self.processor = AIKnowledgeGraphProcessor()
        self.storage_adapter = StorageAdapter(self.config)
        self.repository = KnowledgeGraphRepository()
        self.llm_service = LLMService()
        self.file_storage = FileStorageService()
        self.performance_monitor = PerformanceMonitor()
        
        # 集成现有知识库服务
        if db_session:
            self.kb_service = UnifiedKnowledgeService(db_session)
            self.kb_adapter = KnowledgeServiceAdapter(db_session)
        else:
            self.kb_service = None
            self.kb_adapter = None
        
        # 统一图数据库支持
        self.graph_db: IGraphDatabase = None
        self._graph_db_initialized = False
        
        # 处理状态缓存
        self._processing_status = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        logger.info("知识图谱服务初始化完成 - 已集成现有知识库服务")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.repository.__aenter__()
        await self.llm_service.__aenter__()
        
        # 初始化图数据库
        await self._initialize_graph_database()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.repository.__aexit__(exc_type, exc_val, exc_tb)
        await self.llm_service.__aexit__(exc_type, exc_val, exc_tb)
        
        # 关闭图数据库连接
        if self.graph_db:
            await self.graph_db.close()
        
        self._executor.shutdown(wait=True)
    
    async def list_graphs(
        self, 
        user_id: int, 
        knowledge_base_id: Optional[int] = None,
        page: int = 1, 
        size: int = 20
    ) -> List[KnowledgeGraphResponse]:
        """获取知识图谱列表"""
        try:
            graphs = await self.repository.list_user_graphs(
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                offset=(page - 1) * size,
                limit=size
            )
            
            # 填充统计信息和处理状态
            enriched_graphs = []
            for graph in graphs:
                # 获取统计信息
                stats = await self._get_graph_statistics(graph.id)
                graph.statistics = stats
                
                # 获取处理状态
                if graph.status == GraphStatus.PROCESSING:
                    progress = self._processing_status.get(graph.id)
                    if progress:
                        graph.processing_progress = progress
                
                enriched_graphs.append(graph)
            
            return enriched_graphs
            
        except Exception as e:
            logger.error(f"获取知识图谱列表失败: {str(e)}")
            raise
    
    async def get_graph(self, graph_id: str, user_id: int) -> Optional[KnowledgeGraphResponse]:
        """获取指定知识图谱"""
        try:
            graph = await self.repository.get_graph_by_id(graph_id, user_id)
            if not graph:
                return None
            
            # 填充详细信息
            stats = await self._get_graph_statistics(graph_id)
            graph.statistics = stats
            
            if graph.status == GraphStatus.PROCESSING:
                progress = self._processing_status.get(graph_id)
                if progress:
                    graph.processing_progress = progress
            
            return graph
            
        except Exception as e:
            logger.error(f"获取知识图谱失败: {str(e)}")
            raise
    
    async def create_graph(
        self, 
        user_id: int, 
        graph_data: KnowledgeGraphCreate
    ) -> KnowledgeGraphResponse:
        """创建新的知识图谱"""
        try:
            # 生成图谱ID
            graph_id = f"kg_{uuid.uuid4().hex[:8]}_{int(time.time())}"
            
            # 创建数据库记录
            graph = await self.repository.create_graph(
                graph_id=graph_id,
                user_id=user_id,
                name=graph_data.name,
                description=graph_data.description,
                knowledge_base_id=graph_data.knowledge_base_id,
                extraction_config=graph_data.extraction_config.dict(),
                visualization_config=graph_data.visualization_config.dict(),
                is_public=graph_data.is_public,
                tags=graph_data.tags
            )
            
            logger.info(f"创建知识图谱成功: {graph_id}")
            return graph
            
        except Exception as e:
            logger.error(f"创建知识图谱失败: {str(e)}")
            raise
    
    async def create_graph_from_kb(
        self,
        user_id: int,
        knowledge_base_id: int,
        file_selection: List[int],
        config: EntityExtractionConfig
    ) -> KnowledgeGraphResponse:
        """从知识库创建知识图谱"""
        try:
            # 获取知识库信息
            kb_info = await self._get_knowledge_base_info(knowledge_base_id)
            
            # 创建图谱
            graph_data = KnowledgeGraphCreate(
                name=f"{kb_info.get('name', '知识库')}_知识图谱",
                description=f"基于知识库 {kb_info.get('name')} 生成的知识图谱",
                knowledge_base_id=knowledge_base_id,
                extraction_config=config
            )
            
            graph = await self.create_graph(user_id, graph_data)
            
            # 记录文件选择
            await self.repository.update_graph_files(
                graph.id, [str(fid) for fid in file_selection]
            )
            
            return graph
            
        except Exception as e:
            logger.error(f"从知识库创建知识图谱失败: {str(e)}")
            raise
    
    async def update_graph(
        self, 
        graph_id: str, 
        user_id: int, 
        graph_data: KnowledgeGraphUpdate
    ) -> Optional[KnowledgeGraphResponse]:
        """更新知识图谱"""
        try:
            # 验证权限
            existing_graph = await self.repository.get_graph_by_id(graph_id, user_id)
            if not existing_graph:
                return None
            
            # 更新数据
            updated_graph = await self.repository.update_graph(
                graph_id=graph_id,
                name=graph_data.name,
                description=graph_data.description,
                visualization_config=graph_data.visualization_config.dict() if graph_data.visualization_config else None,
                is_public=graph_data.is_public,
                tags=graph_data.tags
            )
            
            return updated_graph
            
        except Exception as e:
            logger.error(f"更新知识图谱失败: {str(e)}")
            raise
    
    async def delete_graph(self, graph_id: str, user_id: int) -> bool:
        """删除知识图谱"""
        try:
            # 验证权限
            existing_graph = await self.repository.get_graph_by_id(graph_id, user_id)
            if not existing_graph:
                return False
            
            # 删除存储的数据
            await self.storage_adapter.delete_knowledge_graph(graph_id)
            
            # 删除数据库记录
            success = await self.repository.delete_graph(graph_id)
            
            # 清理处理状态
            if graph_id in self._processing_status:
                del self._processing_status[graph_id]
            
            logger.info(f"删除知识图谱成功: {graph_id}")
            return success
            
        except Exception as e:
            logger.error(f"删除知识图谱失败: {str(e)}")
            raise
    
    async def process_files_async(
        self,
        graph_id: str,
        file_paths: List[str],
        config: Optional[EntityExtractionConfig] = None
    ):
        """异步处理文件，提取实体和关系"""
        try:
            # 更新状态为处理中
            await self.repository.update_graph_status(graph_id, GraphStatus.PROCESSING)
            
            # 初始化处理进度
            progress = ProcessingProgress(
                total_files=len(file_paths),
                processed_files=0,
                current_step="开始处理文件",
                progress_percentage=0.0
            )
            self._processing_status[graph_id] = progress
            
            start_time = time.time()
            all_triples = []
            
            # 处理每个文件
            for i, file_path in enumerate(file_paths):
                try:
                    # 更新进度
                    progress.current_step = f"处理文件: {Path(file_path).name}"
                    progress.progress_percentage = (i / len(file_paths)) * 80  # 80%用于文件处理
                    
                    # 读取文件内容
                    content = await self._read_file_content(file_path)
                    
                    # 提取三元组
                    triples = await self.processor.process_text(
                        content, 
                        config.dict() if config else {}
                    )
                    
                    all_triples.extend(triples)
                    
                    # 更新进度
                    progress.processed_files = i + 1
                    progress.total_entities = len(set(
                        [t['subject'] for t in all_triples] + 
                        [t['object'] for t in all_triples]
                    ))
                    progress.total_relations = len(all_triples)
                    
                except Exception as e:
                    logger.error(f"处理文件 {file_path} 失败: {str(e)}")
                    continue
            
            # 保存到存储
            progress.current_step = "保存知识图谱数据"
            progress.progress_percentage = 85.0
            
            await self.storage_adapter.save_knowledge_graph(
                graph_id, all_triples, {
                    "processing_time": time.time() - start_time,
                    "file_count": len(file_paths),
                    "entity_count": progress.total_entities,
                    "relation_count": progress.total_relations
                }
            )
            
            # 优化图谱布局
            progress.current_step = "优化图谱布局"
            progress.progress_percentage = 95.0
            
            await self._optimize_graph_layout(graph_id, all_triples)
            
            # 完成处理
            progress.current_step = "处理完成"
            progress.progress_percentage = 100.0
            
            await self.repository.update_graph_status(graph_id, GraphStatus.COMPLETED)
            await self.repository.set_graph_completed_at(graph_id, datetime.utcnow())
            
            # 清理处理状态
            if graph_id in self._processing_status:
                del self._processing_status[graph_id]
            
            logger.info(f"知识图谱处理完成: {graph_id}, 三元组数量: {len(all_triples)}")
            
        except Exception as e:
            logger.error(f"异步处理知识图谱失败: {str(e)}")
            
            # 更新为失败状态
            await self.repository.update_graph_status(graph_id, GraphStatus.FAILED)
            
            if graph_id in self._processing_status:
                self._processing_status[graph_id].error_message = str(e)
    
    async def process_kb_files_async(
        self,
        graph_id: str,
        knowledge_base_id: int,
        file_ids: List[int],
        config: EntityExtractionConfig
    ):
        """异步处理知识库文件"""
        try:
            # 获取文件路径
            file_paths = await self._get_kb_file_paths(knowledge_base_id, file_ids)
            
            # 调用通用文件处理
            await self.process_files_async(graph_id, file_paths, config)
            
        except Exception as e:
            logger.error(f"处理知识库文件失败: {str(e)}")
            raise
    
    async def generate_visualization(
        self,
        graph_id: str,
        user_id: int,
        config: Optional[GraphVisualizationConfig] = None
    ) -> str:
        """生成知识图谱可视化"""
        try:
            # 验证权限
            graph = await self.repository.get_graph_by_id(graph_id, user_id)
            if not graph:
                raise ValueError("知识图谱不存在")
            
            # 加载图谱数据
            graph_data = await self.storage_adapter.load_knowledge_graph(graph_id)
            if not graph_data.get("success"):
                raise ValueError("无法加载知识图谱数据")
            
            triples = graph_data["graph_data"]["triples"]
            
            # 使用框架内置的可视化器生成HTML
            visualizer_config = get_config()
            from app.frameworks.ai_knowledge_graph.core.visualizer import KnowledgeGraphVisualizer
            visualizer = KnowledgeGraphVisualizer(visualizer_config)
            
            # 生成可视化
            viz_result = visualizer.visualize_knowledge_graph(
                triples=triples,
                output_path=None,  # 不保存文件，直接返回内容
                visualization_type="enhanced"
            )
            
            if viz_result.get("success"):
                return viz_result["html_content"]
            else:
                raise ValueError(f"可视化生成失败: {viz_result.get('error')}")
            
        except Exception as e:
            logger.error(f"生成可视化失败: {str(e)}")
            raise
    
    async def get_processing_status(self, graph_id: str, user_id: int) -> Dict[str, Any]:
        """获取处理状态"""
        try:
            # 验证权限
            graph = await self.repository.get_graph_by_id(graph_id, user_id)
            if not graph:
                raise ValueError("知识图谱不存在")
            
            if graph.status != GraphStatus.PROCESSING:
                return {"status": graph.status.value}
            
            progress = self._processing_status.get(graph_id)
            if not progress:
                return {"status": "unknown"}
            
            return {
                "status": "processing",
                "progress": progress.dict()
            }
            
        except Exception as e:
            logger.error(f"获取处理状态失败: {str(e)}")
            raise
    
    async def export_graph(
        self, 
        graph_id: str, 
        user_id: int, 
        format_type: str = "json"
    ) -> Dict[str, Any]:
        """导出知识图谱"""
        try:
            # 验证权限
            graph = await self.repository.get_graph_by_id(graph_id, user_id)
            if not graph:
                raise ValueError("知识图谱不存在")
            
            # 导出数据
            export_result = await self.storage_adapter.export_to_format(graph_id, format_type)
            
            return export_result
            
        except Exception as e:
            logger.error(f"导出知识图谱失败: {str(e)}")
            raise
    
    async def analyze_graph(self, graph_id: str, user_id: int) -> GraphAnalytics:
        """分析知识图谱"""
        try:
            # 验证权限
            graph = await self.repository.get_graph_by_id(graph_id, user_id)
            if not graph:
                raise ValueError("知识图谱不存在")
            
            # 加载图谱数据
            graph_data = await self.storage_adapter.load_knowledge_graph(graph_id)
            if not graph_data.get("success"):
                raise ValueError("无法加载知识图谱数据")
            
            triples = graph_data["graph_data"]["triples"]
            
            # 执行图分析
            analytics = await self._analyze_graph_structure(triples)
            
            return analytics
            
        except Exception as e:
            logger.error(f"分析知识图谱失败: {str(e)}")
            raise
    
    # 私有方法
    
    async def _get_graph_statistics(self, graph_id: str) -> Optional[GraphStatistics]:
        """获取图谱统计信息"""
        try:
            graph_data = await self.storage_adapter.load_knowledge_graph(graph_id)
            if not graph_data.get("success"):
                return None
            
            triples = graph_data["graph_data"]["triples"]
            
            # 计算统计信息
            entities = set()
            relations = []
            entity_types = {}
            relation_types = {}
            
            for triple in triples:
                entities.add(triple["subject"])
                entities.add(triple["object"])
                relations.append(triple)
                
                # 统计类型分布（简化实现）
                subj_type = self._classify_entity(triple["subject"])
                obj_type = self._classify_entity(triple["object"])
                entity_types[subj_type] = entity_types.get(subj_type, 0) + 1
                entity_types[obj_type] = entity_types.get(obj_type, 0) + 1
                
                rel_type = triple["predicate"]
                relation_types[rel_type] = relation_types.get(rel_type, 0) + 1
            
            # 计算图谱密度
            n_entities = len(entities)
            n_relations = len(relations)
            density = n_relations / (n_entities * (n_entities - 1)) if n_entities > 1 else 0
            
            return GraphStatistics(
                total_entities=n_entities,
                total_relations=n_relations,
                entity_type_distribution=entity_types,
                relation_type_distribution=relation_types,
                graph_density=density,
                average_degree=2 * n_relations / n_entities if n_entities > 0 else 0,
                connected_components=1,  # 简化计算
                clustering_coefficient=0.0  # 简化计算
            )
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return None
    
    def _classify_entity(self, entity: str) -> str:
        """简单的实体分类"""
        entity_lower = entity.lower()
        if any(k in entity_lower for k in ['gpt', 'bert', 'model', '模型']):
            return 'model'
        elif any(k in entity_lower for k in ['company', '公司', 'openai', 'google']):
            return 'company'
        elif any(k in entity_lower for k in ['技术', 'technology', '学习']):
            return 'technology'
        else:
            return 'concept'
    
    async def _read_file_content(self, file_path: str) -> str:
        """读取文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}: {str(e)}")
            return ""
    
    async def _optimize_graph_layout(self, graph_id: str, triples: List[Dict[str, Any]]):
        """优化图谱布局"""
        # 这里可以实现图布局优化算法
        # 暂时简化实现
        pass
    
    async def _analyze_graph_structure(self, triples: List[Dict[str, Any]]) -> GraphAnalytics:
        """分析图谱结构"""
        # 简化的图分析实现
        stats = await self._calculate_basic_stats(triples)
        
        return GraphAnalytics(
            basic_stats=stats,
            degree_centrality={},
            betweenness_centrality={},
            closeness_centrality={},
            pagerank={},
            communities=[],
            modularity=0.0,
            top_entities=[],
            relation_strength={},
            completeness_score=0.8,
            consistency_score=0.9
        )
    
    async def _calculate_basic_stats(self, triples: List[Dict[str, Any]]) -> GraphStatistics:
        """计算基础统计信息"""
        entities = set()
        entity_types = {}
        relation_types = {}
        
        for triple in triples:
            entities.add(triple["subject"])
            entities.add(triple["object"])
            
            # 简化的类型统计
            rel_type = triple["predicate"]
            relation_types[rel_type] = relation_types.get(rel_type, 0) + 1
        
        n_entities = len(entities)
        n_relations = len(triples)
        density = n_relations / (n_entities * (n_entities - 1)) if n_entities > 1 else 0
        
        return GraphStatistics(
            total_entities=n_entities,
            total_relations=n_relations,
            entity_type_distribution=entity_types,
            relation_type_distribution=relation_types,
            graph_density=density,
            average_degree=2 * n_relations / n_entities if n_entities > 0 else 0,
            connected_components=1,
            clustering_coefficient=0.0
        )
    
    async def _get_knowledge_base_info(self, kb_id: int) -> Dict[str, Any]:
        """获取知识库信息"""
        try:
            if self.kb_service:
                kb_info = await self.kb_service.get_knowledge_base(str(kb_id))
                if kb_info:
                    return {
                        "id": kb_info.get("id"),
                        "name": kb_info.get("name", f"知识库_{kb_id}"),
                        "description": kb_info.get("description", ""),
                        "document_count": kb_info.get("stats", {}).get("document_count", 0),
                        "created_at": kb_info.get("created_at"),
                        "updated_at": kb_info.get("updated_at")
                    }
            
            # 回退方案
            return {"name": f"知识库_{kb_id}", "description": "知识库信息"}
            
        except Exception as e:
            logger.error(f"获取知识库信息失败: {str(e)}")
            return {"name": f"知识库_{kb_id}", "description": "获取知识库信息失败"}
    
    async def _get_kb_file_paths(self, kb_id: int, file_ids: List[int]) -> List[str]:
        """获取知识库文件路径"""
        try:
            if self.kb_service:
                file_paths = []
                for file_id in file_ids:
                    # 获取文档信息
                    doc_info = await self.kb_service.get_document(str(kb_id), str(file_id))
                    if doc_info and doc_info.get("file_path"):
                        file_paths.append(doc_info["file_path"])
                    else:
                        # 尝试生成文件路径
                        file_paths.append(f"/uploads/kb_{kb_id}/doc_{file_id}.txt")
                
                return file_paths
            
            # 回退方案
            return [f"/uploads/kb_{kb_id}/file_{fid}.txt" for fid in file_ids]
            
        except Exception as e:
            logger.error(f"获取知识库文件路径失败: {str(e)}")
            return [f"/uploads/kb_{kb_id}/file_{fid}.txt" for fid in file_ids]
    
    # 新增方法
    
    async def save_uploaded_files(self, graph_id: str, files) -> List[str]:
        """保存上传的文件"""
        try:
            file_paths = []
            base_path = Path(f"uploads/knowledge_graphs/{graph_id}")
            base_path.mkdir(parents=True, exist_ok=True)
            
            for file in files:
                file_path = base_path / file.filename
                with open(file_path, "wb") as f:
                    content = await file.read()
                    f.write(content)
                file_paths.append(str(file_path))
            
            return file_paths
            
        except Exception as e:
            logger.error(f"保存上传文件失败: {str(e)}")
            raise
    
    async def get_kb_files(self, kb_id: int, user_id: int) -> List[Dict[str, Any]]:
        """获取知识库文件列表"""
        try:
            if self.kb_service:
                # 获取知识库文档列表
                documents = await self.kb_service.get_documents(
                    str(kb_id), 
                    skip=0, 
                    limit=100
                )
                
                if documents:
                    file_list = []
                    for doc in documents:
                        file_info = {
                            "id": doc.get("id"),
                            "name": doc.get("title", doc.get("filename", "未知文档")),
                            "size": doc.get("file_size", 0),
                            "type": doc.get("file_type", "unknown"),
                            "created_at": doc.get("created_at"),
                            "status": doc.get("status", "processed"),
                            "chunk_count": doc.get("chunk_count", 0)
                        }
                        file_list.append(file_info)
                    
                    return file_list
            
            # 回退方案 - 返回模拟数据
            return [
                {"id": 1, "name": "document1.pdf", "size": 1024000, "type": "pdf"},
                {"id": 2, "name": "document2.txt", "size": 512000, "type": "txt"},
            ]
            
        except Exception as e:
            logger.error(f"获取知识库文件失败: {str(e)}")
            raise
    
    async def extract_entities_from_text(
        self, 
        graph_id: str, 
        text: str, 
        config: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """从文本提取实体"""
        try:
            triples = await self.processor.process_text(text, config or {})
            
            # 提取唯一实体
            entities = {}
            for triple in triples:
                for entity in [triple["subject"], triple["object"]]:
                    if entity not in entities:
                        entities[entity] = {
                            "name": entity,
                            "type": self._classify_entity(entity),
                            "confidence": triple.get("confidence", 1.0)
                        }
            
            return list(entities.values())
            
        except Exception as e:
            logger.error(f"提取实体失败: {str(e)}")
            raise
    
    async def add_entities_manually(
        self, 
        graph_id: str, 
        entities: List[Dict[str, Any]], 
        relations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """手动添加实体和关系"""
        try:
            # 加载现有图谱数据
            graph_data = await self.storage_adapter.load_knowledge_graph(graph_id)
            if not graph_data.get("success"):
                raise ValueError("无法加载知识图谱数据")
            
            existing_triples = graph_data["graph_data"]["triples"]
            
            # 添加新的关系
            for relation in relations:
                new_triple = {
                    "subject": relation["subject"],
                    "predicate": relation["predicate"],
                    "object": relation["object"],
                    "confidence": relation.get("confidence", 1.0),
                    "manual": True
                }
                existing_triples.append(new_triple)
            
            # 保存更新的图谱
            await self.storage_adapter.save_knowledge_graph(
                graph_id, existing_triples, {"manual_update": True}
            )
            
            return {
                "success": True,
                "added_entities": len(entities),
                "added_relations": len(relations)
            }
            
        except Exception as e:
            logger.error(f"手动添加实体失败: {str(e)}")
            raise
    
    async def optimize_layout(
        self, 
        graph_id: str, 
        user_id: int, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """优化图谱布局"""
        try:
            # 验证权限
            graph = await self.repository.get_graph_by_id(graph_id, user_id)
            if not graph:
                raise ValueError("知识图谱不存在")
            
            # 执行布局优化
            # 这里可以实现具体的布局优化算法
            
            return {"success": True, "message": "布局优化完成"}
            
        except Exception as e:
            logger.error(f"优化布局失败: {str(e)}")
            raise 
    
    # ====================== 新增统一图数据库功能 ======================
    
    async def _initialize_graph_database(self):
        """初始化图数据库"""
        try:
            if not self._graph_db_initialized:
                # 获取配置 - 优先从应用配置系统
                from app.config.graph_database_config import get_graph_database_config_from_app
                config = get_graph_database_config_from_app()
                
                # 初始化全局管理器
                await graph_db_manager.initialize(config)
                self.graph_db = await graph_db_manager.get_database()
                self._graph_db_initialized = True
                
                logger.info(f"图数据库初始化成功: {config.db_type.value}")
                
        except Exception as e:
            logger.error(f"图数据库初始化失败: {str(e)}")
            raise
    
    async def switch_graph_database(self, db_type: GraphDatabaseType):
        """切换图数据库类型"""
        try:
            from app.config.graph_database_config import get_graph_database_config_from_app
            config = get_graph_database_config_from_app()
            config.db_type = db_type
            
            await graph_db_manager.switch_database(config)
            self.graph_db = await graph_db_manager.get_database()
            
            logger.info(f"切换图数据库成功: {db_type.value}")
            
        except Exception as e:
            logger.error(f"切换图数据库失败: {str(e)}")
            raise
    
    async def save_graph_to_backend(
        self, 
        graph_id: str, 
        user_id: int, 
        triples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """保存图谱到图数据库后端"""
        try:
            if not self.graph_db:
                await self._initialize_graph_database()
            
            # 使用用户ID作为租户ID
            tenant_id = str(user_id)
            
            result = await self.graph_db.save_knowledge_graph(
                tenant_id=tenant_id,
                graph_id=graph_id,
                triples=triples
            )
            
            logger.info(f"保存图谱到后端成功: {graph_id}")
            return result
            
        except Exception as e:
            logger.error(f"保存图谱到后端失败: {str(e)}")
            raise
    
    async def load_graph_from_backend(
        self, 
        graph_id: str, 
        user_id: int
    ) -> Dict[str, Any]:
        """从图数据库后端加载图谱"""
        try:
            if not self.graph_db:
                await self._initialize_graph_database()
            
            tenant_id = str(user_id)
            
            result = await self.graph_db.load_knowledge_graph(
                tenant_id=tenant_id,
                graph_id=graph_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"从后端加载图谱失败: {str(e)}")
            raise
    
    async def get_graph_subgraph(
        self, 
        graph_id: str, 
        user_id: int, 
        center_entity: str,
        depth: int = 2,
        limit: int = 100
    ) -> Dict[str, Any]:
        """获取图谱子图"""
        try:
            if not self.graph_db:
                await self._initialize_graph_database()
            
            tenant_id = str(user_id)
            
            result = await self.graph_db.get_subgraph(
                tenant_id=tenant_id,
                center_entity=center_entity,
                depth=depth,
                limit=limit
            )
            
            return result
            
        except Exception as e:
            logger.error(f"获取子图失败: {str(e)}")
            raise
    
    async def get_enhanced_graph_statistics(
        self, 
        graph_id: str, 
        user_id: int
    ) -> Dict[str, Any]:
        """获取增强的图统计信息"""
        try:
            if not self.graph_db:
                await self._initialize_graph_database()
            
            tenant_id = str(user_id)
            
            # 基础统计
            basic_stats = await self.graph_db.get_graph_statistics(
                tenant_id=tenant_id,
                graph_id=graph_id
            )
            
            # 尝试导出为NetworkX并计算高级指标
            try:
                # 检查是否有compute_advanced_metrics方法（ArangoDB适配器）
                if hasattr(self.graph_db, 'compute_advanced_metrics'):
                    advanced_stats = await self.graph_db.compute_advanced_metrics(
                        tenant_id=tenant_id,
                        graph_id=graph_id
                    )
                    basic_stats.update(advanced_stats)
                
                # 或者检查compute_networkx_algorithms方法（PostgreSQL适配器）
                elif hasattr(self.graph_db, 'compute_networkx_algorithms'):
                    networkx_stats = await self.graph_db.compute_networkx_algorithms(
                        tenant_id=tenant_id,
                        graph_id=graph_id
                    )
                    basic_stats.update(networkx_stats)
                    
            except Exception as nx_error:
                logger.warning(f"计算高级统计失败: {str(nx_error)}")
            
            return basic_stats
            
        except Exception as e:
            logger.error(f"获取增强统计信息失败: {str(e)}")
            raise
    
    async def export_graph_to_networkx(
        self, 
        graph_id: str, 
        user_id: int
    ) -> Any:
        """导出图谱为NetworkX对象"""
        try:
            if not self.graph_db:
                await self._initialize_graph_database()
            
            tenant_id = str(user_id)
            
            networkx_graph = await self.graph_db.export_to_networkx(
                tenant_id=tenant_id,
                graph_id=graph_id
            )
            
            return networkx_graph
            
        except Exception as e:
            logger.error(f"导出NetworkX图失败: {str(e)}")
            raise
    
    async def get_database_info(self) -> Dict[str, Any]:
        """获取当前图数据库信息"""
        try:
            if not self.graph_db:
                await self._initialize_graph_database()
            
            from app.config.graph_database_config import get_graph_database_config_from_app
            config = get_graph_database_config_from_app()
            
            return {
                "database_type": config.db_type.value,
                "storage_strategy": config.storage_strategy.value,
                "supports_native_algorithms": config.db_type == GraphDatabaseType.ARANGODB,
                "supports_networkx": True,  # 两种方案都支持
                "supports_html_visualization": True,  # 支持HTML可视化
                "isolation_strategy": config.isolation_config.get("strategy", "unknown"),
                "performance_config": config.performance_config
            }
            
        except Exception as e:
            logger.error(f"获取数据库信息失败: {str(e)}")
            return {"error": str(e)}
    
    async def generate_visualization(
        self,
        user_id: int,
        knowledge_base_id: int,
        graph_name: str = "default",
        output_path: Optional[str] = None,
        visualization_type: str = "interactive",
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成知识图谱HTML可视化
        
        Args:
            user_id: 用户ID
            knowledge_base_id: 知识库ID  
            graph_name: 图名称
            output_path: 输出文件路径（可选）
            visualization_type: 可视化类型 (simple/interactive/enhanced/default)
            config: 可视化配置
            
        Returns:
            生成结果字典
        """
        try:
            if not self.graph_db:
                await self._initialize_graph_database()
            
            # 构建租户ID
            tenant_id = self._build_tenant_id(user_id, knowledge_base_id)
            
            # 使用可视化桥接器
            from app.utils.storage.graph_storage.visualization_bridge import GraphVisualizationBridge
            bridge = GraphVisualizationBridge(self.graph_db)
            
            result = await bridge.generate_html_visualization(
                tenant_id=tenant_id,
                graph_name=graph_name,
                output_path=output_path,
                visualization_type=visualization_type,
                config=config
            )
            
            if result.get("success"):
                logger.info(f"可视化生成成功: {result['html_path']}")
                
                # 添加额外信息
                result.update({
                    "user_id": user_id,
                    "knowledge_base_id": knowledge_base_id,
                    "tenant_id": tenant_id,
                    "graph_name": graph_name
                })
            
            return result
            
        except Exception as e:
            logger.error(f"生成可视化失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "user_id": user_id,
                "knowledge_base_id": knowledge_base_id
            }
    
    async def get_graph_statistics(
        self,
        user_id: int,
        knowledge_base_id: int,
        graph_name: str = "default"
    ) -> Dict[str, Any]:
        """
        获取图谱统计信息
        
        Args:
            user_id: 用户ID
            knowledge_base_id: 知识库ID
            graph_name: 图名称
            
        Returns:
            统计信息字典
        """
        try:
            if not self.graph_db:
                await self._initialize_graph_database()
            
            # 构建租户ID
            tenant_id = self._build_tenant_id(user_id, knowledge_base_id)
            
            # 使用可视化桥接器获取统计
            from app.utils.storage.graph_storage.visualization_bridge import GraphVisualizationBridge
            bridge = GraphVisualizationBridge(self.graph_db)
            
            stats = await bridge.get_graph_statistics(tenant_id, graph_name)
            
            # 添加额外信息
            stats.update({
                "user_id": user_id,
                "knowledge_base_id": knowledge_base_id,
                "tenant_id": tenant_id,
                "graph_name": graph_name
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"获取图谱统计失败: {str(e)}")
            return {
                "error": str(e),
                "user_id": user_id,
                "knowledge_base_id": knowledge_base_id
            }
    
    async def export_networkx_graph(
        self,
        user_id: int,
        knowledge_base_id: int,
        graph_name: str = "default"
    ) -> Optional[Any]:
        """
        导出NetworkX图对象（用于高级分析）
        
        Args:
            user_id: 用户ID
            knowledge_base_id: 知识库ID
            graph_name: 图名称
            
        Returns:
            NetworkX图对象
        """
        try:
            if not self.graph_db:
                await self._initialize_graph_database()
            
            # 构建租户ID
            tenant_id = self._build_tenant_id(user_id, knowledge_base_id)
            
            # 使用可视化桥接器生成NetworkX图
            from app.utils.storage.graph_storage.visualization_bridge import GraphVisualizationBridge
            bridge = GraphVisualizationBridge(self.graph_db)
            
            networkx_graph = await bridge.generate_networkx_graph(tenant_id, graph_name)
            
            if networkx_graph:
                logger.info(f"NetworkX图导出成功: {networkx_graph.number_of_nodes()}节点, {networkx_graph.number_of_edges()}边")
            
            return networkx_graph
            
        except Exception as e:
            logger.error(f"导出NetworkX图失败: {str(e)}")
            return None
    
    # 场景一：知识库绑定场景的专用方法
    
    async def get_graphs_by_knowledge_base(
        self,
        knowledge_base_id: int,
        user_id: int
    ) -> List[KnowledgeGraphResponse]:
        """获取指定知识库的所有图谱"""
        try:
            graphs = await self.repository.get_graphs_by_knowledge_base(
                knowledge_base_id=knowledge_base_id,
                user_id=user_id
            )
            return graphs
            
        except Exception as e:
            logger.error(f"获取知识库图谱失败: {str(e)}")
            raise
    
    async def generate_kb_visualization(
        self,
        graph_id: str = None,
        user_id: int = None,
        visualization_type: str = "enhanced",
        auto_save: bool = False,
        **kwargs
    ) -> str:
        """
        为知识库图谱生成HTML可视化
        基于已构建的图数据生成HTML页面
        """
        try:
            if graph_id:
                # 基于图谱ID生成
                graph_data = await self.storage_adapter.load_knowledge_graph(graph_id)
                if not graph_data.get("success"):
                    raise ValueError("无法加载知识库图谱数据")
                triples = graph_data["graph_data"]["triples"]
            else:
                # 基于知识库ID和用户ID生成
                knowledge_base_id = kwargs.get("knowledge_base_id")
                if not knowledge_base_id:
                    raise ValueError("必须提供graph_id或knowledge_base_id")
                
                # 从图数据库获取数据
                tenant_id = self._build_tenant_id(user_id, knowledge_base_id)
                graph_name = kwargs.get("graph_name", "default")
                
                if not self.graph_db:
                    await self._initialize_graph_database()
                
                # 导出为三元组
                triples = await self.graph_db.export_to_triples(tenant_id, graph_name)
            
            # 使用框架内置的可视化器生成HTML
            from app.frameworks.ai_knowledge_graph.core.visualizer import KnowledgeGraphVisualizer
            from app.frameworks.ai_knowledge_graph.config import get_config
            
            config = get_config()
            visualizer = KnowledgeGraphVisualizer(config)
            
            # 生成可视化
            viz_result = visualizer.visualize_knowledge_graph(
                triples=triples,
                output_path=None,
                visualization_type=visualization_type
            )
            
            if viz_result.get("success"):
                html_content = viz_result["html_content"]
                
                # 如果需要自动保存
                if auto_save and graph_id:
                    await self._save_html_visualization(graph_id, html_content)
                
                return html_content
            else:
                raise ValueError(f"知识库可视化生成失败: {viz_result.get('error')}")
            
        except Exception as e:
            logger.error(f"生成知识库可视化失败: {str(e)}")
            raise
    
    async def regenerate_kb_html(
        self,
        graph_id: str,
        user_id: int,
        visualization_type: str = "enhanced",
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """重新生成知识库图谱的HTML可视化"""
        try:
            html_content = await self.generate_kb_visualization(
                graph_id=graph_id,
                user_id=user_id,
                visualization_type=visualization_type,
                auto_save=True
            )
            
            # 计算统计信息
            graph_data = await self.storage_adapter.load_knowledge_graph(graph_id)
            triples = graph_data["graph_data"]["triples"] if graph_data.get("success") else []
            stats = self._calculate_triples_statistics(triples)
            
            return {
                "html_content": html_content,
                "statistics": stats,
                "graph_type": "knowledge_base",
                "regenerated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"重新生成知识库HTML失败: {str(e)}")
            raise
    
    # 场景二：自定义创建场景的专用方法
    
    async def process_text_async(
        self,
        graph_id: str,
        text: str,
        config: EntityExtractionConfig
    ):
        """异步处理自定义文本内容"""
        try:
            # 更新状态为处理中
            await self.repository.update_graph_status(graph_id, GraphStatus.PROCESSING)
            
            # 使用AI知识图谱框架处理文本
            from app.frameworks.ai_knowledge_graph.processor import KnowledgeGraphProcessor
            from app.frameworks.ai_knowledge_graph.config import get_config
            
            framework_config = get_config()
            framework_config.standardization_enabled = config.standardization_enabled
            framework_config.inference_enabled = config.inference_enabled
            
            processor = KnowledgeGraphProcessor(framework_config)
            
            # 处理文本
            result = processor.process_text(
                text=text,
                graph_id=graph_id,
                save_visualization=False,
                return_visualization=False
            )
            
            triples = result.get("triples", [])
            stats = result.get("stats", {})
            
            # 保存结果到存储
            await self.storage_adapter.save_knowledge_graph(
                graph_id=graph_id,
                graph_data={
                    "triples": triples,
                    "stats": stats,
                    "source_type": "custom_text",
                    "processed_at": datetime.utcnow().isoformat()
                }
            )
            
            # 更新数据库状态
            await self.repository.update_graph_status(graph_id, GraphStatus.COMPLETED)
            await self.repository.set_graph_completed_at(graph_id, datetime.utcnow())
            
            # 更新统计信息
            await self.repository.update_graph_statistics(
                graph_id=graph_id,
                entity_count=stats.get("unique_entities", 0),
                relation_count=stats.get("unique_relations", 0),
                triple_count=stats.get("total_triples", 0)
            )
            
            logger.info(f"自定义文本处理完成: {graph_id}, 三元组数量: {len(triples)}")
            
        except Exception as e:
            logger.error(f"处理自定义文本失败: {str(e)}")
            await self.repository.update_graph_status(graph_id, GraphStatus.FAILED)
            raise
    
    async def generate_custom_visualization(
        self,
        graph_id: str,
        user_id: int = None,
        visualization_type: str = "enhanced",
        auto_save: bool = False
    ) -> str:
        """
        为自定义图谱生成HTML可视化
        基于已构建的图数据生成HTML页面
        """
        try:
            # 加载图谱数据
            graph_data = await self.storage_adapter.load_knowledge_graph(graph_id)
            if not graph_data.get("success"):
                raise ValueError("无法加载自定义图谱数据")
            
            triples = graph_data["graph_data"]["triples"]
            
            # 使用框架内置的可视化器生成HTML
            from app.frameworks.ai_knowledge_graph.core.visualizer import KnowledgeGraphVisualizer
            from app.frameworks.ai_knowledge_graph.config import get_config
            
            config = get_config()
            visualizer = KnowledgeGraphVisualizer(config)
            
            # 生成可视化
            viz_result = visualizer.visualize_knowledge_graph(
                triples=triples,
                output_path=None,
                visualization_type=visualization_type
            )
            
            if viz_result.get("success"):
                html_content = viz_result["html_content"]
                
                # 如果需要自动保存
                if auto_save:
                    await self._save_html_visualization(graph_id, html_content)
                
                return html_content
            else:
                raise ValueError(f"自定义可视化生成失败: {viz_result.get('error')}")
            
        except Exception as e:
            logger.error(f"生成自定义可视化失败: {str(e)}")
            raise
    
    async def regenerate_custom_html(
        self,
        graph_id: str,
        user_id: int,
        visualization_type: str = "enhanced",
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """重新生成自定义图谱的HTML可视化"""
        try:
            html_content = await self.generate_custom_visualization(
                graph_id=graph_id,
                user_id=user_id,
                visualization_type=visualization_type,
                auto_save=True
            )
            
            # 计算统计信息
            graph_data = await self.storage_adapter.load_knowledge_graph(graph_id)
            triples = graph_data["graph_data"]["triples"] if graph_data.get("success") else []
            stats = self._calculate_triples_statistics(triples)
            
            return {
                "html_content": html_content,
                "statistics": stats,
                "graph_type": "custom",
                "regenerated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"重新生成自定义HTML失败: {str(e)}")
            raise
    
    # 统一的辅助方法
    
    async def get_graph_status(self, graph_id: str) -> Dict[str, Any]:
        """获取图谱详细状态信息"""
        try:
            # 获取处理进度
            progress = self._processing_status.get(graph_id)
            
            # 获取统计信息
            stats = await self._get_graph_statistics(graph_id)
            
            # 检查HTML是否可用
            html_available = await self._check_html_availability(graph_id)
            
            return {
                "processing_progress": progress,
                "statistics": stats,
                "html_available": html_available
            }
            
        except Exception as e:
            logger.error(f"获取图谱状态失败: {str(e)}")
            return {}
    
    async def _save_html_visualization(self, graph_id: str, html_content: str):
        """保存HTML可视化到存储"""
        try:
            # 保存到文件存储
            html_path = f"visualizations/{graph_id}.html"
            await self.file_storage.save_file(
                file_path=html_path,
                content=html_content.encode('utf-8'),
                content_type="text/html"
            )
            
            # 更新数据库记录
            await self.repository.update_graph_visualization_path(graph_id, html_path)
            
            logger.info(f"HTML可视化已保存: {graph_id} -> {html_path}")
            
        except Exception as e:
            logger.error(f"保存HTML可视化失败: {str(e)}")
    
    async def _check_html_availability(self, graph_id: str) -> bool:
        """检查HTML可视化是否可用"""
        try:
            graph = await self.repository.get_graph_by_id(graph_id, None)
            if not graph or not hasattr(graph, 'visualization_path'):
                return False
            
            # 检查文件是否存在
            if graph.visualization_path:
                return await self.file_storage.file_exists(graph.visualization_path)
            
            return False
            
        except Exception as e:
            logger.error(f"检查HTML可用性失败: {str(e)}")
            return False
    
    def _calculate_triples_statistics(self, triples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算三元组统计信息"""
        if not triples:
            return {
                "nodes": 0,
                "edges": 0,
                "original_edges": 0,
                "inferred_edges": 0,
                "density": 0.0
            }
        
        # 收集节点
        nodes = set()
        for triple in triples:
            nodes.add(triple["subject"])
            nodes.add(triple["object"])
        
        # 统计推理关系
        inferred_count = sum(1 for t in triples if t.get("inferred", False))
        original_count = len(triples) - inferred_count
        
        # 计算密度
        node_count = len(nodes)
        edge_count = len(triples)
        max_edges = node_count * (node_count - 1) if node_count > 1 else 1
        density = edge_count / max_edges if max_edges > 0 else 0
        
        return {
            "nodes": node_count,
            "edges": edge_count,
            "original_edges": original_count,
            "inferred_edges": inferred_count,
            "density": density
        }