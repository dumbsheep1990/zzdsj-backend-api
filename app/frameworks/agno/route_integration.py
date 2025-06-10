"""
ZZDSJ Agno路由集成模块

将现有FastAPI路由与Agno代理系统集成，提供：
- 聊天路由的Agno代理集成
- 知识库路由的Agno代理集成  
- 助手路由的Agno代理集成
- AI服务路由的Agno代理集成
- 向后兼容性支持

Phase 3: API层适配的路由集成组件
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable
from functools import wraps

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .api_adapter import (
    get_api_adapter,
    ChatRequest,
    KnowledgeRequest,
    TeamRequest,
    APIResponse
)

logger = logging.getLogger(__name__)


class AgnoRouteConfig(BaseModel):
    """Agno路由配置"""
    enable_agno: bool = True
    fallback_to_legacy: bool = True
    enable_streaming: bool = False
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    rate_limit_enabled: bool = True
    max_requests_per_minute: int = 60


class ChatRequestModel(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    context: Optional[Dict[str, Any]] = Field(None, description="附加上下文")
    stream: bool = Field(False, description="是否流式响应")
    model_config: Optional[Dict[str, Any]] = Field(None, description="模型配置")


class KnowledgeRequestModel(BaseModel):
    """知识库请求模型"""
    query: str = Field(..., description="查询内容")
    kb_id: str = Field(..., description="知识库ID")
    context: Optional[Dict[str, Any]] = Field(None, description="附加上下文")
    stream: bool = Field(False, description="是否流式响应")
    search_kwargs: Optional[Dict[str, Any]] = Field(None, description="搜索参数")


class TeamRequestModel(BaseModel):
    """团队协作请求模型"""
    task: str = Field(..., description="任务描述")
    team_name: str = Field(..., description="团队名称")
    additional_context: Optional[Dict[str, Any]] = Field(None, description="附加上下文")
    stream: bool = Field(False, description="是否流式响应")


class ZZDSJAgnoRouteIntegrator:
    """ZZDSJ Agno路由集成器"""
    
    def __init__(self, config: AgnoRouteConfig = None):
        """初始化路由集成器"""
        self.config = config or AgnoRouteConfig()
        self.api_adapter = get_api_adapter()
        
        # 请求计数器（用于速率限制）
        self.request_counts: Dict[str, Dict[str, int]] = {}
        
        # 缓存存储
        self.response_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info("ZZDSJ Agno路由集成器已初始化")
    
    def agno_route(self, 
                   legacy_handler: Callable = None,
                   route_type: str = "chat",
                   enable_fallback: bool = True):
        """Agno路由装饰器"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    # 检查是否启用Agno
                    if not self.config.enable_agno:
                        if legacy_handler:
                            return await legacy_handler(*args, **kwargs)
                        else:
                            return await func(*args, **kwargs)
                    
                    # 速率限制检查
                    if self.config.rate_limit_enabled:
                        if not self._check_rate_limit(kwargs.get("user_id", "anonymous")):
                            raise HTTPException(
                                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                detail="请求频率过高，请稍后再试"
                            )
                    
                    # 尝试使用Agno处理
                    try:
                        agno_response = await self._handle_agno_request(route_type, *args, **kwargs)
                        if agno_response and agno_response.success:
                            return self._format_response(agno_response)
                    except Exception as agno_error:
                        logger.warning(f"Agno处理失败: {agno_error}")
                        
                        # 如果启用了回退机制
                        if enable_fallback and self.config.fallback_to_legacy:
                            logger.info("使用遗留处理器作为回退")
                            if legacy_handler:
                                return await legacy_handler(*args, **kwargs)
                            else:
                                return await func(*args, **kwargs)
                        else:
                            raise agno_error
                    
                    # 如果Agno没有成功处理且启用回退
                    if enable_fallback and self.config.fallback_to_legacy:
                        if legacy_handler:
                            return await legacy_handler(*args, **kwargs)
                        else:
                            return await func(*args, **kwargs)
                    
                    # 如果没有回退选项，返回错误
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Agno服务不可用且未配置回退选项"
                    )
                    
                except Exception as e:
                    logger.error(f"路由处理失败: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"内部服务器错误: {str(e)}"
                    )
            
            return wrapper
        return decorator
    
    async def _handle_agno_request(self, route_type: str, *args, **kwargs) -> Optional[APIResponse]:
        """处理Agno请求"""
        try:
            if route_type == "chat":
                return await self._handle_chat_request(*args, **kwargs)
            elif route_type == "knowledge":
                return await self._handle_knowledge_request(*args, **kwargs)
            elif route_type == "team":
                return await self._handle_team_request(*args, **kwargs)
            else:
                logger.warning(f"未知的路由类型: {route_type}")
                return None
                
        except Exception as e:
            logger.error(f"Agno请求处理失败: {e}")
            return None
    
    async def _handle_chat_request(self, request: ChatRequestModel, *args, **kwargs) -> APIResponse:
        """处理聊天请求"""
        chat_request = ChatRequest(
            message=request.message,
            session_id=request.session_id,
            user_id=request.user_id,
            context=request.context,
            stream=request.stream,
            model_config=request.model_config
        )
        
        return await self.api_adapter.handle_chat_request(chat_request)
    
    async def _handle_knowledge_request(self, request: KnowledgeRequestModel, *args, **kwargs) -> APIResponse:
        """处理知识库请求"""
        knowledge_request = KnowledgeRequest(
            query=request.query,
            kb_id=request.kb_id,
            context=request.context,
            stream=request.stream,
            search_kwargs=request.search_kwargs
        )
        
        return await self.api_adapter.handle_knowledge_request(knowledge_request)
    
    async def _handle_team_request(self, request: TeamRequestModel, *args, **kwargs) -> APIResponse:
        """处理团队协作请求"""
        team_request = TeamRequest(
            task=request.task,
            team_name=request.team_name,
            additional_context=request.additional_context,
            stream=request.stream
        )
        
        return await self.api_adapter.handle_team_request(team_request)
    
    def _check_rate_limit(self, user_id: str) -> bool:
        """检查速率限制"""
        if not self.config.rate_limit_enabled:
            return True
        
        try:
            current_minute = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            if user_id not in self.request_counts:
                self.request_counts[user_id] = {}
            
            user_requests = self.request_counts[user_id]
            current_count = user_requests.get(current_minute, 0)
            
            if current_count >= self.config.max_requests_per_minute:
                return False
            
            # 更新计数
            user_requests[current_minute] = current_count + 1
            
            # 清理旧的计数记录
            self._cleanup_old_counts(user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"速率限制检查失败: {e}")
            return True  # 出错时允许请求
    
    def _cleanup_old_counts(self, user_id: str):
        """清理旧的计数记录"""
        try:
            current_time = datetime.now()
            user_requests = self.request_counts[user_id]
            
            # 删除超过1小时的记录
            keys_to_delete = []
            for time_key in user_requests.keys():
                try:
                    record_time = datetime.strptime(time_key, "%Y-%m-%d %H:%M")
                    if (current_time - record_time).total_seconds() > 3600:
                        keys_to_delete.append(time_key)
                except:
                    keys_to_delete.append(time_key)
            
            for key in keys_to_delete:
                del user_requests[key]
                
        except Exception as e:
            logger.error(f"清理计数记录失败: {e}")
    
    def _format_response(self, api_response: APIResponse) -> JSONResponse:
        """格式化响应"""
        response_data = {
            "success": api_response.success,
            "data": api_response.data,
            "message": api_response.message,
            "timestamp": api_response.timestamp,
            "request_id": api_response.request_id
        }
        
        if api_response.error_code:
            response_data["error_code"] = api_response.error_code
        
        status_code = 200 if api_response.success else 500
        if api_response.error_code == "AGENT_CREATION_FAILED":
            status_code = 503
        elif api_response.error_code == "CHAT_PROCESSING_ERROR":
            status_code = 422
        
        return JSONResponse(
            content=response_data,
            status_code=status_code,
            headers={
                "X-Request-ID": api_response.request_id,
                "X-Powered-By": "ZZDSJ-Agno"
            }
        )
    
    def create_chat_router(self, legacy_chat_handler: Callable = None) -> APIRouter:
        """创建聊天路由"""
        router = APIRouter(tags=["Agno Chat"])
        
        @router.post("/chat", response_model=Dict[str, Any])
        @self.agno_route(legacy_handler=legacy_chat_handler, route_type="chat")
        async def agno_chat(
            request: ChatRequestModel,
            background_tasks: BackgroundTasks
        ):
            """Agno聊天接口"""
            # 实际处理在装饰器中完成
            pass
        
        @router.get("/chat/status")
        async def chat_status():
            """获取聊天服务状态"""
            status = self.api_adapter.get_api_status()
            return self._format_response(status)
        
        return router
    
    def create_knowledge_router(self, legacy_knowledge_handler: Callable = None) -> APIRouter:
        """创建知识库路由"""
        router = APIRouter(tags=["Agno Knowledge"])
        
        @router.post("/knowledge/query", response_model=Dict[str, Any])
        @self.agno_route(legacy_handler=legacy_knowledge_handler, route_type="knowledge")
        async def agno_knowledge_query(
            request: KnowledgeRequestModel,
            background_tasks: BackgroundTasks
        ):
            """Agno知识库查询接口"""
            # 实际处理在装饰器中完成
            pass
        
        @router.get("/knowledge/status")
        async def knowledge_status():
            """获取知识库服务状态"""
            status = self.api_adapter.get_api_status()
            return self._format_response(status)
        
        return router
    
    def create_team_router(self) -> APIRouter:
        """创建团队协作路由"""
        router = APIRouter(tags=["Agno Teams"])
        
        @router.post("/team/collaborate", response_model=Dict[str, Any])
        @self.agno_route(route_type="team", enable_fallback=False)
        async def agno_team_collaborate(
            request: TeamRequestModel,
            background_tasks: BackgroundTasks
        ):
            """Agno团队协作接口"""
            # 实际处理在装饰器中完成
            pass
        
        @router.get("/team/list")
        async def list_teams():
            """列出可用团队"""
            teams = self.api_adapter.list_available_teams()
            return self._format_response(teams)
        
        @router.get("/team/status")
        async def team_status():
            """获取团队服务状态"""
            status = self.api_adapter.get_api_status()
            return self._format_response(status)
        
        return router


