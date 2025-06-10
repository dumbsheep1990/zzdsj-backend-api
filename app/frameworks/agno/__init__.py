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
    
    # 元信息
    "__version__",
    "__author__",
    "__description__"
]
