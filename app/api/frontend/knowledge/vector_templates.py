"""
向量化模板管理API
提供向量化模板的选择、推荐和应用功能
"""

from fastapi import APIRouter, Depends, HTTPException, status
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
from app.services.knowledge.vector_template_service import get_vector_template_service
from app.utils.storage.core.vector_factory import VectorBackendType

# 导入Pydantic模型
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

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

@router.get("/templates", response_model=Dict[str, Any])
async def list_vector_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取所有可用的向量化模板
    """
    try:
        template_service = get_vector_template_service(db)
        templates = template_service.list_available_templates()
        
        logger.info(f"用户 {current_user.id} 获取向量化模板列表")
        
        return ResponseFormatter.format_success(
            templates,
            message="获取向量化模板列表成功"
        )
        
    except Exception as e:
        logger.error(f"获取向量化模板列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="获取模板列表失败"
        )

@router.get("/templates/{template_id}", response_model=Dict[str, Any])
async def get_vector_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取指定模板的详细配置
    """
    try:
        template_service = get_vector_template_service(db)
        template_config = template_service.get_template_by_id(template_id)
        
        if not template_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模板 {template_id} 不存在"
            )
        
        logger.info(f"用户 {current_user.id} 获取模板配置: {template_id}")
        
        return ResponseFormatter.format_success(
            template_config,
            message="获取模板配置成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模板配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取模板配置失败"
        )

@router.post("/templates/recommend", response_model=Dict[str, Any])
async def recommend_vector_templates(
    request: TemplateRecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    推荐适合的向量化模板
    """
    try:
        template_service = get_vector_template_service(db)
        recommendations = template_service.recommend_template(
            content_type=request.content_type,
            industry=request.industry,
            use_case=request.use_case,
            document_count=request.document_count
        )
        
        logger.info(f"用户 {current_user.id} 获取模板推荐")
        
        return ResponseFormatter.format_success(
            {
                "recommendations": recommendations,
                "criteria": {
                    "content_type": request.content_type,
                    "industry": request.industry,
                    "use_case": request.use_case,
                    "document_count": request.document_count
                }
            },
            message="获取模板推荐成功"
        )
        
    except Exception as e:
        logger.error(f"获取模板推荐失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取模板推荐失败"
        )

@router.post("/templates/apply", response_model=Dict[str, Any])
async def apply_vector_template(
    request: ApplyTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    将向量化模板应用到知识库
    """
    try:
        # 验证后端类型
        try:
            backend_type = VectorBackendType(request.backend_type.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的向量数据库后端类型: {request.backend_type}"
            )
        
        template_service = get_vector_template_service(db)
        result = await template_service.apply_template_to_knowledge_base(
            kb_id=request.kb_id,
            template_id=request.template_id,
            backend_type=backend_type,
            custom_config=request.custom_config
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "应用模板失败")
            )
        
        logger.info(f"用户 {current_user.id} 应用模板 {request.template_id} 到知识库 {request.kb_id}")
        
        return ResponseFormatter.format_success(
            result["data"],
            message="应用向量化模板成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"应用向量化模板失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="应用模板失败"
        )

@router.get("/templates/{template_id}/metadata-schema", response_model=Dict[str, Any])
async def get_template_metadata_schema(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取模板的元数据Schema
    """
    try:
        template_service = get_vector_template_service(db)
        schema = template_service.get_template_metadata_schema(template_id)
        
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模板 {template_id} 的元数据Schema不存在"
            )
        
        logger.info(f"用户 {current_user.id} 获取模板元数据Schema: {template_id}")
        
        return ResponseFormatter.format_success(
            schema,
            message="获取元数据Schema成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模板元数据Schema失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取元数据Schema失败"
        )

@router.post("/templates/check-compatibility", response_model=Dict[str, Any])
async def check_template_compatibility(
    request: TemplateCompatibilityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    检查模板与向量数据库后端的兼容性
    """
    try:
        # 验证后端类型
        try:
            backend_type = VectorBackendType(request.backend_type.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的向量数据库后端类型: {request.backend_type}"
            )
        
        template_service = get_vector_template_service(db)
        compatibility = template_service.validate_template_compatibility(
            template_id=request.template_id,
            backend_type=backend_type,
            document_count=request.document_count,
            storage_size_mb=request.storage_size_mb
        )
        
        logger.info(f"用户 {current_user.id} 检查模板兼容性: {request.template_id} - {request.backend_type}")
        
        return ResponseFormatter.format_success(
            compatibility,
            message="兼容性检查完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检查模板兼容性失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="兼容性检查失败"
        )

@router.get("/backends", response_model=Dict[str, Any])
async def list_vector_backends(
    current_user: User = Depends(get_current_user)
):
    """
    获取支持的向量数据库后端列表
    """
    try:
        backends = []
        for backend_type in VectorBackendType:
            backend_info = {
                "type": backend_type.value,
                "name": backend_type.value.title(),
                "description": self._get_backend_description(backend_type),
                "features": self._get_backend_features(backend_type)
            }
            backends.append(backend_info)
        
        logger.info(f"用户 {current_user.id} 获取向量数据库后端列表")
        
        return ResponseFormatter.format_success(
            {"backends": backends},
            message="获取向量数据库后端列表成功"
        )
        
    except Exception as e:
        logger.error(f"获取向量数据库后端列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取后端列表失败"
        )

def _get_backend_description(backend_type: VectorBackendType) -> str:
    """获取后端描述"""
    descriptions = {
        VectorBackendType.MILVUS: "高性能向量数据库，适合大规模向量检索",
        VectorBackendType.PGVECTOR: "基于PostgreSQL的向量扩展，适合关系型数据集成",
        VectorBackendType.ELASTICSEARCH: "基于Elasticsearch的向量搜索，适合混合搜索"
    }
    return descriptions.get(backend_type, "向量数据库后端")

def _get_backend_features(backend_type: VectorBackendType) -> List[str]:
    """获取后端特性"""
    features = {
        VectorBackendType.MILVUS: [
            "高性能向量检索",
            "支持多种索引算法",
            "分布式架构",
            "丰富的数据类型支持"
        ],
        VectorBackendType.PGVECTOR: [
            "SQL兼容",
            "ACID事务支持",
            "成熟的生态系统",
            "备份恢复机制"
        ],
        VectorBackendType.ELASTICSEARCH: [
            "全文搜索集成",
            "实时搜索",
            "聚合分析",
            "RESTful API"
        ]
    }
    return features.get(backend_type, []) 