"""
智能体模版API路由
提供5步前端配置流程的REST API接口
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.frameworks.agno.template_manager import (
    get_template_manager,
    create_agent_from_template,
    get_available_templates,
    recommend_templates
)
from app.frameworks.agno.frontend_config_parser import (
    get_config_parser,
    parse_frontend_config,
    validate_frontend_config
)
from app.frameworks.agno.templates import TemplateType
from app.utils.auth import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/templates", tags=["智能体模版"])


# ==================== Pydantic模型定义 ====================

class TemplateSelectionModel(BaseModel):
    """步骤1: 模版选择"""
    template_id: str = Field(..., description="模版ID")
    template_name: Optional[str] = Field(None, description="模版名称")
    description: Optional[str] = Field(None, description="模版描述")
    use_cases: Optional[List[str]] = Field(None, description="使用场景")
    estimated_cost: Optional[str] = Field(None, description="预估成本")


class BasicConfigurationModel(BaseModel):
    """步骤2: 基础配置"""
    agent_name: str = Field(..., description="Agent名称", min_length=1, max_length=100)
    agent_description: str = Field(..., description="Agent描述", min_length=1, max_length=500)
    personality: str = Field("professional", description="个性类型", regex="^(professional|friendly|creative)$")
    language: str = Field("zh-CN", description="语言")
    response_length: str = Field("medium", description="回复长度", regex="^(short|medium|long)$")


class ModelConfigurationModel(BaseModel):
    """步骤3: 模型配置"""
    model_provider: str = Field(..., description="模型提供商")
    model_name: str = Field(..., description="模型名称")
    temperature: float = Field(0.7, description="Temperature", ge=0.0, le=2.0)
    max_tokens: int = Field(1000, description="最大Token数", gt=0, le=8192)
    cost_tier: str = Field("standard", description="成本等级", regex="^(economy|standard|premium)$")


class CapabilityConfigurationModel(BaseModel):
    """步骤4: 能力配置"""
    enabled_tools: List[str] = Field([], description="启用的工具")
    knowledge_bases: List[str] = Field([], description="知识库")
    external_integrations: List[str] = Field([], description="外部集成")
    custom_instructions: List[str] = Field([], description="自定义指令")


class AdvancedConfigurationModel(BaseModel):
    """步骤5: 高级配置"""
    execution_timeout: int = Field(300, description="执行超时时间", gt=0, le=1800)
    max_iterations: int = Field(10, description="最大迭代次数", gt=0, le=50)
    enable_team_mode: bool = Field(False, description="启用团队模式")
    enable_streaming: bool = Field(True, description="启用流式响应")
    enable_citations: bool = Field(True, description="启用引用")
    privacy_level: str = Field("standard", description="隐私级别", regex="^(basic|standard|strict)$")


class FrontendConfigModel(BaseModel):
    """完整的前端配置"""
    template_selection: TemplateSelectionModel
    basic_configuration: BasicConfigurationModel
    model_configuration: ModelConfigurationModel
    capability_configuration: CapabilityConfigurationModel
    advanced_configuration: AdvancedConfigurationModel


class AgentCreationRequest(BaseModel):
    """Agent创建请求"""
    config: FrontendConfigModel
    session_id: Optional[str] = Field(None, description="会话ID")


class RequirementsModel(BaseModel):
    """需求模型"""
    use_case: Optional[str] = Field(None, description="使用场景")
    complexity: Optional[str] = Field("medium", description="复杂度", regex="^(low|medium|high)$")
    budget: Optional[str] = Field("medium", description="预算", regex="^(low|medium|high)$")


# ==================== API端点 ====================

@router.get("/", summary="获取所有可用模版")
async def get_templates():
    """获取所有可用的智能体模版"""
    try:
        templates = get_available_templates()
        return {
            "success": True,
            "data": templates,
            "total": len(templates)
        }
    except Exception as e:
        logger.error(f"获取模版列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取模版列表失败"
        )


@router.get("/{template_id}", summary="获取模版详情")
async def get_template_details(template_id: str):
    """获取指定模版的详细信息"""
    try:
        manager = get_template_manager()
        template_details = manager.get_template_details(template_id)
        
        if not template_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模版 {template_id} 不存在"
            )
        
        return {
            "success": True,
            "data": template_details
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模版详情失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取模版详情失败"
        )


@router.post("/recommend", summary="推荐模版")
async def recommend_templates_endpoint(requirements: RequirementsModel):
    """根据需求推荐合适的模版"""
    try:
        recommendations = recommend_templates(requirements.dict())
        
        return {
            "success": True,
            "data": recommendations,
            "total": len(recommendations)
        }
    except Exception as e:
        logger.error(f"推荐模版失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="推荐模版失败"
        )


@router.get("/{template_id}/default-config", summary="获取模版默认配置")
async def get_template_default_config(template_id: str):
    """获取指定模版的默认配置"""
    try:
        parser = get_config_parser()
        default_config = parser.get_default_config_for_template(template_id)
        
        if not default_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模版 {template_id} 不存在"
            )
        
        return {
            "success": True,
            "data": default_config
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取默认配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取默认配置失败"
        )


@router.post("/validate", summary="验证前端配置")
async def validate_config(config: FrontendConfigModel):
    """验证前端配置的有效性"""
    try:
        validation_result = await validate_frontend_config(config.dict())
        
        return {
            "success": True,
            "data": validation_result
        }
    except Exception as e:
        logger.error(f"配置验证失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="配置验证失败"
        )


@router.post("/create", summary="从模版创建Agent")
async def create_agent_from_template_endpoint(
    request: AgentCreationRequest,
    current_user: User = Depends(get_current_user)
):
    """根据模版和前端配置创建Agent"""
    try:
        # 1. 验证配置
        validation_result = await validate_frontend_config(request.config.dict())
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": "配置验证失败",
                "validation_errors": validation_result["errors"],
                "validation_warnings": validation_result.get("warnings", [])
            }
        
        # 2. 创建Agent
        agent = await create_agent_from_template(
            template_id=request.config.template_selection.template_id,
            frontend_config=request.config.dict(),
            user_id=current_user.id,
            session_id=request.session_id
        )
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Agent创建失败"
            )
        
        # 3. 返回创建结果
        return {
            "success": True,
            "data": {
                "agent_id": getattr(agent, 'id', None) or str(id(agent)),
                "agent_name": agent.name,
                "template_id": request.config.template_selection.template_id,
                "created_at": str(datetime.now()),
                "capabilities": getattr(agent, '_template_capabilities', []),
                "execution_graph_enabled": hasattr(agent, '_execution_engine')
            },
            "validation_warnings": validation_result.get("warnings", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建Agent失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建Agent失败: {str(e)}"
        )


@router.get("/{template_id}/visualization", summary="获取模版执行图可视化")
async def get_template_visualization(template_id: str):
    """获取模版执行图的可视化数据"""
    try:
        manager = get_template_manager()
        template_details = manager.get_template_details(template_id)
        
        if not template_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模版 {template_id} 不存在"
            )
        
        execution_graph = template_details.get("execution_graph", {})
        
        # 转换为可视化格式
        visualization = {
            "nodes": [],
            "edges": [],
            "metadata": {
                "template_id": template_id,
                "template_name": template_details["name"],
                "total_nodes": len(execution_graph.get("nodes", [])),
                "total_edges": len(execution_graph.get("edges", []))
            }
        }
        
        # 处理节点
        for node in execution_graph.get("nodes", []):
            visualization["nodes"].append({
                "id": node["id"],
                "type": node["type"],
                "label": f"{node['id']} ({node['type']})",
                "config": node.get("config", {}),
                "style": {
                    "color": _get_node_color(node["type"]),
                    "shape": _get_node_shape(node["type"])
                }
            })
        
        # 处理边
        for edge in execution_graph.get("edges", []):
            visualization["edges"].append({
                "from": edge["from"],
                "to": edge["to"],
                "label": edge.get("condition", ""),
                "weight": edge.get("weight", 1.0),
                "style": {
                    "color": "#666",
                    "width": edge.get("weight", 1.0) * 2
                }
            })
        
        return {
            "success": True,
            "data": visualization
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取可视化数据失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取可视化数据失败"
        )


@router.get("/stats/usage", summary="获取模版使用统计")
async def get_template_usage_stats():
    """获取模版使用统计数据"""
    try:
        manager = get_template_manager()
        stats = manager.get_template_usage_stats()
        
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取使用统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取使用统计失败"
        )


# ==================== 辅助函数 ====================

def _get_node_color(node_type: str) -> str:
    """根据节点类型获取颜色"""
    color_map = {
        "processor": "#4CAF50",
        "classifier": "#2196F3", 
        "retriever": "#FF9800",
        "generator": "#9C27B0",
        "formatter": "#607D8B",
        "analyzer": "#00BCD4",
        "scorer": "#FFEB3B",
        "filter": "#795548",
        "synthesizer": "#E91E63",
        "evaluator": "#3F51B5",
        "decomposer": "#009688",
        "assessor": "#FF5722",
        "planner": "#8BC34A",
        "executor": "#FFC107",
        "validator": "#673AB7",
        "reporter": "#CDDC39",
        "coordinator": "#F44336"
    }
    return color_map.get(node_type, "#9E9E9E")


def _get_node_shape(node_type: str) -> str:
    """根据节点类型获取形状"""
    shape_map = {
        "processor": "rectangle",
        "classifier": "diamond",
        "retriever": "circle",
        "generator": "ellipse",
        "formatter": "rectangle",
        "coordinator": "hexagon"
    }
    return shape_map.get(node_type, "rectangle")