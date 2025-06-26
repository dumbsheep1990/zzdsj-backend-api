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
import sys
from pathlib import Path
from typing import Dict, Any, Optional

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
# 使用新的标准化向量存储组件，保持向后兼容
from app.utils.storage.vector_storage import (
    init_standard_document_collection,
    init_milvus  # 向后兼容的导入
)
from app.utils.object_storage import init_minio
from app.utils.service_discovery import register_service, deregister_service, start_heartbeat
from app.utils.core.config import ConfigBootstrap, validate_config
from app.utils.mcp_service_registrar import get_mcp_service_registrar
from app.utils.services.management import get_service_manager, register_lightrag_service
from core.mcp_service_manager import get_mcp_service_manager
from app.middleware.sensitive_word_middleware import SensitiveWordMiddleware
from app.startup import register_searxng_startup, register_context_compression
from app.utils.core.config import inject_config_to_env, get_base_dependencies
from app.utils.core.config import get_config_manager as get_legacy_config_manager

# 导入新的高级配置管理系统
from app.core.config.advanced_manager import (
    AdvancedConfigManager, 
    get_config_manager as get_advanced_config_manager,
    load_minimal_config,
    validate_current_config,
    ConfigurationError
)

# 导入日志系统
from app.middleware.logging_middleware import setup_logging, get_logger
from app.utils.logging_config import load_logging_config, register_logging_env_mappings

# ============================================================================
# 配置系统启动检查
# ============================================================================

def pre_startup_config_check():
    """启动前配置检查"""
    print("🔍 执行启动前配置检查...")
    
    # 检查环境变量
    app_env = os.getenv("APP_ENV", "development")
    config_mode = os.getenv("CONFIG_MODE", "standard")
    
    print(f"   当前环境: {app_env}")
    print(f"   配置模式: {config_mode}")
    
    # 检查配置文件存在性
    project_root = Path(__file__).parent
    config_dir = project_root / "config"
    
    if not config_dir.exists():
        print("❌ 配置目录不存在，请确保 config/ 目录存在")
        sys.exit(1)
    
    # 检查必需的配置文件
    required_files = ["default.yaml"]
    if config_mode != "minimal":
        required_files.append(f"{app_env}.yaml")
    
    missing_files = []
    for file_name in required_files:
        config_file = config_dir / file_name
        if not config_file.exists():
            missing_files.append(file_name)
    
    if missing_files:
        print(f"❌ 缺失必需的配置文件: {', '.join(missing_files)}")
        print("请使用环境管理脚本创建配置文件:")
        print(f"   python scripts/env_manager.py switch {app_env}")
        sys.exit(1)
    
    print("✅ 配置检查通过")

def validate_startup_config() -> Dict[str, Any]:
    """验证启动配置"""
    print("🔍 验证启动配置...")
    
    try:
        # 检查是否为最小配置模式
        config_mode = os.getenv("CONFIG_MODE", "standard")
        minimal_mode = (config_mode == "minimal" or os.getenv("APP_ENV") == "minimal")
        
        # 初始化高级配置管理器
        app_env = os.getenv("APP_ENV", "development")
        config_manager = AdvancedConfigManager(environment=app_env)
        
        # 加载配置
        config = config_manager.load_configuration(minimal_mode=minimal_mode)
        
        # 验证配置
        validation_result = config_manager.validate_configuration(config)
        
        if not validation_result.is_valid:
            print("❌ 配置验证失败:")
            for error in validation_result.errors[:5]:  # 显示前5个错误
                print(f"   • {error}")
            
            if validation_result.missing_required:
                print("缺失必需配置:")
                for missing in validation_result.missing_required[:5]:
                    print(f"   • {missing}")
            
            # 非致命错误，继续启动但发出警告
            print("⚠️ 配置验证有误，继续启动但可能影响功能")
        else:
            print("✅ 配置验证通过")
        
        # 显示配置摘要
        print(f"   配置项总数: {len(config)}")
        print(f"   环境: {app_env}")
        print(f"   模式: {config_mode}")
        
        if minimal_mode:
            print("   🚀 使用最小配置模式（快速启动）")
        
        return config
        
    except ConfigurationError as e:
        print(f"❌ 配置错误: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 配置验证失败: {str(e)}")
        print("⚠️ 使用默认配置继续启动")
        return {}

def setup_application_config(config: Dict[str, Any]) -> FastAPI:
    """根据配置设置应用"""
    
    # 从配置中获取应用设置
    app_config = config.get("app", {})
    api_config = config.get("api", {})
    
    app_title = api_config.get("title", app_config.get("name", "知识库问答系统API"))
    app_description = api_config.get("description", "智能知识问答系统接口文档")
    app_version = app_config.get("version", "1.0.0")
    
    # 创建FastAPI应用
    app = FastAPI(
        title=app_title,
        description=app_description,
        version=app_version,
        docs_url=None,  # 禁用默认文档
        redoc_url=None,  # 禁用默认redoc
    )
    
    return app

