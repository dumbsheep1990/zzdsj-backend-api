import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
import atexit
import os
import asyncio
import logging
import json

from app.api import assistants, knowledge, chat, assistant, model_provider, assistant_qa, mcp, mcp_service
from app.api import auth, user, api_key, resource_permission
from app.api import system_config, sensitive_word, settings, lightrag, agent
# 导入工具相关API
from app.api import owl_api, unified_tool_api, base_tools
# 导入高级检索和重排序模型API
from app.api import advanced_retrieval, rerank_models
# 导入上下文压缩API
from app.api import context_compression
# 导入前端API路由
from app.api.frontend import frontend_router
from app.config import settings
from app.utils.core.database import init_database as init_db
from app.utils.vector_store import init_milvus
from app.utils.object_storage import init_minio
from app.utils.service_discovery import register_service, deregister_service, start_heartbeat
from app.utils.core.config import ConfigBootstrap, validate_config
from app.utils.mcp_service_registrar import get_mcp_service_registrar
from app.utils.service_manager import get_service_manager, register_lightrag_service
from core.mcp_service_manager import get_mcp_service_manager
from app.middleware.sensitive_word_middleware import SensitiveWordMiddleware
from app.startup import register_searxng_startup, register_context_compression
from app.utils.core.config import inject_config_to_env, get_base_dependencies
from app.utils.core.config import get_config_manager

# 导入日志系统
from app.middleware.logging_middleware import setup_logging, get_logger
from app.utils.logging_config import load_logging_config, register_logging_env_mappings

# 初始化默认日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = get_logger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="知识库问答系统API - 高级助手框架集成",
    version="1.0.0",
    docs_url=None,  # 禁用默认文档
    redoc_url=None,  # 禁用默认redoc
)

# 从配置中加载CORS设置
config = get_config_manager().get_config()

# 检查是否启用CORS
cors_enabled = config.get("cors_enabled", True)
if cors_enabled:
    # 获取CORS来源
    cors_origins_str = config.get("cors_origins", '["http://localhost:3000", "http://127.0.0.1:3000"]')
    try:
        if isinstance(cors_origins_str, str):
            cors_origins = json.loads(cors_origins_str)
        else:
            cors_origins = cors_origins_str
    except json.JSONDecodeError:
        logger.error(f"CORS来源解析失败: {cors_origins_str}，使用默认值")
        cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # 获取是否允许携带认证信息
    allow_credentials = config.get("cors_allow_credentials", True)
    
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"已配置CORS，允许的来源: {', '.join(cors_origins)}")
else:
    logger.info("CORS已禁用")

# 安装所有安全中间件
from app.middleware.security import setup_security_middleware
setup_security_middleware(app)

# 注册SearxNG服务启动
register_searxng_startup(app)

# 如果静态文件目录不存在则创建
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 导入新的统一API路由
try:
    from app.api.v1 import api_router as v1_api_router
    # 添加统一的API v1路由
    app.include_router(v1_api_router)
    logger.info("成功集成API v1统一架构路由")
except ImportError as e:
    logger.warning(f"导入API v1统一架构失败: {str(e)}，将使用传统路由")

# 导入API中间件
try:
    from app.api.v1.middleware import setup_middlewares
    # 设置API中间件
    setup_middlewares(app)
    logger.info("成功设置API v1中间件")
except ImportError as e:
    logger.warning(f"设置API v1中间件失败: {str(e)}")

