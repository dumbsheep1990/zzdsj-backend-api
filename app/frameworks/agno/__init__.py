"""
Agno框架集成模块

将ZZDSJ的LlamaIndex系统迁移到Agno框架，
提供完整的代理、工具和服务集成功能
"""

# 核心组件
from .core import AgnoCore, get_agno_core
from .agent import AgnoAgent, AgnoAgentAdapter
from .chat import AgnoChat, AgnoChatAdapter
from .query_engine import AgnoQueryEngine, AgnoQueryEngineAdapter
from .document_processor import AgnoDocumentProcessor, AgnoDocumentProcessorAdapter
from .retrieval import AgnoRetrieval, AgnoRetrievalAdapter
from .vector_store import AgnoVectorStore, AgnoVectorStoreAdapter
from .indexing import AgnoIndexing, AgnoIndexingAdapter
from .knowledge_base import AgnoKnowledgeBase

# 配置和初始化
from .config import AgnoConfig
from .initialization import initialize_agno, cleanup_agno
from .memory_adapter import AgnoMemoryAdapter
from .embeddings import AgnoEmbeddings

# 工具和服务集成 (Phase 2)
from .tools import (
    ZZDSJKnowledgeTools,
    ZZDSJFileManagementTools, 
    ZZDSJSystemTools,
    get_zzdsj_knowledge_tools,
    get_zzdsj_file_tools,
    get_zzdsj_system_tools,
    create_zzdsj_agent_tools
)

from .mcp_adapter import (
    ZZDSJMCPAdapter,
    MCPServiceConfig,
    create_zzdsj_mcp_agent,
    test_all_mcp_services
)

from .service_adapter import (
    ZZDSJServiceAdapter,
    ServiceConfig,
    get_service_adapter,
    create_zzdsj_chat_agent,
    get_service_health
)

# 测试和状态跟踪 (Phase 2完善)
from .integration_test import (
    AgnoIntegrationTest,
    run_integration_tests
)

from .migration_status import (
    MigrationStatusTracker,
    get_migration_tracker,
    print_migration_summary
)

# 团队协作管理器 (Phase 2高级功能)
from .team_coordinator import (
    ZZDSJTeamCoordinator,
    TeamMode,
    AgentRole,
    AgentSpec,
    TeamSpec,
    CollaborationResult,
    get_team_coordinator,
    create_research_team,
    create_content_team,
    create_problem_solving_team,
    run_research_collaboration,
    run_content_collaboration,
    run_problem_solving_collaboration
)

# API适配器 (Phase 3核心组件)
from .api_adapter import (
    ZZDSJAgnoAPIAdapter,
    APIResponse,
    ChatRequest,
    KnowledgeRequest,
    TeamRequest,
    get_api_adapter,
    handle_chat_api,
    handle_knowledge_api,
    handle_team_api,
    get_agno_api_status,
    list_agno_teams
)

# 路由集成 (Phase 3路由层)
from .route_integration import (
    ZZDSJAgnoRouteIntegrator,
    AgnoRouteConfig,
    ChatRequestModel,
    KnowledgeRequestModel,
    TeamRequestModel,
    get_route_integrator,
    create_agno_chat_router,
    create_agno_knowledge_router,
    create_agno_team_router,
    agno_route
)

# 响应格式化器 (Phase 3响应格式)
from .response_formatters import (
    ZZDSJResponseFormatter,
    ResponseStatus,
    ErrorType,
    ResponseMetadata,
    PaginationInfo,
    get_response_formatter,
    success_response,
    error_response,
    streaming_response
)

# FastAPI集成 (Phase 3完善)
from .fastapi_integration import (
    ZZDSJAgnoFastAPIIntegration,
    get_agno_integration
)

# Phase 4: 核心业务逻辑迁移
from .chat_manager_adapter import (
    ZZDSJAgnoChatManager,
    get_chat_manager
)

from .knowledge_manager_adapter import (
    ZZDSJAgnoKnowledgeManager,
    get_knowledge_manager
)

# 模型配置适配器
from .model_config_adapter import (
    ZZDSJAgnoModelAdapter,
    ModelConfiguration,
    SupportedProvider,
    get_model_adapter,
    create_default_agno_model,
    create_agno_model_by_provider,
    create_agno_model_by_id
)

# 使用示例
from .model_config_usage_example import (
    example_create_agent_with_configured_model,
    example_create_agent_with_specific_provider,
    example_create_team_with_configured_models,
    example_list_available_configurations,
    example_validate_model_configuration,
    example_model_fallback_mechanism,
    run_all_examples
)

