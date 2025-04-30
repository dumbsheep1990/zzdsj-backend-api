from typing import List, Dict, Any
from app.utils.config_manager import get_config

class Settings:
    # 服务信息
    PROJECT_NAME: str = get_config("service", "name", default="智政知识库问答系统")
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
    
    # 模型提供商配置
    # OpenAI配置
    OPENAI_API_BASE: str = get_config("model_providers", "openai", "api_base", default="https://api.openai.com/v1")
    OPENAI_ORGANIZATION: str = get_config("model_providers", "openai", "organization", default="")
    
    # 智谱AI配置
    ZHIPU_API_KEY: str = get_config("model_providers", "zhipu", "api_key", default="")
    
    # DeepSeek配置
    DEEPSEEK_API_KEY: str = get_config("model_providers", "deepseek", "api_key", default="")
    DEEPSEEK_API_BASE: str = get_config("model_providers", "deepseek", "api_base", default="https://api.deepseek.com/v1")
    
    # Ollama配置
    OLLAMA_API_BASE: str = get_config("model_providers", "ollama", "api_base", default="http://localhost:11434")
    
    # VLLM配置
    VLLM_API_BASE: str = get_config("model_providers", "vllm", "api_base", default="http://localhost:8000")
    
    # 通义千问配置
    DASHSCOPE_API_KEY: str = get_config("model_providers", "dashscope", "api_key", default="")
    
    # Anthropic配置
    ANTHROPIC_API_KEY: str = get_config("model_providers", "anthropic", "api_key", default="")
    ANTHROPIC_API_BASE: str = get_config("model_providers", "anthropic", "api_base", default="https://api.anthropic.com")
    
    # TogetherAI配置
    TOGETHER_API_KEY: str = get_config("model_providers", "together", "api_key", default="")
    TOGETHER_API_BASE: str = get_config("model_providers", "together", "api_base", default="https://api.together.xyz/v1")
    
    # 千问API配置
    QWEN_API_KEY: str = get_config("model_providers", "qwen", "api_key", default="")
    QWEN_API_BASE: str = get_config("model_providers", "qwen", "api_base", default="https://dashscope.aliyuncs.com/api/v1")
    
    # 百度文心一言配置
    BAIDU_API_KEY: str = get_config("model_providers", "baidu", "api_key", default="")
    BAIDU_SECRET_KEY: str = get_config("model_providers", "baidu", "secret_key", default="")
    BAIDU_API_BASE: str = get_config("model_providers", "baidu", "api_base", default="https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop")
    
    # 月之暗面配置
    MOONSHOT_API_KEY: str = get_config("model_providers", "moonshot", "api_key", default="")
    MOONSHOT_API_BASE: str = get_config("model_providers", "moonshot", "api_base", default="https://api.moonshot.cn/v1")
    
    # 智谱GLM配置
    GLM_API_KEY: str = get_config("model_providers", "glm", "api_key", default="")
    GLM_API_BASE: str = get_config("model_providers", "glm", "api_base", default="https://open.bigmodel.cn/api/paas/v4")
    
    # MiniMax配置
    MINIMAX_API_KEY: str = get_config("model_providers", "minimax", "api_key", default="")
    MINIMAX_GROUP_ID: str = get_config("model_providers", "minimax", "group_id", default="")
    MINIMAX_API_BASE: str = get_config("model_providers", "minimax", "api_base", default="https://api.minimax.chat/v1")
    
    # 百川配置
    BAICHUAN_API_KEY: str = get_config("model_providers", "baichuan", "api_key", default="")
    BAICHUAN_SECRET_KEY: str = get_config("model_providers", "baichuan", "secret_key", default="")
    BAICHUAN_API_BASE: str = get_config("model_providers", "baichuan", "api_base", default="https://api.baichuan-ai.com/v1")
    
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
    # LlamaIndex配置（替代LangChain）
    EMBEDDING_MODEL: str = get_config("frameworks", "llamaindex", "embedding_model", default="text-embedding-ada-002")
    CHAT_MODEL: str = get_config("frameworks", "llamaindex", "llm_model", default="gpt-3.5-turbo")
    MEMORY_TYPE: str = get_config("frameworks", "llamaindex", "memory_type", default="conversation_buffer")
    MEMORY_K: int = get_config("frameworks", "llamaindex", "memory_k", default=5)
    
    # 保留LangChain配置（为了兼容性，但已不再使用）
    LANGCHAIN_EMBEDDING_MODEL: str = EMBEDDING_MODEL
    LANGCHAIN_CHAT_MODEL: str = CHAT_MODEL
    LANGCHAIN_MEMORY_TYPE: str = MEMORY_TYPE
    LANGCHAIN_MEMORY_K: int = MEMORY_K
    LANGCHAIN_USE_LANGSMITH: bool = False
    LANGCHAIN_LANGSMITH_API_KEY: str = ""
    LANGCHAIN_LANGSMITH_PROJECT: str = "knowledge-qa"
    
    # Haystack配置
    HAYSTACK_READER_MODEL: str = get_config("frameworks", "haystack", "reader_model", default="deepset/roberta-base-squad2")
    HAYSTACK_RETRIEVER_TYPE: str = get_config("frameworks", "haystack", "retriever_type", default="embedding")
    HAYSTACK_USE_BM25: bool = get_config("frameworks", "haystack", "use_bm25", default=True)
    HAYSTACK_TOP_K: int = get_config("frameworks", "haystack", "top_k", default=5)
    HAYSTACK_EMBEDDING_MODEL: str = get_config("frameworks", "haystack", "embedding_model", default="sentence-transformers/all-MiniLM-L6-v2")
    HAYSTACK_RERANK_DOCUMENTS: bool = get_config("frameworks", "haystack", "rerank_documents", default=False)
    HAYSTACK_RERANKER_MODEL: str = get_config("frameworks", "haystack", "reranker_model", default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    
    # LlamaIndex配置
    LLAMAINDEX_CHUNK_SIZE: int = get_config("frameworks", "llamaindex", "chunk_size", default=1000)
    LLAMAINDEX_CHUNK_OVERLAP: int = get_config("frameworks", "llamaindex", "chunk_overlap", default=200)
    LLAMAINDEX_EMBEDDING_MODEL: str = get_config("frameworks", "llamaindex", "embedding_model", default="text-embedding-ada-002")
    LLAMAINDEX_LLM_MODEL: str = get_config("frameworks", "llamaindex", "llm_model", default="gpt-3.5-turbo")
    LLAMAINDEX_INDEX_TYPE: str = get_config("frameworks", "llamaindex", "index_type", default="vector_store")
    LLAMAINDEX_USE_KNOWLEDGE_GRAPH: bool = get_config("frameworks", "llamaindex", "use_knowledge_graph", default=False)
    
    # Agno配置
    AGNO_AGENT_TYPE: str = get_config("frameworks", "agno", "agent_type", default="conversational")
    AGNO_MODEL: str = get_config("frameworks", "agno", "model", default="gpt-3.5-turbo")
    AGNO_MAX_ITERATIONS: int = get_config("frameworks", "agno", "max_iterations", default=5)
    AGNO_MEMORY_TYPE: str = get_config("frameworks", "agno", "memory_type", default="conversation_buffer")
    AGNO_MEMORY_K: int = get_config("frameworks", "agno", "memory_k", default=5)
    
    # 框架集成配置
    # 统一入口 - LlamaIndex（替代LangChain）
    FRAMEWORK_ENTRY_POINT: str = get_config("framework_integration", "entry_point", default="llamaindex")
    
    # QA助手 - Agno与检索集成
    QA_ASSISTANT_FRAMEWORK: str = get_config("framework_integration", "qa_assistant", "framework", default="agno")
    QA_RETRIEVER_FRAMEWORK: str = get_config("framework_integration", "qa_assistant", "retriever", default="haystack")
    QA_INDEXER_FRAMEWORK: str = get_config("framework_integration", "qa_assistant", "indexer", default="llamaindex")
    
    # QA管理 - LlamaIndex与Agno协作（替代LangChain）
    QA_MANAGEMENT_CONVERSATION_FRAMEWORK: str = get_config("framework_integration", "qa_management", "conversation", default="llamaindex")
    QA_MANAGEMENT_MEMORY_FRAMEWORK: str = get_config("framework_integration", "qa_management", "memory", default="agno")
    QA_MANAGEMENT_API_FRAMEWORK: str = get_config("framework_integration", "qa_management", "api", default="llamaindex")
    
    # 知识库管理 - LlamaIndex与Haystack分工
    KNOWLEDGE_MANAGEMENT_INDEXING_FRAMEWORK: str = get_config("framework_integration", "knowledge_management", "indexing", default="llamaindex")
    KNOWLEDGE_MANAGEMENT_SEARCH_FRAMEWORK: str = get_config("framework_integration", "knowledge_management", "search", default="haystack")
    
    # 遗留路径（保留以兼容）
    VECTOR_STORE_PATH: str = get_config("paths", "vector_store", default="./vector_store")
    KNOWLEDGE_BASE_PATH: str = get_config("paths", "knowledge_base", default="./knowledge_base")


settings = Settings()
