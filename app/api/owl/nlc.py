from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.utils.database import get_db
from core.nl_config_parser import NLConfigParser
from app.api.deps import get_current_user

router = APIRouter()

class NLParseRequest(BaseModel):
    """自然语言配置解析请求"""
    description: str = Field(..., description="智能体需求描述")

class SuggestionRequest(BaseModel):
    """优化建议请求"""
    current_config: Dict[str, Any] = Field(..., description="当前配置")

class ConfigResponse(BaseModel):
    """配置响应"""
    config: Dict[str, Any] = Field(..., description="解析后的配置")
    
class SuggestionResponse(BaseModel):
    """建议响应"""
    suggestions: Dict[str, Any] = Field(..., description="优化建议")

@router.post("/parse", response_model=ConfigResponse)
async def parse_natural_language(
    request: NLParseRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    将自然语言描述解析为结构化的智能体配置
    
    - **request**: 自然语言描述请求
    - 返回解析后的配置
    """
    try:
        parser = NLConfigParser()
        config = await parser.parse_description(request.description)
        
        if "error" in config:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=config["error"]
            )
        
        return ConfigResponse(config=config)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"解析配置失败: {str(e)}"
        )

@router.post("/suggest", response_model=SuggestionResponse)
async def suggest_improvements(
    request: SuggestionRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    基于当前配置提供优化建议
    
    - **request**: 当前配置
    - 返回优化建议
    """
    try:
        parser = NLConfigParser()
        suggestions = await parser.suggest_improvements(request.current_config)
        
        if "error" in suggestions:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=suggestions["error"]
            )
        
        return SuggestionResponse(suggestions=suggestions)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成建议失败: {str(e)}"
        )
