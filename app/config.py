from typing import List
from app.utils.config_manager import get_config

class Settings:
    # 服务信息
    PROJECT_NAME: str = get_config("service", "name", default="知识库问答系统")
    API_V1_STR: str = "/api"
    SERVICE_NAME: str = get_config("service", "name", default="knowledge-qa-backend")
    SERVICE_IP: str = get_config("service", "ip", default="127.0.0.1")
    SERVICE_PORT: int = get_config("service", "port", default=8000)
    
    # 数据库
    DATABASE_URL: str = get_config("database", "url", default="postgresql://postgres:postgres@localhost:5432/knowledge_qa")
    
    # CORS跨域
    CORS_ORIGINS: List[str] = get_config("cors", "origins", default=["http://localhost", "http://localhost:3000", "http://localhost:8080", "*"])
    
    # LLM配置
    OPENAI_API_KEY: str = get_config("llm", "openai_api_key", default="")
    DEFAULT_MODEL: str = get_config("llm", "default_model", default="gpt-4")
    
    # 向量存储 - Milvus配置
    MILVUS_HOST: str = get_config("vector_store", "milvus", "host", default="localhost")
    MILVUS_PORT: str = get_config("vector_store", "milvus", "port", default="19530")
    MILVUS_COLLECTION: str = get_config("vector_store", "milvus", "collection", default="knowledge_embeddings")
    
    # Redis配置
    REDIS_HOST: str = get_config("redis", "host", default="localhost")
    REDIS_PORT: int = get_config("redis", "port", default=6379)
    REDIS_DB: int = get_config("redis", "db", default=0)
    REDIS_PASSWORD: str = get_config("redis", "password", default="")
    
    # MinIO配置
    MINIO_ENDPOINT: str = get_config("storage", "minio", "endpoint", default="localhost:9000")
    MINIO_ACCESS_KEY: str = get_config("storage", "minio", "access_key", default="minioadmin")
    MINIO_SECRET_KEY: str = get_config("storage", "minio", "secret_key", default="minioadmin")
    MINIO_SECURE: bool = get_config("storage", "minio", "secure", default=False)
    MINIO_BUCKET: str = get_config("storage", "minio", "bucket", default="knowledge-docs")
    
    # RabbitMQ配置
    RABBITMQ_HOST: str = get_config("message_queue", "rabbitmq", "host", default="localhost")
    RABBITMQ_PORT: int = get_config("message_queue", "rabbitmq", "port", default=5672)
    RABBITMQ_USER: str = get_config("message_queue", "rabbitmq", "user", default="guest")
    RABBITMQ_PASSWORD: str = get_config("message_queue", "rabbitmq", "password", default="guest")
    
    # Nacos配置
    NACOS_SERVER_ADDRESSES: str = get_config("service_discovery", "nacos", "server_addresses", default="127.0.0.1:8848")
    NACOS_NAMESPACE: str = get_config("service_discovery", "nacos", "namespace", default="public")
    NACOS_GROUP: str = get_config("service_discovery", "nacos", "group", default="DEFAULT_GROUP")
    
    # Celery配置
    CELERY_BROKER_URL: str = get_config("celery", "broker_url", default="amqp://guest:guest@localhost:5672//")
    CELERY_RESULT_BACKEND: str = get_config("celery", "result_backend", default="redis://localhost:6379/0")
    
    # 框架配置
    LANGCHAIN_EMBEDDING_MODEL: str = get_config("frameworks", "langchain", "embedding_model", default="text-embedding-ada-002")
    HAYSTACK_READER_MODEL: str = get_config("frameworks", "haystack", "reader_model", default="deepset/roberta-base-squad2")
    LLAMAINDEX_CHUNK_SIZE: int = get_config("frameworks", "llamaindex", "chunk_size", default=1000)
    LLAMAINDEX_CHUNK_OVERLAP: int = get_config("frameworks", "llamaindex", "chunk_overlap", default=200)
    
    # 遗留路径（保留以兼容）
    VECTOR_STORE_PATH: str = get_config("paths", "vector_store", default="./vector_store")
    KNOWLEDGE_BASE_PATH: str = get_config("paths", "knowledge_base", default="./knowledge_base")


settings = Settings()