# 包含传统路由器（保持向后兼容）
app.include_router(assistants.router, prefix="/api/v1/assistants/classic", tags=["经典助手"])
app.include_router(assistant.router, prefix="/api/v1/assistants", tags=["AI助手"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["知识库"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["对话"])
app.include_router(model_provider.router, prefix="/api/v1/models", tags=["模型管理"])
app.include_router(assistant_qa.router, prefix="/api/v1/assistant-qa", tags=["问答助手"])
app.include_router(lightrag.router, tags=["LightRAG服务"])
app.include_router(mcp.router, tags=["MCP服务"])
app.include_router(mcp_service.router, tags=["MCP服务管理"])
app.include_router(system_config.router)
app.include_router(sensitive_word.router, tags=["敏感词管理"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["系统设置"])
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(api_key.router)
app.include_router(resource_permission.router)

# 注册OWL框架API路由
app.include_router(owl_api.router, prefix="/api", tags=["OWL智能体框架"])
app.include_router(agent.router, prefix="/api/agent", tags=["智能体服务"])
# 注册统一工具API路由
app.include_router(unified_tool_api.router, prefix="/api", tags=["统一工具系统"])
# 注册高级检索和重排序模型API路由
app.include_router(advanced_retrieval.router, tags=["高级检索"])
app.include_router(rerank_models.router, tags=["重排序模型"])
# 注册基础工具API路由
app.include_router(base_tools.router, prefix="/api", tags=["基础工具系统"])
# 注册上下文压缩API路由
app.include_router(context_compression.router, prefix="/api", tags=["上下文压缩"])
# 注册前端API路由
app.include_router(frontend_router)

@app.get("/", include_in_schema=False)
def root():
    return {"message": "欢迎使用知识库问答系统API", "docs": "/docs"}

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{settings.PROJECT_NAME} - API文档",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_favicon_url="/static/favicon.ico",
    )

@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    return get_openapi(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="""
# 知识库问答系统API

## 功能特点
- **多框架集成**: 支持Haystack、LlamaIndex和Agno
- **知识库管理**: 创建、更新和查询知识库
- **文档处理**: 上传、处理和检索文档
- **AI助手**: 配置和与AI助手交互
- **对话管理**: 跟踪和管理对话
- **多模态支持**: 文本、图像和语音交互

## 认证
API请求需要使用API密钥进行认证。在`Authorization`头中包含您的API密钥:
```
Authorization: Bearer YOUR_API_KEY
```

## 速率限制
API请求受到速率限制以防止滥用。当前限制为:
- 标准: 每分钟60个请求
- 突发: 一次最多10个请求
        """,
        routes=app.routes,
    )

# 注册MCP服务健康检查任务
@app.on_event("startup")
async def startup_mcp_health_check():
    """启动MCP服务健康检查任务"""
    async def health_check_task():
        mcp_manager = get_mcp_service_manager()
        
        while True:
            try:
                # 获取所有部署的MCP服务
                deployments = mcp_manager.list_deployments()
                
                # 检查每个服务的健康状态
                for deployment in deployments:
                    deployment_id = deployment.get("deployment_id")
                    if deployment_id:
                        # 仅检查运行中的服务
                        if deployment.get("status", {}).get("state") == "running":
                            await mcp_manager.check_deployment_health(deployment_id)
                
                # 每60秒检查一次
                await asyncio.sleep(60)
            
            except Exception as e:
                logger.error(f"MCP服务健康检查任务出错: {str(e)}")
                await asyncio.sleep(10)  # 出错后等待较短时间再重试
    
    # 创建后台任务
    asyncio.create_task(health_check_task())
    logger.info("已启动MCP服务健康检查任务")

@app.on_event("startup")
async def startup_event():
    """启动时初始化服务"""
    # 第1步: 将配置注入到环境变量
    # 使用print而非logger，因为日志系统还未配置
    print("正在将配置注入到环境变量...")
    inject_config_to_env()
    
    # 注册日志配置环境变量映射
    config_manager = get_config_manager()
    register_logging_env_mappings(config_manager)
    
    # 第2步: 初始化日志系统
    print("正在初始化日志系统...")
    logging_config = load_logging_config()
    setup_logging(
        app=app,
        log_level=logging_config.level,
        log_to_console=logging_config.console_enabled,
        log_to_file=logging_config.file_enabled,
        log_file_path=logging_config.file_path,
        log_format=logging_config.format,
        log_retention=logging_config.file_retention,
        log_rotation=logging_config.file_rotation,
        exclude_paths=logging_config.request_exclude_paths,
        log_request_body=logging_config.log_request_body,
        log_response_body=logging_config.log_response_body
    )
    
    # 设置模块特定的日志级别
    if logging_config.module_levels:
        for module_name, level in logging_config.module_levels.items():
            module_logger = logging.getLogger(module_name)
            module_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    logger.info("日志系统初始化完成")
    
    # 第3步: 检查基础依赖配置
    base_deps = get_base_dependencies()
    missing_deps = [dep for dep, config in base_deps.items() if not config]
    if missing_deps:
        logger.warning(f"以下必要的依赖配置缺失或不完整: {', '.join(missing_deps)}")
    
    # 第4步: 运行配置自检和引导流程
    logger.info("正在执行配置自检和引导流程...")
    config_manager = get_config_manager()
    bootstrap = ConfigBootstrap()
    await bootstrap.bootstrap_config()
    
    # 第5步: 初始化数据库
    logger.info("正在初始化数据库...")
    from app.utils.core.database.migration import get_migrator
    migrator = get_migrator()
    migrator.init_db(create_tables=True, seed_data=True)
    
    # 第6步: 生成数据库模式文档
    try:
        from app.utils.swagger_helper import save_db_schema_doc, add_schema_examples, generate_model_examples
        logger.info("正在生成数据库模式文档...")
        schema_path = save_db_schema_doc()
        logger.info(f"数据库模式文档已保存到 {schema_path}")
        
        # 为Swagger文档添加示例数据
        examples = generate_model_examples()
        add_schema_examples(app, examples)
    except Exception as e:
        logger.error(f"生成数据库模式文档时出错: {str(e)}", exc_info=True)
    
    # 第7步: 执行配置验证
    config_data = config_manager.get_all()
    service_health = validate_config(config_data)
    
    # 第8步: Milvus初始化
    milvus_available = service_health.get("milvus", False)
    if milvus_available:
        try:
            from app.utils.vector_store import init_milvus
            logger.info("正在初始化Milvus...")
            init_milvus()
            logger.info("Milvus初始化成功")
        except Exception as e:
            logger.error(f"初始化Milvus时出错: {str(e)}", exc_info=True)
    else:
        logger.warning("Milvus服务不可用，跳过初始化")
    
    # 第9步: MinIO初始化
    minio_available = service_health.get("minio", False)
    if minio_available:
        try:
            from app.utils.object_storage import init_minio
            logger.info("正在初始化MinIO...")
            init_minio()
            logger.info("MinIO初始化成功")
        except Exception as e:
            logger.error(f"初始化MinIO时出错: {str(e)}", exc_info=True)
    else:
        logger.warning("MinIO服务不可用，跳过初始化")
    
    # 第10步: Nacos服务注册
    nacos_available = service_health.get("nacos", False)
    if nacos_available:
        try:
            from app.utils.service_discovery import register_service, start_heartbeat
            logger.info("正在向Nacos注册服务...")
            register_service()
            # 启动心跳线程
            start_heartbeat()
            logger.info("服务注册成功")
            
            # 注册装饰器标记的应用服务
            from app.utils.service_registry import register_decorated_services
            logger.info("正在注册应用服务到Nacos...")
            registered_count = register_decorated_services()
            logger.info(f"应用服务注册完成: {registered_count}个服务已注册")
            
            # 初始MCP服务注册器
            mcp_registrar = get_mcp_service_registrar()
            logger.info("MCP服务注册器初始化完成")
            
            # 注册正在运行的MCP服务
            mcp_manager = get_mcp_service_manager()
            for deployment in mcp_manager.list_deployments():
                deployment_id = deployment.get("deployment_id")
                # 仅注册运行中的服务
                if deployment.get("status", {}).get("state") == "running":
                    mcp_manager._register_service_to_nacos(deployment_id, deployment)
            logger.info("已重新注册所有运行中的MCP服务")
        except Exception as e:
            logger.error(f"向Nacos注册服务时出错: {str(e)}", exc_info=True)
    else:
        logger.warning("Nacos服务不可用，跳过服务注册")
        
    # 第11步: 注册和启动LightRAG服务
    try:
        logger.info("正在注册 LightRAG 服务...")
        # 初始化服务管理器
        service_manager = get_service_manager()
        
        # 注册LightRAG服务
        register_lightrag_service()
        logger.info("LightRAG服务注册成功")
        
        # 检查是否启用LightRAG
        lightrag_enabled = getattr(settings, "LIGHTRAG_ENABLED", True)
        if lightrag_enabled:
            # 自动启动LightRAG服务
            logger.info("正在启动 LightRAG 服务...")
            lightrag_status = service_manager.start_service("lightrag-api")
            if lightrag_status:
                logger.info("LightRAG服务启动成功")
            else:
                logger.warning("LightRAG服务启动失败")
        else:
            logger.info("LightRAG服务已注册但未启用")
    except Exception as e:
        logger.error(f"初始化LightRAG服务时出错: {str(e)}", exc_info=True)
    
    # 第12步: 初始化OWL框架
    try:
        logger.info("正在初始化OWL框架...")
        from app.startup.owl_init import register_owl_init
        # 注册OWL框架初始化模块
        register_owl_init(app)
        logger.info("OWL框架初始化模块注册成功")
    except Exception as e:
        logger.error(f"注册OWL框架初始化模块时出错: {str(e)}", exc_info=True)
        
    # 第13步: 初始化工具系统
    try:
        logger.info("正在初始化基础工具系统...")
        from app.startup.tools import init_tools
        # 获取系统配置
        config = get_config_manager().get_config()
        # 初始化工具系统
        init_tools(app, config)
        logger.info("基础工具系统初始化成功")
    except Exception as e:
        logger.error(f"初始化基础工具系统时出错: {str(e)}", exc_info=True)
        
    # 第14步: 初始化上下文压缩功能
    try:
        logger.info("正在初始化上下文压缩功能...")
        # 注册上下文压缩功能
        register_context_compression(app)
        logger.info("上下文压缩功能初始化成功")
    except Exception as e:
        logger.error(f"初始化上下文压缩功能时出错: {str(e)}", exc_info=True)

@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理"""
    # 从Nacos注销服务
    try:
        # 注销所有MCP服务
        mcp_registrar = get_mcp_service_registrar()
        mcp_registrar.stop()
        logger.info("已注销所有MCP服务")
        
        # 注销装饰器标记的应用服务
        try:
            from app.utils.service_registry import deregister_decorated_services
            logger.info("正在从Nacos注销应用服务...")
            deregistered_count = deregister_decorated_services()
            logger.info(f"应用服务注销完成: {deregistered_count}个服务已注销")
        except Exception as e:
            logger.error(f"注销应用服务时出错: {str(e)}", exc_info=True)
        
        # 注销主服务
        logger.info("正在从Nacos注销主服务...")
        deregister_service()
        logger.info("主服务注销成功")
    except Exception as e:
        logger.error(f"从Nacos注销服务时出错: {str(e)}", exc_info=True)
    
    # 停止LightRAG服务
    try:
        service_manager = get_service_manager()
        lightrag_status = service_manager.stop_service("lightrag-api")
        if lightrag_status:
            logger.info("LightRAG服务已停止")
        else:
            logger.warning("LightRAG服务停止失败")
    except Exception as e:
        logger.error(f"停止LightRAG服务时出错: {e}")

# 注册关闭处理程序
atexit.register(deregister_service)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.SERVICE_PORT, reload=True)
