import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import atexit

from app.api import assistants, knowledge, chat
from app.config import settings
from app.utils.database import init_db
from app.utils.vector_store import init_milvus
from app.utils.object_storage import init_minio
from app.utils.service_discovery import register_service, deregister_service, start_heartbeat

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Knowledge Base QA System API",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(assistants.router, prefix="/api/assistants", tags=["Assistants"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge Base"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])

@app.get("/")
def root():
    return {"message": "Welcome to Knowledge Base QA System API"}

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # Initialize database
    init_db()
    
    # Initialize Milvus
    try:
        init_milvus()
        print("Milvus initialized successfully")
    except Exception as e:
        print(f"Error initializing Milvus: {e}")
    
    # Initialize MinIO
    try:
        init_minio()
        print("MinIO initialized successfully")
    except Exception as e:
        print(f"Error initializing MinIO: {e}")
    
    # Register service with Nacos
    try:
        register_service()
        # Start heartbeat thread
        start_heartbeat()
    except Exception as e:
        print(f"Error registering service with Nacos: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    # Deregister service from Nacos
    try:
        deregister_service()
    except Exception as e:
        print(f"Error deregistering service from Nacos: {e}")

# Register shutdown handler
atexit.register(deregister_service)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.SERVICE_PORT, reload=True)
