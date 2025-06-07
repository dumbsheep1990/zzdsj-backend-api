"""
向量化模板管理API
提供向量化模板的选择、推荐和应用功能
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging

# 导入依赖
from app.utils.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.api.frontend.dependencies import ResponseFormatter

# 导入服务
from app.services.knowledge.vector_template_service import get_vector_template_service, VectorTemplateService
from app.utils.storage.core.vector_factory import VectorBackendType

# 导入Pydantic模型
from pydantic import BaseModel, Field

# 导入表格向量化工具
from app.tools.advanced.structured_data.table_vectorizer import TableVectorizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge/vector-templates", tags=["向量化模板"])

# Pydantic 模型定义
class TemplateRecommendationRequest(BaseModel):
    """模板推荐请求"""
    content_type: Optional[str] = Field(None, description="内容类型")
    industry: Optional[str] = Field(None, description="行业类型")
    use_case: Optional[str] = Field(None, description="使用场景")
    document_count: Optional[int] = Field(None, description="预期文档数量")
    storage_size_mb: Optional[int] = Field(None, description="预期存储大小(MB)")

class ApplyTemplateRequest(BaseModel):
    """应用模板请求"""
    kb_id: str = Field(..., description="知识库ID")
    template_id: str = Field(..., description="模板ID")
    backend_type: str = Field("milvus", description="向量数据库后端类型")
    custom_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="自定义配置")

class TemplateCompatibilityRequest(BaseModel):
    """模板兼容性检查请求"""
    template_id: str = Field(..., description="模板ID")
    backend_type: str = Field("milvus", description="向量数据库后端类型")
    document_count: Optional[int] = Field(None, description="预期文档数量")
    storage_size_mb: Optional[int] = Field(None, description="预期存储大小(MB)")


# ========== 向量化模板管理接口 ==========

@router.get("/list")
async def list_templates(
    industry: Optional[str] = Query(None, description="行业筛选"),
    db: Session = Depends(get_db)
):
    """
    获取可用的向量化模板列表
    
    Args:
        industry: 行业筛选（可选）
    """
    try:
        template_service = VectorTemplateService(db)
        templates = template_service.get_available_templates(industry)
        
        return {
            "success": True,
            "data": templates,
            "total": len(templates)
        }
    except Exception as e:
        logger.error(f"获取模板列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取模板列表失败: {str(e)}")

@router.post("/recommend")
async def recommend_templates(
    recommendation_request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    推荐适合的向量化模板
    
    Args:
        recommendation_request: 推荐请求参数
    """
    try:
        template_service = VectorTemplateService(db)
        
        recommendations = template_service.recommend_template(
            content_type=recommendation_request.get("content_type"),
            industry=recommendation_request.get("industry"),
            use_case=recommendation_request.get("use_case"),
            document_count=recommendation_request.get("document_count"),
            content_complexity=recommendation_request.get("content_complexity"),
            service_type=recommendation_request.get("service_type")
        )
        
        return {
            "success": True,
            "data": recommendations,
            "recommendation_count": len(recommendations)
        }
    except Exception as e:
        logger.error(f"模板推荐失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"模板推荐失败: {str(e)}")

@router.get("/{template_id}")
async def get_template_detail(
    template_id: str,
    db: Session = Depends(get_db)
):
    """
    获取模板详细信息
    
    Args:
        template_id: 模板ID
    """
    try:
        template_service = VectorTemplateService(db)
        template = template_service.get_template_by_id(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        return {
            "success": True,
            "data": template
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模板详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取模板详情失败: {str(e)}")

@router.get("/{template_id}/backends")
async def get_compatible_backends(
    template_id: str,
    db: Session = Depends(get_db)
):
    """
    获取模板兼容的向量数据库后端
    
    Args:
        template_id: 模板ID
    """
    try:
        template_service = VectorTemplateService(db)
        backends = template_service.get_compatible_backends(template_id)
        
        return {
            "success": True,
            "data": backends
        }
    except Exception as e:
        logger.error(f"获取兼容后端失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取兼容后端失败: {str(e)}")

@router.get("/{template_id}/metadata-schema")
async def get_metadata_schema(
    template_id: str,
    db: Session = Depends(get_db)
):
    """
    获取模板的元数据模式
    
    Args:
        template_id: 模板ID
    """
    try:
        template_service = VectorTemplateService(db)
        schema = template_service.get_metadata_schema(template_id)
        
        return {
            "success": True,
            "data": schema
        }
    except Exception as e:
        logger.error(f"获取元数据模式失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取元数据模式失败: {str(e)}")

@router.post("/{template_id}/apply")
async def apply_template(
    template_id: str,
    apply_request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    将模板应用到知识库
    
    Args:
        template_id: 模板ID
        apply_request: 应用请求参数
    """
    try:
        template_service = VectorTemplateService(db)
        
        kb_id = apply_request.get("kb_id")
        if not kb_id:
            raise HTTPException(status_code=400, detail="知识库ID不能为空")
        
        backend_type_str = apply_request.get("backend_type", "milvus")
        try:
            backend_type = VectorBackendType(backend_type_str.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"不支持的后端类型: {backend_type_str}")
        
        custom_config = apply_request.get("custom_config", {})
        
        success = template_service.apply_template_to_knowledge_base(
            kb_id=kb_id,
            template_id=template_id,
            backend_type=backend_type,
            custom_config=custom_config
        )
        
        if success:
            return {
                "success": True,
                "message": "模板应用成功",
                "data": {
                    "kb_id": kb_id,
                    "template_id": template_id,
                    "backend_type": backend_type_str
                }
            }
        else:
            raise HTTPException(status_code=500, detail="模板应用失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"应用模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"应用模板失败: {str(e)}")

@router.post("/custom")
async def create_custom_template(
    custom_request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    创建自定义模板
    
    Args:
        custom_request: 自定义模板请求
    """
    try:
        template_service = VectorTemplateService(db)
        
        base_template_id = custom_request.get("base_template_id")
        template_name = custom_request.get("template_name")
        custom_config = custom_request.get("custom_config", {})
        
        if not base_template_id or not template_name:
            raise HTTPException(status_code=400, detail="基础模板ID和模板名称不能为空")
        
        custom_template = template_service.create_custom_template(
            base_template_id=base_template_id,
            custom_config=custom_config,
            template_name=template_name
        )
        
        return {
            "success": True,
            "data": custom_template,
            "message": "自定义模板创建成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建自定义模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建自定义模板失败: {str(e)}")

@router.post("/analyze-table")
async def analyze_table_data(
    table_request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    分析表格数据并推荐模板
    
    Args:
        table_request: 表格分析请求
    """
    try:
        table_data = table_request.get("table_data", {})
        if not table_data:
            raise HTTPException(status_code=400, detail="表格数据不能为空")
        
        # 使用表格向量化工具分析
        table_vectorizer = TableVectorizer()
        analysis_result = table_vectorizer.vectorize_table(table_data)
        
        # 获取推荐模板的详细信息
        template_service = VectorTemplateService(db)
        recommended_template_id = analysis_result.metadata.get("recommended_template")
        
        template_detail = None
        if recommended_template_id:
            template_detail = template_service.get_template_by_id(recommended_template_id)
        
        return {
            "success": True,
            "data": {
                "analysis_result": {
                    "service_classification": analysis_result.metadata.get("service_classification"),
                    "complexity_score": analysis_result.complexity_score,
                    "processing_strategy": analysis_result.processing_strategy,
                    "special_features": analysis_result.metadata.get("special_features", [])
                },
                "recommended_template": template_detail,
                "structured_data": analysis_result.structured_data,
                "text_chunks": analysis_result.text_chunks,
                "field_suggestions": {
                    "required_fields": template_detail.get("field_combinations", {}).get("basic_fields", []) if template_detail else [],
                    "optimal_fields": template_detail.get("field_combinations", {}).get("search_optimized", []) if template_detail else [],
                    "scenario_specific": template_detail.get("field_combinations", {}) if template_detail else {}
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"表格数据分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"表格数据分析失败: {str(e)}")

@router.post("/field-combinations")
async def get_field_combinations(
    combination_request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    获取字段组合建议
    
    Args:
        combination_request: 字段组合请求
    """
    try:
        template_id = combination_request.get("template_id")
        scenario = combination_request.get("scenario", "general")
        
        if not template_id:
            raise HTTPException(status_code=400, detail="模板ID不能为空")
        
        template_service = VectorTemplateService(db)
        template = template_service.get_template_by_id(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        field_combinations = template.get("field_combinations", {})
        all_fields = template.get("metadata_fields", [])
        
        # 根据场景提供特定建议
        scenario_mapping = {
            "citizen_service": "citizen_focused",
            "fee_analysis": "fee_focused", 
            "process_oriented": "process_focused",
            "legal_compliance": "legal_focused"
        }
        
        recommended_combination = field_combinations.get(
            scenario_mapping.get(scenario, "basic_fields"), 
            field_combinations.get("basic_fields", [])
        )
        
        # 提供字段详细信息
        field_details = {}
        for field in all_fields:
            field_name = field.get("name")
            if field_name:
                field_details[field_name] = {
                    "data_type": field.get("data_type"),
                    "description": field.get("description"),
                    "required": field.get("required", False),
                    "searchable": field.get("searchable", False),
                    "filterable": field.get("filterable", False)
                }
        
        return {
            "success": True,
            "data": {
                "template_id": template_id,
                "scenario": scenario,
                "recommended_fields": recommended_combination,
                "all_combinations": field_combinations,
                "field_details": field_details,
                "usage_suggestions": {
                    "search_optimization": "使用searchable字段提升搜索体验",
                    "filter_optimization": "使用filterable字段支持精确筛选",
                    "performance_tips": "避免使用过多索引字段以保持性能"
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取字段组合失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取字段组合失败: {str(e)}")

@router.post("/government-service/smart-analysis")
async def smart_government_service_analysis(
    analysis_request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    智能政府服务分析（针对您展示的表格差异）
    
    Args:
        analysis_request: 分析请求
    """
    try:
        table_data = analysis_request.get("table_data", {})
        service_name = analysis_request.get("service_name", "")
        
        if not table_data:
            raise HTTPException(status_code=400, detail="表格数据不能为空")
        
        # 使用表格向量化工具进行智能分析
        table_vectorizer = TableVectorizer()
        
        # 服务类型分类
        content_text = table_vectorizer._extract_text_from_table(table_data)
        service_classification = table_vectorizer.classify_service_type(content_text, service_name)
        
        # 处理表格数据
        processing_result = table_vectorizer.process_government_service_table(
            table_data, service_classification
        )
        
        # 获取模板推荐
        template_service = VectorTemplateService(db)
        template_recommendations = template_service.recommend_template(
            content_type="government_service",
            industry="government",
            service_type=service_classification.primary_type,
            content_complexity=service_classification.complexity_level
        )
        
        # 特殊处理建议
        special_handling = []
        
        # 针对收费信息复杂度的特殊建议
        fee_info = processing_result.structured_data.get("fee_info", {})
        if fee_info.get("fee_basis") or fee_info.get("fee_calculation_rules"):
            special_handling.append({
                "type": "complex_fee_structure",
                "description": "检测到复杂收费结构，建议使用不动产登记模板以更好处理政策依据",
                "recommended_fields": ["fee_standard", "fee_basis", "fee_calculation_rules", "policy_references"],
                "processing_strategy": "legal_document_oriented"
            })
        
        # 针对多部门协同的建议
        if "联办" in content_text or "多部门" in content_text:
            special_handling.append({
                "type": "multi_department_service",
                "description": "检测到多部门协同服务，建议关注联办机构和流程复杂度",
                "recommended_fields": ["liaison_organization", "service_departments", "process_steps"],
                "processing_strategy": "multi_department_coordination"
            })
        
        # 针对在线办理的建议
        if any(online_indicator in content_text for online_indicator in ["网上", "在线", "线上"]):
            special_handling.append({
                "type": "online_service",
                "description": "检测到在线服务功能，建议优化数字化服务字段",
                "recommended_fields": ["online_url", "service_channels", "processing_method"],
                "processing_strategy": "digital_service_oriented"
            })
        
        return {
            "success": True,
            "data": {
                "service_classification": {
                    "primary_type": service_classification.primary_type,
                    "secondary_types": service_classification.secondary_types,
                    "complexity_level": service_classification.complexity_level,
                    "special_features": service_classification.special_features,
                    "recommended_template": service_classification.recommended_template
                },
                "processing_result": {
                    "structured_data": processing_result.structured_data,
                    "complexity_score": processing_result.complexity_score,
                    "processing_strategy": processing_result.processing_strategy,
                    "text_chunks_count": len(processing_result.text_chunks)
                },
                "template_recommendations": template_recommendations[:3],  # 返回前3个推荐
                "special_handling": special_handling,
                "field_optimization": {
                    "dynamic_fields": self._get_dynamic_field_suggestions(service_classification, processing_result),
                    "search_optimization": self._get_search_optimization_suggestions(processing_result),
                    "performance_tuning": self._get_performance_suggestions(processing_result)
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"智能政府服务分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"智能政府服务分析失败: {str(e)}")

def _get_dynamic_field_suggestions(service_classification, processing_result) -> List[Dict[str, Any]]:
    """获取动态字段建议"""
    suggestions = []
    
    if service_classification.primary_type == "real_estate_registration":
        suggestions.append({
            "field_group": "real_estate_specialized",
            "fields": ["registration_type", "property_type", "fee_calculation_rules"],
            "reason": "不动产登记需要专业字段支持"
        })
    
    if service_classification.complexity_level == "complex":
        suggestions.append({
            "field_group": "complex_processing",
            "fields": ["special_conditions", "policy_references", "multi_step_process"],
            "reason": "复杂服务需要额外字段记录特殊情况"
        })
    
    return suggestions

def _get_search_optimization_suggestions(processing_result) -> List[Dict[str, Any]]:
    """获取搜索优化建议"""
    suggestions = []
    
    structured_data = processing_result.structured_data
    
    if structured_data.get("fee_info", {}).get("fee_standard"):
        suggestions.append({
            "optimization": "fee_search",
            "description": "启用收费信息的全文搜索",
            "fields": ["fee_standard", "fee_description"]
        })
    
    if structured_data.get("service_conditions"):
        suggestions.append({
            "optimization": "condition_search", 
            "description": "优化办理条件的语义搜索",
            "fields": ["service_conditions", "eligibility_criteria"]
        })
    
    return suggestions

def _get_performance_suggestions(processing_result) -> List[Dict[str, Any]]:
    """获取性能优化建议"""
    suggestions = []
    
    if processing_result.complexity_score > 0.8:
        suggestions.append({
            "optimization": "high_complexity_handling",
            "description": "高复杂度数据建议使用HNSW索引",
            "config": {"index_type": "HNSW", "m": 20, "ef_construction": 300}
        })
    
    if len(processing_result.text_chunks) > 10:
        suggestions.append({
            "optimization": "chunk_optimization",
            "description": "大量文本块建议启用分区存储",
            "config": {"enable_partitioning": True, "partition_key": "chunk_type"}
        })
    
    return suggestions 