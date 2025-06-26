"""
Agno API动态适配器
与ZZDSJ API系统动态集成，基于系统配置和用户权限提供Agno框架的API接口
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from app.frameworks.agno.dynamic_agent_factory import get_agent_factory, create_dynamic_agent
from app.frameworks.agno.config import get_user_agno_config, get_system_agno_config
from app.frameworks.agno.chat import DynamicAgnoChatManager, get_session_manager
from app.frameworks.agno.tools import get_tools_manager

logger = logging.getLogger(__name__)

class DynamicAgnoAPIAdapter:
    """
    动态Agno API适配器
    提供与ZZDSJ API系统的动态集成，支持用户权限和系统配置
    """
    
    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id
        self._agent_factory = get_agent_factory()
        self._tools_manager = get_tools_manager(user_id)
        self._session_manager = get_session_manager()
        
    async def create_agent_from_config(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        从配置创建Agent
        
        Args:
            agent_config: Agent配置
            
        Returns:
            创建结果
        """
        try:
            # 验证配置
            validated_config = await self._validate_agent_config(agent_config)
            
            # 创建Agent
            agent = await create_dynamic_agent(
                agent_config=validated_config,
                user_id=self.user_id or "system"
            )
            
            if agent:
                agent_id = f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(validated_config))}"
                
                return {
                    "success": True,
                    "agent_id": agent_id,
                    "config": validated_config,
                    "message": "Agent创建成功"
                }
            else:
                return {
                    "success": False,
                    "error": "Agent创建失败",
                    "config": validated_config
                }
                
        except Exception as e:
            logger.error(f"创建Agent失败: {str(e)}")
            return {
                "success": False,
                "error": f"创建Agent失败: {str(e)}"
            }
    
    async def _validate_agent_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证Agent配置"""
        try:
            # 获取用户配置
            if self.user_id:
                agno_config = await get_user_agno_config(self.user_id)
            else:
                agno_config = await get_system_agno_config()
            
            # 验证和填充默认值
            validated_config = {
                "name": config.get("name", "Dynamic Agent"),
                "role": config.get("role", "AI Assistant"),
                "description": config.get("description", "A dynamic AI agent"),
                "instructions": config.get("instructions", []),
                "model_config": config.get("model_config", {
                    "model_id": agno_config.models.default_chat_model,
                    "type": "chat"
                }),
                "tools": await self._validate_tools(config.get("tools", [])),
                "knowledge_bases": config.get("knowledge_bases", []),
                "show_tool_calls": config.get("show_tool_calls", agno_config.features.show_tool_calls),
                "markdown": config.get("markdown", agno_config.features.markdown)
            }
            
            return validated_config
            
        except Exception as e:
            logger.error(f"验证Agent配置失败: {str(e)}")
            raise
    
    async def _validate_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """验证工具配置"""
        validated_tools = []
        
        try:
            for tool in tools:
                tool_id = tool.get("tool_id")
                if not tool_id:
                    continue
                
                # 检查用户权限
                if self.user_id:
                    from app.services.tools.tool_service import ToolService
                    from app.utils.core.database import get_db
                    
                    db = next(get_db())
                    tool_service = ToolService(db)
                    
                    has_permission = await tool_service.check_tool_permission(
                        self.user_id, tool_id
                    )
                    
                    if has_permission:
                        validated_tools.append(tool)
                else:
                    # 系统级别，直接添加
                    validated_tools.append(tool)
            
            return validated_tools
            
        except Exception as e:
            logger.error(f"验证工具配置失败: {str(e)}")
            return []
    
    async def query_agent(
        self,
        agent_id: str,
        query: str,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], Dict[str, Any]]:
        """
        查询Agent
        
        Args:
            agent_id: Agent ID
            query: 查询内容
            stream: 是否流式响应
            **kwargs: 其他参数
            
        Returns:
            查询结果
        """
        try:
            # 这里可以根据agent_id获取已创建的Agent
            # 或者创建一个临时的聊天会话
            
            chat_session = await self._session_manager.create_session(
                user_id=self.user_id or "system"
            )
            
            if stream:
                # 流式响应处理需要特殊处理
                # 这里返回一个标识，实际流式数据通过其他接口提供
                return {
                    "success": True,
                    "stream": True,
                    "session_id": chat_session.session_id,
                    "message": "流式查询已启动"
                }
            else:
                response = await chat_session.send(query, **kwargs)
                
                return {
                    "success": True,
                    "response": response,
                    "session_id": chat_session.session_id,
                    "agent_id": agent_id
                }
                
        except Exception as e:
            logger.error(f"查询Agent失败: {str(e)}")
            return {
                "success": False,
                "error": f"查询Agent失败: {str(e)}"
            }
    
    async def create_chat_session(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        创建聊天会话
        
        Args:
            config: 聊天配置
            
        Returns:
            会话信息
        """
        try:
            chat_manager = DynamicAgnoChatManager(
                user_id=self.user_id,
                chat_config=config or {}
            )
            
            await chat_manager.initialize()
            
            return {
                "success": True,
                "session_id": chat_manager.session_id,
                "user_id": self.user_id,
                "config": config,
                "message": "聊天会话创建成功"
            }
            
        except Exception as e:
            logger.error(f"创建聊天会话失败: {str(e)}")
            return {
                "success": False,
                "error": f"创建聊天会话失败: {str(e)}"
            }
    
    async def send_chat_message(
        self,
        session_id: str,
        message: str,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送聊天消息
        
        Args:
            session_id: 会话ID
            message: 消息内容
            stream: 是否流式响应
            **kwargs: 其他参数
            
        Returns:
            响应结果
        """
        try:
            session = self._session_manager.get_session(session_id)
            if not session:
                return {
                    "success": False,
                    "error": f"会话 {session_id} 不存在"
                }
            
            if stream:
                # 流式响应标识
                return {
                    "success": True,
                    "stream": True,
                    "session_id": session_id,
                    "message": "流式响应已启动"
                }
            else:
                response = await session.send(message, **kwargs)
                
                return {
                    "success": True,
                    "response": response,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"发送聊天消息失败: {str(e)}")
            return {
                "success": False,
                "error": f"发送聊天消息失败: {str(e)}"
            }
    
    async def get_available_models(self) -> Dict[str, Any]:
        """获取可用模型列表"""
        try:
            from app.frameworks.agno.model_config_adapter import get_model_adapter
            
            model_adapter = get_model_adapter()
            models = await model_adapter.get_available_models(self.user_id)
            
            return {
                "success": True,
                "models": models,
                "count": len(models)
            }
            
        except Exception as e:
            logger.error(f"获取可用模型失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取可用模型失败: {str(e)}",
                "models": []
            }
    
    async def get_available_tools(self) -> Dict[str, Any]:
        """获取可用工具列表"""
        try:
            tools = await self._tools_manager.get_available_tools()
            
            return {
                "success": True,
                "tools": tools,
                "count": len(tools)
            }
            
        except Exception as e:
            logger.error(f"获取可用工具失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取可用工具失败: {str(e)}",
                "tools": []
            }
    
    async def get_user_config(self) -> Dict[str, Any]:
        """获取用户配置"""
        try:
            if not self.user_id:
                config = await get_system_agno_config()
            else:
                config = await get_user_agno_config(self.user_id)
            
            return {
                "success": True,
                "config": config.to_dict(),
                "user_id": self.user_id
            }
            
        except Exception as e:
            logger.error(f"获取用户配置失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取用户配置失败: {str(e)}"
            }
    
    async def update_user_config(self, config_updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新用户配置"""
        try:
            if not self.user_id:
                return {
                    "success": False,
                    "error": "无法更新系统级配置"
                }
            
            from app.frameworks.agno.config import get_config_manager
            
            config_manager = get_config_manager()
            success = await config_manager.update_user_config(self.user_id, config_updates)
            
            if success:
                return {
                    "success": True,
                    "message": "用户配置更新成功",
                    "user_id": self.user_id,
                    "updates": config_updates
                }
            else:
                return {
                    "success": False,
                    "error": "用户配置更新失败"
                }
                
        except Exception as e:
            logger.error(f"更新用户配置失败: {str(e)}")
            return {
                "success": False,
                "error": f"更新用户配置失败: {str(e)}"
            }

class AgnoAPIRouter:
    """Agno API路由器 - 提供统一的API接口"""
    
    def __init__(self):
        self._adapters: Dict[str, DynamicAgnoAPIAdapter] = {}
    
    def get_adapter(self, user_id: Optional[str] = None) -> DynamicAgnoAPIAdapter:
        """获取用户的API适配器"""
        key = user_id or "system"
        
        if key not in self._adapters:
            self._adapters[key] = DynamicAgnoAPIAdapter(user_id)
        
        return self._adapters[key]
    
    async def handle_agent_request(
        self,
        request_type: str,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理Agent请求
        
        Args:
            request_type: 请求类型
            user_id: 用户ID
            **kwargs: 请求参数
            
        Returns:
            处理结果
        """
        try:
            adapter = self.get_adapter(user_id)
            
            if request_type == "create_agent":
                return await adapter.create_agent_from_config(kwargs.get("config", {}))
            elif request_type == "query_agent":
                return await adapter.query_agent(**kwargs)
            elif request_type == "create_chat":
                return await adapter.create_chat_session(kwargs.get("config"))
            elif request_type == "send_message":
                return await adapter.send_chat_message(**kwargs)
            elif request_type == "get_models":
                return await adapter.get_available_models()
            elif request_type == "get_tools":
                return await adapter.get_available_tools()
            elif request_type == "get_config":
                return await adapter.get_user_config()
            elif request_type == "update_config":
                return await adapter.update_user_config(kwargs.get("config_updates", {}))
            else:
                return {
                    "success": False,
                    "error": f"未知的请求类型: {request_type}"
                }
                
        except Exception as e:
            logger.error(f"处理Agent请求失败: {str(e)}")
            return {
                "success": False,
                "error": f"处理请求失败: {str(e)}"
            }

# 全局API路由器实例
_global_api_router: Optional[AgnoAPIRouter] = None

def get_api_router() -> AgnoAPIRouter:
    """获取全局API路由器"""
    global _global_api_router
    if _global_api_router is None:
        _global_api_router = AgnoAPIRouter()
    return _global_api_router

# 便利函数
async def create_user_agent(user_id: str, agent_config: Dict[str, Any]) -> Dict[str, Any]:
    """为用户创建Agent"""
    router = get_api_router()
    return await router.handle_agent_request(
        "create_agent",
        user_id=user_id,
        config=agent_config
    )

async def create_user_chat(user_id: str, chat_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """为用户创建聊天会话"""
    router = get_api_router()
    return await router.handle_agent_request(
        "create_chat",
        user_id=user_id,
        config=chat_config
    )

async def get_user_available_models(user_id: Optional[str] = None) -> Dict[str, Any]:
    """获取用户可用模型"""
    router = get_api_router()
    return await router.handle_agent_request("get_models", user_id=user_id)

async def get_user_available_tools(user_id: Optional[str] = None) -> Dict[str, Any]:
    """获取用户可用工具"""
    router = get_api_router()
    return await router.handle_agent_request("get_tools", user_id=user_id)

# 导出主要组件
__all__ = [
    "DynamicAgnoAPIAdapter",
    "AgnoAPIRouter",
    "get_api_router",
    "create_user_agent",
    "create_user_chat",
    "get_user_available_models",
    "get_user_available_tools"
] 