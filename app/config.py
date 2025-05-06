from typing import List, Dict, Any
from app.utils.config_manager import get_config
from pydantic import BaseSettings, Field

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
    
    # 认证与安全配置
    JWT_SECRET_KEY: str = get_config("security", "jwt_secret_key", default="23f0767704249cd7be7181a0dad23c74e0739c98ce54d7140fc2e94dfa584fb0")
    JWT_ALGORITHM: str = get_config("security", "jwt_algorithm", default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = get_config("security", "jwt_access_token_expire_minutes", default=30)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = get_config("security", "jwt_refresh_token_expire_days", default=7)
    
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
    MILVUS_COLLECTION: str = get_config("vector_store", "milvus", "collection", default="document_vectors")
    
    # 向量存储 - Elasticsearch配置
    ELASTICSEARCH_URL: str = get_config("vector_store", "elasticsearch", "url", default="http://localhost:9200")
    ELASTICSEARCH_USERNAME: str = get_config("vector_store", "elasticsearch", "username", default="")
    ELASTICSEARCH_PASSWORD: str = get_config("vector_store", "elasticsearch", "password", default="")
    ELASTICSEARCH_CLOUD_ID: str = get_config("vector_store", "elasticsearch", "cloud_id", default="")
    ELASTICSEARCH_API_KEY: str = get_config("vector_store", "elasticsearch", "api_key", default="")
    ELASTICSEARCH_INDEX: str = get_config("vector_store", "elasticsearch", "index", default="document_index")
    ELASTICSEARCH_DEFAULT_ANALYZER: str = get_config("vector_store", "elasticsearch", "analyzer", default="standard")
    ELASTICSEARCH_EMBEDDING_DIM: int = get_config("vector_store", "elasticsearch", "embedding_dim", default=1536)
    ELASTICSEARCH_SIMILARITY: str = get_config("vector_store", "elasticsearch", "similarity", default="cosine")
    ELASTICSEARCH_HYBRID_SEARCH: bool = get_config("vector_store", "elasticsearch", "hybrid_search", default=True)
    ELASTICSEARCH_HYBRID_WEIGHT: float = get_config("vector_store", "elasticsearch", "hybrid_weight", default=0.5)
    
    # 文档处理配置
    DOCUMENT_SPLITTER_TYPE: str = get_config("document_processing", "splitter_type", default="sentence")
    DOCUMENT_CHUNK_SIZE: int = get_config("document_processing", "chunk_size", default=1000)
    DOCUMENT_CHUNK_OVERLAP: int = get_config("document_processing", "chunk_overlap", default=200)
    DOCUMENT_PROCESSING_CONCURRENCY: int = get_config("document_processing", "concurrency", default=4)
    EMBEDDING_BATCH_SIZE: int = get_config("document_processing", "embedding_batch_size", default=16)
    DOCUMENT_PROCESSING_TIMEOUT: int = get_config("document_processing", "timeout", default=3600)
    DOCUMENT_SEMANTIC_CHUNK_STRATEGY: str = get_config("document_processing", "semantic_chunk_strategy", default="auto")
    DOCUMENT_USE_METADATA_EXTRACTION: bool = get_config("document_processing", "use_metadata_extraction", default=True)
    
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
    LLAMAINDEX_CHUNK_SIZE: int = get_config("frameworks", "llamaindex", "chunk_size", default=DOCUMENT_CHUNK_SIZE)
    LLAMAINDEX_CHUNK_OVERLAP: int = get_config("frameworks", "llamaindex", "chunk_overlap", default=DOCUMENT_CHUNK_OVERLAP)
    LLAMAINDEX_EMBEDDING_MODEL: str = get_config("frameworks", "llamaindex", "embedding_model", default="text-embedding-ada-002")
    LLAMAINDEX_LLM_MODEL: str = get_config("frameworks", "llamaindex", "llm_model", default="gpt-3.5-turbo")
    LLAMAINDEX_INDEX_TYPE: str = get_config("frameworks", "llamaindex", "index_type", default="vector_store")
    LLAMAINDEX_USE_KNOWLEDGE_GRAPH: bool = get_config("frameworks", "llamaindex", "use_knowledge_graph", default=False)
    LLAMAINDEX_DEFAULT_STORE: str = get_config("frameworks", "llamaindex", "default_store", default="elasticsearch")
    
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
    
    # 敏感词过滤配置
    SENSITIVE_WORD_FILTER_TYPE: str = get_config("sensitive_word", "filter_type", default="local")
    SENSITIVE_WORD_FILTER_RESPONSE: str = get_config("sensitive_word", "default_response", 
                                                default="很抱歉，您的消息包含敏感内容，请调整后重新发送。")
    SENSITIVE_WORD_DICT_PATH: str = get_config("sensitive_word", "dict_path", default="")
    SENSITIVE_WORD_API_URL: str = get_config("sensitive_word", "api_url", default="")
    SENSITIVE_WORD_API_KEY: str = get_config("sensitive_word", "api_key", default="")
    SENSITIVE_WORD_API_TIMEOUT: float = get_config("sensitive_word", "api_timeout", default=3.0)
    SENSITIVE_WORD_CACHE_ENABLED: bool = get_config("sensitive_word", "cache_enabled", default=True)
    SENSITIVE_WORD_CACHE_TTL: int = get_config("sensitive_word", "cache_ttl", default=3600)
    
    # SearxNG 搜索引擎配置
    class SearxNGSettings(BaseSettings):
        """SearxNG搜索引擎设置"""
        enabled: bool = Field(True, env="SEARXNG_ENABLED")
        auto_deploy: bool = Field(True, env="SEARXNG_AUTO_DEPLOY")
        host: str = Field("localhost", env="SEARXNG_HOST") 
        port: int = Field(8888, env="SEARXNG_PORT")
        default_engines: List[str] = Field(["google", "bing", "baidu", "wikipedia"], env="SEARXNG_DEFAULT_ENGINES")
        default_language: str = Field("zh-CN", env="SEARXNG_DEFAULT_LANGUAGE")
        max_results: int = Field(10, env="SEARXNG_MAX_RESULTS")
        timeout: float = Field(10.0, env="SEARXNG_TIMEOUT")
        
        class Config:
            env_prefix = "SEARXNG_"
    
    # 组件配置
    llamaindex: LlamaIndexSettings = LlamaIndexSettings()
    haystack: HaystackSettings = HaystackSettings()
    agno: AgnoSettings = AgnoSettings()
    searxng: SearxNGSettings = SearxNGSettings()
    
    # InfluxDB指标统计配置
    class MetricsSettings(BaseSettings):
        """指标统计设置"""
        enabled: bool = Field(get_config("metrics", "enabled", default=False), env="METRICS_ENABLED")
        provider: str = Field(get_config("metrics", "provider", default="influxdb"), env="METRICS_PROVIDER")
        token_statistics: bool = Field(get_config("metrics", "token_statistics", default=True), env="METRICS_TOKEN_STATISTICS")
        
        # InfluxDB设置
        influxdb_url: str = Field(get_config("metrics", "influxdb", "url", default="http://localhost:8086"), env="INFLUXDB_URL")
        influxdb_token: str = Field(get_config("metrics", "influxdb", "token", default=""), env="INFLUXDB_TOKEN")
        influxdb_org: str = Field(get_config("metrics", "influxdb", "org", default="knowledge_qa_org"), env="INFLUXDB_ORG")
        influxdb_bucket: str = Field(get_config("metrics", "influxdb", "bucket", default="llm_metrics"), env="INFLUXDB_BUCKET")
        influxdb_batch_size: int = Field(get_config("metrics", "influxdb", "batch_size", default=50), env="INFLUXDB_BATCH_SIZE")
        influxdb_flush_interval: int = Field(get_config("metrics", "influxdb", "flush_interval", default=10), env="INFLUXDB_FLUSH_INTERVAL")
        
        class Config:
            env_prefix = "METRICS_"
    
    metrics: MetricsSettings = MetricsSettings()

    # 遗留路径（保留以兼容）
    VECTOR_STORE_PATH: str = get_config("paths", "vector_store", default="./vector_store")
    KNOWLEDGE_BASE_PATH: str = get_config("paths", "knowledge_base", default="./knowledge_base")


settings = Settings()
