"""
Agno编排系统API接口
为前端提供完全解耦合的智能Agent编排服务
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from app.frameworks.agno.orchestration import (
    initialize_orchestration_system,
    create_agent_from_frontend_config,
    get_orchestration_status,
    AgentRole,
    ToolCategory,
    ResponseFormat
)

logger = logging.getLogger(__name__)
router = APIRouter()

# 请求/响应模型
class OrchestrationRequest(BaseModel):
    """编排请求模型"""
    user_id: str = Field(..., description="用户ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    frontend_config: Dict[str, Any] = Field(..., description="前端配置")
    auto_optimize: bool = Field(True, description="是否自动优化工具链")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "user123",
                "session_id": "session456",
                "frontend_config": {
                    "name": "智能助手",
                    "role": "assistant",
                    "description": "帮助用户解决问题",
                    "capabilities": ["reasoning", "search"],
                    "model_config": {"type": "chat"}
                },
                "auto_optimize": True
            }
        }

class OrchestrationResponse(BaseModel):
    """编排响应模型"""
    success: bool = Field(..., description="是否成功")
    agent_id: Optional[str] = Field(None, description="Agent ID")
    agent_config: Optional[Dict[str, Any]] = Field(None, description="Agent配置")
    recommended_tools: List[str] = Field(default_factory=list, description="推荐工具")
    system_info: Dict[str, Any] = Field(default_factory=dict, description="系统信息")
    error: Optional[str] = Field(None, description="错误信息")
    validation_errors: List[str] = Field(default_factory=list, description="验证错误")

class ToolDiscoveryResponse(BaseModel):
    """工具发现响应模型"""
    total_tools: int = Field(..., description="总工具数")
    categories: Dict[str, List[Dict[str, str]]] = Field(..., description="按类别分组的工具")
    search_results: List[Dict[str, Any]] = Field(default_factory=list, description="搜索结果")

class SystemStatusResponse(BaseModel):
    """系统状态响应模型"""
    status: str = Field(..., description="系统状态")
    version: str = Field(..., description="版本号")
    components: Dict[str, str] = Field(..., description="组件状态")
    registry_stats: Dict[str, Any] = Field(..., description="注册中心统计")

# API路由

@router.post("/orchestrate", response_model=OrchestrationResponse)
async def create_orchestrated_agent(request: OrchestrationRequest):
    """
    创建编排Agent
    
    根据前端配置自动解析、匹配工具、组装Agent
    """
    try:
        # 调用编排系统
        result = await create_agent_from_frontend_config(
            user_id=request.user_id,
            frontend_config=request.frontend_config,
            session_id=request.session_id
        )
        
        if result['success']:
            # 转换AgentConfig为字典格式
            agent_config_dict = {
                'name': result['agent_config'].name,
                'role': result['agent_config'].role.value,
                'description': result['agent_config'].description,
                'instructions': result['agent_config'].instructions,
                'model_config': result['agent_config'].model_config,
                'tools': result['agent_config'].tools,
                'knowledge_bases': result['agent_config'].knowledge_bases,
                'memory_config': result['agent_config'].memory_config,
                'max_loops': result['agent_config'].max_loops,
                'timeout': result['agent_config'].timeout,
                'show_tool_calls': result['agent_config'].show_tool_calls,
                'markdown': result['agent_config'].markdown,
                'custom_params': result['agent_config'].custom_params
            }
            
            return OrchestrationResponse(
                success=True,
                agent_id=f"agno_{request.user_id}_{hash(str(request.frontend_config))}",
                agent_config=agent_config_dict,
                recommended_tools=result['recommended_tools'],
                system_info=result['system_info']
            )
        else:
            return OrchestrationResponse(
                success=False,
                error=result['error'],
                validation_errors=result.get('validation_errors', [])
            )
            
    except Exception as e:
        logger.error(f"编排Agent失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"编排失败: {str(e)}")

@router.get("/tools/discover", response_model=ToolDiscoveryResponse)
async def discover_tools(
    category: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 50
):
    """
    发现可用工具
    
    按类别或搜索查询发现工具
    """
    try:
        # 初始化系统
        system = await initialize_orchestration_system()
        if system['status'] != 'initialized':
            raise HTTPException(status_code=500, detail="系统初始化失败")
        
        registry = system['registry']
        
        # 按类别过滤
        category_filter = None
        if category:
            try:
                category_filter = ToolCategory(category.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的工具类别: {category}")
        
        # 获取工具列表
        if search_query:
            tools = await registry.search_tools(search_query)
        else:
            tools = await registry.list_tools(category_filter)
        
        # 按类别分组
        categories = {}
        for tool in tools[:limit]:
            cat = tool.category.value
            if cat not in categories:
                categories[cat] = []
            
            categories[cat].append({
                'id': tool.id,
                'name': tool.name,
                'description': tool.description,
                'framework': tool.framework.value,
                'capabilities': tool.capabilities
            })
        
        # 搜索结果
        search_results = []
        if search_query:
            search_results = [
                {
                    'id': tool.id,
                    'name': tool.name,
                    'description': tool.description,
                    'category': tool.category.value,
                    'relevance': 'high'  # 简化的相关性评分
                }
                for tool in tools[:10]
            ]
        
        return ToolDiscoveryResponse(
            total_tools=len(tools),
            categories=categories,
            search_results=search_results
        )
        
    except Exception as e:
        logger.error(f"工具发现失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"工具发现失败: {str(e)}")

@router.get("/tools/categories")
async def get_tool_categories():
    """获取所有工具类别"""
    try:
        categories = [
            {
                'value': category.value,
                'name': category.value.replace('_', ' ').title(),
                'description': f"{category.value}类工具"
            }
            for category in ToolCategory
        ]
        
        return {
            'success': True,
            'categories': categories
        }
        
    except Exception as e:
        logger.error(f"获取工具类别失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tools/recommend")
async def recommend_tools(
    task_description: str = Field(..., description="任务描述"),
    user_preferences: Optional[Dict[str, Any]] = None,
    max_tools: int = 10
):
    """
    推荐工具
    
    根据任务描述智能推荐合适的工具
    """
    try:
        system = await initialize_orchestration_system()
        matcher = system['matcher']
        
        # 构建上下文
        context = {
            'user_preferences': user_preferences or {},
            'resource_limits': {'max_tools': max_tools}
        }
        
        # 获取推荐
        recommended_tools = await matcher.recommend_tools(task_description, context)
        
        # 获取工具详情
        registry = system['registry']
        tool_details = []
        
        for tool_id in recommended_tools:
            metadata = await registry.get_tool_metadata(tool_id)
            if metadata:
                tool_details.append({
                    'id': metadata.id,
                    'name': metadata.name,
                    'description': metadata.description,
                    'category': metadata.category.value,
                    'capabilities': metadata.capabilities,
                    'confidence': 0.8  # 简化的置信度
                })
        
        return {
            'success': True,
            'task_description': task_description,
            'recommended_tools': tool_details,
            'total_recommendations': len(tool_details)
        }
        
    except Exception as e:
        logger.error(f"工具推荐失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"工具推荐失败: {str(e)}")

@router.post("/config/parse")
async def parse_frontend_config(config: Dict[str, Any]):
    """
    解析前端配置
    
    验证和标准化前端传递的配置
    """
    try:
        system = await initialize_orchestration_system()
        parser = system['parser']
        
        # 解析配置
        agent_config = await parser.parse_frontend_config(config)
        
        # 验证配置
        validation_errors = await parser.validate_config(agent_config)
        
        # 转换为字典格式
        parsed_config = {
            'name': agent_config.name,
            'role': agent_config.role.value,
            'description': agent_config.description,
            'instructions': agent_config.instructions,
            'model_config': agent_config.model_config,
            'tools': agent_config.tools,
            'knowledge_bases': agent_config.knowledge_bases,
            'memory_config': agent_config.memory_config,
            'max_loops': agent_config.max_loops,
            'timeout': agent_config.timeout,
            'show_tool_calls': agent_config.show_tool_calls,
            'markdown': agent_config.markdown,
            'custom_params': agent_config.custom_params
        }
        
        return {
            'success': True,
            'original_config': config,
            'parsed_config': parsed_config,
            'validation_errors': validation_errors,
            'is_valid': len(validation_errors) == 0
        }
        
    except Exception as e:
        logger.error(f"配置解析失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"配置解析失败: {str(e)}")

@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    """
    获取编排系统状态
    
    返回系统健康状态、组件信息和统计数据
    """
    try:
        status = await get_orchestration_status()
        
        return SystemStatusResponse(
            status=status['status'],
            version=status.get('version', 'unknown'),
            components=status.get('components', {}),
            registry_stats=status.get('registry', {})
        )
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取系统状态失败: {str(e)}")

@router.post("/system/initialize")
async def initialize_system():
    """
    初始化编排系统
    
    手动触发系统初始化
    """
    try:
        system = await initialize_orchestration_system()
        
        return {
            'success': system['status'] == 'initialized',
            'status': system['status'],
            'error': system.get('error'),
            'components': {
                'registry': 'initialized' if 'registry' in system else 'failed',
                'parser': 'initialized' if 'parser' in system else 'failed',
                'matcher': 'initialized' if 'matcher' in system else 'failed'
            }
        }
        
    except Exception as e:
        logger.error(f"系统初始化失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"系统初始化失败: {str(e)}")

@router.get("/health")
async def health_check():
    """
    健康检查
    
    快速检查系统是否正常运行
    """
    try:
        # 简单的健康检查
        from app.frameworks.agno.orchestration import get_tool_registry
        
        registry = await get_tool_registry()
        stats = await registry.get_registry_stats()
        
        return {
            'status': 'healthy',
            'timestamp': str(datetime.now()),
            'tools_available': stats['total_tools'],
            'system_ready': stats['initialized']
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': str(datetime.now())
        }

# 导出路由
__all__ = ['router'] 