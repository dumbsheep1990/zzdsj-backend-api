"""
V1 API - AI模型信息接口
提供AI模型信息查询功能，专门为第三方开发者设计
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

from app.api.v1.dependencies import (
    V1ServiceContainer, 
    V1Context, 
    V1DataFilter,
    get_v1_service_container,
    get_v1_context,
    APIKey
)
from app.api.shared.responses import ExternalResponseFormatter

logger = logging.getLogger(__name__)

router = APIRouter()


# ================================
# 响应模型
# ================================

class ModelInfo(BaseModel):
    """模型信息模型"""
    id: str = Field(..., description="模型ID")
    name: str = Field(..., description="模型名称")
    provider: str = Field(..., description="模型提供商")
    description: str = Field(..., description="模型描述")
    capabilities: List[str] = Field(..., description="模型能力")
    max_tokens: int = Field(..., description="最大token数")
    pricing: Dict[str, Any] = Field(..., description="定价信息")
    status: str = Field(..., description="模型状态")


class ModelUsageInfo(BaseModel):
    """模型使用信息模型"""
    model_id: str = Field(..., description="模型ID")
    total_requests: int = Field(..., description="总请求数")
    total_tokens: int = Field(..., description="总token数")
    avg_response_time: float = Field(..., description="平均响应时间")
    success_rate: float = Field(..., description="成功率")


# ================================
# API接口实现
# ================================

@router.get("/list", response_model=Dict[str, Any], summary="获取模型列表")
async def list_models(
    provider: Optional[str] = Query(None, description="模型提供商筛选"),
    capability: Optional[str] = Query(None, description="能力筛选"),
    status: str = Query("active", description="状态筛选: active, deprecated, beta"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取可用的AI模型列表
    
    返回当前可用的AI模型信息，包括能力、限制和定价。
    """
    try:
        logger.info(f"V1 API - 获取模型列表: provider={provider}, capability={capability}")
        
        # 获取AI服务
        ai_service = container.get_ai_service()
        
        # 构建查询参数
        query_params = {
            "provider": provider,
            "capability": capability,
            "status": status,
            "limit": limit,
            "api_mode": "v1_external"
        }
        
        # 查询模型列表
        models_data = await ai_service.list_models(query_params)
        
        # 过滤模型数据（移除内部信息）
        filtered_models = []
        for model in models_data.get("models", []):
            filtered_model = {
                "id": model.get("id"),
                "name": model.get("name"),
                "provider": model.get("provider"),
                "description": model.get("description"),
                "capabilities": model.get("capabilities", []),
                "max_tokens": model.get("max_tokens"),
                "context_window": model.get("context_window"),
                "pricing": {
                    "input_tokens": model.get("pricing", {}).get("input_tokens"),
                    "output_tokens": model.get("pricing", {}).get("output_tokens"),
                    "currency": model.get("pricing", {}).get("currency", "USD")
                },
                "status": model.get("status"),
                "version": model.get("version"),
                "release_date": model.get("release_date"),
                "supported_features": model.get("supported_features", [])
            }
            filtered_models.append(filtered_model)
        
        # 构建响应
        response_data = {
            "models": filtered_models,
            "total": len(filtered_models),
            "providers": list(set(model.get("provider") for model in filtered_models)),
            "capabilities": list(set(
                cap for model in filtered_models 
                for cap in model.get("capabilities", [])
            ))
        }
        
        return ExternalResponseFormatter.format_success(
            data=response_data,
            message="获取模型列表成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 获取模型列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取模型列表失败"
        )


