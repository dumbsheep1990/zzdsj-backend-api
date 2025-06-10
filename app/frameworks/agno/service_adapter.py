"""
Agno服务适配器：将ZZDSJ现有业务服务集成到Agno代理框架中
提供ZZDSJ业务逻辑与Agno代理能力之间的桥梁

支持的服务集成：
- 聊天服务
- 知识库服务  
- 助手管理服务
- 工具编排服务
- 模型管理服务
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass
from datetime import datetime

# Agno核心导入
try:
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    from agno.team import Team
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False
    
    class Agent:
        pass
    
    class Team:
        pass

# ZZDSJ服务导入
from app.frameworks.agno.tools import (
    ZZDSJKnowledgeTools, 
    ZZDSJFileManagementTools, 
    ZZDSJSystemTools
)

logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """服务配置"""
    name: str
    description: str
    enabled: bool = True
    timeout_seconds: int = 30
    retry_count: int = 3
    config: Dict[str, Any] = None


class ZZDSJServiceAdapter:
    """ZZDSJ服务适配器 - 将业务服务集成到Agno框架"""
    
    def __init__(self):
        """初始化服务适配器"""
        self.services: Dict[str, Any] = {}
        self.agents: Dict[str, Agent] = {}
        self.service_configs: Dict[str, ServiceConfig] = {}
        
        # 初始化核心服务
        self._initialize_core_services()
    
    def _initialize_core_services(self):
        """初始化核心业务服务"""
        
        # 注册聊天服务
        self._register_chat_service()
        
        # 注册知识库服务
        self._register_knowledge_service()
        
        # 注册助手管理服务
        self._register_assistant_service()
        
        # 注册工具编排服务
        self._register_tool_orchestration_service()
        
        # 注册模型管理服务
        self._register_model_management_service()

    def _register_chat_service(self):
        """注册聊天服务"""
        try:
            from app.services.chat.chat_service import ChatService
            
            chat_service = ChatService()
            self.services['chat'] = chat_service
            
            self.service_configs['chat'] = ServiceConfig(
                name="chat",
                description="ZZDSJ聊天服务",
                timeout_seconds=60
            )
            
            logger.info("已注册聊天服务")
            
        except ImportError as e:
            logger.warning(f"聊天服务导入失败: {e}")
        except Exception as e:
            logger.error(f"聊天服务注册失败: {e}")

    def _register_knowledge_service(self):
        """注册知识库服务"""
        try:
            from app.services.knowledge.knowledge_service import KnowledgeService
            
            kb_service = KnowledgeService()
            self.services['knowledge'] = kb_service
            
            self.service_configs['knowledge'] = ServiceConfig(
                name="knowledge",
                description="ZZDSJ知识库服务",
                timeout_seconds=45
            )
            
            logger.info("已注册知识库服务")
            
        except ImportError as e:
            logger.warning(f"知识库服务导入失败: {e}")
        except Exception as e:
            logger.error(f"知识库服务注册失败: {e}")

    def _register_assistant_service(self):
        """注册助手管理服务"""
        try:
            from app.services.assistants.assistant_service import AssistantService
            
            assistant_service = AssistantService()
            self.services['assistant'] = assistant_service
            
            self.service_configs['assistant'] = ServiceConfig(
                name="assistant",
                description="ZZDSJ助手管理服务",
                timeout_seconds=30
            )
            
            logger.info("已注册助手管理服务")
            
        except ImportError as e:
            logger.warning(f"助手管理服务导入失败: {e}")
        except Exception as e:
            logger.error(f"助手管理服务注册失败: {e}")

    def _register_tool_orchestration_service(self):
        """注册工具编排服务"""
        try:
            from core.tool_orchestrator.tool_orchestrator import ToolOrchestrator
            
            tool_orchestrator = ToolOrchestrator()
            self.services['tool_orchestrator'] = tool_orchestrator
            
            self.service_configs['tool_orchestrator'] = ServiceConfig(
                name="tool_orchestrator",
                description="ZZDSJ工具编排服务",
                timeout_seconds=40
            )
            
            logger.info("已注册工具编排服务")
            
        except ImportError as e:
            logger.warning(f"工具编排服务导入失败: {e}")
        except Exception as e:
            logger.error(f"工具编排服务注册失败: {e}")

    def _register_model_management_service(self):
        """注册模型管理服务"""
        try:
            from core.model_manager.model_manager import ModelManager
            
            model_manager = ModelManager()
            self.services['model_manager'] = model_manager
            
            self.service_configs['model_manager'] = ServiceConfig(
                name="model_manager",
                description="ZZDSJ模型管理服务",
                timeout_seconds=35
            )
            
            logger.info("已注册模型管理服务")
            
        except ImportError as e:
            logger.warning(f"模型管理服务导入失败: {e}")
        except Exception as e:
            logger.error(f"模型管理服务注册失败: {e}")

    async def create_chat_agent(self, 
                               session_id: str,
                               user_id: str,
                               model_config: Optional[Dict] = None) -> Optional[Agent]:
        """
        创建聊天代理
        
        参数:
            session_id: 会话ID
            user_id: 用户ID
            model_config: 模型配置
            
        返回:
            聊天代理实例
        """
        if not AGNO_AVAILABLE:
            logger.error("Agno框架未安装")
            return None
        
        try:
            # 获取聊天服务
            chat_service = self.services.get('chat')
            if not chat_service:
                logger.error("聊天服务未注册")
                return None
            
            # 创建工具
            knowledge_tools = ZZDSJKnowledgeTools()
            file_tools = ZZDSJFileManagementTools()
            
            # 设置默认模型配置
            default_model_config = {
                "id": "gpt-4o",
                "temperature": 0.7,
                "max_tokens": 2048
            }
            model_config = {**default_model_config, **(model_config or {})}
            
            # 创建聊天代理
            agent = Agent(
                model=OpenAIChat(**model_config),
                name=f"ZZDSJ-Chat-Agent-{session_id}",
                description=f"ZZDSJ聊天代理，用户: {user_id}",
                instructions=[
                    "你是ZZDSJ平台的智能助手",
                    "帮助用户解答问题并完成任务",
                    "如果需要查找信息，请使用知识库工具",
                    "保持友好和专业的回复风格"
                ],
                tools=[knowledge_tools, file_tools],
                show_tool_calls=True,
                markdown=True
            )
            
            # 缓存代理
            agent_key = f"chat_{session_id}_{user_id}"
            self.agents[agent_key] = agent
            
            logger.info(f"已创建聊天代理: {agent_key}")
            return agent
            
        except Exception as e:
            logger.error(f"创建聊天代理失败: {e}")
            return None

    async def create_knowledge_agent(self,
                                   kb_id: str,
                                   model_config: Optional[Dict] = None) -> Optional[Agent]:
        """
        创建知识库专用代理
        
        参数:
            kb_id: 知识库ID
            model_config: 模型配置
            
        返回:
            知识库代理实例
        """
        if not AGNO_AVAILABLE:
            logger.error("Agno框架未安装")
            return None
        
        try:
            # 获取知识库服务
            kb_service = self.services.get('knowledge')
            if not kb_service:
                logger.error("知识库服务未注册")
                return None
            
            # 创建专用知识库工具
            knowledge_tools = ZZDSJKnowledgeTools(kb_id=kb_id)
            
            # 设置默认模型配置
            default_model_config = {
                "id": "gpt-4o",
                "temperature": 0.3,  # 知识库查询使用较低温度
                "max_tokens": 4096
            }
            model_config = {**default_model_config, **(model_config or {})}
            
            # 创建知识库代理
            agent = Agent(
                model=OpenAIChat(**model_config),
                name=f"ZZDSJ-Knowledge-Agent-{kb_id}",
                description=f"ZZDSJ知识库专用代理，知识库: {kb_id}",
                instructions=[
                    "你是专门的知识库查询助手",
                    "主要任务是从知识库中搜索和提取相关信息",
                    "提供准确、详细的答案，并引用来源",
                    "如果知识库中没有相关信息，请明确说明"
                ],
                tools=[knowledge_tools],
                show_tool_calls=True,
                markdown=True
            )
            
            # 缓存代理
            agent_key = f"knowledge_{kb_id}"
            self.agents[agent_key] = agent
            
            logger.info(f"已创建知识库代理: {agent_key}")
            return agent
            
        except Exception as e:
            logger.error(f"创建知识库代理失败: {e}")
            return None

    async def create_assistant_agent(self,
                                   assistant_id: str,
                                   assistant_config: Dict,
                                   model_config: Optional[Dict] = None) -> Optional[Agent]:
        """
        创建基于助手配置的代理
        
        参数:
            assistant_id: 助手ID
            assistant_config: 助手配置
            model_config: 模型配置
            
        返回:
            助手代理实例
        """
        if not AGNO_AVAILABLE:
            logger.error("Agno框架未安装")
            return None
        
        try:
            # 获取助手服务
            assistant_service = self.services.get('assistant')
            if not assistant_service:
                logger.error("助手服务未注册")
                return None
            
            # 根据助手配置创建工具
            tools = []
            
            # 如果助手需要知识库访问
            if assistant_config.get('enable_knowledge_base'):
                kb_id = assistant_config.get('knowledge_base_id')
                knowledge_tools = ZZDSJKnowledgeTools(kb_id=kb_id)
                tools.append(knowledge_tools)
            
            # 如果助手需要文件管理
            if assistant_config.get('enable_file_management'):
                file_tools = ZZDSJFileManagementTools()
                tools.append(file_tools)
            
            # 如果助手需要系统监控
            if assistant_config.get('enable_system_monitoring'):
                system_tools = ZZDSJSystemTools()
                tools.append(system_tools)
            
            # 设置模型配置
            default_model_config = {
                "id": assistant_config.get('model_name', 'gpt-4o'),
                "temperature": assistant_config.get('temperature', 0.7),
                "max_tokens": assistant_config.get('max_tokens', 2048)
            }
            model_config = {**default_model_config, **(model_config or {})}
            
            # 创建助手代理
            agent = Agent(
                model=OpenAIChat(**model_config),
                name=assistant_config.get('name', f"ZZDSJ-Assistant-{assistant_id}"),
                description=assistant_config.get('description', f"ZZDSJ助手代理: {assistant_id}"),
                instructions=assistant_config.get('instructions', [
                    "你是ZZDSJ平台的专业助手",
                    "根据用户需求提供帮助和支持"
                ]),
                tools=tools,
                show_tool_calls=assistant_config.get('show_tool_calls', True),
                markdown=assistant_config.get('enable_markdown', True)
            )
            
            # 缓存代理
            agent_key = f"assistant_{assistant_id}"
            self.agents[agent_key] = agent
            
            logger.info(f"已创建助手代理: {agent_key}")
            return agent
            
        except Exception as e:
            logger.error(f"创建助手代理失败: {e}")
            return None

    async def create_agent_team(self,
                              agent_configs: List[Dict],
                              team_config: Optional[Dict] = None) -> Optional[Team]:
        """
        创建代理团队
        
        参数:
            agent_configs: 代理配置列表
            team_config: 团队配置
            
        返回:
            代理团队实例
        """
        if not AGNO_AVAILABLE:
            logger.error("Agno框架未安装")
            return None
        
        try:
            # 创建团队成员代理
            team_members = []
            
            for config in agent_configs:
                agent_type = config.get('type', 'general')
                
                if agent_type == 'chat':
                    agent = await self.create_chat_agent(
                        session_id=config.get('session_id', 'team'),
                        user_id=config.get('user_id', 'system'),
                        model_config=config.get('model_config')
                    )
                elif agent_type == 'knowledge':
                    agent = await self.create_knowledge_agent(
                        kb_id=config.get('kb_id'),
                        model_config=config.get('model_config')
                    )
                elif agent_type == 'assistant':
                    agent = await self.create_assistant_agent(
                        assistant_id=config.get('assistant_id'),
                        assistant_config=config.get('assistant_config', {}),
                        model_config=config.get('model_config')
                    )
                else:
                    logger.warning(f"未知代理类型: {agent_type}")
                    continue
                
                if agent:
                    team_members.append(agent)
            
            if not team_members:
                logger.error("没有可用的团队成员代理")
                return None
            
            # 设置默认团队配置
            default_team_config = {
                "mode": "coordinate",
                "model": OpenAIChat(id="gpt-4o"),
                "success_criteria": "成功完成用户请求并提供满意的结果",
                "instructions": [
                    "团队协作完成用户任务",
                    "发挥各自专业优势",
                    "提供综合性解决方案"
                ],
                "show_tool_calls": True,
                "markdown": True
            }
            team_config = {**default_team_config, **(team_config or {})}
            
            # 创建代理团队
            team = Team(
                members=team_members,
                **team_config
            )
            
            logger.info(f"已创建代理团队，成员数量: {len(team_members)}")
            return team
            
        except Exception as e:
            logger.error(f"创建代理团队失败: {e}")
            return None

    def get_agent(self, agent_key: str) -> Optional[Agent]:
        """
        获取缓存的代理实例
        
        参数:
            agent_key: 代理键名
            
        返回:
            代理实例或None
        """
        return self.agents.get(agent_key)

    def list_agents(self) -> List[str]:
        """
        列出所有缓存的代理
        
        返回:
            代理键名列表
        """
        return list(self.agents.keys())

    def remove_agent(self, agent_key: str) -> bool:
        """
        移除缓存的代理
        
        参数:
            agent_key: 代理键名
            
        返回:
            是否成功移除
        """
        if agent_key in self.agents:
            del self.agents[agent_key]
            logger.info(f"已移除代理: {agent_key}")
            return True
        return False

    def get_service_status(self) -> Dict[str, Any]:
        """
        获取所有服务状态
        
        返回:
            服务状态信息
        """
        status = {
            "timestamp": datetime.now().isoformat(),
            "agno_available": AGNO_AVAILABLE,
            "total_services": len(self.services),
            "active_agents": len(self.agents),
            "services": {}
        }
        
        for service_name, config in self.service_configs.items():
            service_instance = self.services.get(service_name)
            status["services"][service_name] = {
                "name": config.name,
                "description": config.description,
                "enabled": config.enabled,
                "available": service_instance is not None,
                "timeout_seconds": config.timeout_seconds
            }
        
        return status

    async def health_check(self) -> Dict[str, Any]:
        """
        执行健康检查
        
        返回:
            健康检查结果
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        # 检查Agno可用性
        health_status["checks"]["agno_framework"] = {
            "status": "healthy" if AGNO_AVAILABLE else "unhealthy",
            "available": AGNO_AVAILABLE
        }
        
        # 检查各个服务
        for service_name, service_instance in self.services.items():
            try:
                # 这里可以添加具体的服务健康检查逻辑
                if hasattr(service_instance, 'health_check'):
                    result = await service_instance.health_check()
                    health_status["checks"][service_name] = result
                else:
                    health_status["checks"][service_name] = {
                        "status": "healthy",
                        "message": "Service available"
                    }
            except Exception as e:
                health_status["checks"][service_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health_status["status"] = "degraded"
        
        return health_status


# 全局服务适配器实例
_service_adapter = None

def get_service_adapter() -> ZZDSJServiceAdapter:
    """
    获取全局服务适配器实例
    
    返回:
        服务适配器实例
    """
    global _service_adapter
    if _service_adapter is None:
        _service_adapter = ZZDSJServiceAdapter()
    return _service_adapter


# 便捷函数
async def create_zzdsj_chat_agent(session_id: str, 
                                 user_id: str,
                                 model_config: Optional[Dict] = None) -> Optional[Agent]:
    """
    便捷函数：创建ZZDSJ聊天代理
    """
    adapter = get_service_adapter()
    return await adapter.create_chat_agent(session_id, user_id, model_config)


async def create_zzdsj_knowledge_agent(kb_id: str,
                                     model_config: Optional[Dict] = None) -> Optional[Agent]:
    """
    便捷函数：创建ZZDSJ知识库代理
    """
    adapter = get_service_adapter()
    return await adapter.create_knowledge_agent(kb_id, model_config)


async def get_service_health() -> Dict[str, Any]:
    """
    便捷函数：获取服务健康状态
    """
    adapter = get_service_adapter()
    return adapter.get_service_status()


# 示例使用
async def example_usage():
    """服务适配器使用示例"""
    if not AGNO_AVAILABLE:
        print("请安装Agno框架: pip install agno")
        return
    
    adapter = get_service_adapter()
    
    # 创建聊天代理
    chat_agent = await adapter.create_chat_agent(
        session_id="demo_session",
        user_id="demo_user"
    )
    
    if chat_agent:
        print("聊天代理创建成功")
        
        # 测试对话
        response = await chat_agent.aprint_response(
            "你好，请介绍一下ZZDSJ平台的功能",
            stream=True
        )
        print(f"代理回复: {response}")
    
    # 获取服务状态
    status = adapter.get_service_status()
    print(f"服务状态: {status}")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage()) 