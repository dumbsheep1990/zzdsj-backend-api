"""
智能体框架集成接口
提供统一的框架抽象层，支持多种AI框架的集成
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum

# 导入框架管理器和工厂
from app.frameworks.manager import get_framework_manager, FrameworkType, FrameworkCapability
from app.frameworks.factory import get_agent_framework

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """智能体类型枚举"""
    KNOWLEDGE_AGENT = "knowledge_agent"
    CHAT_AGENT = "chat_agent"
    TASK_AGENT = "task_agent"
    MCP_AGENT = "mcp_agent"
    RETRIEVAL_AGENT = "retrieval_agent"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IAgentFramework(ABC):
    """智能体框架通用接口，为不同框架提供统一调用方式"""
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """初始化框架"""
        pass
        
    @abstractmethod
    async def create_agent(self, agent_type: str, config: Dict[str, Any]) -> Any:
        """创建智能体"""
        pass
        
    @abstractmethod
    async def run_task(self, task: str, tools: List[Any], **kwargs) -> Tuple[str, Any, Dict[str, Any]]:
        """运行任务
        
        Args:
            task: 任务描述
            tools: 可用工具列表
            
        Returns:
            Tuple[str, Any, Dict[str, Any]]: (回答, 交互历史, 其他元数据)
        """
        pass


class IToolkitManager(ABC):
    """工具包管理器接口"""
    
    @abstractmethod
    async def load_toolkit(self, toolkit_name: str, config: Optional[Dict[str, Any]] = None) -> Any:
        """加载指定的工具包"""
        pass
        
    @abstractmethod
    async def get_tools(self, toolkit_name: Optional[str] = None) -> List[Any]:
        """获取指定工具包中的工具，如不指定则返回所有工具"""
        pass
        
    @abstractmethod
    async def register_custom_tool(self, tool: Any) -> None:
        """注册自定义工具"""
        pass


class IKnowledgeRetriever(ABC):
    """知识检索接口"""
    
    @abstractmethod
    async def query(self, query_text: str, **kwargs) -> List[Dict[str, Any]]:
        """从知识库中检索相关内容"""
        pass
        
    @abstractmethod
    async def create_retrieval_tool(self) -> Any:
        """创建检索工具，供智能体使用"""
        pass


class UnifiedAgentFramework(IAgentFramework):
    """
    统一智能体框架实现
    整合多种AI框架，提供统一的接口访问
    """
    
    def __init__(self, framework_type: Optional[FrameworkType] = None):
        """
        初始化统一框架
        
        参数:
            framework_type: 优先使用的框架类型，如不指定则使用默认框架
        """
        self.framework_manager = get_framework_manager()
        self.preferred_framework = framework_type
        self.agents = {}  # 存储创建的智能体实例
        self.is_initialized = False
        
        # 性能监控
        self._stats = {
            "agents_created": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_response_time": 0.0
        }
        
        logger.info(f"统一智能体框架初始化，优先框架: {framework_type}")
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """
        初始化框架
        
        参数:
            config: 初始化配置
                - framework_type: 优先框架类型
                - model: 默认模型
                - max_agents: 最大智能体数量
                - enable_tools: 是否启用工具
                - knowledge_bases: 默认知识库列表
        """
        try:
            logger.info("开始初始化统一智能体框架")
            
            # 解析配置
            self.preferred_framework = config.get("framework_type", self.preferred_framework)
            self.default_model = config.get("model", "gpt-3.5-turbo")
            self.max_agents = config.get("max_agents", 10)
            self.enable_tools = config.get("enable_tools", True)
            self.default_knowledge_bases = config.get("knowledge_bases", [])
            
            # 验证框架可用性
            available_frameworks = self.framework_manager.list_frameworks()
            if self.preferred_framework and self.preferred_framework not in available_frameworks:
                logger.warning(f"优先框架 {self.preferred_framework} 不可用，使用默认框架")
                self.preferred_framework = None
            
            # 预热工具包管理器
            if self.enable_tools:
                try:
                    self.toolkit_manager = UnifiedToolkitManager()
                    await self.toolkit_manager.initialize(config.get("tools", {}))
                    logger.info("工具包管理器初始化完成")
                except Exception as e:
                    logger.warning(f"工具包管理器初始化失败: {str(e)}")
                    self.enable_tools = False
            
            # 预热知识检索器
            if self.default_knowledge_bases:
                try:
                    self.knowledge_retriever = UnifiedKnowledgeRetriever()
                    await self.knowledge_retriever.initialize(self.default_knowledge_bases)
                    logger.info("知识检索器初始化完成")
                except Exception as e:
                    logger.warning(f"知识检索器初始化失败: {str(e)}")
                    self.knowledge_retriever = None
            
            self.is_initialized = True
            logger.info("统一智能体框架初始化完成")
            
        except Exception as e:
            logger.error(f"框架初始化失败: {str(e)}")
            raise
    
    async def create_agent(self, agent_type: str, config: Dict[str, Any]) -> Any:
        """
        创建智能体
        
        参数:
            agent_type: 智能体类型
            config: 智能体配置
                - name: 智能体名称
                - description: 智能体描述
                - model: 使用的模型
                - knowledge_bases: 关联的知识库
                - tools: 可用工具列表
                - framework: 指定使用的框架
                - settings: 其他设置
                
        返回:
            创建的智能体实例
        """
        try:
            if not self.is_initialized:
                raise RuntimeError("框架未初始化，请先调用 initialize()")
            
            # 检查智能体数量限制
            if len(self.agents) >= self.max_agents:
                raise RuntimeError(f"智能体数量已达上限: {self.max_agents}")
            
            # 解析配置
            name = config.get("name", f"agent_{len(self.agents) + 1}")
            description = config.get("description")
            model = config.get("model", self.default_model)
            knowledge_bases = config.get("knowledge_bases", self.default_knowledge_bases)
            framework_type = config.get("framework", self.preferred_framework)
            settings = config.get("settings", {})
            
            # 选择使用的框架
            if framework_type:
                if isinstance(framework_type, str):
                    framework_type = FrameworkType(framework_type.lower())
            else:
                # 根据智能体类型选择最适合的框架
                framework_type = self._select_framework_for_agent_type(agent_type)
            
            # 获取框架工厂
            framework_factory = get_agent_framework(framework_type.value)
            
            # 创建智能体
            agent = await framework_factory.create_agent(
                name=name,
                description=description,
                knowledge_bases=knowledge_bases,
                model=model,
                settings=settings
            )
            
            # 添加工具（如果启用）
            if self.enable_tools and hasattr(self, 'toolkit_manager'):
                tools = config.get("tools", [])
                if tools:
                    for tool_name in tools:
                        try:
                            await self.toolkit_manager.load_toolkit(tool_name)
                        except Exception as e:
                            logger.warning(f"加载工具包 {tool_name} 失败: {str(e)}")
            
            # 存储智能体实例
            agent_id = f"{name}_{len(self.agents)}"
            self.agents[agent_id] = {
                "agent": agent,
                "type": agent_type,
                "config": config,
                "framework": framework_type,
                "created_at": asyncio.get_event_loop().time()
            }
            
            # 更新统计
            self._stats["agents_created"] += 1
            
            logger.info(f"智能体创建成功: {name} (类型: {agent_type}, 框架: {framework_type.value})")
            return agent
            
        except Exception as e:
            logger.error(f"创建智能体失败: {str(e)}")
            raise
    
    async def run_task(self, task: str, tools: List[Any] = None, **kwargs) -> Tuple[str, Any, Dict[str, Any]]:
        """
        运行任务
        
        参数:
            task: 任务描述
            tools: 可用工具列表
            **kwargs: 其他参数
                - agent_id: 指定使用的智能体ID
                - agent_type: 智能体类型（如果没有指定agent_id）
                - conversation_id: 对话ID
                - stream: 是否流式输出
                
        返回:
            Tuple[str, Any, Dict[str, Any]]: (回答, 交互历史, 元数据)
        """
        import time
        start_time = time.time()
        
        try:
            if not self.is_initialized:
                raise RuntimeError("框架未初始化，请先调用 initialize()")
            
            # 选择或创建智能体
            agent_id = kwargs.get("agent_id")
            if agent_id and agent_id in self.agents:
                agent_info = self.agents[agent_id]
                agent = agent_info["agent"]
                framework_type = agent_info["framework"]
            else:
                # 创建临时智能体
                agent_type = kwargs.get("agent_type", AgentType.KNOWLEDGE_AGENT)
                temp_config = {
                    "name": "temp_agent",
                    "description": f"临时智能体用于执行任务: {task[:50]}...",
                    "knowledge_bases": kwargs.get("knowledge_bases", []),
                    "model": kwargs.get("model", self.default_model)
                }
                agent = await self.create_agent(agent_type, temp_config)
            
            # 准备工具
            if tools is None:
                tools = []
            
            # 如果启用了工具包管理器，添加默认工具
            if self.enable_tools and hasattr(self, 'toolkit_manager'):
                try:
                    default_tools = await self.toolkit_manager.get_tools()
                    tools.extend(default_tools)
                except Exception as e:
                    logger.warning(f"获取默认工具失败: {str(e)}")
            
            # 执行任务
            conversation_id = kwargs.get("conversation_id")
            
            # 根据智能体类型调用不同的方法
            if hasattr(agent, 'query'):
                # LlamaIndex代理
                response = await agent.query(task, conversation_id=conversation_id)
                answer = response.get("answer", "")
                history = response.get("sources", [])
            elif hasattr(agent, 'run'):
                # 其他类型的代理
                response = await agent.run(task, tools=tools, **kwargs)
                answer = str(response)
                history = []
            else:
                # 通用处理
                response = await agent.aquery(task) if hasattr(agent, 'aquery') else str(agent)
                answer = str(response)
                history = []
            
            # 计算响应时间
            response_time = time.time() - start_time
            
            # 构建元数据
            metadata = {
                "task": task,
                "agent_id": agent_id,
                "framework": framework_type.value if 'framework_type' in locals() else "unknown",
                "response_time": response_time,
                "tools_used": len(tools),
                "timestamp": time.time(),
                "status": TaskStatus.COMPLETED
            }
            
            # 更新统计
            self._stats["tasks_completed"] += 1
            self._stats["total_response_time"] += response_time
            
            logger.info(f"任务执行完成，响应时间: {response_time:.2f}秒")
            return answer, history, metadata
            
        except Exception as e:
            # 更新失败统计
            self._stats["tasks_failed"] += 1
            
            error_metadata = {
                "task": task,
                "error": str(e),
                "status": TaskStatus.FAILED,
                "timestamp": time.time()
            }
            
            logger.error(f"任务执行失败: {str(e)}")
            raise RuntimeError(f"任务执行失败: {str(e)}") from e
    
    def _select_framework_for_agent_type(self, agent_type: str) -> FrameworkType:
        """根据智能体类型选择最适合的框架"""
        agent_type_enum = AgentType(agent_type)
        
        # 根据智能体类型选择框架
        if agent_type_enum == AgentType.KNOWLEDGE_AGENT:
            # 知识智能体优先使用LlamaIndex
            if FrameworkType.LLAMAINDEX in self.framework_manager.list_frameworks():
                return FrameworkType.LLAMAINDEX
        elif agent_type_enum == AgentType.MCP_AGENT:
            # MCP智能体优先使用FastMCP
            if FrameworkType.FASTMCP in self.framework_manager.list_frameworks():
                return FrameworkType.FASTMCP
        elif agent_type_enum == AgentType.RETRIEVAL_AGENT:
            # 检索智能体优先使用Haystack
            if FrameworkType.HAYSTACK in self.framework_manager.list_frameworks():
                return FrameworkType.HAYSTACK
        
        # 默认使用第一个可用框架
        available_frameworks = self.framework_manager.list_frameworks()
        return available_frameworks[0] if available_frameworks else FrameworkType.LLAMAINDEX
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        avg_response_time = (
            self._stats["total_response_time"] / self._stats["tasks_completed"]
            if self._stats["tasks_completed"] > 0 else 0.0
        )
        
        return {
            **self._stats,
            "average_response_time": avg_response_time,
            "active_agents": len(self.agents),
            "success_rate": (
                self._stats["tasks_completed"] / 
                (self._stats["tasks_completed"] + self._stats["tasks_failed"])
                if (self._stats["tasks_completed"] + self._stats["tasks_failed"]) > 0 
                else 0.0
            )
        }
    
    async def cleanup(self):
        """清理资源"""
        try:
            self.agents.clear()
            if hasattr(self, 'toolkit_manager'):
                await self.toolkit_manager.cleanup()
            if hasattr(self, 'knowledge_retriever'):
                await self.knowledge_retriever.cleanup()
            
            logger.info("统一智能体框架清理完成")
        except Exception as e:
            logger.error(f"框架清理失败: {str(e)}")


class UnifiedToolkitManager(IToolkitManager):
    """
    统一工具包管理器实现
    管理不同类型的工具包和工具
    """
    
    def __init__(self):
        """初始化工具包管理器"""
        self.toolkits = {}  # 存储已加载的工具包
        self.tools = {}     # 存储所有工具
        self.custom_tools = []  # 存储自定义工具
        
        logger.info("统一工具包管理器初始化")
    
    async def initialize(self, config: Dict[str, Any]):
        """
        初始化工具包管理器
        
        参数:
            config: 工具配置
                - enabled_toolkits: 启用的工具包列表
                - mcp_tools: MCP工具配置
                - custom_tools: 自定义工具配置
        """
        try:
            enabled_toolkits = config.get("enabled_toolkits", [])
            
            # 加载启用的工具包
            for toolkit_name in enabled_toolkits:
                try:
                    await self.load_toolkit(toolkit_name, config.get(toolkit_name, {}))
                except Exception as e:
                    logger.warning(f"加载工具包 {toolkit_name} 失败: {str(e)}")
            
            # 加载MCP工具
            mcp_config = config.get("mcp_tools", {})
            if mcp_config.get("enabled", False):
                await self._load_mcp_tools(mcp_config)
            
            logger.info("工具包管理器初始化完成")
            
        except Exception as e:
            logger.error(f"工具包管理器初始化失败: {str(e)}")
            raise
    
    async def load_toolkit(self, toolkit_name: str, config: Optional[Dict[str, Any]] = None) -> Any:
        """
        加载指定的工具包
        
        参数:
            toolkit_name: 工具包名称
            config: 工具包配置
            
        返回:
            加载的工具包实例
        """
        try:
            if toolkit_name in self.toolkits:
                logger.debug(f"工具包 {toolkit_name} 已加载")
                return self.toolkits[toolkit_name]
            
            toolkit = None
            config = config or {}
            
            # 根据工具包名称加载对应的工具包
            if toolkit_name == "llamaindex":
                from app.frameworks.llamaindex.tools import get_all_mcp_tools
                toolkit = get_all_mcp_tools()
                
            elif toolkit_name == "fastmcp":
                from app.frameworks.fastmcp.tools import MCPToolkit
                toolkit = MCPToolkit(config)
                await toolkit.initialize()
                
            elif toolkit_name == "web_search":
                from app.tools.web_search import WebSearchTool
                toolkit = [WebSearchTool(config)]
                
            elif toolkit_name == "file_operations":
                from app.tools.file_operations import FileOperationsTool
                toolkit = [FileOperationsTool(config)]
                
            else:
                logger.warning(f"未知的工具包: {toolkit_name}")
                return None
            
            # 存储工具包
            self.toolkits[toolkit_name] = toolkit
            
            # 注册工具包中的工具
            if isinstance(toolkit, list):
                for tool in toolkit:
                    tool_name = getattr(tool, 'name', f"{toolkit_name}_tool_{len(self.tools)}")
                    self.tools[tool_name] = tool
            else:
                self.tools[toolkit_name] = toolkit
            
            logger.info(f"工具包 {toolkit_name} 加载成功")
            return toolkit
            
        except Exception as e:
            logger.error(f"加载工具包 {toolkit_name} 失败: {str(e)}")
            raise
    
    async def get_tools(self, toolkit_name: Optional[str] = None) -> List[Any]:
        """
        获取指定工具包中的工具，如不指定则返回所有工具
        
        参数:
            toolkit_name: 工具包名称，如为None则返回所有工具
            
        返回:
            工具列表
        """
        try:
            if toolkit_name is None:
                # 返回所有工具
                all_tools = list(self.tools.values()) + self.custom_tools
                return all_tools
            
            if toolkit_name not in self.toolkits:
                logger.warning(f"工具包 {toolkit_name} 未加载")
                return []
            
            toolkit = self.toolkits[toolkit_name]
            if isinstance(toolkit, list):
                return toolkit
            else:
                return [toolkit]
                
        except Exception as e:
            logger.error(f"获取工具失败: {str(e)}")
            return []
    
    async def register_custom_tool(self, tool: Any) -> None:
        """
        注册自定义工具
        
        参数:
            tool: 自定义工具实例
        """
        try:
            # 验证工具接口
            if not hasattr(tool, 'name'):
                tool.name = f"custom_tool_{len(self.custom_tools)}"
            
            if not hasattr(tool, 'description'):
                tool.description = "自定义工具"
            
            self.custom_tools.append(tool)
            
            # 同时添加到工具字典
            self.tools[tool.name] = tool
            
            logger.info(f"自定义工具注册成功: {tool.name}")
            
        except Exception as e:
            logger.error(f"注册自定义工具失败: {str(e)}")
            raise
    
    async def _load_mcp_tools(self, config: Dict[str, Any]):
        """加载MCP工具"""
        try:
            # 从不同的MCP提供商加载工具
            providers = config.get("providers", [])
            
            for provider_config in providers:
                provider_name = provider_config.get("name")
                if provider_name:
                    await self.load_toolkit(f"mcp_{provider_name}", provider_config)
            
            logger.info("MCP工具加载完成")
            
        except Exception as e:
            logger.error(f"加载MCP工具失败: {str(e)}")
    
    async def cleanup(self):
        """清理工具包管理器"""
        try:
            for toolkit in self.toolkits.values():
                if hasattr(toolkit, 'cleanup'):
                    await toolkit.cleanup()
            
            self.toolkits.clear()
            self.tools.clear()
            self.custom_tools.clear()
            
            logger.info("工具包管理器清理完成")
            
        except Exception as e:
            logger.error(f"工具包管理器清理失败: {str(e)}")


class UnifiedKnowledgeRetriever(IKnowledgeRetriever):
    """
    统一知识检索器实现
    整合多种知识库和检索方法
    """
    
    def __init__(self):
        """初始化知识检索器"""
        self.knowledge_bases = {}
        self.retrievers = {}
        self.default_similarity_threshold = 0.7
        
        logger.info("统一知识检索器初始化")
    
    async def initialize(self, knowledge_base_ids: List[str]):
        """
        初始化知识检索器
        
        参数:
            knowledge_base_ids: 知识库ID列表
        """
        try:
            from app.config import get_db
            from app.services.unified_knowledge_service import get_unified_knowledge_service
            
            db = next(get_db())
            knowledge_service = get_unified_knowledge_service(db)
            
            # 初始化知识库
            for kb_id in knowledge_base_ids:
                try:
                    kb = await knowledge_service.get_knowledge_base(kb_id)
                    if kb:
                        self.knowledge_bases[kb_id] = kb
                        
                        # 创建检索器
                        retriever = await self._create_retriever(kb_id)
                        if retriever:
                            self.retrievers[kb_id] = retriever
                            
                        logger.info(f"知识库 {kb_id} 初始化成功")
                    else:
                        logger.warning(f"知识库 {kb_id} 不存在")
                        
                except Exception as e:
                    logger.error(f"初始化知识库 {kb_id} 失败: {str(e)}")
            
            logger.info(f"知识检索器初始化完成，共加载 {len(self.retrievers)} 个知识库")
            
        except Exception as e:
            logger.error(f"知识检索器初始化失败: {str(e)}")
            raise
    
    async def query(self, query_text: str, **kwargs) -> List[Dict[str, Any]]:
        """
        从知识库中检索相关内容
        
        参数:
            query_text: 查询文本
            **kwargs: 其他参数
                - kb_ids: 指定搜索的知识库ID列表
                - top_k: 返回结果数量
                - similarity_threshold: 相似度阈值
                
        返回:
            检索结果列表
        """
        try:
            kb_ids = kwargs.get("kb_ids", list(self.retrievers.keys()))
            top_k = kwargs.get("top_k", 5)
            similarity_threshold = kwargs.get("similarity_threshold", self.default_similarity_threshold)
            
            all_results = []
            
            # 从指定的知识库中检索
            for kb_id in kb_ids:
                if kb_id not in self.retrievers:
                    logger.warning(f"知识库 {kb_id} 未初始化")
                    continue
                
                try:
                    retriever = self.retrievers[kb_id]
                    
                    # 执行检索
                    if hasattr(retriever, 'query'):
                        results = await retriever.query(query_text, top_k=top_k)
                    else:
                        # 使用通用检索方法
                        results = await self._generic_query(retriever, query_text, top_k)
                    
                    # 过滤结果并添加知识库信息
                    for result in results:
                        if result.get("score", 1.0) >= similarity_threshold:
                            result["knowledge_base_id"] = kb_id
                            result["knowledge_base_name"] = self.knowledge_bases.get(kb_id, {}).get("name", kb_id)
                            all_results.append(result)
                            
                except Exception as e:
                    logger.error(f"从知识库 {kb_id} 检索失败: {str(e)}")
            
            # 按相似度排序并限制结果数量
            all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            return all_results[:top_k]
            
        except Exception as e:
            logger.error(f"知识检索失败: {str(e)}")
            return []
    
    async def create_retrieval_tool(self) -> Any:
        """
        创建检索工具，供智能体使用
        
        返回:
            检索工具实例
        """
        try:
            from llama_index.core.tools import FunctionTool
            
            async def retrieve_knowledge(query: str, kb_ids: Optional[List[str]] = None) -> str:
                """知识检索工具函数"""
                results = await self.query(query, kb_ids=kb_ids)
                
                if not results:
                    return "未找到相关信息"
                
                # 格式化结果
                formatted_results = []
                for i, result in enumerate(results[:3], 1):  # 最多返回3个结果
                    content = result.get("content", "")
                    kb_name = result.get("knowledge_base_name", "")
                    score = result.get("score", 0)
                    
                    formatted_results.append(
                        f"{i}. [来源: {kb_name}, 相似度: {score:.2f}]\n{content}"
                    )
                
                return "\n\n".join(formatted_results)
            
            # 创建检索工具
            retrieval_tool = FunctionTool.from_defaults(
                fn=retrieve_knowledge,
                name="knowledge_retrieval",
                description="从知识库中检索相关信息，支持指定特定知识库"
            )
            
            logger.info("检索工具创建成功")
            return retrieval_tool
            
        except Exception as e:
            logger.error(f"创建检索工具失败: {str(e)}")
            raise
    
    async def _create_retriever(self, kb_id: str):
        """为知识库创建检索器"""
        try:
            from app.frameworks.llamaindex.indexing import load_or_create_index
            from app.frameworks.llamaindex.retrieval import get_query_engine
            
            # 创建索引
            collection_name = f"kb_{kb_id}"
            index = load_or_create_index(collection_name=collection_name)
            
            # 创建查询引擎
            retriever = get_query_engine(
                index,
                similarity_top_k=10,
                similarity_cutoff=self.default_similarity_threshold
            )
            
            return retriever
            
        except Exception as e:
            logger.error(f"为知识库 {kb_id} 创建检索器失败: {str(e)}")
            return None
    
    async def _generic_query(self, retriever, query_text: str, top_k: int) -> List[Dict[str, Any]]:
        """通用查询方法"""
        try:
            if hasattr(retriever, 'query'):
                response = await retriever.query(query_text)
                
                results = []
                if hasattr(response, 'source_nodes'):
                    for node in response.source_nodes[:top_k]:
                        results.append({
                            "content": node.text,
                            "metadata": node.metadata,
                            "score": getattr(node, 'score', 1.0)
                        })
                
                return results
                
        except Exception as e:
            logger.error(f"通用查询失败: {str(e)}")
            return []
    
    async def cleanup(self):
        """清理知识检索器"""
        try:
            self.knowledge_bases.clear()
            self.retrievers.clear()
            
            logger.info("知识检索器清理完成")
            
        except Exception as e:
            logger.error(f"知识检索器清理失败: {str(e)}")


# ========== 工厂函数 ==========

def create_unified_framework(framework_type: Optional[FrameworkType] = None) -> UnifiedAgentFramework:
    """
    创建统一智能体框架实例
    
    参数:
        framework_type: 优先使用的框架类型
        
    返回:
        统一智能体框架实例
    """
    return UnifiedAgentFramework(framework_type)


def create_toolkit_manager() -> UnifiedToolkitManager:
    """
    创建工具包管理器实例
    
    返回:
        工具包管理器实例
    """
    return UnifiedToolkitManager()


def create_knowledge_retriever() -> UnifiedKnowledgeRetriever:
    """
    创建知识检索器实例
    
    返回:
        知识检索器实例
    """
    return UnifiedKnowledgeRetriever()


# ========== 全局实例 ==========

_unified_framework = None
_toolkit_manager = None
_knowledge_retriever = None


def get_unified_framework() -> UnifiedAgentFramework:
    """获取全局统一智能体框架实例"""
    global _unified_framework
    if _unified_framework is None:
        _unified_framework = create_unified_framework()
    return _unified_framework


def get_toolkit_manager() -> UnifiedToolkitManager:
    """获取全局工具包管理器实例"""
    global _toolkit_manager
    if _toolkit_manager is None:
        _toolkit_manager = create_toolkit_manager()
    return _toolkit_manager


def get_knowledge_retriever() -> UnifiedKnowledgeRetriever:
    """获取全局知识检索器实例"""
    global _knowledge_retriever
    if _knowledge_retriever is None:
        _knowledge_retriever = create_knowledge_retriever()
    return _knowledge_retriever