@router.get("/{model_id}", response_model=Dict[str, Any], summary="获取模型详情")
async def get_model_info(
    model_id: str,
    include_pricing: bool = Query(True, description="是否包含定价信息"),
    include_stats: bool = Query(False, description="是否包含使用统计"),
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取指定模型的详细信息
    
    返回模型的完整信息，包括能力、限制、定价和使用统计。
    """
    try:
        logger.info(f"V1 API - 获取模型详情: model_id={model_id}")
        
        # 获取AI服务
        ai_service = container.get_ai_service()
        
        # 查询模型详情
        model_data = await ai_service.get_model_info(
            model_id, 
            include_pricing=include_pricing,
            include_stats=include_stats,
            api_mode="v1_external"
        )
        
        if not model_data:
            raise HTTPException(
                status_code=404,
                detail="模型不存在或不可访问"
            )
        
        # 构建详细信息
        model_info = {
            "id": model_data.get("id"),
            "name": model_data.get("name"),
            "provider": model_data.get("provider"),
            "description": model_data.get("description"),
            "capabilities": model_data.get("capabilities", []),
            "specifications": {
                "max_tokens": model_data.get("max_tokens"),
                "context_window": model_data.get("context_window"),
                "input_languages": model_data.get("input_languages", []),
                "output_languages": model_data.get("output_languages", []),
                "supported_formats": model_data.get("supported_formats", [])
            },
            "parameters": {
                "temperature_range": model_data.get("temperature_range", [0.0, 2.0]),
                "top_p_range": model_data.get("top_p_range", [0.0, 1.0]),
                "supports_streaming": model_data.get("supports_streaming", False),
                "supports_functions": model_data.get("supports_functions", False)
            },
            "status": model_data.get("status"),
            "version": model_data.get("version"),
            "release_date": model_data.get("release_date"),
            "documentation_url": model_data.get("documentation_url")
        }
        
        # 添加定价信息
        if include_pricing and model_data.get("pricing"):
            model_info["pricing"] = {
                "input_tokens": model_data["pricing"].get("input_tokens"),
                "output_tokens": model_data["pricing"].get("output_tokens"),
                "currency": model_data["pricing"].get("currency", "USD"),
                "billing_unit": model_data["pricing"].get("billing_unit", "per_1k_tokens"),
                "free_tier": model_data["pricing"].get("free_tier")
            }
        
        # 添加使用统计
        if include_stats and model_data.get("stats"):
            model_info["usage_stats"] = {
                "total_requests": model_data["stats"].get("total_requests", 0),
                "avg_response_time": model_data["stats"].get("avg_response_time", 0),
                "success_rate": model_data["stats"].get("success_rate", 0),
                "uptime": model_data["stats"].get("uptime", 0)
            }
        
        return ExternalResponseFormatter.format_success(
            data=model_info,
            message="获取模型详情成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V1 API - 获取模型详情失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取模型详情失败"
        )


@router.get("/{model_id}/capabilities", response_model=Dict[str, Any], summary="获取模型能力")
async def get_model_capabilities(
    model_id: str,
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取模型的详细能力信息
    
    返回模型支持的功能、限制和最佳实践建议。
    """
    try:
        logger.info(f"V1 API - 获取模型能力: model_id={model_id}")
        
        # 获取AI服务
        ai_service = container.get_ai_service()
        
        # 查询模型能力
        capabilities_data = await ai_service.get_model_capabilities(
            model_id, 
            api_mode="v1_external"
        )
        
        if not capabilities_data:
            raise HTTPException(
                status_code=404,
                detail="模型不存在或不可访问"
            )
        
        # 构建能力信息
        capabilities_info = {
            "model_id": model_id,
            "core_capabilities": capabilities_data.get("core_capabilities", []),
            "supported_tasks": capabilities_data.get("supported_tasks", []),
            "input_types": capabilities_data.get("input_types", []),
            "output_types": capabilities_data.get("output_types", []),
            "function_calling": {
                "supported": capabilities_data.get("supports_functions", False),
                "max_functions": capabilities_data.get("max_functions", 0),
                "parallel_calls": capabilities_data.get("supports_parallel_calls", False)
            },
            "streaming": {
                "supported": capabilities_data.get("supports_streaming", False),
                "chunk_types": capabilities_data.get("stream_chunk_types", [])
            },
            "limitations": {
                "max_tokens": capabilities_data.get("max_tokens"),
                "context_window": capabilities_data.get("context_window"),
                "rate_limits": capabilities_data.get("rate_limits", {}),
                "content_filters": capabilities_data.get("content_filters", [])
            },
            "best_practices": capabilities_data.get("best_practices", []),
            "use_cases": capabilities_data.get("recommended_use_cases", [])
        }
        
        return ExternalResponseFormatter.format_success(
            data=capabilities_info,
            message="获取模型能力成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V1 API - 获取模型能力失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取模型能力失败"
        )


@router.get("/providers", response_model=Dict[str, Any], summary="获取模型提供商")
async def list_model_providers(
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取所有模型提供商信息
    
    返回支持的模型提供商列表和基本信息。
    """
    try:
        logger.info("V1 API - 获取模型提供商")
        
        # 获取AI服务
        ai_service = container.get_ai_service()
        
        # 查询提供商信息
        providers_data = await ai_service.list_model_providers(api_mode="v1_external")
        
        # 过滤提供商数据
        filtered_providers = []
        for provider in providers_data.get("providers", []):
            filtered_provider = {
                "id": provider.get("id"),
                "name": provider.get("name"),
                "description": provider.get("description"),
                "website": provider.get("website"),
                "models_count": provider.get("models_count", 0),
                "capabilities": provider.get("capabilities", []),
                "status": provider.get("status", "active"),
                "documentation": provider.get("documentation_url")
            }
            filtered_providers.append(filtered_provider)
        
        return ExternalResponseFormatter.format_success(
            data={"providers": filtered_providers},
            message="获取模型提供商成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 获取模型提供商失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取模型提供商失败"
        )


@router.get("/{model_id}/pricing", response_model=Dict[str, Any], summary="获取模型定价")
async def get_model_pricing(
    model_id: str,
    currency: str = Query("USD", description="货币类型"),
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取模型的详细定价信息
    
    返回模型的定价结构、免费额度和计费方式。
    """
    try:
        logger.info(f"V1 API - 获取模型定价: model_id={model_id}, currency={currency}")
        
        # 获取AI服务
        ai_service = container.get_ai_service()
        
        # 查询定价信息
        pricing_data = await ai_service.get_model_pricing(
            model_id, 
            currency=currency,
            api_mode="v1_external"
        )
        
        if not pricing_data:
            raise HTTPException(
                status_code=404,
                detail="模型定价信息不存在"
            )
        
        # 构建定价信息
        pricing_info = {
            "model_id": model_id,
            "currency": currency,
            "pricing_tiers": pricing_data.get("pricing_tiers", []),
            "base_pricing": {
                "input_tokens": pricing_data.get("input_token_price"),
                "output_tokens": pricing_data.get("output_token_price"),
                "billing_unit": pricing_data.get("billing_unit", "per_1k_tokens")
            },
            "free_tier": {
                "available": pricing_data.get("has_free_tier", False),
                "monthly_quota": pricing_data.get("free_monthly_quota", 0),
                "daily_quota": pricing_data.get("free_daily_quota", 0)
            },
            "volume_discounts": pricing_data.get("volume_discounts", []),
            "billing_cycle": pricing_data.get("billing_cycle", "monthly"),
            "minimum_charge": pricing_data.get("minimum_charge", 0),
            "last_updated": pricing_data.get("last_updated")
        }
        
        return ExternalResponseFormatter.format_success(
            data=pricing_info,
            message="获取模型定价成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V1 API - 获取模型定价失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取模型定价失败"
        )


@router.get("/{model_id}/status", response_model=Dict[str, Any], summary="获取模型状态")
async def get_model_status(
    model_id: str,
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取模型的实时状态信息
    
    返回模型的可用性、性能指标和服务状态。
    """
    try:
        logger.info(f"V1 API - 获取模型状态: model_id={model_id}")
        
        # 获取AI服务
        ai_service = container.get_ai_service()
        
        # 查询模型状态
        status_data = await ai_service.get_model_status(
            model_id, 
            api_mode="v1_external"
        )
        
        if not status_data:
            raise HTTPException(
                status_code=404,
                detail="模型不存在"
            )
        
        # 构建状态信息
        status_info = {
            "model_id": model_id,
            "status": status_data.get("status", "unknown"),
            "availability": {
                "is_available": status_data.get("is_available", False),
                "uptime_percentage": status_data.get("uptime_percentage", 0),
                "last_outage": status_data.get("last_outage")
            },
            "performance": {
                "avg_response_time": status_data.get("avg_response_time", 0),
                "success_rate": status_data.get("success_rate", 0),
                "current_load": status_data.get("current_load", 0)
            },
            "rate_limits": {
                "requests_per_minute": status_data.get("rate_limit_rpm", 0),
                "tokens_per_minute": status_data.get("rate_limit_tpm", 0),
                "concurrent_requests": status_data.get("max_concurrent", 0)
            },
            "maintenance": {
                "scheduled_maintenance": status_data.get("scheduled_maintenance"),
                "maintenance_window": status_data.get("maintenance_window")
            },
            "last_updated": status_data.get("last_updated")
        }
        
        return ExternalResponseFormatter.format_success(
            data=status_info,
            message="获取模型状态成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V1 API - 获取模型状态失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取模型状态失败"
        )


@router.post("/{model_id}/validate", response_model=Dict[str, Any], summary="验证模型参数")
async def validate_model_parameters(
    model_id: str,
    parameters: Dict[str, Any],
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    验证模型参数的有效性
    
    检查传入的参数是否符合模型的要求和限制。
    """
    try:
        logger.info(f"V1 API - 验证模型参数: model_id={model_id}")
        
        # 获取AI服务
        ai_service = container.get_ai_service()
        
        # 验证参数
        validation_result = await ai_service.validate_model_parameters(
            model_id, 
            parameters,
            api_mode="v1_external"
        )
        
        # 构建验证结果
        validation_info = {
            "model_id": model_id,
            "is_valid": validation_result.get("is_valid", False),
            "validated_parameters": validation_result.get("validated_parameters", {}),
            "errors": validation_result.get("errors", []),
            "warnings": validation_result.get("warnings", []),
            "suggestions": validation_result.get("suggestions", []),
            "parameter_ranges": validation_result.get("parameter_ranges", {})
        }
        
        return ExternalResponseFormatter.format_success(
            data=validation_info,
            message="参数验证完成"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 验证模型参数失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="验证模型参数失败"
        ) 