# Phase 5: 智能体模版化系统 - 三种内置模版和执行图引擎
from .templates import (
    # 模版定义
    AgentTemplate,
    TemplateType,
    ExecutionGraph,
    ExecutionNode,
    ExecutionEdge,
    get_template,
    list_available_templates,
    BASIC_CONVERSATION_TEMPLATE,
    KNOWLEDGE_BASE_TEMPLATE,
    DEEP_THINKING_TEMPLATE,
    AVAILABLE_TEMPLATES
)

from .template_manager import (
    # 模版管理器
    AgnoTemplateManager,
    get_template_manager,
    create_agent_from_template,
    get_available_templates as get_template_list,
    recommend_templates
)

from .frontend_config_parser import (
    # 前端配置解析
    AgnoConfigParser,
    get_config_parser,
    parse_frontend_config,
    validate_frontend_config,
    TemplateSelection,
    BasicConfiguration,
    ModelConfiguration,
    CapabilityConfiguration,
    AdvancedConfiguration,
    FrontendConfig,
    PersonalityType,
    ResponseLength,
    CostTier,
    PrivacyLevel
)

from .execution_engine import (
    # 执行图引擎
    AgnoExecutionEngine,
    NodeType,
    NodeProcessor,
    ProcessorNode,
    ClassifierNode,
    GeneratorNode,
    RetrieverNode,
    FormatterNode,
    create_execution_engine,
    execute_with_graph
)

# Phase 6: 编排系统 - 完全解耦合的智能Agent编排
from .orchestration import (
    # 核心编排组件
    AgnoToolRegistry,
    AgnoConfigParser as OrchestrationConfigParser,
    AgnoMatchingEngine,
    
    # 类型定义
    ToolFramework,
    ToolCategory,
    ExecutionStatus,
    AgentRole as OrchestrationAgentRole,
    ResponseFormat,
    OrchestrationEvent,
    ErrorCode,
    ToolMetadata,
    ToolInstance,
    AgentConfig as OrchestrationAgentConfig,
    OrchestrationRequest,
    ToolCallResult,
    ExecutionContext,
    OrchestrationResult,
    EventData,
    
    # 工厂函数和快捷接口
    get_tool_registry,
    get_config_parser,
    get_matching_engine,
    initialize_registry,
    cleanup_registry,
    initialize_orchestration_system,
    create_agent_from_frontend_config,
    get_system_status as get_orchestration_status,
    
    # 常量
    DEFAULT_TOOL_TIMEOUT,
    DEFAULT_AGENT_MAX_LOOPS,
    DEFAULT_EXECUTION_TIMEOUT,
    DEFAULT_CACHE_TTL,
    MAX_CONCURRENT_EXECUTIONS,
    MAX_TOOL_CALLS_PER_REQUEST,
    MAX_REQUEST_SIZE
)

# 版本信息
__version__ = "1.0.0"
__author__ = "ZZDSJ Development Team"
__description__ = "ZZDSJ Agno框架集成 - LlamaIndex到Agno的完整迁移解决方案"