# 全局路由集成器实例
_route_integrator = None

def get_route_integrator(config: AgnoRouteConfig = None) -> ZZDSJAgnoRouteIntegrator:
    """获取全局路由集成器实例"""
    global _route_integrator
    if _route_integrator is None:
        _route_integrator = ZZDSJAgnoRouteIntegrator(config)
    return _route_integrator


# 便捷函数
def create_agno_chat_router(legacy_handler: Callable = None) -> APIRouter:
    """创建Agno聊天路由"""
    integrator = get_route_integrator()
    return integrator.create_chat_router(legacy_handler)


def create_agno_knowledge_router(legacy_handler: Callable = None) -> APIRouter:
    """创建Agno知识库路由"""
    integrator = get_route_integrator()
    return integrator.create_knowledge_router(legacy_handler)


def create_agno_team_router() -> APIRouter:
    """创建Agno团队协作路由"""
    integrator = get_route_integrator()
    return integrator.create_team_router()


def agno_route(route_type: str = "chat", 
               legacy_handler: Callable = None,
               enable_fallback: bool = True):
    """Agno路由装饰器（便捷函数）"""
    integrator = get_route_integrator()
    return integrator.agno_route(legacy_handler, route_type, enable_fallback)


# 示例集成
def example_integration():
    """路由集成示例"""
    from fastapi import FastAPI
    
    app = FastAPI(title="ZZDSJ Agno API")
    
    # 配置Agno路由
    config = AgnoRouteConfig(
        enable_agno=True,
        fallback_to_legacy=True,
        enable_streaming=False,
        rate_limit_enabled=True,
        max_requests_per_minute=60
    )
    
    # 获取路由集成器
    integrator = get_route_integrator(config)
    
    # 添加路由
    app.include_router(integrator.create_chat_router(), prefix="/api/v1/agno")
    app.include_router(integrator.create_knowledge_router(), prefix="/api/v1/agno")
    app.include_router(integrator.create_team_router(), prefix="/api/v1/agno")
    
    logger.info("Agno路由集成示例配置完成")
    return app


if __name__ == "__main__":
    # 运行示例
    example_app = example_integration()
    logger.info("✅ Agno路由集成测试完成") 