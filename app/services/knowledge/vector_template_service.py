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
    
    def get_available_templates(self, industry: str = None) -> List[Dict[str, Any]]:
        """
        获取可用的向量化模板列表
        
        Args:
            industry: 可选的行业筛选
            
        Returns:
            模板列表
        """
        try:
            templates = []
            industry_templates = self.industry_templates.get("industry_templates", {})
            
            for template_id, template_config in industry_templates.items():
                template_info = {
                    "id": template_id,
                    "name": template_config.get("name", template_id),
                    "description": template_config.get("description", ""),
                    "industry": template_config.get("industry", "general"),
                    "scenario": template_config.get("scenario", ""),
                    "metadata_fields": self._get_template_fields(template_config),
                    "vectorization_features": self._extract_vectorization_features(template_config)
                }
                
                # 行业筛选
                if industry and template_info["industry"] != industry and template_info["industry"] != "general":
                    continue
                    
                templates.append(template_info)
            
            return templates
            
        except Exception as e:
            logger.error(f"获取模板列表失败: {str(e)}")
            return []
    
    def _get_template_fields(self, template_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取模板的元数据字段信息"""
        metadata_schema = template_config.get("metadata_schema", {})
        fields_ref = metadata_schema.get("fields", "")
        
        if fields_ref and fields_ref in self.industry_templates.get("metadata_fields", {}):
            field_definitions = self.industry_templates["metadata_fields"][fields_ref]
            return [
                {
                    "name": field.get("name"),
                    "data_type": field.get("data_type"),
                    "description": field.get("description"),
                    "required": field.get("name") in metadata_schema.get("required_fields", []),
                    "searchable": field.get("name") in metadata_schema.get("searchable_fields", []),
                    "filterable": field.get("name") in metadata_schema.get("filterable_fields", [])
                }
                for field in field_definitions
            ]
        return []
    
    def _extract_vectorization_features(self, template_config: Dict[str, Any]) -> Dict[str, Any]:
        """提取向量化特性"""
        vectorization_config = template_config.get("vectorization_config", {})
        search_config = template_config.get("search_config", {})
        
        return {
            "chunk_size": vectorization_config.get("chunk_size", 1000),
            "chunk_strategy": vectorization_config.get("chunk_strategy", "general"),
            "language": vectorization_config.get("language", "auto"),
            "embedding_model": vectorization_config.get("embedding_model", "text-embedding-ada-002"),
            "similarity_threshold": search_config.get("similarity_threshold", 0.7),
            "hybrid_search": search_config.get("hybrid_search", {}).get("enabled", False),
            "special_features": self._extract_special_features(vectorization_config)
        }
    
    def _extract_special_features(self, vectorization_config: Dict[str, Any]) -> List[str]:
        """提取特殊处理功能"""
        features = []
        if vectorization_config.get("structured_data_processing"):
            features.append("结构化数据处理")
        if vectorization_config.get("table_aware"):
            features.append("表格识别")
        if vectorization_config.get("legal_document_processing"):
            features.append("法律文档处理")
        if vectorization_config.get("policy_reference_extraction"):
            features.append("政策引用提取")
        if vectorization_config.get("citizen_friendly_processing"):
            features.append("民生服务导向")
        return features

    def recommend_template(self, 
                          content_type: str = None,
                          industry: str = None,
                          use_case: str = None,
                          document_count: int = None,
                          content_complexity: str = None,
                          service_type: str = None) -> List[Dict[str, Any]]:
        """
        基于场景推荐合适的向量化模板
        
        Args:
            content_type: 内容类型
            industry: 行业
            use_case: 使用场景
            document_count: 文档数量
            content_complexity: 内容复杂度 (simple/medium/complex)
            service_type: 服务类型 (针对政府服务)
            
        Returns:
            推荐的模板列表，按推荐度排序
        """
        try:
            recommendations = []
            industry_templates = self.industry_templates.get("industry_templates", {})
            
            for template_id, template_config in industry_templates.items():
                score = 0
                template_industry = template_config.get("industry", "general")
                template_scenario = template_config.get("scenario", "")
                
                # 行业匹配 (40分)
                if industry:
                    if template_industry == industry:
                        score += 40
                    elif template_industry == "general":
                        score += 10
                
                # 内容类型匹配 (30分)
                if content_type:
                    if content_type in template_scenario:
                        score += 30
                    elif content_type in template_id:
                        score += 20
                
                # 使用场景匹配 (20分)
                if use_case:
                    if use_case in template_scenario:
                        score += 20
                
                # 特殊：政府服务类型匹配 (25分)
                if service_type and industry == "government":
                    score += self._calculate_government_service_score(template_id, service_type)
                
                # 内容复杂度匹配 (15分)
                if content_complexity:
                    score += self._calculate_complexity_score(template_config, content_complexity)
                
                # 文档数量考虑 (10分)
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
                    recommendations.append({
                        "template_id": template_id,
                        "name": template_config.get("name", template_id),
                        "description": template_config.get("description", ""),
                        "score": score,
                        "match_reasons": self._get_match_reasons(template_config, industry, content_type, use_case),
                        "industry": template_industry,
                        "scenario": template_scenario
                    })
            
            # 按评分排序
            recommendations.sort(key=lambda x: x["score"], reverse=True)
            return recommendations[:5]  # 返回前5个推荐
            
        except Exception as e:
            logger.error(f"模板推荐失败: {str(e)}")
            return []
    
    def _calculate_government_service_score(self, template_id: str, service_type: str) -> int:
        """计算政府服务类型匹配分数"""
        service_mapping = {
            "real_estate": ["real_estate_registration_template"],
            "property_registration": ["real_estate_registration_template"],
            "mortgage_registration": ["real_estate_registration_template"],
            "social_security": ["social_security_template"],
            "insurance": ["social_security_template"],
            "benefit_application": ["social_security_template"],
            "general_service": ["government_service_template"]
        }
        
        for service_key, templates in service_mapping.items():
            if service_type.lower() in service_key or service_key in service_type.lower():
                if template_id in templates:
                    return 25
        
        return 0
    
    def _calculate_complexity_score(self, template_config: Dict[str, Any], complexity: str) -> int:
        """计算复杂度匹配分数"""
        vectorization_config = template_config.get("vectorization_config", {})
        
        if complexity == "simple":
            # 简单内容偏向小chunk和基础处理
            if vectorization_config.get("chunk_size", 1000) <= 800:
                return 15
            return 5
        elif complexity == "complex":
            # 复杂内容偏向大chunk和特殊处理
            if (vectorization_config.get("chunk_size", 1000) >= 1000 or 
                vectorization_config.get("legal_document_processing") or
                vectorization_config.get("policy_reference_extraction")):
                return 15
            return 5
        else:  # medium
            return 10
    
    def _get_match_reasons(self, template_config: Dict[str, Any], industry: str, 
                          content_type: str, use_case: str) -> List[str]:
        """获取匹配原因"""
        reasons = []
        template_industry = template_config.get("industry", "general")
        template_scenario = template_config.get("scenario", "")
        
        if industry and template_industry == industry:
            reasons.append(f"行业匹配: {industry}")
        if content_type and content_type in template_scenario:
            reasons.append(f"内容类型匹配: {content_type}")
        if use_case and use_case in template_scenario:
            reasons.append(f"使用场景匹配: {use_case}")
            
        return reasons

    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取模板详情
        
        Args:
            template_id: 模板ID
            
        Returns:
            模板详细信息
        """
        try:
            industry_templates = self.industry_templates.get("industry_templates", {})
            if template_id not in industry_templates:
                return None
                
            template_config = industry_templates[template_id]
            
            return {
                "id": template_id,
                "name": template_config.get("name", template_id),
                "description": template_config.get("description", ""),
                "industry": template_config.get("industry", "general"),
                "scenario": template_config.get("scenario", ""),
                "metadata_schema": template_config.get("metadata_schema", {}),
                "vectorization_config": template_config.get("vectorization_config", {}),
                "index_config": template_config.get("index_config", {}),
                "search_config": template_config.get("search_config", {}),
                "metadata_fields": self._get_template_fields(template_config),
                "field_combinations": self._get_field_combinations(template_config)
            }
            
        except Exception as e:
            logger.error(f"获取模板详情失败: {str(e)}, template_id: {template_id}")
            return None
    
    def _get_field_combinations(self, template_config: Dict[str, Any]) -> Dict[str, List[str]]:
        """获取字段组合建议（用于复杂场景的字段动态组合）"""
        metadata_schema = template_config.get("metadata_schema", {})
        fields_ref = metadata_schema.get("fields", "")
        
        combinations = {
            "basic_fields": metadata_schema.get("required_fields", []),
            "search_optimized": metadata_schema.get("searchable_fields", []),
            "filter_optimized": metadata_schema.get("filterable_fields", [])
        }
        
        # 针对政府服务的特殊字段组合
        if "government" in template_config.get("industry", ""):
            combinations.update({
                "citizen_focused": [
                    "service_name", "service_department", "target_audience", 
                    "service_conditions", "required_materials", "contact_info"
                ],
                "fee_focused": [
                    "service_name", "fee_type", "is_free", "fee_standard", "fee_basis"
                ],
                "process_focused": [
                    "service_name", "process_steps", "legal_deadline", 
                    "actual_deadline", "service_channels"
                ]
            })
            
            # 针对不动产登记的专门组合
            if "real_estate" in template_config.get("scenario", ""):
                combinations["legal_focused"] = [
                    "service_name", "registration_type", "property_type",
                    "fee_calculation_rules", "policy_references", "special_conditions"
                ]
        
        return combinations

    def get_compatible_backends(self, template_id: str) -> List[Dict[str, Any]]:
        """
        获取模板兼容的向量数据库后端
        
        Args:
            template_id: 模板ID
            
        Returns:
            兼容的后端列表及其配置
        """
        try:
            compatible_backends = []
            backend_configs = self.industry_templates.get("backend_specific_configs", {})
            
            for backend_name, backend_config in backend_configs.items():
                if template_id in backend_config:
                    backend_info = {
                        "backend": backend_name,
                        "config": backend_config[template_id],
                        "recommended": False
                    }
                    
                    # 根据模板特性推荐后端
                    template_config = self.industry_templates.get("industry_templates", {}).get(template_id, {})
                    vectorization_config = template_config.get("vectorization_config", {})
                    
                    if backend_name == "milvus" and vectorization_config.get("chunk_size", 1000) > 1000:
                        backend_info["recommended"] = True
                    elif backend_name == "pgvector" and vectorization_config.get("chunk_size", 1000) <= 1000:
                        backend_info["recommended"] = True
                        
                    compatible_backends.append(backend_info)
            
            return compatible_backends
            
        except Exception as e:
            logger.error(f"获取兼容后端失败: {str(e)}")
            return []

    def create_custom_template(self, base_template_id: str, custom_config: Dict[str, Any], 
                             template_name: str) -> Dict[str, Any]:
        """
        基于现有模板创建自定义模板
        
        Args:
            base_template_id: 基础模板ID
            custom_config: 自定义配置
            template_name: 自定义模板名称
            
        Returns:
            创建的自定义模板信息
        """
        try:
            base_template = self.get_template_by_id(base_template_id)
            if not base_template:
                raise ValueError(f"基础模板不存在: {base_template_id}")
            
            custom_template_id = f"custom_{uuid.uuid4().hex[:8]}"
            
            # 合并配置
            custom_template = {
                "id": custom_template_id,
                "name": template_name,
                "description": f"基于 {base_template['name']} 的自定义模板",
                "base_template": base_template_id,
                "industry": base_template["industry"],
                "scenario": base_template["scenario"],
                "metadata_schema": base_template["metadata_schema"].copy(),
                "vectorization_config": base_template["vectorization_config"].copy(),
                "index_config": base_template["index_config"].copy(),
                "search_config": base_template["search_config"].copy(),
                "created_at": datetime.now().isoformat(),
                "custom": True
            }
            
            # 应用自定义配置
            if "vectorization_overrides" in custom_config:
                custom_template["vectorization_config"].update(custom_config["vectorization_overrides"])
                
            if "custom_fields" in custom_config:
                # 添加自定义字段（这里可以扩展实现）
                pass
            
            logger.info(f"创建自定义模板成功: {custom_template_id}")
            return custom_template
            
        except Exception as e:
            logger.error(f"创建自定义模板失败: {str(e)}")
            raise

    def apply_template_to_knowledge_base(self, kb_id: str, template_id: str, 
                                       backend_type: VectorBackendType,
                                       custom_config: Dict[str, Any] = None) -> bool:
        """
        将模板应用到知识库
        
        Args:
            kb_id: 知识库ID
            template_id: 模板ID
            backend_type: 向量数据库后端类型
            custom_config: 自定义配置
            
        Returns:
            应用成功状态
        """
        try:
            # 获取知识库
            kb = self.kb_repo.get_by_id(kb_id)
            if not kb:
                raise ValueError(f"知识库不存在: {kb_id}")
            
            # 获取模板
            template = self.get_template_by_id(template_id)
            if not template:
                raise ValueError(f"模板不存在: {template_id}")
            
            # 检查后端兼容性
            compatible_backends = self.get_compatible_backends(template_id)
            backend_names = [b["backend"] for b in compatible_backends]
            
            if backend_type.value not in backend_names:
                logger.warning(f"模板 {template_id} 可能不完全兼容后端 {backend_type.value}")
            
            # 准备向量存储配置
            vector_config = template["vectorization_config"].copy()
            if custom_config:
                vector_config.update(custom_config)
            
            # 创建向量存储
            vector_storage = VectorStorageFactory.create_storage(
                backend_type=backend_type,
                collection_name=f"kb_{kb_id}",
                **vector_config
            )
            
            # 更新知识库配置
            kb.vector_template_id = template_id
            kb.vector_backend_type = backend_type.value
            kb.vector_config = vector_config
            kb.updated_at = datetime.now()
            
            self.db.commit()
            
            logger.info(f"模板应用成功: kb_id={kb_id}, template_id={template_id}")
            return True
            
        except Exception as e:
            logger.error(f"应用模板失败: {str(e)}")
            self.db.rollback()
            return False

    def get_metadata_schema(self, template_id: str) -> Dict[str, Any]:
        """
        获取模板的元数据模式
        
        Args:
            template_id: 模板ID
            
        Returns:
            元数据模式信息
        """
        try:
            template = self.get_template_by_id(template_id)
            if not template:
                return {}
            
            metadata_schema = template.get("metadata_schema", {})
            field_definitions = template.get("metadata_fields", [])
            
            return {
                "schema": metadata_schema,
                "fields": field_definitions,
                "field_combinations": template.get("field_combinations", {}),
                "validation_rules": self._get_validation_rules(field_definitions)
            }
            
        except Exception as e:
            logger.error(f"获取元数据模式失败: {str(e)}")
            return {}
    
    def _get_validation_rules(self, field_definitions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取字段验证规则"""
        rules = {}
        for field in field_definitions:
            field_name = field.get("name")
            if field_name:
                rules[field_name] = {
                    "required": not field.get("nullable", True),
                    "data_type": field.get("data_type"),
                    "max_length": field.get("max_length")
                }
        return rules


# 全局实例获取函数
def get_vector_template_service(db: Session) -> VectorTemplateService:
    """获取向量模板服务实例"""
    return VectorTemplateService(db) 