"""
Agno动态Agent工厂
根据前端用户配置和系统工具动态创建Agent，实现真正的插件化架构
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from app.frameworks.agno.model_config_adapter import (
    ZZDSJAgnoModelAdapter, 
    ModelType, 
    get_model_adapter
)
from app.services.tools.tool_service import ToolService
from app.services.assistants.assistant_service import AssistantService
from app.repositories.tool_repository import ToolRepository
from app.utils.core.database import get_db

# 导入执行图引擎
from app.frameworks.agno.execution_engine import AgnoExecutionEngine, create_execution_engine
from app.frameworks.agno.templates import ExecutionGraph, ExecutionNode, ExecutionEdge
from app.frameworks.agno.orchestration.types import ExecutionContext, ExecutionStatus

# 动态导入Agno组件
try:
    from agno.agent import Agent as AgnoAgent
    from agno.team import Team as AgnoTeam
    from agno.memory import Memory as AgnoMemory
    from agno.storage import Storage as AgnoStorage
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False
    AgnoAgent = object
    AgnoTeam = object

logger = logging.getLogger(__name__)

class DynamicAgnoAgentFactory:
    """动态Agno Agent工厂
    
    根据前端用户配置、系统模型配置和工具注册表动态创建Agent
    """
    
    def __init__(self, db_session=None):
        """初始化工厂"""
        self.db = db_session or next(get_db())
        self.model_adapter = get_model_adapter()
        self.tool_service = ToolService(self.db)
        self.assistant_service = AssistantService(self.db)
        self.tool_repository = ToolRepository(self.db)
        # 新增执行图引擎支持
        self.execution_engines = {}
        
    async def create_agent_from_config(
        self, 
        agent_config: Dict[str, Any],
        user_id: str,
        session_id: Optional[str] = None
    ) -> Optional[AgnoAgent]:
        """根据配置创建Agent
        
        Args:
            agent_config: Agent配置，包含name, role, tools, model等
            user_id: 用户ID
            session_id: 会话ID（可选）
            
        Returns:
            创建的AgnoAgent实例
        """
        if not AGNO_AVAILABLE:
            logger.error("Agno框架不可用")
            return None
            
        try:
            # 1. 获取动态模型配置
            model_instance = await self._get_dynamic_model(
                agent_config.get('model_config', {})
            )
            
            if not model_instance:
                logger.error("无法获取模型实例")
                return None
            
            # 2. 获取动态工具配置
            tools = await self._get_dynamic_tools(
                agent_config.get('tools', []),
                user_id
            )
            
            # 3. 获取知识库配置（如果有）
            knowledge = await self._get_dynamic_knowledge(
                agent_config.get('knowledge_bases', []),
                user_id
            )
            
            # 4. 设置内存和存储
            memory = self._create_memory(session_id)
            storage = self._create_storage(user_id, agent_config.get('name', 'agent'))
            
            # 5. 构建指令
            instructions = self._build_instructions(agent_config)
            
            # 6. 设置执行图（如果配置了）
            execution_graph_config = agent_config.get('execution_graph')
            execution_engine = None
            
            if execution_graph_config:
                try:
                    execution_engine = self._create_execution_engine(execution_graph_config)
                    logger.info("成功创建执行图引擎")
                except Exception as e:
                    logger.warning(f"创建执行图引擎失败: {str(e)}")
            
            # 7. 创建Agno Agent
            agent = AgnoAgent(
                name=agent_config.get('name', 'AI Assistant'),
                role=agent_config.get('role', 'AI Assistant'),
                model=model_instance,
                tools=tools,
                knowledge=knowledge,
                memory=memory,
                storage=storage,
                instructions=instructions,
                description=agent_config.get('description', ''),
                show_tool_calls=agent_config.get('show_tool_calls', True),
                markdown=agent_config.get('markdown', True),
                max_loops=agent_config.get('max_loops', 10),
                add_history_to_messages=agent_config.get('add_history', True)
            )
            
            # 8. 如果有执行图，包装Agent的查询方法
            if execution_engine:
                agent = self._wrap_agent_with_execution_graph(
                    agent, execution_engine, user_id, session_id
                )
            
            logger.info(f"成功创建动态Agent: {agent_config.get('name')}")
            return agent
            
        except Exception as e:
            logger.error(f"创建动态Agent失败: {str(e)}", exc_info=True)
            return None
    
    async def _get_dynamic_model(self, model_config: Dict[str, Any]):
        """获取动态模型配置"""
        try:
            model_id = model_config.get('model_id')
            model_type = ModelType(model_config.get('type', 'chat'))
            
            # 如果指定了模型ID，使用指定模型
            if model_id:
                return await self.model_adapter.create_agno_model_by_type(
                    model_type, model_id
                )
            
            # 否则使用默认模型
            return await self.model_adapter.create_agno_model_by_type(model_type)
            
        except Exception as e:
            logger.error(f"获取动态模型失败: {str(e)}")
            return None
    
    async def _get_dynamic_tools(self, tool_configs: List[Dict], user_id: str) -> List[Any]:
        """获取动态工具配置"""
        tools = []
        
        try:
            for tool_config in tool_configs:
                tool_id = tool_config.get('tool_id')
                if not tool_id:
                    continue
                
                # 从工具注册表获取工具实例
                tool_instance = await self._create_tool_instance(
                    tool_id, tool_config, user_id, self.tool_service, self.tool_repository
                )
                if tool_instance:
                    tools.append(tool_instance)
            
            logger.info(f"成功加载 {len(tools)} 个动态工具")
            return tools
            
        except Exception as e:
            logger.error(f"获取动态工具失败: {str(e)}")
            return []
    
    async def _create_tool_instance(self, tool_id: str, tool_config: Dict, user_id: str, tool_service, tool_repository):
        """创建工具实例"""
        try:
            # 从统一工具注册表获取工具
            tool_definition = await tool_repository.get_tool_by_id(tool_id)
            if not tool_definition:
                logger.warning(f"工具 {tool_id} 不存在")
                return None
            
            # 检查用户权限
            has_permission = await tool_service.check_tool_permission(
                user_id, tool_id
            )
            if not has_permission:
                logger.warning(f"用户 {user_id} 没有工具 {tool_id} 的使用权限")
                return None
            
            # 根据工具框架创建实例
            framework = tool_definition.framework
            
            if framework == 'agno':
                return await self._create_agno_tool(tool_definition, tool_config)
            elif framework in ['llamaindex', 'owl', 'fastmcp', 'haystack']:
                return await self._create_framework_tool_wrapper(tool_definition, tool_config, framework)
            else:
                logger.warning(f"不支持的工具框架: {framework}")
                return None
                
        except Exception as e:
            logger.error(f"创建工具实例 {tool_id} 失败: {str(e)}")
            return None
    
    async def _create_agno_tool(self, tool_definition, tool_config):
        """创建Agno原生工具"""
        try:
            # 根据工具类型动态导入和创建
            tool_class_path = tool_definition.class_path
            module_path, class_name = tool_class_path.rsplit('.', 1)
            
            # 动态导入
            import importlib
            module = importlib.import_module(module_path)
            tool_class = getattr(module, class_name)
            
            # 合并配置参数
            init_params = tool_definition.config.copy()
            init_params.update(tool_config.get('params', {}))
            
            # 创建工具实例
            return tool_class(**init_params)
            
        except Exception as e:
            logger.error(f"创建Agno工具失败: {str(e)}")
            return None
    
    async def _create_framework_tool_wrapper(self, tool_definition, tool_config, framework):
        """创建其他框架工具包装器"""
        try:
            # 从统一工具适配器创建工具
            from app.adapters.tool_adapter import UniversalToolAdapter
            
            adapter = UniversalToolAdapter()
            tool_instance = await adapter.create_tool_instance(
                tool_definition.id, tool_config.get('params', {}), framework
            )
            
            # 包装为Agno兼容的工具
            return self._wrap_external_tool(tool_instance, tool_definition)
            
        except Exception as e:
            logger.error(f"创建{framework}工具包装器失败: {str(e)}")
            return None
    
    def _wrap_external_tool(self, tool_instance, tool_definition):
        """将外部工具包装为Agno兼容格式"""
        # 这里实现工具包装逻辑，使其兼容Agno的工具接口
        # 根据Agno的工具规范包装
        
        class AgnoToolWrapper:
            def __init__(self, tool_instance, tool_def):
                self.tool_instance = tool_instance
                self.tool_def = tool_def
                self.name = tool_def.name
                self.description = tool_def.description
            
            async def __call__(self, *args, **kwargs):
                # 调用底层工具实例
                return await self.tool_instance.execute(*args, **kwargs)
        
        return AgnoToolWrapper(tool_instance, tool_definition)
    
    async def _get_dynamic_knowledge(self, knowledge_configs: List[Dict], user_id: str):
        """获取动态知识库配置"""
        try:
            if not knowledge_configs:
                return None
            
            # 集成知识库服务
            from app.services.knowledge.knowledge_service import KnowledgeService
            
            knowledge_service = KnowledgeService(self.db)
            knowledge_sources = []
            
            for kb_config in knowledge_configs:
                kb_id = kb_config.get('knowledge_base_id')
                if kb_id:
                    # 检查权限
                    has_permission = await knowledge_service.check_knowledge_base_permission(
                        user_id, kb_id
                    )
                    if has_permission:
                        knowledge_sources.append(kb_id)
            
            # 返回知识库配置
            return knowledge_sources if knowledge_sources else None
            
        except Exception as e:
            logger.error(f"获取动态知识库失败: {str(e)}")
            return None
    
    def _create_memory(self, session_id: Optional[str]) -> Optional[AgnoMemory]:
        """创建内存实例"""
        try:
            if session_id and AGNO_AVAILABLE:
                # 创建持久化内存
                return AgnoMemory(
                    db_url=f"sqlite:///sessions/{session_id}.db",
                    table_name="agent_memory"
                )
            return None
            
        except Exception as e:
            logger.error(f"创建内存实例失败: {str(e)}")
            return None
    
    def _create_storage(self, user_id: str, agent_name: str) -> Optional[AgnoStorage]:
        """创建存储实例"""
        try:
            if AGNO_AVAILABLE:
                # 创建用户级别的存储
                return AgnoStorage(
                    db_url=f"sqlite:///storage/{user_id}_{agent_name}.db",
                    table_name="agent_storage"
                )
            return None
            
        except Exception as e:
            logger.error(f"创建存储实例失败: {str(e)}")
            return None
    
    def _build_instructions(self, agent_config: Dict[str, Any]) -> List[str]:
        """构建Agent指令"""
        instructions = []
        
        # 基础指令
        name = agent_config.get('name', 'AI Assistant')
        role = agent_config.get('role', 'AI Assistant')
        instructions.append(f"You are {name}, a {role}.")
        
        # 用户自定义指令
        custom_instructions = agent_config.get('instructions', [])
        if isinstance(custom_instructions, str):
            instructions.append(custom_instructions)
        elif isinstance(custom_instructions, list):
            instructions.extend(custom_instructions)
        
        # 工具使用指令
        if agent_config.get('tools'):
            instructions.append("Use the available tools when necessary to provide accurate and helpful responses.")
        
        # 知识库使用指令
        if agent_config.get('knowledge_bases'):
            instructions.append("Utilize the knowledge base information when relevant to answer questions accurately.")
        
        return instructions
    
    def _create_execution_engine(self, execution_graph_config: Dict[str, Any]) -> AgnoExecutionEngine:
        """创建执行图引擎"""
        try:
            # 解析执行图配置
            nodes = []
            for node_config in execution_graph_config.get("nodes", []):
                node = ExecutionNode(
                    id=node_config["id"],
                    type=node_config["type"],
                    config=node_config.get("config", {})
                )
                nodes.append(node)
            
            edges = []
            for edge_config in execution_graph_config.get("edges", []):
                edge = ExecutionEdge(
                    from_node=edge_config["from"],
                    to_node=edge_config["to"],
                    condition=edge_config.get("condition"),
                    weight=edge_config.get("weight", 1.0),
                    timeout=edge_config.get("timeout", 30)
                )
                edges.append(edge)
            
            execution_graph = ExecutionGraph(nodes=nodes, edges=edges)
            return create_execution_engine(execution_graph)
            
        except Exception as e:
            logger.error(f"创建执行图引擎失败: {str(e)}")
            raise
    
    def _wrap_agent_with_execution_graph(
        self, 
        agent: AgnoAgent, 
        execution_engine: AgnoExecutionEngine,
        user_id: str,
        session_id: Optional[str]
    ) -> AgnoAgent:
        """使用执行图包装Agent"""
        
        # 保存原始查询方法
        original_query = getattr(agent, 'query', None)
        original_aquery = getattr(agent, 'aquery', None)
        
        async def execution_graph_query(query_str: str, **kwargs) -> str:
            """基于执行图的查询方法"""
            try:
                # 创建执行上下文
                import uuid
                context = ExecutionContext(
                    request_id=str(uuid.uuid4()),
                    user_id=user_id,
                    session_id=session_id
                )
                
                # 使用执行图执行查询
                result = await execution_engine.execute(query_str, context)
                
                if result.success:
                    return str(result.result)
                else:
                    logger.error(f"执行图查询失败: {result.error}")
                    # 回退到原始查询方法
                    if original_query:
                        return await original_query(query_str, **kwargs)
                    return f"查询失败: {result.error}"
                    
            except Exception as e:
                logger.error(f"执行图查询异常: {str(e)}")
                # 回退到原始查询方法
                if original_query:
                    return await original_query(query_str, **kwargs)
                return f"查询异常: {str(e)}"
        
        async def execution_graph_aquery(query_str: str, **kwargs) -> str:
            """异步执行图查询"""
            return await execution_graph_query(query_str, **kwargs)
        
        # 替换查询方法
        if hasattr(agent, 'query'):
            agent.query = execution_graph_query
        if hasattr(agent, 'aquery'):
            agent.aquery = execution_graph_aquery
        
        # 添加执行图相关属性
        agent._execution_engine = execution_engine
        agent._original_query = original_query
        agent._original_aquery = original_aquery
        
        return agent

# 全局工厂实例
_global_factory: Optional[DynamicAgnoAgentFactory] = None

def get_agent_factory() -> DynamicAgnoAgentFactory:
    """获取全局Agent工厂实例"""
    global _global_factory
    if _global_factory is None:
        _global_factory = DynamicAgnoAgentFactory()
    return _global_factory

# 便利函数
async def create_dynamic_agent(
    agent_config: Dict[str, Any],
    user_id: str,
    session_id: Optional[str] = None
) -> Optional[AgnoAgent]:
    """创建动态Agent"""
    factory = get_agent_factory()
    return await factory.create_agent_from_config(agent_config, user_id, session_id)

async def create_dynamic_team(
    team_config: Dict[str, Any],
    user_id: str
) -> Optional[AgnoTeam]:
    """创建动态团队"""
    factory = get_agent_factory()
    return await factory.create_team_from_config(team_config, user_id) 