def setup_cors_middleware(app: FastAPI, config: Dict[str, Any]):
    """设置CORS中间件"""
    
    # 检查是否启用CORS
    features = config.get("features", {})
    security_config = config.get("security", {})
    cors_config = security_config.get("cors", {})
    
    cors_enabled = features.get("cors_enabled", cors_config.get("enabled", True))
    
    if cors_enabled:
        # 获取CORS配置
        origins = cors_config.get("origins", ["*"])
        methods = cors_config.get("methods", ["GET", "POST", "PUT", "DELETE", "OPTIONS"])
        headers = cors_config.get("headers", ["*"])
        
        # 处理字符串格式的origins
        if isinstance(origins, str):
            try:
                origins = json.loads(origins)
            except json.JSONDecodeError:
                origins = [origins]
        
        # 添加CORS中间件
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=methods,
            allow_headers=headers,
        )
        print(f"✅ CORS已启用，允许的来源: {', '.join(origins) if len(origins) <= 3 else f'{len(origins)}个来源'}")
    else:
        print("ℹ️  CORS已禁用")

# ============================================================================
# 应用初始化
# ============================================================================

# 执行启动前检查
pre_startup_config_check()

# 验证配置并获取配置数据
startup_config = validate_startup_config()

# 创建应用
app = setup_application_config(startup_config)

# 设置CORS
setup_cors_middleware(app, startup_config)

# 初始化默认日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = get_logger(__name__)

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

# 注册智能体编排API路由
try:
    from app.api.orchestration.routes import router as orchestration_router
    app.include_router(orchestration_router, prefix="/api/orchestration", tags=["智能体编排"])
    logger.info("成功注册智能体编排API路由")
except ImportError as e:
    logger.warning(f"导入智能体编排API失败: {str(e)}")

@app.get("/", include_in_schema=False)
def root():
    return {"message": "欢迎使用知识库问答系统API", "docs": "/docs"}

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    api_config = startup_config.get("api", {})
    title = api_config.get("title", "知识库问答系统API")
    
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{title} - API文档",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_favicon_url="/static/favicon.ico",
    )

@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    app_config = startup_config.get("app", {})
    api_config = startup_config.get("api", {})
    
    title = api_config.get("title", app_config.get("name", "知识库问答系统API"))
    version = app_config.get("version", "1.0.0")
    description = api_config.get("description", "智能知识问答系统接口文档")
    
    return get_openapi(
        title=title,
        version=version,
        description=f"""
# {title}

## 🎯 功能特点
- **多框架集成**: 支持Haystack、LlamaIndex和Agno
- **知识库管理**: 创建、更新和查询知识库
- **文档处理**: 上传、处理和检索文档
- **AI助手**: 配置和与AI助手交互
- **对话管理**: 跟踪和管理对话
- **多模态支持**: 文本、图像和语音交互

## 🔧 环境信息
- **当前环境**: {os.getenv('APP_ENV', 'development')}
- **配置模式**: {os.getenv('CONFIG_MODE', 'standard')}
- **服务版本**: {version}

## 🔐 认证
API请求需要使用API密钥进行认证。在`Authorization`头中包含您的API密钥:
```
Authorization: Bearer YOUR_API_KEY
```

## ⚡ 速率限制
API请求受到速率限制以防止滥用。当前限制为:
- 标准: 每分钟60个请求
- 突发: 一次最多10个请求

{description}
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
    """应用启动事件"""
    logger.info("ZZDSJ Backend API 启动中...")
    
    # 初始化向量数据库
    try:
        from app.utils.vector_db_initializer import initialize_vector_database, get_current_vector_backend
        
        logger.info("开始初始化向量数据库...")
        success = await initialize_vector_database()
        
        if success:
            current_backend = get_current_vector_backend()
            logger.info(f"向量数据库初始化成功，当前使用: {current_backend.value if current_backend else 'None'}")
        else:
            logger.warning("向量数据库初始化失败，部分功能可能不可用")
            
    except Exception as e:
        logger.error(f"向量数据库初始化过程中发生异常: {str(e)}")
    
    # 保留原有的Milvus初始化逻辑作为回退
    try:
        from app.utils.storage.vector_storage import init_milvus
        await init_milvus()
        logger.info("备用Milvus初始化完成")
    except Exception as e:
        logger.warning(f"备用Milvus初始化失败: {str(e)}")
    
    logger.info("ZZDSJ Backend API 启动完成")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("ZZDSJ Backend API 关闭中...")
    
    # 关闭向量数据库
    try:
        from app.utils.vector_db_initializer import shutdown_vector_database
        await shutdown_vector_database()
        logger.info("向量数据库已关闭")
    except Exception as e:
        logger.error(f"关闭向量数据库时发生异常: {str(e)}")
    
    logger.info("ZZDSJ Backend API 已关闭")

# 注册关闭处理程序
atexit.register(deregister_service)

if __name__ == "__main__":
    # 获取配置
    service_config = startup_config.get("service", {})
    host = service_config.get("ip", "0.0.0.0")
    port = service_config.get("port", getattr(settings, "SERVICE_PORT", 8000))
    
    # 开发环境启用重载
    reload = startup_config.get("app", {}).get("debug", False)
    
    logger.info(f"🚀 启动服务: {host}:{port} (重载: {reload})")
    uvicorn.run("main:app", host=host, port=port, reload=reload)
