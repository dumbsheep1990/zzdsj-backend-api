from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Dict, Any, Optional
import os

class Settings:
    # 服务信息
    PROJECT_NAME: str = os.getenv("SERVICE_NAME", "智政知识库问答系统")
    API_V1_STR: str = "/api"
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "knowledge-qa-backend")
    SERVICE_IP: str = os.getenv("SERVICE_IP", "127.0.0.1")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8000"))
    
    # 数据库
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/knowledge_qa")
    
    # CORS跨域
    CORS_ORIGINS: List[str] = ["http://localhost", "http://localhost:3000", "http://localhost:8080", "*"]
    
    # 认证与安全配置
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "23f0767704249cd7be7181a0dad23c74e0739c98ce54d7140fc2e94dfa584fb0")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # LLM配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gpt-4")
    
    # 模型提供商配置
    # OpenAI配置
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    
    # 语音功能配置
    VOICE_ENABLED: bool = os.getenv("VOICE_ENABLED", "false").lower() == "true"
    
    # 语音转文本(STT)配置
    STT_MODEL_NAME: str = os.getenv("STT_MODEL_NAME", "xunfei-stt")
    STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "zh-CN")
    STT_SAMPLING_RATE: int = int(os.getenv("STT_SAMPLING_RATE", "16000"))
    
    # 文本转语音(TTS)配置
    TTS_MODEL_NAME: str = os.getenv("TTS_MODEL_NAME", "xunfei-tts")
    TTS_VOICE: str = os.getenv("TTS_VOICE", "xiaoyan")
    TTS_SPEED: float = float(os.getenv("TTS_SPEED", "50"))
    TTS_AUDIO_FORMAT: str = os.getenv("TTS_AUDIO_FORMAT", "mp3")
    
    # 讯飞语音服务配置
    XUNFEI_APP_ID: str = os.getenv("XUNFEI_APP_ID", "")
    XUNFEI_API_KEY: str = os.getenv("XUNFEI_API_KEY", "")
    XUNFEI_API_SECRET: str = os.getenv("XUNFEI_API_SECRET", "")
    
    # MiniMax语音服务配置
    MINIMAX_API_KEY: str = os.getenv("MINIMAX_API_KEY", "")
    MINIMAX_GROUP_ID: str = os.getenv("MINIMAX_GROUP_ID", "")
    
    # 阿里云语音服务配置
    ALIYUN_ACCESS_KEY_ID: str = os.getenv("ALIYUN_ACCESS_KEY_ID", "")
    ALIYUN_ACCESS_KEY_SECRET: str = os.getenv("ALIYUN_ACCESS_KEY_SECRET", "")
    ALIYUN_SPEECH_APPKEY: str = os.getenv("ALIYUN_SPEECH_APPKEY", "")
    OPENAI_ORGANIZATION: str = os.getenv("OPENAI_ORGANIZATION", "")
    
    # 智谱AI配置
    ZHIPU_API_KEY: str = os.getenv("ZHIPU_API_KEY", "")
    
    # DeepSeek配置
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_API_BASE: str = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
    
    # Ollama配置
    OLLAMA_API_BASE: str = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    
    # VLLM配置
    VLLM_API_BASE: str = os.getenv("VLLM_API_BASE", "http://localhost:8000")
    
    # 通义千问配置
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    
    # Anthropic配置
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_API_BASE: str = os.getenv("ANTHROPIC_API_BASE", "https://api.anthropic.com")
    
    # TogetherAI配置
    TOGETHER_API_KEY: str = os.getenv("TOGETHER_API_KEY", "")
    TOGETHER_API_BASE: str = os.getenv("TOGETHER_API_BASE", "https://api.together.xyz/v1")
    
    # 千问API配置
    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "")
    QWEN_API_BASE: str = os.getenv("QWEN_API_BASE", "https://dashscope.aliyuncs.com/api/v1")
    
    # 百度文心一言配置
    BAIDU_API_KEY: str = os.getenv("BAIDU_API_KEY", "")
    BAIDU_SECRET_KEY: str = os.getenv("BAIDU_SECRET_KEY", "")
    BAIDU_API_BASE: str = os.getenv("BAIDU_API_BASE", "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop")
    
    # 月之暗面配置
    MOONSHOT_API_KEY: str = os.getenv("MOONSHOT_API_KEY", "")
    MOONSHOT_API_BASE: str = os.getenv("MOONSHOT_API_BASE", "https://api.moonshot.cn/v1")
    
    # 智谱GLM配置
    GLM_API_KEY: str = os.getenv("GLM_API_KEY", "")
    GLM_API_BASE: str = os.getenv("GLM_API_BASE", "https://open.bigmodel.cn/api/paas/v4")
    
    # MiniMax配置
    MINIMAX_API_KEY: str = os.getenv("MINIMAX_API_KEY", "")
    MINIMAX_GROUP_ID: str = os.getenv("MINIMAX_GROUP_ID", "")
    MINIMAX_API_BASE: str = os.getenv("MINIMAX_API_BASE", "https://api.minimax.chat/v1")
    
    # 百川配置
    BAICHUAN_API_KEY: str = os.getenv("BAICHUAN_API_KEY", "")
    BAICHUAN_SECRET_KEY: str = os.getenv("BAICHUAN_SECRET_KEY", "")
    BAICHUAN_API_BASE: str = os.getenv("BAICHUAN_API_BASE", "https://api.baichuan-ai.com/v1")
    
    # 向量存储 - Milvus配置
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: str = os.getenv("MILVUS_PORT", "19530")
    MILVUS_COLLECTION: str = os.getenv("MILVUS_COLLECTION", "document_vectors")
    
    # 向量存储 - Elasticsearch配置
    ELASTICSEARCH_URL: str = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    ELASTICSEARCH_USERNAME: str = os.getenv("ELASTICSEARCH_USERNAME", "")
    ELASTICSEARCH_PASSWORD: str = os.getenv("ELASTICSEARCH_PASSWORD", "")
    ELASTICSEARCH_CLOUD_ID: str = os.getenv("ELASTICSEARCH_CLOUD_ID", "")
    ELASTICSEARCH_API_KEY: str = os.getenv("ELASTICSEARCH_API_KEY", "")
    ELASTICSEARCH_INDEX: str = os.getenv("ELASTICSEARCH_INDEX", "document_index")
    ELASTICSEARCH_DEFAULT_ANALYZER: str = os.getenv("ELASTICSEARCH_DEFAULT_ANALYZER", "standard")
    ELASTICSEARCH_EMBEDDING_DIM: int = int(os.getenv("ELASTICSEARCH_EMBEDDING_DIM", "1536"))
    ELASTICSEARCH_SIMILARITY: str = os.getenv("ELASTICSEARCH_SIMILARITY", "cosine")
    ELASTICSEARCH_HYBRID_SEARCH: bool = os.getenv("ELASTICSEARCH_HYBRID_SEARCH", "true").lower() == "true"
    ELASTICSEARCH_HYBRID_WEIGHT: float = float(os.getenv("ELASTICSEARCH_HYBRID_WEIGHT", "0.5"))
    
    # 文档处理配置
    DOCUMENT_SPLITTER_TYPE: str = os.getenv("DOCUMENT_SPLITTER_TYPE", "sentence")
    DOCUMENT_CHUNK_SIZE: int = int(os.getenv("DOCUMENT_CHUNK_SIZE", "1000"))
    DOCUMENT_CHUNK_OVERLAP: int = int(os.getenv("DOCUMENT_CHUNK_OVERLAP", "200"))
    DOCUMENT_PROCESSING_CONCURRENCY: int = int(os.getenv("DOCUMENT_PROCESSING_CONCURRENCY", "4"))
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "16"))
    DOCUMENT_PROCESSING_TIMEOUT: int = int(os.getenv("DOCUMENT_PROCESSING_TIMEOUT", "3600"))
    DOCUMENT_SEMANTIC_CHUNK_STRATEGY: str = os.getenv("DOCUMENT_SEMANTIC_CHUNK_STRATEGY", "auto")
    DOCUMENT_USE_METADATA_EXTRACTION: bool = os.getenv("DOCUMENT_USE_METADATA_EXTRACTION", "true").lower() == "true"
    
    # Redis配置
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    
    # MinIO配置
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "knowledge-docs")
    
    # RabbitMQ配置
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    
    # Nacos配置
    NACOS_SERVER_ADDRESSES: str = os.getenv("NACOS_SERVER_ADDRESSES", "127.0.0.1:8848")
    NACOS_NAMESPACE: str = os.getenv("NACOS_NAMESPACE", "public")
    NACOS_GROUP: str = os.getenv("NACOS_GROUP", "DEFAULT_GROUP")
    
    # Celery配置
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    # 框架配置
    # LlamaIndex配置（替代LangChain）
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    CHAT_MODEL: str = os.getenv("CHAT_MODEL", "gpt-3.5-turbo")
    MEMORY_TYPE: str = os.getenv("MEMORY_TYPE", "conversation_buffer")
    MEMORY_K: int = int(os.getenv("MEMORY_K", "5"))
    
    # 保留LangChain配置（为了兼容性，但已不再使用）
    LANGCHAIN_EMBEDDING_MODEL: str = EMBEDDING_MODEL
    LANGCHAIN_CHAT_MODEL: str = CHAT_MODEL
    LANGCHAIN_MEMORY_TYPE: str = MEMORY_TYPE
    LANGCHAIN_MEMORY_K: int = MEMORY_K
    LANGCHAIN_USE_LANGSMITH: bool = False
    LANGCHAIN_LANGSMITH_API_KEY: str = ""
    LANGCHAIN_LANGSMITH_PROJECT: str = "knowledge-qa"
    
    # Haystack配置
    HAYSTACK_READER_MODEL: str = os.getenv("HAYSTACK_READER_MODEL", "deepset/roberta-base-squad2")
    HAYSTACK_RETRIEVER_TYPE: str = os.getenv("HAYSTACK_RETRIEVER_TYPE", "embedding")
    HAYSTACK_USE_BM25: bool = os.getenv("HAYSTACK_USE_BM25", "true").lower() == "true"
    HAYSTACK_TOP_K: int = int(os.getenv("HAYSTACK_TOP_K", "5"))
    HAYSTACK_EMBEDDING_MODEL: str = os.getenv("HAYSTACK_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    HAYSTACK_RERANK_DOCUMENTS: bool = os.getenv("HAYSTACK_RERANK_DOCUMENTS", "false").lower() == "true"
    HAYSTACK_RERANKER_MODEL: str = os.getenv("HAYSTACK_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    
    # LlamaIndex配置
    LLAMAINDEX_CHUNK_SIZE: int = int(os.getenv("LLAMAINDEX_CHUNK_SIZE", str(DOCUMENT_CHUNK_SIZE)))
    LLAMAINDEX_CHUNK_OVERLAP: int = int(os.getenv("LLAMAINDEX_CHUNK_OVERLAP", str(DOCUMENT_CHUNK_OVERLAP)))
    LLAMAINDEX_EMBEDDING_MODEL: str = os.getenv("LLAMAINDEX_EMBEDDING_MODEL", "text-embedding-ada-002")
    LLAMAINDEX_LLM_MODEL: str = os.getenv("LLAMAINDEX_LLM_MODEL", "gpt-3.5-turbo")
    LLAMAINDEX_INDEX_TYPE: str = os.getenv("LLAMAINDEX_INDEX_TYPE", "vector_store")
    LLAMAINDEX_USE_KNOWLEDGE_GRAPH: bool = os.getenv("LLAMAINDEX_USE_KNOWLEDGE_GRAPH", "false").lower() == "true"
    LLAMAINDEX_DEFAULT_STORE: str = os.getenv("LLAMAINDEX_DEFAULT_STORE", "elasticsearch")
    
    # Agno配置
    AGNO_AGENT_TYPE: str = os.getenv("AGNO_AGENT_TYPE", "conversational")
    AGNO_MODEL: str = os.getenv("AGNO_MODEL", "gpt-3.5-turbo")
    AGNO_MAX_ITERATIONS: int = int(os.getenv("AGNO_MAX_ITERATIONS", "5"))
    AGNO_MEMORY_TYPE: str = os.getenv("AGNO_MEMORY_TYPE", "conversation_buffer")
    AGNO_MEMORY_K: int = int(os.getenv("AGNO_MEMORY_K", "5"))
    
    # 框架集成配置
    # 统一入口 - LlamaIndex（替代LangChain）
    FRAMEWORK_ENTRY_POINT: str = os.getenv("FRAMEWORK_ENTRY_POINT", "llamaindex")
    
    # QA助手 - Agno与检索集成
    QA_ASSISTANT_FRAMEWORK: str = os.getenv("QA_ASSISTANT_FRAMEWORK", "agno")
    QA_RETRIEVER_FRAMEWORK: str = os.getenv("QA_RETRIEVER_FRAMEWORK", "haystack")
    QA_INDEXER_FRAMEWORK: str = os.getenv("QA_INDEXER_FRAMEWORK", "llamaindex")
    
    # QA管理 - LlamaIndex与Agno协作（替代LangChain）
    QA_MANAGEMENT_CONVERSATION_FRAMEWORK: str = os.getenv("QA_MANAGEMENT_CONVERSATION_FRAMEWORK", "llamaindex")
    QA_MANAGEMENT_MEMORY_FRAMEWORK: str = os.getenv("QA_MANAGEMENT_MEMORY_FRAMEWORK", "agno")
    QA_MANAGEMENT_API_FRAMEWORK: str = os.getenv("QA_MANAGEMENT_API_FRAMEWORK", "llamaindex")
    
    # 知识库管理 - LlamaIndex与Haystack分工
    KNOWLEDGE_MANAGEMENT_INDEXING_FRAMEWORK: str = os.getenv("KNOWLEDGE_MANAGEMENT_INDEXING_FRAMEWORK", "llamaindex")
    KNOWLEDGE_MANAGEMENT_SEARCH_FRAMEWORK: str = os.getenv("KNOWLEDGE_MANAGEMENT_SEARCH_FRAMEWORK", "haystack")
    
    # 敏感词过滤配置
    SENSITIVE_WORD_FILTER_TYPE: str = os.getenv("SENSITIVE_WORD_FILTER_TYPE", "local")
    SENSITIVE_WORD_FILTER_RESPONSE: str = os.getenv("SENSITIVE_WORD_FILTER_RESPONSE", "很抱歉，您的消息包含敏感内容，请调整后重新发送。")
    SENSITIVE_WORD_DICT_PATH: str = os.getenv("SENSITIVE_WORD_DICT_PATH", "")
    SENSITIVE_WORD_API_URL: str = os.getenv("SENSITIVE_WORD_API_URL", "")
    SENSITIVE_WORD_API_KEY: str = os.getenv("SENSITIVE_WORD_API_KEY", "")
    SENSITIVE_WORD_API_TIMEOUT: float = float(os.getenv("SENSITIVE_WORD_API_TIMEOUT", "3.0"))
    SENSITIVE_WORD_CACHE_ENABLED: bool = os.getenv("SENSITIVE_WORD_CACHE_ENABLED", "true").lower() == "true"
    SENSITIVE_WORD_CACHE_TTL: int = int(os.getenv("SENSITIVE_WORD_CACHE_TTL", "3600"))
    
    # 遗留路径（保留以兼容）
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "./vector_store")
    KNOWLEDGE_BASE_PATH: str = os.getenv("KNOWLEDGE_BASE_PATH", "./knowledge_base")
    
    # LightRAG配置
    LIGHTRAG_ENABLED: bool = os.getenv("LIGHTRAG_ENABLED", "false").lower() == "true"
    LIGHTRAG_BASE_DIR: str = os.getenv("LIGHTRAG_BASE_DIR", "./data/lightrag")
    LIGHTRAG_DEFAULT_EMBEDDING_DIM: int = int(os.getenv("LIGHTRAG_DEFAULT_EMBEDDING_DIM", "1536"))
    LIGHTRAG_MAX_TOKEN_SIZE: int = int(os.getenv("LIGHTRAG_MAX_TOKEN_SIZE", "8192"))
    
    # LightRAG存储配置
    LIGHTRAG_GRAPH_DB_TYPE: str = os.getenv("LIGHTRAG_GRAPH_DB_TYPE", "file")  # 可选: file, postgres, redis
    LIGHTRAG_PG_HOST: str = os.getenv("LIGHTRAG_PG_HOST", "lightrag-postgres")
    LIGHTRAG_PG_PORT: int = int(os.getenv("LIGHTRAG_PG_PORT", "5432"))
    LIGHTRAG_PG_USER: str = os.getenv("LIGHTRAG_PG_USER", "postgres")
    LIGHTRAG_PG_PASSWORD: str = os.getenv("LIGHTRAG_PG_PASSWORD", "password")
    LIGHTRAG_PG_DB: str = os.getenv("LIGHTRAG_PG_DB", "lightrag")
    
    # LightRAG和Redis存储配置
    LIGHTRAG_REDIS_HOST: str = os.getenv("LIGHTRAG_REDIS_HOST", REDIS_HOST)
    LIGHTRAG_REDIS_PORT: int = int(os.getenv("LIGHTRAG_REDIS_PORT", str(REDIS_PORT)))
    LIGHTRAG_REDIS_DB: int = int(os.getenv("LIGHTRAG_REDIS_DB", "1"))
    LIGHTRAG_REDIS_PASSWORD: str = os.getenv("LIGHTRAG_REDIS_PASSWORD", REDIS_PASSWORD)
    
    # LightRAG知识图谱高级配置
    LIGHTRAG_USE_SEMANTIC_CHUNKING: bool = os.getenv("LIGHTRAG_USE_SEMANTIC_CHUNKING", "false").lower() == "true"
    LIGHTRAG_USE_KNOWLEDGE_GRAPH: bool = os.getenv("LIGHTRAG_USE_KNOWLEDGE_GRAPH", "false").lower() == "true"
    LIGHTRAG_KG_RELATION_THRESHOLD: float = float(os.getenv("LIGHTRAG_KG_RELATION_THRESHOLD", "0.7"))
    LIGHTRAG_MAX_WORKERS: int = int(os.getenv("LIGHTRAG_MAX_WORKERS", "4"))

# 创建设置实例
settings = Settings()
