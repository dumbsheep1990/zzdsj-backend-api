"""
中间件模块 (兼容层)
该模块提供了集中的导入兼容层，实际实现已迁移到app.tools目录结构中
"""

# 导入所有中间件组件的兼容层
from app.middleware.compat import (
    # 基础工具
    WebSearchTool,
    WebSearchResult,
    get_search_tool,
    get_web_search_tool,
    
    FunctionCallingAdapter,
    FunctionCallingConfig,
    FunctionCallingStrategy,
    create_function_calling_adapter,
    
    register_tool,
    get_tool,
    get_all_tools,
    
    HostValidatorMiddleware,
    setup_security_middleware,
    SensitiveWordMiddleware,
    
    RateLimiter,
    InMemoryRateLimiter,
    RedisRateLimiter,
    RateLimiterMiddleware,
    parse_rate_limit,
    add_rate_limiter_middleware,
    
    CustomJSONFormatter,
    StructuredLogger,
    RequestLoggingMiddleware,
    LoggingManager,
    setup_logging,
    get_logger,
    log_execution_time,
    
    async_token_metrics,
    TokenMetricsMiddleware,
    
    # 高级工具
    CoTRequest,
    CoTTool,
    get_cot_tool,
    create_cot_function_tool,
    get_all_cot_tools,
    
    CoTManager,
    DEFAULT_COT_START_TAG,
    DEFAULT_COT_END_TAG,
    DEFAULT_ANS_START_TAG,
    DEFAULT_ANS_END_TAG,
    
    InducedCoTParser,
    MultiStepCoTParser,
    
    DeepResearchTool,
    get_deep_research_tool,
    create_deep_research_function_tool,
    
    DeepResearchService,
    get_deep_research_service,
    
    ModelWithTools,
    create_model_with_tools,
    
    ChatWithTools,
    create_chat_with_tools
)

# 导出所有组件
__all__ = [
    # 基础工具
    "WebSearchTool",
    "WebSearchResult",
    "get_search_tool",
    "get_web_search_tool",
    
    "FunctionCallingAdapter",
    "FunctionCallingConfig",
    "FunctionCallingStrategy",
    "create_function_calling_adapter",
    
    "register_tool",
    "get_tool",
    "get_all_tools",
    
    "HostValidatorMiddleware",
    "setup_security_middleware",
    "SensitiveWordMiddleware",
    
    "RateLimiter",
    "InMemoryRateLimiter",
    "RedisRateLimiter",
    "RateLimiterMiddleware",
    "parse_rate_limit",
    "add_rate_limiter_middleware",
    
    "CustomJSONFormatter",
    "StructuredLogger",
    "RequestLoggingMiddleware",
    "LoggingManager",
    "setup_logging",
    "get_logger",
    "log_execution_time",
    
    "async_token_metrics",
    "TokenMetricsMiddleware",
    
    # 高级工具
    "CoTRequest",
    "CoTTool",
    "get_cot_tool",
    "create_cot_function_tool",
    "get_all_cot_tools",
    
    "CoTManager",
    "DEFAULT_COT_START_TAG",
    "DEFAULT_COT_END_TAG",
    "DEFAULT_ANS_START_TAG",
    "DEFAULT_ANS_END_TAG",
    
    "InducedCoTParser",
    "MultiStepCoTParser",
    
    "DeepResearchTool",
    "get_deep_research_tool",
    "create_deep_research_function_tool",
    
    "DeepResearchService",
    "get_deep_research_service",
    
    "ModelWithTools",
    "create_model_with_tools",
    
    "ChatWithTools",
    "create_chat_with_tools"
]
