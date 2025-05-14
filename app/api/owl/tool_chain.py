from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.utils.database import get_db
from app.repositories.tool_repository import ToolRepository
from app.core.tool_orchestrator import ToolOrchestrator
from app.api.deps import get_current_user

router = APIRouter()

class ToolChainConfig(BaseModel):
    """工具链配置"""
    name: str = Field(..., description="工具链名称")
    description: Optional[str] = Field(None, description="工具链描述")
    tools: List[Dict[str, Any]] = Field(..., description="工具配置列表")
    
class ToolChainConfigResponse(ToolChainConfig):
    """工具链配置响应"""
    id: int
    creator_id: int
    created_at: str
    updated_at: str

class ToolChainValidationRequest(BaseModel):
    """工具链验证请求"""
    config: Dict[str, Any] = Field(..., description="工具链配置")
    
class ToolChainValidationResponse(BaseModel):
    """工具链验证响应"""
    is_valid: bool = Field(..., description="是否有效")
    issues: Optional[List[Dict[str, Any]]] = Field(None, description="问题列表")

@router.post("/validate", response_model=ToolChainValidationResponse)
async def validate_tool_chain(
    request: ToolChainValidationRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    验证工具链配置
    
    - **request**: 工具链配置
    - 返回验证结果
    """
    try:
        # 验证工具配置
        issues = []
        
        # 检查工具是否存在
        if "tools" in request.config:
            repo = ToolRepository()
            for i, tool_config in enumerate(request.config["tools"]):
                if "id" not in tool_config:
                    issues.append({
                        "type": "missing_id",
                        "message": f"工具配置 #{i+1} 缺少ID",
                        "position": i
                    })
                    continue
                    
                tool_id = tool_config["id"]
                tool = await repo.get_by_id(tool_id, db)
                if not tool:
                    issues.append({
                        "type": "tool_not_found",
                        "message": f"找不到ID为 {tool_id} 的工具",
                        "position": i
                    })
                
                # 验证工具参数（如果有）
                if "parameters" in tool_config and tool and tool.parameter_schema:
                    # 这里可以根据参数模式验证参数
                    # 简化实现，只检查必填字段
                    if "required" in tool.parameter_schema:
                        for field in tool.parameter_schema["required"]:
                            if field not in tool_config["parameters"]:
                                issues.append({
                                    "type": "missing_parameter",
                                    "message": f"工具 {tool.name} 缺少必填参数 {field}",
                                    "position": i,
                                    "field": field
                                })
        else:
            issues.append({
                "type": "missing_tools",
                "message": "配置缺少工具列表"
            })
        
        # 检查工具顺序
        if "tools" in request.config:
            tools_with_order = [(i, tool.get("order", i)) for i, tool in enumerate(request.config["tools"])]
            seen_orders = {}
            for i, order in tools_with_order:
                if order in seen_orders:
                    issues.append({
                        "type": "duplicate_order",
                        "message": f"重复的工具顺序 {order}",
                        "positions": [seen_orders[order], i]
                    })
                seen_orders[order] = i
                
        # 验证条件表达式
        if "tools" in request.config:
            for i, tool_config in enumerate(request.config["tools"]):
                if "condition" in tool_config and tool_config["condition"]:
                    try:
                        # 使用安全的eval环境测试条件
                        test_context = {"task": "测试任务", "result": "测试结果"}
                        orchestrator = ToolOrchestrator()
                        orchestrator._evaluate_condition(tool_config["condition"], test_context)
                    except Exception as e:
                        issues.append({
                            "type": "invalid_condition",
                            "message": f"无效的条件表达式: {str(e)}",
                            "position": i,
                            "condition": tool_config["condition"]
                        })
        
        return ToolChainValidationResponse(
            is_valid=len(issues) == 0,
            issues=issues if issues else None
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证工具链配置失败: {str(e)}"
        )
