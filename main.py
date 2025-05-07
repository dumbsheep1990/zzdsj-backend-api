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

from app.api import assistants, knowledge, chat, assistant, model_provider, assistant_qa, mcp, mcp_service
from app.api import auth, user, api_key, resource_permission
from app.api import system_config, sensitive_word, settings, lightrag
from app.config import settings
from app.utils.database import init_db
from app.utils.vector_store import init_milvus
from app.utils.object_storage import init_minio
from app.utils.service_discovery import register_service, deregister_service, start_heartbeat
from app.utils.config_bootstrap import ConfigBootstrap
from app.utils.mcp_service_registrar import get_mcp_service_registrar
from app.utils.service_manager import get_service_manager, register_lightrag_service
from app.core.mcp_service_manager import get_mcp_service_manager
from app.middleware.sensitive_word_middleware import SensitiveWordMiddleware
from app.startup import register_searxng_startup

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="知识库问答系统API - 高级助手框架集成",
    version="1.0.0",
    docs_url=None,  # 禁用默认文档
    redoc_url=None,  # 禁用默认redoc
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加敏感词过滤中间件
app.add_middleware(SensitiveWordMiddleware)

# 注册SearxNG服务启动
register_searxng_startup(app)

# 如果静态文件目录不存在则创建
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 包含路由器
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
    # 第1步: 运行配置自检和引导
    print("正在执行配置自检和引导流程...")
    bootstrap_result = await ConfigBootstrap.run_bootstrap()
    
    # 检查数据库可用性
    db_available = bootstrap_result.get("config_validation", {}).get("services_healthy", {}).get("database", False)
    
    # 第2步: 数据库初始化 (仅当数据库可用时)
    if db_available:
        print("正在初始化数据库...")
        try:
            init_db(create_tables=True, seed_data=True)
            print("数据库初始化成功")
        except Exception as e:
            print(f"初始化数据库时出错: {e}")
        
        # 生成数据库模式文档
        try:
            from app.utils.swagger_helper import save_db_schema_doc, add_schema_examples, generate_model_examples
            schema_path = save_db_schema_doc()
            print(f"数据库模式文档已保存到 {schema_path}")
            
            # 为Swagger文档添加示例数据
            examples = generate_model_examples()
            add_schema_examples(app, examples)
        except Exception as e:
            print(f"生成模式文档时出错: {e}")
    else:
        print("警告: 数据库服务不可用，跳过初始化")
    
    # 第3步: Milvus初始化
    milvus_available = bootstrap_result.get("config_validation", {}).get("services_healthy", {}).get("milvus", False)
    if milvus_available:
        try:
            init_milvus()
            print("Milvus初始化成功")
        except Exception as e:
            print(f"初始化Milvus时出错: {e}")
    else:
        print("警告: Milvus服务不可用，跳过初始化")
    
    # 第4步: MinIO初始化
    minio_available = bootstrap_result.get("config_validation", {}).get("services_healthy", {}).get("minio", False)
    if minio_available:
        try:
            init_minio()
            print("MinIO初始化成功")
        except Exception as e:
            print(f"初始化MinIO时出错: {e}")
    else:
        print("警告: MinIO服务不可用，跳过初始化")
    
    # 第5步: Nacos服务注册
    nacos_available = bootstrap_result.get("config_validation", {}).get("services_healthy", {}).get("nacos", False)
    if nacos_available:
        try:
            register_service()
            # 启动心跳线程
            start_heartbeat()
            print("服务注册成功")
            
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
            print(f"向Nacos注册服务时出错: {e}")
    else:
        print("警告: Nacos服务不可用，跳过服务注册")
        
    # 第6步: 注册和启动LightRAG服务
    try:
        print("正在注册 LightRAG 服务...")
        # 初始化服务管理器
        service_manager = get_service_manager()
        
        # 注册LightRAG服务
        register_lightrag_service()
        
        # 检查是否启用LightRAG
        lightrag_enabled = getattr(settings, "LIGHTRAG_ENABLED", True)
        if lightrag_enabled:
            # 自动启动LightRAG服务
            lightrag_status = service_manager.start_service("lightrag-api")
            if lightrag_status:
                print("LightRAG服务启动成功")
            else:
                print("警告: LightRAG服务启动失败")
        else:
            print("LightRAG服务已注册但未启用")
    except Exception as e:
        print(f"初始化LightRAG服务时出错: {e}")
        logger.error(f"LightRAG初始化错误: {str(e)}", exc_info=True)

@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理"""
    # 从Nacos注销服务
    try:
        # 注销所有MCP服务
        mcp_registrar = get_mcp_service_registrar()
        mcp_registrar.stop()
        logger.info("已注销所有MCP服务")
        
        # 注销主服务
        deregister_service()
    except Exception as e:
        print(f"从Nacos注销服务时出错: {e}")
    
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
