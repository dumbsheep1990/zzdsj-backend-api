"""
智能推荐API端点
暴露AI工具组合推荐、自然语言编排和自动发现的功能
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

# 导入服务和类型
from app.services.recommendations.intelligent_recommendation_service import (
    IntelligentRecommendationService,
    get_intelligent_recommendation_service
)
from app.services.tools.auto_discovery import (
    AutoToolDiscovery,
    get_auto_tool_discovery
)
from app.services.recommendations.recommendation_types import (
    RecommendationContext,
    RecommendationFilter,
    UserFeedback,
    RecommendationMetrics
)

# 导入依赖和认证
from app.dependencies import get_current_user, get_tool_service, get_cache_manager, get_db_manager
from app.utils.monitoring.core.health_checker import get_health_checker
from app.utils.security.core.threat_detector import get_threat_detector
from app.utils.version.tool_usage_stats import get_tool_usage_stats_manager
from core.nl_config.parser import get_nl_parser

# 导入数据模型
from pydantic import BaseModel, Field
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligent-recommendations", tags=["Intelligent Recommendations"])

# ========== 请求模型 ==========

class ToolChainRequest(BaseModel):
    """工具链推荐请求"""
    task_description: str = Field(..., description="任务描述")
    domain: Optional[str] = Field(None, description="领域上下文")
    complexity_preference: str = Field("balanced", description="复杂度偏好")
    time_constraint: Optional[int] = Field(None, description="时间限制（分钟）")
    max_recommendations: int = Field(5, description="最大推荐数量", ge=1, le=20)
    excluded_tools: List[str] = Field(default_factory=list, description="排除的工具")
    preferred_categories: List[str] = Field(default_factory=list, description="偏好的类别")

class NaturalLanguageRequest(BaseModel):
    """自然语言推荐请求"""
    description: str = Field(..., description="自然语言描述")
    domain_context: Optional[str] = Field(None, description="领域上下文")
    complexity_preference: str = Field("balanced", description="复杂度偏好")

class OptimizationRequest(BaseModel):
    """优化请求"""
    chain_id: str = Field(..., description="工具链ID")
    user_feedback: Optional[str] = Field(None, description="用户反馈")
    performance_goals: Optional[Dict[str, Any]] = Field(None, description="性能目标")

class FeedbackRequest(BaseModel):
    """反馈请求"""
    recommendation_id: str = Field(..., description="推荐ID")
    rating: int = Field(..., description="评分1-5", ge=1, le=5)
    comments: Optional[str] = Field(None, description="评论")
    used_recommendation: bool = Field(False, description="是否使用了推荐")
    execution_success: Optional[bool] = Field(None, description="执行是否成功")
    actual_duration: Optional[float] = Field(None, description="实际执行时间")
    suggested_improvements: List[str] = Field(default_factory=list, description="改进建议")

class ToolDiscoveryRequest(BaseModel):
    """工具发现请求"""
    search_paths: Optional[List[str]] = Field(None, description="搜索路径")
    recursive: bool = Field(True, description="是否递归搜索")
    auto_register: bool = Field(False, description="是否自动注册")

# ========== API端点 ==========

@router.post("/tool-chains")
async def get_tool_chain_recommendations(
    request: ToolChainRequest,
    current_user: User = Depends(get_current_user),
    recommendation_service: IntelligentRecommendationService = Depends(
        lambda: get_intelligent_recommendation_service(
            get_tool_service(),
            get_tool_usage_stats_manager(get_cache_manager(), get_db_manager()),
            get_nl_parser()
        )
    )
):
    """
    获取工具链推荐
    
    基于任务描述和用户偏好，返回智能生成的工具链推荐。
    """
    try:
        # 构建推荐上下文
        context = RecommendationContext(
            user_id=current_user.id,
            task_description=request.task_description,
            domain=request.domain,
            complexity_preference=request.complexity_preference,
            time_constraint=request.time_constraint
        )
        
        # 构建过滤器
        filters = RecommendationFilter(
            min_confidence=0.3,
            excluded_tools=request.excluded_tools,
            preferred_categories=request.preferred_categories
        )
        
        # 获取推荐
        result = await recommendation_service.get_tool_chain_recommendations(
            context=context,
            max_recommendations=request.max_recommendations,
            filters=filters
        )
        
        return {
            "success": True,
            "data": {
                "request_id": result.request_id,
                "tool_chain_recommendations": [
                    {
                        "chain_id": rec.chain_id,
                        "objective": rec.objective,
                        "steps": [
                            {
                                "step_number": step.step_number,
                                "tool_name": step.tool_name,
                                "action_description": step.action_description,
                                "estimated_duration": step.estimated_duration
                            } for step in rec.steps
                        ],
                        "confidence_score": rec.confidence_score,
                        "estimated_duration": rec.estimated_duration,
                        "complexity_level": rec.complexity_level,
                        "success_probability": rec.success_probability,
                        "recommendation_type": rec.recommendation_type.value,
                        "reasons": [reason.value for reason in rec.reasons],
                        "explanation": rec.explanation
                    } for rec in result.tool_chain_recommendations
                ],
                "individual_tool_recommendations": [
                    {
                        "tool_id": tool.tool_id,
                        "tool_name": tool.tool_name,
                        "description": tool.description,
                        "category": tool.category,
                        "confidence_score": tool.confidence_score,
                        "reasons": [reason.value for reason in tool.reasons],
                        "estimated_performance": tool.estimated_performance
                    } for tool in result.individual_tool_recommendations
                ],
                "total_recommendations": result.total_recommendations,
                "processing_time": result.processing_time,
                "recommendation_quality": result.recommendation_quality
            }
        }
        
    except Exception as e:
        logger.error(f"获取工具链推荐失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取推荐失败: {str(e)}")

@router.post("/natural-language")
async def get_natural_language_recommendations(
    request: NaturalLanguageRequest,
    current_user: User = Depends(get_current_user),
    recommendation_service: IntelligentRecommendationService = Depends(
        lambda: get_intelligent_recommendation_service(
            get_tool_service(),
            get_tool_usage_stats_manager(get_cache_manager(), get_db_manager()),
            get_nl_parser()
        )
    )
):
    """
    基于自然语言描述获取推荐
    
    用户可以用自然语言描述他们想要完成的任务，系统将智能生成相应的工具链。
    """
    try:
        # 获取自然语言推荐
        recommendation = await recommendation_service.get_natural_language_recommendations(
            description=request.description,
            user_id=current_user.id,
            domain_context=request.domain_context,
            complexity_preference=request.complexity_preference
        )
        
        return {
            "success": True,
            "data": {
                "chain_id": recommendation.chain_id,
                "objective": recommendation.objective,
                "steps": [
                    {
                        "step_number": step.step_number,
                        "tool_name": step.tool_name,
                        "action_description": step.action_description,
                        "expected_input": step.expected_input,
                        "expected_output": step.expected_output,
                        "estimated_duration": step.estimated_duration
                    } for step in recommendation.steps
                ],
                "confidence_score": recommendation.confidence_score,
                "estimated_duration": recommendation.estimated_duration,
                "complexity_level": recommendation.complexity_level,
                "success_probability": recommendation.success_probability,
                "explanation": recommendation.explanation,
                "ai_analysis": {
                    "compatibility_score": recommendation.ai_analysis.compatibility_score,
                    "effectiveness_score": recommendation.ai_analysis.effectiveness_score,
                    "optimization_suggestions": recommendation.ai_analysis.optimization_suggestions,
                    "risk_factors": recommendation.ai_analysis.risk_factors,
                    "synergy_effects": recommendation.ai_analysis.synergy_effects
                } if recommendation.ai_analysis else None
            }
        }
        
    except Exception as e:
        logger.error(f"自然语言推荐失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"自然语言推荐失败: {str(e)}")

@router.post("/optimize")
async def optimize_tool_chain(
    request: OptimizationRequest,
    current_user: User = Depends(get_current_user),
    recommendation_service: IntelligentRecommendationService = Depends(
        lambda: get_intelligent_recommendation_service(
            get_tool_service(),
            get_tool_usage_stats_manager(get_cache_manager(), get_db_manager()),
            get_nl_parser()
        )
    )
):
    """
    优化工具链
    
    基于用户反馈和性能目标优化现有工具链。
    """
    try:
        # 首先需要根据chain_id获取原始推荐
        # 这里简化处理，实际应该从数据库或缓存中获取
        from app.services.recommendations.recommendation_types import ToolChainRecommendation, ToolChainStep, RecommendationType, RecommendationReason
        
        # 创建一个模拟的原始推荐
        original_recommendation = ToolChainRecommendation(
            chain_id=request.chain_id,
            objective="示例目标",
            steps=[
                ToolChainStep(
                    step_number=1,
                    tool_id="example_tool",
                    tool_name="示例工具",
                    action_description="执行示例操作",
                    expected_input={},
                    expected_output={}
                )
            ],
            confidence_score=0.7,
            estimated_duration=30.0,
            complexity_level="medium",
            success_probability=0.75,
            recommendation_type=RecommendationType.AI_GENERATED,
            reasons=[RecommendationReason.AI_ANALYSIS],
            explanation="示例工具链"
        )
        
        # 优化工具链
        optimized_recommendation = await recommendation_service.optimize_tool_chain(
            chain_recommendation=original_recommendation,
            user_feedback=request.user_feedback,
            performance_goals=request.performance_goals
        )
        
        return {
            "success": True,
            "data": {
                "optimized_chain_id": optimized_recommendation.chain_id,
                "objective": optimized_recommendation.objective,
                "steps": [
                    {
                        "step_number": step.step_number,
                        "tool_name": step.tool_name,
                        "action_description": step.action_description,
                        "estimated_duration": step.estimated_duration
                    } for step in optimized_recommendation.steps
                ],
                "confidence_score": optimized_recommendation.confidence_score,
                "estimated_duration": optimized_recommendation.estimated_duration,
                "improvements": {
                    "original_confidence": original_recommendation.confidence_score,
                    "optimized_confidence": optimized_recommendation.confidence_score,
                    "confidence_improvement": optimized_recommendation.confidence_score - original_recommendation.confidence_score
                },
                "explanation": optimized_recommendation.explanation
            }
        }
        
    except Exception as e:
        logger.error(f"优化工具链失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"优化工具链失败: {str(e)}")

@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    recommendation_service: IntelligentRecommendationService = Depends(
        lambda: get_intelligent_recommendation_service(
            get_tool_service(),
            get_tool_usage_stats_manager(get_cache_manager(), get_db_manager()),
            get_nl_parser()
        )
    )
):
    """
    提交用户反馈
    
    用户可以对推荐结果提供反馈，帮助系统改进推荐质量。
    """
    try:
        # 构建反馈对象
        feedback = UserFeedback(
            feedback_id=f"feedback_{datetime.now().timestamp()}",
            user_id=current_user.id,
            recommendation_id=request.recommendation_id,
            rating=request.rating,
            comments=request.comments,
            used_recommendation=request.used_recommendation,
            execution_success=request.execution_success,
            actual_duration=request.actual_duration,
            suggested_improvements=request.suggested_improvements
        )
        
        # 提交反馈
        success = await recommendation_service.submit_feedback(feedback)
        
        if success:
            return {
                "success": True,
                "message": "反馈提交成功，感谢您的建议！",
                "data": {
                    "feedback_id": feedback.feedback_id,
                    "processed_at": feedback.created_at.isoformat()
                }
            }
        else:
            raise HTTPException(status_code=500, detail="反馈提交失败")
        
    except Exception as e:
        logger.error(f"提交反馈失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"提交反馈失败: {str(e)}")

@router.get("/metrics")
async def get_recommendation_metrics(
    days: int = Query(30, description="统计天数", ge=1, le=365),
    current_user: User = Depends(get_current_user),
    recommendation_service: IntelligentRecommendationService = Depends(
        lambda: get_intelligent_recommendation_service(
            get_tool_service(),
            get_tool_usage_stats_manager(get_cache_manager(), get_db_manager()),
            get_nl_parser()
        )
    )
):
    """
    获取推荐系统指标
    
    返回推荐系统的性能指标和统计数据。
    """
    try:
        metrics = await recommendation_service.get_recommendation_metrics(days=days)
        
        return {
            "success": True,
            "data": {
                "total_requests": metrics.total_requests,
                "successful_recommendations": metrics.successful_recommendations,
                "user_satisfaction_avg": metrics.user_satisfaction_avg,
                "execution_success_rate": metrics.execution_success_rate,
                "avg_processing_time": metrics.avg_processing_time,
                "recommendation_diversity": metrics.recommendation_diversity,
                "top_performing_chains": metrics.top_performing_chains,
                "statistics_period": f"过去{days}天"
            }
        }
        
    except Exception as e:
        logger.error(f"获取推荐指标失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取推荐指标失败: {str(e)}")

@router.post("/discover-tools")
async def discover_new_tools(
    request: ToolDiscoveryRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    auto_discovery: AutoToolDiscovery = Depends(
        lambda: get_auto_tool_discovery(
            get_tool_service(),
            get_health_checker(),
            get_threat_detector()
        )
    )
):
    """
    发现新工具
    
    扫描指定路径发现新的工具插件。
    """
    try:
        # 检查用户权限（只有管理员可以发现工具）
        if not getattr(current_user, 'is_admin', False):
            raise HTTPException(status_code=403, detail="只有管理员可以发现新工具")
        
        # 异步执行工具发现
        async def discover_and_register():
            try:
                # 发现工具
                discovered_tools = await auto_discovery.discover_tools(
                    search_paths=request.search_paths,
                    recursive=request.recursive
                )
                
                # 如果启用自动注册
                if request.auto_register:
                    registration_results = await auto_discovery.register_discovered_tools(
                        tools=discovered_tools,
                        auto_enable=True
                    )
                    logger.info(f"自动注册结果: {registration_results}")
                
                logger.info(f"工具发现完成，发现 {len(discovered_tools)} 个工具")
                
            except Exception as e:
                logger.error(f"后台工具发现任务失败: {str(e)}")
        
        # 添加到后台任务
        background_tasks.add_task(discover_and_register)
        
        return {
            "success": True,
            "message": "工具发现任务已启动",
            "data": {
                "search_paths": request.search_paths or auto_discovery.discovery_paths,
                "recursive": request.recursive,
                "auto_register": request.auto_register,
                "started_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"启动工具发现失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"启动工具发现失败: {str(e)}")

@router.get("/discovered-tools")
async def get_discovered_tools(
    current_user: User = Depends(get_current_user),
    auto_discovery: AutoToolDiscovery = Depends(
        lambda: get_auto_tool_discovery(
            get_tool_service(),
            get_health_checker(),
            get_threat_detector()
        )
    )
):
    """
    获取已发现的工具
    
    返回所有已发现但可能尚未注册的工具列表。
    """
    try:
        discovered_tools = []
        
        for tool_name, tool in auto_discovery.discovered_tools.items():
            status = await auto_discovery.get_tool_status(tool_name)
            if status:
                discovered_tools.append(status)
        
        return {
            "success": True,
            "data": {
                "discovered_tools": discovered_tools,
                "total_count": len(discovered_tools)
            }
        }
        
    except Exception as e:
        logger.error(f"获取已发现工具失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取已发现工具失败: {str(e)}")

@router.post("/hot-reload/{tool_name}")
async def hot_reload_tool(
    tool_name: str,
    current_user: User = Depends(get_current_user),
    auto_discovery: AutoToolDiscovery = Depends(
        lambda: get_auto_tool_discovery(
            get_tool_service(),
            get_health_checker(),
            get_threat_detector()
        )
    )
):
    """
    热重载工具
    
    重新加载指定的工具，用于开发过程中的快速迭代。
    """
    try:
        # 检查用户权限
        if not getattr(current_user, 'is_admin', False):
            raise HTTPException(status_code=403, detail="只有管理员可以热重载工具")
        
        success = await auto_discovery.hot_reload_tool(tool_name)
        
        if success:
            return {
                "success": True,
                "message": f"工具 {tool_name} 热重载成功",
                "data": {
                    "tool_name": tool_name,
                    "reloaded_at": datetime.now().isoformat()
                }
            }
        else:
            raise HTTPException(status_code=400, detail=f"工具 {tool_name} 热重载失败")
        
    except Exception as e:
        logger.error(f"热重载工具失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"热重载工具失败: {str(e)}")

# 健康检查端点
@router.get("/health")
async def health_check():
    """推荐系统健康检查"""
    return {
        "status": "healthy",
        "service": "intelligent-recommendations",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    } 