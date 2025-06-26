"""
Agno编排系统
完全解耦合的智能Agent编排系统，实现前端参数→解析→匹配→组装→执行→返回的完整流程
"""

from .types import (
    # 枚举类型
    ToolFramework,
    ToolCategory, 
    ExecutionStatus,
    AgentRole,
    ResponseFormat,
    OrchestrationEvent,
    ErrorCode,
    
    # 数据类
    ToolMetadata,
    ToolInstance,
    AgentConfig,
    OrchestrationRequest,
    ToolCallResult,
    ExecutionContext,
    OrchestrationResult,
    EventData,
    
    # 接口
    IToolRegistry,
    IConfigParser,
    IMatchingEngine,
    IAgentAssembler,
    IExecutionEngine,
    IToolCallManager,
    IResponseProcessor,
    IOrchestrationManager,
    
    # 回调类型
    EventCallback,
    AsyncEventCallback,
    
    # 常量
    DEFAULT_TOOL_TIMEOUT,
    DEFAULT_AGENT_MAX_LOOPS,
    DEFAULT_EXECUTION_TIMEOUT,
    DEFAULT_CACHE_TTL,
    MAX_CONCURRENT_EXECUTIONS,
    MAX_TOOL_CALLS_PER_REQUEST,
    MAX_REQUEST_SIZE
)

from .registry import (
    AgnoToolRegistry,
    get_tool_registry,
    initialize_registry,
    cleanup_registry
)

from .parser import (
    AgnoConfigParser,
    get_config_parser
)

from .matcher import (
    AgnoMatchingEngine,
    get_matching_engine
)

# 版本信息
__version__ = "1.0.0"
__author__ = "ZZDSJ Development Team"
__description__ = "Agno编排系统 - 完全解耦合的智能Agent编排解决方案"

# 快捷函数
async def initialize_orchestration_system():
    """初始化编排系统"""
    try:
        # 初始化工具注册中心
        registry = await initialize_registry()
        
        # 获取其他组件
        parser = get_config_parser()
        matcher = get_matching_engine()
        
        return {
            'registry': registry,
            'parser': parser,
            'matcher': matcher,
            'status': 'initialized'
        }
        
    except Exception as e:
        return {
            'status': 'failed',
            'error': str(e)
        }

async def create_agent_from_frontend_config(
    user_id: str,
    frontend_config: dict,
    session_id: str = None
) -> dict:
    """从前端配置创建Agent的快捷函数"""
    try:
        # 初始化系统
        system = await initialize_orchestration_system()
        if system['status'] != 'initialized':
            return {'success': False, 'error': 'System initialization failed'}
        
        # 解析前端配置
        parser = system['parser']
        agent_config = await parser.parse_frontend_config(frontend_config)
        
        # 验证配置
        validation_errors = await parser.validate_config(agent_config)
        if validation_errors:
            return {
                'success': False, 
                'error': 'Configuration validation failed',
                'validation_errors': validation_errors
            }
        
        # 匹配和推荐工具
        matcher = system['matcher']
        if not agent_config.tools:
            # 如果没有指定工具，自动推荐
            context = {
                'user_id': user_id,
                'frontend_config': frontend_config
            }
            recommended_tools = await matcher.recommend_tools(
                agent_config.description, 
                context
            )
            agent_config.tools = recommended_tools
        
        # 优化工具链
        optimized_tools = await matcher.optimize_tool_chain(agent_config.tools)
        agent_config.tools = optimized_tools
        
        return {
            'success': True,
            'agent_config': agent_config,
            'recommended_tools': optimized_tools,
            'system_info': {
                'total_available_tools': len(system['registry']._tools),
                'matched_tools': len(optimized_tools)
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Agent creation failed: {str(e)}'
        }

async def get_system_status() -> dict:
    """获取编排系统状态"""
    try:
        registry = await get_tool_registry()
        registry_stats = await registry.get_registry_stats()
        
        return {
            'status': 'healthy',
            'registry': registry_stats,
            'version': __version__,
            'components': {
                'registry': 'active',
                'parser': 'active', 
                'matcher': 'active'
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

# 导出所有公共接口
__all__ = [
    # 类型定义
    'ToolFramework',
    'ToolCategory',
    'ExecutionStatus', 
    'AgentRole',
    'ResponseFormat',
    'OrchestrationEvent',
    'ErrorCode',
    'ToolMetadata',
    'ToolInstance',
    'AgentConfig',
    'OrchestrationRequest',
    'ToolCallResult',
    'ExecutionContext',
    'OrchestrationResult',
    'EventData',
    
    # 接口
    'IToolRegistry',
    'IConfigParser',
    'IMatchingEngine',
    'IAgentAssembler',
    'IExecutionEngine',
    'IToolCallManager',
    'IResponseProcessor',
    'IOrchestrationManager',
    
    # 实现类
    'AgnoToolRegistry',
    'AgnoConfigParser',
    'AgnoMatchingEngine',
    
    # 工厂函数
    'get_tool_registry',
    'get_config_parser',
    'get_matching_engine',
    'initialize_registry',
    'cleanup_registry',
    
    # 快捷函数
    'initialize_orchestration_system',
    'create_agent_from_frontend_config',
    'get_system_status',
    
    # 常量
    'DEFAULT_TOOL_TIMEOUT',
    'DEFAULT_AGENT_MAX_LOOPS',
    'DEFAULT_EXECUTION_TIMEOUT',
    'DEFAULT_CACHE_TTL',
    'MAX_CONCURRENT_EXECUTIONS',
    'MAX_TOOL_CALLS_PER_REQUEST',
    'MAX_REQUEST_SIZE',
    
    # 版本信息
    '__version__',
    '__author__',
    '__description__'
] 