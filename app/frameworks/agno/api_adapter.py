"""
ZZDSJ Agno API适配器

将FastAPI路由与Agno代理系统集成，提供：
- 聊天API的Agno代理集成
- 知识库API的Agno代理集成
- 助手API的Agno代理集成
- AI服务API的Agno代理集成
- 统一的错误处理和响应格式

Phase 3: API层适配的核心组件
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
import uuid

try:
    from agno.agent import Agent
    from agno.team import Team
    from agno.models.openai import OpenAIChat
    from agno.models.anthropic import Claude
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False
    # 创建虚拟类以支持类型提示
    class Agent:
        pass
    
    class Team:
        pass

logger = logging.getLogger(__name__)


@dataclass
class APIResponse:
    """统一API响应格式"""
    success: bool
    data: Any = None
    message: str = ""
    timestamp: str = ""
    request_id: str = ""
    error_code: Optional[str] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.request_id:
            self.request_id = str(uuid.uuid4())


@dataclass
class ChatRequest:
    """聊天请求格式"""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    stream: bool = False
    model_config: Optional[Dict[str, Any]] = None


@dataclass
class KnowledgeRequest:
    """知识库请求格式"""
    query: str
    kb_id: str
    context: Optional[Dict[str, Any]] = None
    stream: bool = False
    search_kwargs: Optional[Dict[str, Any]] = None


@dataclass
class TeamRequest:
    """团队协作请求格式"""
    task: str
    team_name: str
    additional_context: Optional[Dict[str, Any]] = None
    stream: bool = False


class ZZDSJAgnoAPIAdapter:
    """ZZDSJ Agno API适配器"""
    
    def __init__(self):
        """初始化API适配器"""
        # 延迟导入以避免循环依赖
        from . import get_service_adapter, get_team_coordinator, ZZDSJMCPAdapter
        from .model_config_adapter import get_model_adapter
        
        self.service_adapter = get_service_adapter()
        self.team_coordinator = get_team_coordinator()
        self.mcp_adapter = ZZDSJMCPAdapter()
        self.model_adapter = get_model_adapter()
        
        # 代理缓存
        self.agent_cache: Dict[str, Agent] = {}
        self.team_cache: Dict[str, Team] = {}
        
        # 会话管理
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        logger.info("ZZDSJ Agno API适配器已初始化")
    
    def _create_error_response(self, 
                             message: str, 
                             error_code: str = "INTERNAL_ERROR",
                             request_id: str = None) -> APIResponse:
        """创建错误响应"""
        return APIResponse(
            success=False,
            message=message,
            error_code=error_code,
            request_id=request_id or str(uuid.uuid4())
        )
    
    def _create_success_response(self, 
                               data: Any = None, 
                               message: str = "Success",
                               request_id: str = None) -> APIResponse:
        """创建成功响应"""
        return APIResponse(
            success=True,
            data=data,
            message=message,
            request_id=request_id or str(uuid.uuid4())
        )
    
    async def handle_chat_request(self, request: ChatRequest) -> APIResponse:
        """处理聊天请求"""
        try:
            if not AGNO_AVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Agno框架不可用"
                )
            
            request_id = str(uuid.uuid4())
            session_id = request.session_id or f"chat_{request.user_id}_{datetime.now().timestamp()}"
            user_id = request.user_id or "anonymous"
            
            agent_key = f"chat_{session_id}_{user_id}"
            agent = self.agent_cache.get(agent_key)
            
            if not agent:
                agent = await self.service_adapter.create_chat_agent(
                    session_id=session_id,
                    user_id=user_id,
                    model_config=request.model_config
                )
                if agent:
                    self.agent_cache[agent_key] = agent
                else:
                    return self._create_error_response(
                        "无法创建聊天代理",
                        "AGENT_CREATION_FAILED",
                        request_id
                    )
            
            # 更新会话状态
            self.active_sessions[session_id] = {
                "user_id": user_id,
                "last_activity": datetime.now().isoformat(),
                "message_count": self.active_sessions.get(session_id, {}).get("message_count", 0) + 1
            }
            
            # 处理响应
            response = agent.run(request.message)
            
            return self._create_success_response(
                data={
                    "response": response.content if hasattr(response, 'content') else str(response),
                    "session_id": session_id,
                    "user_id": user_id,
                    "message_count": self.active_sessions[session_id]["message_count"]
                },
                message="聊天响应生成成功",
                request_id=request_id
            )
                
        except Exception as e:
            logger.error(f"聊天请求处理失败: {e}")
            return self._create_error_response(
                f"聊天请求处理失败: {str(e)}",
                "CHAT_PROCESSING_ERROR",
                request_id
            )
    
    async def handle_knowledge_request(self, request: KnowledgeRequest) -> APIResponse:
        """处理知识库请求"""
        try:
            if not AGNO_AVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Agno框架不可用"
                )
            
            request_id = str(uuid.uuid4())
            
            # 获取或创建知识库代理
            agent_key = f"knowledge_{request.kb_id}"
            agent = self.agent_cache.get(agent_key)
            
            if not agent:
                agent = await self.service_adapter.create_knowledge_agent(
                    kb_id=request.kb_id
                )
                if agent:
                    self.agent_cache[agent_key] = agent
                else:
                    return self._create_error_response(
                        f"无法创建知识库代理: {request.kb_id}",
                        "KNOWLEDGE_AGENT_CREATION_FAILED",
                        request_id
                    )
            
            # 构建查询上下文
            full_query = request.query
            if request.context:
                context_str = "\n".join([f"{k}: {v}" for k, v in request.context.items()])
                full_query = f"{request.query}\n\n上下文:\n{context_str}"
            
            response = agent.run(full_query)
            
            return self._create_success_response(
                data={
                    "response": response.content if hasattr(response, 'content') else str(response),
                    "kb_id": request.kb_id,
                    "query": request.query
                },
                message="知识库查询成功",
                request_id=request_id
            )
                
        except Exception as e:
            logger.error(f"知识库请求处理失败: {e}")
            return self._create_error_response(
                f"知识库请求处理失败: {str(e)}",
                "KNOWLEDGE_PROCESSING_ERROR",
                request_id
            )
    
    async def handle_team_request(self, request: TeamRequest) -> APIResponse:
        """处理团队协作请求"""
        try:
            if not AGNO_AVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Agno框架不可用"
                )
            
            request_id = str(uuid.uuid4())
            
            # 运行团队协作
            result = await self.team_coordinator.run_team_collaboration(
                team_name=request.team_name,
                task=request.task,
                additional_context=request.additional_context
            )
            
            if result.success:
                return self._create_success_response(
                    data={
                        "result": result.result,
                        "team_name": request.team_name,
                        "duration_seconds": result.duration_seconds,
                        "iterations_used": result.iterations_used,
                        "performance_metrics": result.performance_metrics
                    },
                    message="团队协作完成",
                    request_id=request_id
                )
            else:
                return self._create_error_response(
                    f"团队协作失败: {'; '.join(result.issues)}",
                    "TEAM_COLLABORATION_FAILED",
                    request_id
                )
                
        except Exception as e:
            logger.error(f"团队协作请求处理失败: {e}")
            return self._create_error_response(
                f"团队协作请求处理失败: {str(e)}",
                "TEAM_PROCESSING_ERROR",
                request_id
            )
    
    def get_api_status(self) -> APIResponse:
        """获取API状态"""
        try:
            service_status = self.service_adapter.get_service_status()
            team_metrics = self.team_coordinator.get_performance_metrics()
            
            status_data = {
                "agno_available": AGNO_AVAILABLE,
                "active_agents": len(self.agent_cache),
                "active_teams": len(self.team_cache),
                "active_sessions": len(self.active_sessions),
                "service_adapter": service_status,
                "team_coordinator": team_metrics
            }
            
            return self._create_success_response(
                data=status_data,
                message="API状态获取成功"
            )
            
        except Exception as e:
            logger.error(f"API状态获取失败: {e}")
            return self._create_error_response(
                f"API状态获取失败: {str(e)}",
                "STATUS_RETRIEVAL_ERROR"
            )
    
    async def cleanup_inactive_sessions(self, max_age_hours: int = 24):
        """清理不活跃的会话"""
        try:
            current_time = datetime.now()
            inactive_sessions = []
            
            for session_id, session_data in self.active_sessions.items():
                last_activity = datetime.fromisoformat(session_data["last_activity"])
                age_hours = (current_time - last_activity).total_seconds() / 3600
                
                if age_hours > max_age_hours:
                    inactive_sessions.append(session_id)
            
            # 清理不活跃会话
            for session_id in inactive_sessions:
                del self.active_sessions[session_id]
                
                # 清理相关的代理缓存
                agent_keys_to_remove = [
                    key for key in self.agent_cache.keys() 
                    if session_id in key
                ]
                for key in agent_keys_to_remove:
                    del self.agent_cache[key]
            
            logger.info(f"已清理 {len(inactive_sessions)} 个不活跃会话")
            
        except Exception as e:
            logger.error(f"会话清理失败: {e}")
    
    def list_available_teams(self) -> APIResponse:
        """列出可用的团队"""
        try:
            teams = self.team_coordinator.list_available_teams()
            
            team_details = []
            for team_name in teams:
                status = self.team_coordinator.get_team_status(team_name)
                if status:
                    team_details.append(status)
            
            return self._create_success_response(
                data={
                    "teams": team_details,
                    "total_count": len(team_details)
                },
                message="可用团队列表获取成功"
            )
            
        except Exception as e:
            logger.error(f"团队列表获取失败: {e}")
            return self._create_error_response(
                f"团队列表获取失败: {str(e)}",
                "TEAM_LIST_ERROR"
            )


# 全局API适配器实例
_api_adapter = None

def get_api_adapter() -> ZZDSJAgnoAPIAdapter:
    """获取全局API适配器实例"""
    global _api_adapter
    if _api_adapter is None:
        _api_adapter = ZZDSJAgnoAPIAdapter()
    return _api_adapter


# 便捷函数
async def handle_chat_api(request: ChatRequest) -> APIResponse:
    """处理聊天API请求"""
    adapter = get_api_adapter()
    return await adapter.handle_chat_request(request)


async def handle_knowledge_api(request: KnowledgeRequest) -> APIResponse:
    """处理知识库API请求"""
    adapter = get_api_adapter()
    return await adapter.handle_knowledge_request(request)


async def handle_team_api(request: TeamRequest) -> APIResponse:
    """处理团队协作API请求"""
    adapter = get_api_adapter()
    return await adapter.handle_team_request(request)


def get_agno_api_status() -> APIResponse:
    """获取Agno API状态"""
    adapter = get_api_adapter()
    return adapter.get_api_status()


def list_agno_teams() -> APIResponse:
    """列出可用的Agno团队"""
    adapter = get_api_adapter()
    return adapter.list_available_teams()


# 示例使用
async def example_api_usage():
    """API适配器使用示例"""
    try:
        # 获取API适配器
        adapter = get_api_adapter()
        
        # 测试聊天API
        chat_request = ChatRequest(
            message="你好，请介绍一下ZZDSJ项目",
            user_id="test_user",
            stream=False
        )
        
        chat_response = await adapter.handle_chat_request(chat_request)
        print(f"✅ 聊天API测试: {chat_response.success}")
        
        # 测试团队协作API
        team_request = TeamRequest(
            task="分析当前AI代理技术发展趋势",
            team_name="research_team",
            stream=False
        )
        
        team_response = await adapter.handle_team_request(team_request)
        print(f"✅ 团队API测试: {team_response.success}")
        
        # 获取API状态
        status = adapter.get_api_status()
        print(f"✅ API状态: {status.success}")
        
    except Exception as e:
        logger.error(f"API示例使用失败: {e}")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_api_usage()) 