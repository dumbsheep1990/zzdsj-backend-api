"""
Agno框架FastAPI集成组件

实现Agno代理与FastAPI路由系统的深度集成，提供生产级API支持
根据Agno官方文档实现标准化集成模式
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# Agno核心导入 - 根据官方文档语法
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools

# ZZDSJ内部组件导入
from .api_adapter import ZZDSJAgnoAPIAdapter, APIResponse
from .route_integration import ZZDSJAgnoRouteIntegrator, AgnoRouteConfig
from .response_formatters import ZZDSJResponseFormatter, ResponseStatus
from .team_coordinator import ZZDSJTeamCoordinator

logger = logging.getLogger(__name__)


class ZZDSJAgnoFastAPIIntegration:
    """ZZDSJ Agno FastAPI集成器"""
    
    def __init__(self, app: FastAPI = None):
        """初始化FastAPI集成器"""
        self.app = app or FastAPI(
            title="ZZDSJ Agno API",
            description="Agno框架驱动的智能代理API服务",
            version="1.0.0"
        )
        
        # 核心组件
        self.api_adapter = ZZDSJAgnoAPIAdapter()
        self.route_integrator = ZZDSJAgnoRouteIntegrator()
        self.response_formatter = ZZDSJResponseFormatter()
        self.team_coordinator = ZZDSJTeamCoordinator()
        
        # 代理注册表
        self.agents: Dict[str, Agent] = {}
        self.teams: Dict[str, Team] = {}
        
        # 配置中间件
        self._setup_middleware()
        
        # 注册核心路由
        self._setup_core_routes()
        
        # 预定义智能代理
        self._setup_predefined_agents()
        
        logger.info("Agno FastAPI集成器初始化完成")

    def _setup_middleware(self):
        """设置中间件"""
        # CORS中间件
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Gzip压缩中间件
        self.app.add_middleware(GZipMiddleware, minimum_size=1000)
        
        # 自定义Agno中间件
        @self.app.middleware("http")
        async def agno_middleware(request: Request, call_next):
            start_time = datetime.now()
            
            # 添加请求ID
            request_id = f"agno-{int(start_time.timestamp())}"
            request.state.request_id = request_id
            
            # 调用下一个中间件
            response = await call_next(request)
            
            # 添加响应头
            response.headers["X-Agno-Request-ID"] = request_id
            response.headers["X-Agno-Version"] = "1.0.0"
            
            # 记录性能指标
            process_time = (datetime.now() - start_time).total_seconds()
            response.headers["X-Process-Time"] = str(process_time)
            
            return response

    def _setup_core_routes(self):
        """设置核心路由"""
        
        @self.app.get("/")
        async def root():
            """根路径"""
            return self.response_formatter.format_success({
                "message": "ZZDSJ Agno API服务",
                "version": "1.0.0",
                "documentation": "/docs",
                "health": "/health"
            })
        
        @self.app.get("/health")
        async def health_check():
            """健康检查"""
            try:
                # 检查代理状态
                agent_count = len(self.agents)
                team_count = len(self.teams)
                
                health_data = {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "agents": {"count": agent_count, "status": "operational"},
                    "teams": {"count": team_count, "status": "operational"},
                    "components": {
                        "api_adapter": "healthy",
                        "route_integrator": "healthy",
                        "response_formatter": "healthy",
                        "team_coordinator": "healthy"
                    }
                }
                
                return self.response_formatter.format_success(health_data)
                
            except Exception as e:
                logger.error(f"健康检查失败: {e}")
                return self.response_formatter.format_error(
                    f"健康检查失败: {str(e)}",
                    500
                )

        @self.app.get("/agents")
        async def list_agents():
            """列出所有代理"""
            try:
                agent_list = [
                    {
                        "id": agent_id,
                        "name": getattr(agent, 'name', agent_id),
                        "description": getattr(agent, 'description', ''),
                        "tools": [tool.__class__.__name__ for tool in getattr(agent, 'tools', [])],
                        "status": "active"
                    }
                    for agent_id, agent in self.agents.items()
                ]
                
                return self.response_formatter.format_success({
                    "agents": agent_list,
                    "total": len(agent_list)
                })
                
            except Exception as e:
                logger.error(f"列出代理失败: {e}")
                return self.response_formatter.format_error(
                    f"列出代理失败: {str(e)}"
                )

        @self.app.get("/teams")
        async def list_teams():
            """列出所有团队"""
            try:
                team_list = [
                    {
                        "id": team_id,
                        "name": getattr(team, 'name', team_id),
                        "mode": getattr(team, 'mode', 'coordinate'),
                        "members": len(getattr(team, 'members', [])),
                        "status": "active"
                    }
                    for team_id, team in self.teams.items()
                ]
                
                return self.response_formatter.format_success({
                    "teams": team_list,
                    "total": len(team_list)
                })
                
            except Exception as e:
                logger.error(f"列出团队失败: {e}")
                return self.response_formatter.format_error(
                    f"列出团队失败: {str(e)}"
                )

    def _setup_predefined_agents(self):
        """设置预定义智能代理"""
        try:
            # 通用聊天代理 - 根据Agno官方文档语法
            chat_agent = Agent(
                model=OpenAIChat(id="gpt-4o"),
                description="通用聊天助手，可以回答各种问题",
                instructions=[
                    "友好、专业地回答用户问题",
                    "如果不确定答案，诚实地说明",
                    "提供有用、准确的信息"
                ],
                markdown=True
            )
            self.agents["chat"] = chat_agent
            
            # 搜索代理 - 带工具的代理
            search_agent = Agent(
                model=OpenAIChat(id="gpt-4o"),
                tools=[DuckDuckGoTools()],
                description="具备网络搜索能力的智能代理",
                instructions=[
                    "使用搜索工具获取最新信息",
                    "总是包含信息来源",
                    "提供准确、及时的答案"
                ],
                show_tool_calls=True,
                markdown=True
            )
            self.agents["search"] = search_agent
            
            # 创建研究团队 - 根据Agno官方文档的Team语法
            research_team = Team(
                mode="coordinate",
                members=[search_agent],
                model=OpenAIChat(id="gpt-4o"),
                instructions=[
                    "协调搜索代理",
                    "提供综合性研究报告",
                    "确保信息准确性"
                ],
                show_tool_calls=True,
                markdown=True
            )
            self.teams["research"] = research_team
            
            logger.info("预定义代理设置完成")
            
        except Exception as e:
            logger.error(f"预定义代理设置失败: {e}")

    async def register_agent(self, agent_id: str, agent: Agent) -> bool:
        """注册新代理"""
        try:
            self.agents[agent_id] = agent
            logger.info(f"代理 {agent_id} 注册成功")
            return True
        except Exception as e:
            logger.error(f"注册代理 {agent_id} 失败: {e}")
            return False

    async def register_team(self, team_id: str, team: Team) -> bool:
        """注册新团队"""
        try:
            self.teams[team_id] = team
            logger.info(f"团队 {team_id} 注册成功")
            return True
        except Exception as e:
            logger.error(f"注册团队 {team_id} 失败: {e}")
            return False

    async def chat_with_agent(
        self,
        agent_id: str,
        message: str,
        stream: bool = False,
        session_id: Optional[str] = None
    ) -> Union[str, AsyncGenerator[str, None]]:
        """与代理聊天"""
        try:
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail=f"代理 {agent_id} 不存在")
            
            agent = self.agents[agent_id]
            
            if stream:
                # 流式响应
                async def generate_response():
                    try:
                        response = agent.print_response(message, stream=True)
                        if hasattr(response, '__aiter__'):
                            async for chunk in response:
                                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                        else:
                            yield f"data: {json.dumps({'chunk': str(response)})}\n\n"
                        yield "data: [DONE]\n\n"
                    except Exception as e:
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
                
                return generate_response()
            else:
                # 非流式响应
                response = agent.print_response(message, stream=False)
                return str(response)
                
        except Exception as e:
            logger.error(f"代理聊天失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def chat_with_team(
        self,
        team_id: str,
        message: str,
        stream: bool = False,
        session_id: Optional[str] = None
    ) -> Union[str, AsyncGenerator[str, None]]:
        """与团队聊天"""
        try:
            if team_id not in self.teams:
                raise HTTPException(status_code=404, detail=f"团队 {team_id} 不存在")
            
            team = self.teams[team_id]
            
            if stream:
                # 流式响应
                async def generate_response():
                    try:
                        response = team.print_response(message, stream=True)
                        if hasattr(response, '__aiter__'):
                            async for chunk in response:
                                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                        else:
                            yield f"data: {json.dumps({'chunk': str(response)})}\n\n"
                        yield "data: [DONE]\n\n"
                    except Exception as e:
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
                
                return generate_response()
            else:
                # 非流式响应
                response = team.print_response(message, stream=False)
                return str(response)
                
        except Exception as e:
            logger.error(f"团队聊天失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def setup_chat_routes(self):
        """设置聊天路由"""
        
        @self.app.post("/chat/{agent_id}")
        async def chat_agent(
            agent_id: str,
            request: Dict[str, Any],
            background_tasks: BackgroundTasks
        ):
            """与指定代理聊天"""
            try:
                message = request.get("message", "")
                stream = request.get("stream", False)
                session_id = request.get("session_id")
                
                if not message:
                    return self.response_formatter.format_error("消息不能为空", 400)
                
                if stream:
                    response_gen = await self.chat_with_agent(agent_id, message, True, session_id)
                    return StreamingResponse(
                        response_gen,
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive",
                        }
                    )
                else:
                    response = await self.chat_with_agent(agent_id, message, False, session_id)
                    return self.response_formatter.format_success({
                        "response": response,
                        "agent_id": agent_id,
                        "session_id": session_id
                    })
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"聊天路由错误: {e}")
                return self.response_formatter.format_error(str(e), 500)

        @self.app.post("/team/{team_id}")
        async def chat_team(
            team_id: str,
            request: Dict[str, Any],
            background_tasks: BackgroundTasks
        ):
            """与指定团队聊天"""
            try:
                message = request.get("message", "")
                stream = request.get("stream", False)
                session_id = request.get("session_id")
                
                if not message:
                    return self.response_formatter.format_error("消息不能为空", 400)
                
                if stream:
                    response_gen = await self.chat_with_team(team_id, message, True, session_id)
                    return StreamingResponse(
                        response_gen,
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive",
                        }
                    )
                else:
                    response = await self.chat_with_team(team_id, message, False, session_id)
                    return self.response_formatter.format_success({
                        "response": response,
                        "team_id": team_id,
                        "session_id": session_id
                    })
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"团队聊天路由错误: {e}")
                return self.response_formatter.format_error(str(e), 500)

    def get_app(self) -> FastAPI:
        """获取FastAPI应用实例"""
        # 设置聊天路由
        self.setup_chat_routes()
        return self.app


# 全局集成器实例
_agno_integration: Optional[ZZDSJAgnoFastAPIIntegration] = None


def get_agno_integration() -> ZZDSJAgnoFastAPIIntegration:
    """获取全局Agno集成器实例"""
    global _agno_integration
    if _agno_integration is None:
        _agno_integration = ZZDSJAgnoFastAPIIntegration()
    return _agno_integration


async def init_agno_integration(app: FastAPI):
    """初始化Agno集成"""
    global _agno_integration
    _agno_integration = ZZDSJAgnoFastAPIIntegration(app)
    logger.info("Agno FastAPI集成初始化完成")


@asynccontextmanager
async def agno_lifespan(app: FastAPI):
    """Agno生命周期管理器"""
    # 启动时
    await init_agno_integration(app)
    logger.info("Agno集成启动完成")
    
    yield
    
    # 关闭时
    logger.info("Agno集成关闭")


# 便捷函数
def create_agno_app() -> FastAPI:
    """创建带Agno集成的FastAPI应用"""
    app = FastAPI(
        title="ZZDSJ Agno API",
        description="Agno框架驱动的智能代理API服务",
        version="1.0.0",
        lifespan=agno_lifespan
    )
    
    integration = ZZDSJAgnoFastAPIIntegration(app)
    return integration.get_app() 