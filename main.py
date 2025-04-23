import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
import atexit
import os

from app.api import assistants, knowledge, chat, assistant, model_provider, assistant_qa, mcp
from app.config import settings
from app.utils.database import init_db
from app.utils.vector_store import init_milvus
from app.utils.object_storage import init_minio
from app.utils.service_discovery import register_service, deregister_service, start_heartbeat

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
app.include_router(mcp.router, tags=["MCP服务"])

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
- **多框架集成**: 支持LangChain、Haystack、LlamaIndex和Agno
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

@app.on_event("startup")
async def startup_event():
    """启动时初始化服务"""
    # 初始化数据库
    init_db()
    
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
    
    # 初始化Milvus
    try:
        init_milvus()
        print("Milvus初始化成功")
    except Exception as e:
        print(f"初始化Milvus时出错: {e}")
    
    # 初始化MinIO
    try:
        init_minio()
        print("MinIO初始化成功")
    except Exception as e:
        print(f"初始化MinIO时出错: {e}")
    
    # 向Nacos注册服务
    try:
        register_service()
        # 启动心跳线程
        start_heartbeat()
    except Exception as e:
        print(f"向Nacos注册服务时出错: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理"""
    # 从Nacos注销服务
    try:
        deregister_service()
    except Exception as e:
        print(f"从Nacos注销服务时出错: {e}")

# 注册关闭处理程序
atexit.register(deregister_service)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.SERVICE_PORT, reload=True)
