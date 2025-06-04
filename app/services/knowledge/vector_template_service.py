"""
向量化模板管理服务
提供向量化模板的加载、选择、应用和管理功能
"""

import yaml
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.utils.storage.core.vector_factory import VectorStorageFactory, VectorBackendType
from app.utils.storage.vector_storage.template_loader import VectorStoreTemplateLoader
from app.models.knowledge import KnowledgeBase
from app.repositories.knowledge import KnowledgeBaseRepository

logger = logging.getLogger(__name__)


class VectorTemplateService:
    """向量化模板管理服务"""
    
    def __init__(self, db: Session):
        """
        初始化模板服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.kb_repo = KnowledgeBaseRepository(db)
        
        # 加载行业模板配置
        template_file = Path(__file__).parent.parent.parent / "config" / "vector_templates_industry.yaml"
        self.industry_templates = self._load_industry_templates(template_file)
        
        # 加载向量存储模板
        self.vector_template_loader = VectorStoreTemplateLoader()
        
        logger.info("向量化模板服务初始化完成")
    
    def _load_industry_templates(self, template_file: Path) -> Dict[str, Any]:
        """加载行业模板配置"""
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载行业模板配置失败: {str(e)}")
            return {}
    
    def list_available_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取所有可用的向量化模板
        
        Returns:
            按行业分类的模板列表
        """
        try:
            templates_by_industry = {}
            industry_templates = self.industry_templates.get("industry_templates", {})
            
            for template_name, template_config in industry_templates.items():
                industry = template_config.get("industry", "general")
                
                if industry not in templates_by_industry:
                    templates_by_industry[industry] = []
                
                template_info = {
                    "template_id": template_name,
                    "name": template_config.get("name", template_name),
                    "description": template_config.get("description", ""),
                    "scenario": template_config.get("scenario", ""),
                    "industry": industry,
                    "vectorization_config": template_config.get("vectorization_config", {}),
                    "search_config": template_config.get("search_config", {})
                }
                
                templates_by_industry[industry].append(template_info)
            
            return templates_by_industry
            
        except Exception as e:
            logger.error(f"获取可用模板失败: {str(e)}")
            return {}
    
    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取模板配置
        
        Args:
            template_id: 模板ID
            
        Returns:
            模板配置或None
        """
        try:
            industry_templates = self.industry_templates.get("industry_templates", {})
            return industry_templates.get(template_id)
        except Exception as e:
            logger.error(f"获取模板 {template_id} 失败: {str(e)}")
            return None
    
    def recommend_template(self, 
                          content_type: str = None,
                          industry: str = None,
                          use_case: str = None,
                          document_count: int = None) -> List[Dict[str, Any]]:
        """
        推荐适合的向量化模板
        
        Args:
            content_type: 内容类型 (document, qa, manual等)
            industry: 行业类型
            use_case: 使用场景
            document_count: 文档数量
            
        Returns:
            推荐的模板列表，按适合度排序
        """
        try:
            recommendations = []
            industry_templates = self.industry_templates.get("industry_templates", {})
            
            for template_id, template_config in industry_templates.items():
                score = 0
                template_industry = template_config.get("industry", "general")
                template_scenario = template_config.get("scenario", "")
                
                # 行业匹配
                if industry:
                    if template_industry == industry:
                        score += 40
                    elif template_industry == "general":
                        score += 10
                
                # 内容类型匹配
                if content_type:
                    if content_type in template_scenario:
                        score += 30
                    elif content_type in template_id:
                        score += 20
                
                # 使用场景匹配
                if use_case:
                    if use_case in template_scenario:
                        score += 20
                
                # 文档数量考虑
                if document_count:
                    vectorization_config = template_config.get("vectorization_config", {})
                    chunk_size = vectorization_config.get("chunk_size", 1000)
                    
                    if document_count < 100:
                        # 小规模：偏向简单配置
                        if chunk_size <= 1000:
                            score += 10
                    elif document_count > 10000:
                        # 大规模：偏向高性能配置
                        index_config = template_config.get("index_config", {})
                        vector_index = index_config.get("vector_index", {})
                        if vector_index.get("type") == "HNSW":
                            score += 15
                
                if score > 0:
                    recommendation = {
                        "template_id": template_id,
                        "name": template_config.get("name", template_id),
                        "description": template_config.get("description", ""),
                        "industry": template_industry,
                        "scenario": template_scenario,
                        "score": score,
                        "config": template_config
                    }
                    recommendations.append(recommendation)
            
            # 按评分排序
            recommendations.sort(key=lambda x: x["score"], reverse=True)
            return recommendations[:5]  # 返回前5个推荐
            
        except Exception as e:
            logger.error(f"推荐模板失败: {str(e)}")
            return []
    
    async def apply_template_to_knowledge_base(self,
                                             kb_id: str,
                                             template_id: str,
                                             backend_type: VectorBackendType = VectorBackendType.MILVUS,
                                             custom_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        将模板应用到知识库
        
        Args:
            kb_id: 知识库ID
            template_id: 模板ID
            backend_type: 向量数据库后端类型
            custom_config: 自定义配置覆盖
            
        Returns:
            应用结果
        """
        try:
            # 获取知识库
            kb = await self.kb_repo.get_by_id(kb_id)
            if not kb:
                return {
                    "success": False,
                    "error": f"知识库 {kb_id} 不存在"
                }
            
            # 获取模板配置
            template_config = self.get_template_by_id(template_id)
            if not template_config:
                return {
                    "success": False,
                    "error": f"模板 {template_id} 不存在"
                }
            
            # 构建向量存储配置
            vector_config = self._build_vector_config(
                template_config, 
                backend_type, 
                template_id, 
                custom_config
            )
            
            # 创建向量存储实例
            vector_store = VectorStorageFactory.create_vector_store(
                backend_type=backend_type,
                name=f"kb_{kb_id}",
                config=vector_config
            )
            
            # 初始化向量存储
            await vector_store.initialize()
            
            # 创建集合/表
            collection_name = f"kb_{kb_id}"
            dimension = vector_config.get("dimension", 1536)
            
            success = await vector_store.create_collection(
                name=collection_name,
                dimension=dimension,
                **vector_config
            )
            
            if success:
                # 更新知识库配置
                kb_settings = kb.settings or {}
                kb_settings.update({
                    "vector_template_id": template_id,
                    "vector_backend": backend_type.value,
                    "vector_config": vector_config,
                    "applied_at": datetime.now().isoformat()
                })
                
                await self.kb_repo.update(kb_id, {"settings": kb_settings})
                
                logger.info(f"成功将模板 {template_id} 应用到知识库 {kb_id}")
                
                return {
                    "success": True,
                    "data": {
                        "kb_id": kb_id,
                        "template_id": template_id,
                        "backend_type": backend_type.value,
                        "collection_name": collection_name,
                        "vector_config": vector_config
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "创建向量集合失败"
                }
            
        except Exception as e:
            logger.error(f"应用模板到知识库失败: {str(e)}")
            return {
                "success": False,
                "error": f"应用模板失败: {str(e)}"
            }
    
    def _build_vector_config(self,
                           template_config: Dict[str, Any],
                           backend_type: VectorBackendType,
                           template_id: str,
                           custom_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """构建向量存储配置"""
        try:
            # 基础配置
            vectorization_config = template_config.get("vectorization_config", {})
            index_config = template_config.get("index_config", {})
            metadata_schema = template_config.get("metadata_schema", {})
            
            # 构建向量配置
            vector_config = {
                "dimension": 1536,  # 默认OpenAI embedding维度
                "embedding_model": vectorization_config.get("embedding_model", "text-embedding-ada-002"),
                "chunk_size": vectorization_config.get("chunk_size", 1000),
                "chunk_overlap": vectorization_config.get("chunk_overlap", 200),
                "chunk_strategy": vectorization_config.get("chunk_strategy", "paragraph"),
                "language": vectorization_config.get("language", "auto"),
            }
            
            # 索引配置
            vector_index_config = index_config.get("vector_index", {})
            vector_config.update({
                "index_type": vector_index_config.get("type", "HNSW"),
                "metric_type": vector_index_config.get("metric", "cosine"),
                "index_params": vector_index_config.get("parameters", {})
            })
            
            # 元数据字段配置
            fields_template = metadata_schema.get("fields", "")
            if fields_template:
                metadata_fields = self.industry_templates.get("metadata_field_templates", {}).get(fields_template, [])
                vector_config["metadata_fields"] = metadata_fields
                vector_config["required_fields"] = metadata_schema.get("required_fields", [])
                vector_config["searchable_fields"] = metadata_schema.get("searchable_fields", [])
                vector_config["filterable_fields"] = metadata_schema.get("filterable_fields", [])
            
            # 后端特定配置
            backend_configs = self.industry_templates.get("backend_specific_configs", {})
            backend_name = backend_type.value.lower()
            
            if backend_name in backend_configs:
                backend_config = backend_configs[backend_name]
                # 尝试获取模板特定的配置
                template_key = template_id.replace("_template", "")
                if template_key in backend_config:
                    vector_config.update(backend_config[template_key])
            
            # 应用自定义配置覆盖
            if custom_config:
                vector_config.update(custom_config)
            
            return vector_config
            
        except Exception as e:
            logger.error(f"构建向量配置失败: {str(e)}")
            return {}
    
    def get_template_metadata_schema(self, template_id: str) -> Dict[str, Any]:
        """
        获取模板的元数据schema
        
        Args:
            template_id: 模板ID
            
        Returns:
            元数据schema配置
        """
        try:
            template_config = self.get_template_by_id(template_id)
            if not template_config:
                return {}
            
            metadata_schema = template_config.get("metadata_schema", {})
            fields_template = metadata_schema.get("fields", "")
            
            if fields_template:
                metadata_fields = self.industry_templates.get("metadata_field_templates", {}).get(fields_template, [])
                return {
                    "fields": metadata_fields,
                    "required_fields": metadata_schema.get("required_fields", []),
                    "searchable_fields": metadata_schema.get("searchable_fields", []),
                    "filterable_fields": metadata_schema.get("filterable_fields", [])
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"获取模板元数据schema失败: {str(e)}")
            return {}
    
    def validate_template_compatibility(self,
                                      template_id: str,
                                      backend_type: VectorBackendType,
                                      document_count: int = None,
                                      storage_size_mb: int = None) -> Dict[str, Any]:
        """
        验证模板与后端的兼容性
        
        Args:
            template_id: 模板ID
            backend_type: 后端类型
            document_count: 预期文档数量
            storage_size_mb: 预期存储大小(MB)
            
        Returns:
            兼容性检查结果
        """
        try:
            template_config = self.get_template_by_id(template_id)
            if not template_config:
                return {
                    "compatible": False,
                    "error": "模板不存在"
                }
            
            warnings = []
            recommendations = []
            
            # 检查后端配置支持
            backend_configs = self.industry_templates.get("backend_specific_configs", {})
            backend_name = backend_type.value.lower()
            
            if backend_name not in backend_configs:
                warnings.append(f"后端 {backend_name} 没有特定配置，将使用默认配置")
            
            # 检查索引类型支持
            index_config = template_config.get("index_config", {})
            vector_index = index_config.get("vector_index", {})
            index_type = vector_index.get("type", "HNSW")
            
            # 不同后端的索引类型支持检查
            if backend_type == VectorBackendType.PGVECTOR:
                if index_type not in ["HNSW", "IVFFLAT"]:
                    warnings.append(f"PostgreSQL+pgvector 不支持索引类型 {index_type}，建议使用 HNSW 或 IVFFLAT")
            elif backend_type == VectorBackendType.ELASTICSEARCH:
                if index_type != "DENSE_VECTOR":
                    warnings.append(f"Elasticsearch 将使用 DENSE_VECTOR 替代 {index_type}")
            
            # 性能预估
            if document_count:
                vectorization_config = template_config.get("vectorization_config", {})
                chunk_size = vectorization_config.get("chunk_size", 1000)
                estimated_chunks = document_count * 10  # 粗略估算：每个文档约10个chunk
                
                if estimated_chunks > 100000:
                    if index_type == "IVFFLAT":
                        recommendations.append("大量数据建议使用 HNSW 索引以获得更好的查询性能")
                    if backend_type == VectorBackendType.MILVUS:
                        recommendations.append("建议启用分区功能以提高大规模数据的管理效率")
            
            return {
                "compatible": True,
                "warnings": warnings,
                "recommendations": recommendations,
                "estimated_performance": self._estimate_performance(template_config, document_count)
            }
            
        except Exception as e:
            logger.error(f"验证模板兼容性失败: {str(e)}")
            return {
                "compatible": False,
                "error": f"兼容性检查失败: {str(e)}"
            }
    
    def _estimate_performance(self, template_config: Dict[str, Any], document_count: int = None) -> Dict[str, Any]:
        """估算性能指标"""
        try:
            performance = {
                "search_latency": "medium",
                "indexing_speed": "medium",
                "memory_usage": "medium",
                "accuracy": "high"
            }
            
            if not document_count:
                return performance
            
            index_config = template_config.get("index_config", {})
            vector_index = index_config.get("vector_index", {})
            index_type = vector_index.get("type", "HNSW")
            
            # 基于索引类型和数据量的性能估算
            if index_type == "HNSW":
                if document_count < 10000:
                    performance["search_latency"] = "low"
                    performance["accuracy"] = "very_high"
                elif document_count > 100000:
                    performance["memory_usage"] = "high"
                    performance["indexing_speed"] = "slow"
            elif index_type == "IVFFLAT":
                performance["indexing_speed"] = "fast"
                if document_count > 50000:
                    performance["search_latency"] = "medium"
                    performance["accuracy"] = "medium"
            
            return performance
            
        except Exception as e:
            logger.error(f"性能估算失败: {str(e)}")
            return {}


# 全局实例获取函数
def get_vector_template_service(db: Session) -> VectorTemplateService:
    """获取向量模板服务实例"""
    return VectorTemplateService(db) 