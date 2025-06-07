"""
工具配置管理API
提供工具参数配置的前端接口
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from app.utils.core.database import get_db
from core.tools.configuration_manager import ToolConfigurationManager
from app.schemas.tool_configuration import (
    ToolConfigurationSchemaCreate,
    ToolConfigurationCreate,
    ToolConfigurationResponse,
    ToolConfigurationSchemaResponse,
    ToolConfigurationValidationResponse
)
from app.utils.auth.core.auth_utils import get_current_user

router = APIRouter(prefix="/configuration", tags=["工具配置"])

@router.post("/schema", response_model=Dict[str, Any])
async def create_configuration_schema(
    schema_data: ToolConfigurationSchemaCreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """创建工具配置模式
    
    Args:
        schema_data: 配置模式数据
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        Dict[str, Any]: 创建结果
    """
    manager = ToolConfigurationManager(db)
    
    result = await manager.create_configuration_schema(
        tool_id=schema_data.tool_id,
        config_schema=schema_data.config_schema,
        display_name=schema_data.display_name,
        description=schema_data.description,
        default_config=schema_data.default_config,
        ui_schema=schema_data.ui_schema,
        validation_rules=schema_data.validation_rules
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "配置模式创建成功", "data": result["data"]}
    )

@router.get("/schema/{tool_id}", response_model=ToolConfigurationSchemaResponse)
async def get_tool_configuration_schema(
    tool_id: str,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """获取工具配置模式
    
    Args:
        tool_id: 工具ID
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        ToolConfigurationSchemaResponse: 配置模式信息
    """
    manager = ToolConfigurationManager(db)
    
    result = await manager.get_tool_configuration_schema(tool_id)
    
    if not result["success"]:
        if result.get("error_code") == "SCHEMA_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具配置模式不存在"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
    return ToolConfigurationSchemaResponse(**result["data"])

@router.post("/configure", response_model=Dict[str, Any])
async def create_user_configuration(
    config_data: ToolConfigurationCreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """创建或更新用户工具配置
    
    Args:
        config_data: 配置数据
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        Dict[str, Any]: 配置结果
    """
    manager = ToolConfigurationManager(db)
    
    result = await manager.create_user_configuration(
        schema_id=config_data.schema_id,
        user_id=current_user["id"],
        config_values=config_data.config_values,
        configuration_name=config_data.configuration_name
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "工具配置成功", "data": result["data"]}
    )

@router.get("/my-config/{tool_id}", response_model=ToolConfigurationResponse)
async def get_my_tool_configuration(
    tool_id: str,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """获取当前用户的工具配置
    
    Args:
        tool_id: 工具ID
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        ToolConfigurationResponse: 配置信息
    """
    manager = ToolConfigurationManager(db)
    
    result = await manager.get_user_tool_configuration(tool_id, current_user["id"])
    
    if not result["success"]:
        if result.get("error_code") == "CONFIG_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户未配置此工具"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
    return ToolConfigurationResponse(**result["data"])

@router.post("/validate/{tool_id}", response_model=ToolConfigurationValidationResponse)
async def validate_tool_configuration(
    tool_id: str,
    config_values: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """验证工具配置
    
    Args:
        tool_id: 工具ID
        config_values: 要验证的配置值（可选）
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        ToolConfigurationValidationResponse: 验证结果
    """
    manager = ToolConfigurationManager(db)
    
    result = await manager.validate_tool_configuration(
        tool_id, current_user["id"], config_values
    )
    
    if not result["success"] and result.get("error_code") != "CONFIG_NOT_FOUND":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
    return ToolConfigurationValidationResponse(
        is_valid=result.get("is_valid", False),
        errors=result.get("errors", []),
        tool_name=result.get("tool_name", ""),
        message=result.get("error", "验证完成")
    )

@router.get("/check-ready/{tool_id}", response_model=Dict[str, Any])
async def check_tool_ready_for_execution(
    tool_id: str,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """检查工具是否已准备好执行
    
    Args:
        tool_id: 工具ID
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        Dict[str, Any]: 检查结果
    """
    manager = ToolConfigurationManager(db)
    
    result = await manager.check_tool_ready_for_execution(tool_id, current_user["id"])
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
    return {
        "ready": result["ready"],
        "message": result["message"],
        "error_code": result.get("error_code"),
        "action_required": result.get("action_required"),
        "validation_errors": result.get("validation_errors")
    }

@router.get("/wizard/{tool_id}", response_model=Dict[str, Any])
async def get_configuration_wizard(
    tool_id: str,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """获取工具配置向导信息
    
    Args:
        tool_id: 工具ID
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        Dict[str, Any]: 配置向导数据
    """
    manager = ToolConfigurationManager(db)
    
    # 获取配置模式
    schema_result = await manager.get_tool_configuration_schema(tool_id)
    if not schema_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工具不需要配置或配置模式不存在"
        )
    
    # 获取用户现有配置（如果存在）
    config_result = await manager.get_user_tool_configuration(tool_id, current_user["id"])
    existing_config = config_result.get("data", {}).get("config_values") if config_result["success"] else None
    
    return {
        "tool_name": schema_result["data"]["tool_name"],
        "display_name": schema_result["data"]["display_name"],
        "description": schema_result["data"]["description"],
        "config_schema": schema_result["data"]["config_schema"],
        "ui_schema": schema_result["data"]["ui_schema"],
        "default_config": schema_result["data"]["default_config"],
        "existing_config": existing_config,
        "required_fields": schema_result["data"]["required_fields"]
    }

@router.post("/extract-keywords/{tool_id}")
async def extract_keywords_from_intent(
    tool_id: str,
    query_data: dict,
    current_user: User = Depends(get_current_user),
    config_manager: ToolConfigurationManager = Depends(get_config_manager)
):
    """
    从用户查询中智能提取关键字
    支持意图识别和关键字自动扩展
    """
    try:
        user_query = query_data.get("query", "")
        if not user_query:
            raise HTTPException(
                status_code=400,
                detail="用户查询不能为空"
            )
        
        # 执行意图识别和关键字提取
        result = await config_manager.extract_keywords_from_intent(
            tool_id=tool_id,
            user_query=user_query,
            user_id=str(current_user.id)
        )
        
        return ToolConfigurationResponse(
            success=True,
            message="关键字提取成功",
            data={
                "extracted_keywords": result["keywords"],
                "intent": result["intent"],
                "confidence": result["confidence"],
                "source": result["source"],
                "expanded_keywords": result.get("expanded_keywords", []),
                "category_keywords": result.get("category_keywords", {}),
                "query": user_query,
                "suggestion": _generate_keyword_suggestions(result)
            }
        )
        
    except Exception as e:
        logger.error(f"关键字提取失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"关键字提取失败: {str(e)}"
        )

def _generate_keyword_suggestions(extraction_result: Dict[str, Any]) -> Dict[str, Any]:
    """生成关键字使用建议"""
    try:
        intent = extraction_result["intent"]
        confidence = extraction_result["confidence"]
        keywords = extraction_result["keywords"]
        expanded_keywords = extraction_result.get("expanded_keywords", [])
        
        suggestions = {
            "primary_keywords": keywords[:3],  # 主要关键字
            "secondary_keywords": keywords[3:6],  # 次要关键字
            "expanded_options": expanded_keywords,  # 扩展选项
            "confidence_level": "高" if confidence > 0.8 else "中" if confidence > 0.5 else "低",
            "recommended_strategy": "auto",  # 推荐检索策略
            "tips": []
        }
        
        # 根据意图提供使用建议
        if intent == "welfare_inquiry":
            suggestions["tips"].extend([
                "建议重点关注社会保障相关政策",
                "可以添加具体的福利类型关键字",
                "注意查看最新的补贴标准更新"
            ])
            suggestions["recommended_strategy"] = "local_only"
            
        elif intent == "business_inquiry":
            suggestions["tips"].extend([
                "企业政策更新频繁，建议使用自动策略",
                "可以添加行业特定关键字",
                "注意查看税收优惠的时效性"
            ])
            
        elif intent == "procedure_inquiry":
            suggestions["tips"].extend([
                "办事指南类政策建议从地方门户开始",
                "注意查看最新的流程变更",
                "可以添加具体的证件或手续名称"
            ])
            suggestions["recommended_strategy"] = "local_only"
            
        elif confidence < 0.5:
            suggestions["tips"].extend([
                "查询意图不太明确，建议细化关键字",
                "可以尝试使用更具体的词汇",
                "建议使用自动策略进行广泛检索"
            ])
        
        return suggestions
        
    except Exception as e:
        logger.error(f"生成关键字建议失败: {str(e)}")
        return {"tips": ["自动关键字提取功能暂时不可用"]}

@router.post("/preview-search/{tool_id}")
async def preview_search_with_keywords(
    tool_id: str,
    preview_data: dict,
    current_user: User = Depends(get_current_user),
    config_manager: ToolConfigurationManager = Depends(get_config_manager)
):
    """
    预览使用指定关键字的搜索效果
    不执行实际搜索，只显示将会使用的配置
    """
    try:
        keywords = preview_data.get("keywords", [])
        strategy = preview_data.get("strategy", "auto")
        region = preview_data.get("region", "六盘水")
        
        if not keywords:
            raise HTTPException(
                status_code=400,
                detail="关键字列表不能为空"
            )
        
        # 获取工具配置
        config = await config_manager.get_user_configuration(tool_id, str(current_user.id))
        if not config:
            raise HTTPException(
                status_code=404,
                detail="工具配置未找到"
            )
        
        # 生成搜索预览
        search_preview = {
            "keywords": keywords,
            "strategy": strategy,
            "region": region,
            "portals": [],
            "estimated_results": 0,
            "search_urls": []
        }
        
        # 根据策略确定将要使用的门户
        search_portals = config.get("search_portals", {})
        primary_portal = search_portals.get("primary_portal", {})
        backup_portals = search_portals.get("backup_portals", [])
        
        if strategy in ["auto", "local_only"] and primary_portal.get("enabled"):
            search_preview["portals"].append({
                "name": primary_portal["name"],
                "type": "primary",
                "url": primary_portal["base_url"]
            })
            # 构建预览搜索URL
            for keyword in keywords[:3]:  # 只预览前3个关键字
                search_url = f"{primary_portal['base_url']}{primary_portal['search_endpoint']}?searchWord={keyword}"
                search_preview["search_urls"].append({
                    "keyword": keyword,
                    "url": search_url,
                    "portal": primary_portal["name"]
                })
        
        if strategy in ["auto", "provincial_only"]:
            for portal in backup_portals:
                if portal.get("enabled"):
                    search_preview["portals"].append({
                        "name": portal["name"],
                        "type": "backup",
                        "url": portal["base_url"]
                    })
        
        # 估算结果数量
        search_strategy_config = config.get("search_strategy", {})
        max_results = search_strategy_config.get("max_results", 10)
        search_preview["estimated_results"] = min(len(keywords) * len(search_preview["portals"]) * 3, max_results)
        
        return ToolConfigurationResponse(
            success=True,
            message="搜索预览生成成功",
            data=search_preview
        )
        
    except Exception as e:
        logger.error(f"搜索预览失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"搜索预览失败: {str(e)}"
        ) 