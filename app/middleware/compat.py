"""
中间件兼容层
该模块集中提供所有中间件工具的导入兼容，实际实现已迁移到app.tools目录下
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple, Callable

# 基础工具导入
from app.tools.base.search.search_tool import (
    WebSearchTool,
    WebSearchResult,
    get_search_tool,
    get_web_search_tool
)

from app.tools.base.function_calling.adapter import (
    FunctionCallingAdapter,
    FunctionCallingConfig,
    FunctionCallingStrategy,
    create_function_calling_adapter
)

from app.tools.base.utils.tool_utils import (
    register_tool,
    get_tool,
    get_all_tools
)

from app.tools.base.security.validator import (
    HostValidatorMiddleware
)

from app.tools.base.security.security import (
    setup_security_middleware
)

from app.tools.base.security.sensitive_word_middleware import (
    SensitiveWordMiddleware
)

from app.tools.base.security.rate_limiter import (
    RateLimiter,
    InMemoryRateLimiter,
    RedisRateLimiter,
    RateLimiterMiddleware,
    parse_rate_limit,
    add_rate_limiter_middleware
)

from app.tools.base.logging.logging_middleware import (
    CustomJSONFormatter,
    StructuredLogger,
    RequestLoggingMiddleware,
    LoggingManager,
    setup_logging,
    get_logger,
    log_execution_time
)

from app.tools.base.metrics.token_metrics_middleware import (
    async_token_metrics,
    TokenMetricsMiddleware
)

# 高级工具导入
from app.tools.advanced.reasoning.cot_tool import (
    CoTRequest,
    CoTTool,
    get_cot_tool,
    create_cot_function_tool,
    get_all_cot_tools
)

from app.tools.advanced.reasoning.cot_manager import (
    CoTManager,
    DEFAULT_COT_START_TAG,
    DEFAULT_COT_END_TAG,
    DEFAULT_ANS_START_TAG,
    DEFAULT_ANS_END_TAG
)

from app.tools.advanced.reasoning.cot_parser import (
    InducedCoTParser,
    MultiStepCoTParser
)

from app.tools.advanced.reasoning.deep_research import (
    DeepResearchTool,
    get_deep_research_tool,
    create_deep_research_function_tool
)

from app.tools.advanced.reasoning.deep_research_service import (
    DeepResearchService,
    get_deep_research_service
)

from app.tools.advanced.integration.model_with_tools import (
    ModelWithTools,
    create_model_with_tools
)

from app.tools.advanced.integration.chat_with_tools import (
    ChatWithTools,
    create_chat_with_tools
)

logger = logging.getLogger(__name__)