# 导出列表
__all__ = [
    # 核心组件
    "AgnoCore",
    "get_agno_core", 
    "AgnoAgent",
    "AgnoAgentAdapter",
    "AgnoChat",
    "AgnoChatAdapter",
    "AgnoQueryEngine", 
    "AgnoQueryEngineAdapter",
    "AgnoDocumentProcessor",
    "AgnoDocumentProcessorAdapter",
    "AgnoRetrieval",
    "AgnoRetrievalAdapter",
    "AgnoVectorStore",
    "AgnoVectorStoreAdapter",
    "AgnoIndexing",
    "AgnoIndexingAdapter",
    "AgnoKnowledgeBase",
    
    # 配置和工具
    "AgnoConfig",
    "initialize_agno",
    "cleanup_agno",
    "AgnoMemoryAdapter",
    "AgnoEmbeddings",
    
    # ZZDSJ工具集成
    "ZZDSJKnowledgeTools",
    "ZZDSJFileManagementTools",
    "ZZDSJSystemTools",
    "get_zzdsj_knowledge_tools",
    "get_zzdsj_file_tools", 
    "get_zzdsj_system_tools",
    "create_zzdsj_agent_tools",
    
    # MCP集成
    "ZZDSJMCPAdapter",
    "MCPServiceConfig",
    "create_zzdsj_mcp_agent",
    "test_all_mcp_services",
    
    # 服务适配器
    "ZZDSJServiceAdapter",
    "ServiceConfig", 
    "get_service_adapter",
    "create_zzdsj_chat_agent",
    "get_service_health",
    
    # 测试和状态跟踪
    "AgnoIntegrationTest",
    "run_integration_tests", 
    "MigrationStatusTracker",
    "get_migration_tracker",
    "print_migration_summary",
    
    # 团队协作管理器
    "ZZDSJTeamCoordinator",
    "TeamMode",
    "AgentRole", 
    "AgentSpec",
    "TeamSpec",
    "CollaborationResult",
    "get_team_coordinator",
    "create_research_team",
    "create_content_team",
    "create_problem_solving_team",
    "run_research_collaboration",
    "run_content_collaboration",
    "run_problem_solving_collaboration",
    
    # API适配器
    "ZZDSJAgnoAPIAdapter",
    "APIResponse",
    "ChatRequest",
    "KnowledgeRequest",
    "TeamRequest",
    "get_api_adapter",
    "handle_chat_api",
    "handle_knowledge_api",
    "handle_team_api",
    "get_agno_api_status",
    "list_agno_teams",
    
    # 路由集成
    "ZZDSJAgnoRouteIntegrator",
    "AgnoRouteConfig",
    "ChatRequestModel",
    "KnowledgeRequestModel",
    "TeamRequestModel",
    "get_route_integrator",
    "create_agno_chat_router",
    "create_agno_knowledge_router",
    "create_agno_team_router",
    "agno_route",
    
    # 响应格式化器
    "ZZDSJResponseFormatter",
    "ResponseStatus",
    "ErrorType",
    "ResponseMetadata",
    "PaginationInfo",
    "get_response_formatter",
    "success_response",
    "error_response",
    "streaming_response",
    
    # FastAPI集成
    "ZZDSJAgnoFastAPIIntegration",
    "get_agno_integration",
    
    # Phase 4: 核心业务逻辑迁移
    "ZZDSJAgnoChatManager",
    "get_chat_manager",
    "ZZDSJAgnoKnowledgeManager",
    "get_knowledge_manager",
    
    # 模型配置适配器
    "ZZDSJAgnoModelAdapter",
    "ModelConfiguration",
    "SupportedProvider",
    "get_model_adapter",
    "create_default_agno_model",
    "create_agno_model_by_provider",
    "create_agno_model_by_id",
    
    # 使用示例
    "example_create_agent_with_configured_model",
    "example_create_agent_with_specific_provider",
    "example_create_team_with_configured_models",
    "example_list_available_configurations",
    "example_validate_model_configuration",
    "example_model_fallback_mechanism",
    "run_all_examples",
    
    # Phase 5: 智能体模版化系统
    "AgentTemplate",
    "TemplateType",
    "ExecutionGraph", 
    "ExecutionNode",
    "ExecutionEdge",
    "get_template",
    "list_available_templates",
    "BASIC_CONVERSATION_TEMPLATE",
    "KNOWLEDGE_BASE_TEMPLATE", 
    "DEEP_THINKING_TEMPLATE",
    "AVAILABLE_TEMPLATES",
    "AgnoTemplateManager",
    "get_template_manager",
    "create_agent_from_template",
    "get_template_list",
    "recommend_templates",
    "AgnoConfigParser",
    "get_config_parser",
    "parse_frontend_config",
    "validate_frontend_config",
    "TemplateSelection",
    "BasicConfiguration",
    "ModelConfiguration", 
    "CapabilityConfiguration",
    "AdvancedConfiguration",
    "FrontendConfig",
    "PersonalityType",
    "ResponseLength",
    "CostTier",
    "PrivacyLevel",
    "AgnoExecutionEngine",
    "NodeType",
    "NodeProcessor",
    "ProcessorNode",
    "ClassifierNode", 
    "GeneratorNode",
    "RetrieverNode",
    "FormatterNode",
    "create_execution_engine",
    "execute_with_graph",
    
    # Phase 6: 编排系统
    "AgnoToolRegistry",
    "OrchestrationConfigParser", 
    "AgnoMatchingEngine",
    "ToolFramework",
    "ToolCategory",
    "ExecutionStatus",
    "OrchestrationAgentRole",
    "ResponseFormat",
    "OrchestrationEvent",
    "ErrorCode",
    "ToolMetadata",
    "ToolInstance",
    "OrchestrationAgentConfig",
    "OrchestrationRequest",
    "ToolCallResult",
    "ExecutionContext",
    "OrchestrationResult",
    "EventData",
    "get_tool_registry",
    "get_config_parser",
    "get_matching_engine",
    "initialize_registry",
    "cleanup_registry",
    "initialize_orchestration_system",
    "create_agent_from_frontend_config",
    "get_orchestration_status",
    "DEFAULT_TOOL_TIMEOUT",
    "DEFAULT_AGENT_MAX_LOOPS",
    "DEFAULT_EXECUTION_TIMEOUT",
    "DEFAULT_CACHE_TTL",
    "MAX_CONCURRENT_EXECUTIONS",
    "MAX_TOOL_CALLS_PER_REQUEST",
    "MAX_REQUEST_SIZE",
    
    # 元信息
    "__version__",
    "__author__",
    "__description__"
]
