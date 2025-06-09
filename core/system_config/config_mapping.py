"""
配置项映射 - 定义环境变量与配置管理系统的映射关系
确保所有配置都能正确地在系统中管理和访问
"""

from typing import Dict, Any, List


class ConfigMapping:
    """配置映射管理器"""
    
    @staticmethod
    def get_env_to_config_mapping() -> Dict[str, Dict[str, Any]]:
        """获取环境变量到配置项的映射"""
        return {
            # ===============================================================================
            # 系统基础配置
            # ===============================================================================
            
            # 服务配置
            "SERVICE_NAME": {
                "config_key": "service.name",
                "category": "系统配置",
                "value_type": "string",
                "description": "服务名称",
                "default_value": "knowledge-qa-backend",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"required": True, "min_length": 1, "max_length": 100}
            },
            "SERVICE_IP": {
                "config_key": "service.ip", 
                "category": "系统配置",
                "value_type": "string",
                "description": "服务IP地址",
                "default_value": "127.0.0.1",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"required": True}
            },
            "SERVICE_PORT": {
                "config_key": "service.port",
                "category": "系统配置",
                "value_type": "number",
                "description": "服务端口",
                "default_value": "8000",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"required": True, "min_value": 1, "max_value": 65535}
            },
            "APP_ENV": {
                "config_key": "app.environment",
                "category": "系统配置",
                "value_type": "string",
                "description": "应用环境",
                "default_value": "development",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"required": True, "enum": ["development", "testing", "production"]}
            },
            "DEBUG_MODE": {
                "config_key": "app.debug_mode",
                "category": "系统配置",
                "value_type": "boolean",
                "description": "调试模式",
                "default_value": "False",
                "is_system": True,
                "is_sensitive": False
            },
            
            # 域名和网络配置
            "BASE_URL": {
                "config_key": "app.base_url",
                "category": "系统配置",
                "value_type": "string",
                "description": "系统基础URL",
                "default_value": "http://localhost:8000",
                "is_system": True,
                "is_sensitive": False
            },
            "ALLOWED_HOSTS": {
                "config_key": "app.allowed_hosts",
                "category": "系统配置",
                "value_type": "json",
                "description": "允许访问的域名列表",
                "default_value": '["localhost", "127.0.0.1"]',
                "is_system": True,
                "is_sensitive": False
            },
            
            # CORS配置
            "CORS_ENABLED": {
                "config_key": "cors.enabled",
                "category": "系统配置",
                "value_type": "boolean",
                "description": "是否启用CORS",
                "default_value": "True",
                "is_system": True,
                "is_sensitive": False
            },
            "CORS_ORIGINS": {
                "config_key": "cors.origins",
                "category": "系统配置",
                "value_type": "json",
                "description": "允许的跨域来源",
                "default_value": '["http://localhost:3000", "http://127.0.0.1:3000"]',
                "is_system": True,
                "is_sensitive": False
            },
            "CORS_ALLOW_CREDENTIALS": {
                "config_key": "cors.allow_credentials",
                "category": "系统配置",
                "value_type": "boolean",
                "description": "是否允许携带认证信息",
                "default_value": "True",
                "is_system": True,
                "is_sensitive": False
            },
            
            # 请求限制配置
            "REQUEST_LIMITING_ENABLED": {
                "config_key": "request.limiting_enabled",
                "category": "系统配置",
                "value_type": "boolean",
                "description": "是否启用请求限制",
                "default_value": "True",
                "is_system": True,
                "is_sensitive": False
            },
            "REQUEST_RATE_LIMIT": {
                "config_key": "request.rate_limit",
                "category": "系统配置",
                "value_type": "string",
                "description": "每分钟允许的请求数",
                "default_value": "60/minute",
                "is_system": True,
                "is_sensitive": False
            },
            
            # ===============================================================================
            # 安全配置
            # ===============================================================================
            
            "JWT_SECRET_KEY": {
                "config_key": "security.jwt_secret_key",
                "category": "安全配置",
                "value_type": "string",
                "description": "JWT密钥",
                "default_value": "",  # 系统生成
                "is_system": True,
                "is_sensitive": True,
                "validation_rules": {"required": True, "min_length": 32}
            },
            "JWT_ALGORITHM": {
                "config_key": "security.jwt_algorithm",
                "category": "安全配置",
                "value_type": "string",
                "description": "JWT算法",
                "default_value": "HS256",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"enum": ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]}
            },
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": {
                "config_key": "security.jwt_access_token_expire_minutes",
                "category": "安全配置",
                "value_type": "number",
                "description": "JWT访问令牌过期时间（分钟）",
                "default_value": "30",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"min_value": 1, "max_value": 43200}
            },
            "JWT_REFRESH_TOKEN_EXPIRE_DAYS": {
                "config_key": "security.jwt_refresh_token_expire_days",
                "category": "安全配置",
                "value_type": "number",
                "description": "JWT刷新令牌过期时间（天）",
                "default_value": "7",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"min_value": 1, "max_value": 365}
            },
            "ENCRYPTION_KEY": {
                "config_key": "security.encryption_key",
                "category": "安全配置",
                "value_type": "string",
                "description": "配置数据加密密钥",
                "default_value": "",  # 系统生成
                "is_system": True,
                "is_sensitive": True,
                "validation_rules": {"required": True, "min_length": 32}
            },
            
            # ===============================================================================
            # 数据库配置
            # ===============================================================================
            
            "DATABASE_URL": {
                "config_key": "database.url",
                "category": "数据库配置",
                "value_type": "string",
                "description": "数据库连接URL",
                "default_value": "postgresql://postgres:postgres@localhost:5432/knowledge_qa",
                "is_system": True,
                "is_sensitive": True,
                "validation_rules": {"required": True, "pattern": r"^postgresql://.*"}
            },
            "POSTGRES_HOST": {
                "config_key": "database.postgres.host",
                "category": "数据库配置",
                "value_type": "string",
                "description": "PostgreSQL主机地址",
                "default_value": "localhost",
                "is_system": True,
                "is_sensitive": False
            },
            "POSTGRES_PORT": {
                "config_key": "database.postgres.port",
                "category": "数据库配置",
                "value_type": "number",
                "description": "PostgreSQL端口",
                "default_value": "5432",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"min_value": 1, "max_value": 65535}
            },
            "POSTGRES_USER": {
                "config_key": "database.postgres.user",
                "category": "数据库配置",
                "value_type": "string",
                "description": "PostgreSQL用户名",
                "default_value": "postgres",
                "is_system": True,
                "is_sensitive": False
            },
            "POSTGRES_PASSWORD": {
                "config_key": "database.postgres.password",
                "category": "数据库配置",
                "value_type": "string",
                "description": "PostgreSQL密码",
                "default_value": "postgres",
                "is_system": True,
                "is_sensitive": True
            },
            "POSTGRES_DB": {
                "config_key": "database.postgres.database",
                "category": "数据库配置",
                "value_type": "string",
                "description": "PostgreSQL数据库名",
                "default_value": "knowledge_qa",
                "is_system": True,
                "is_sensitive": False
            },
            
            # ===============================================================================
            # 服务配置
            # ===============================================================================
            
            # Redis配置
            "REDIS_HOST": {
                "config_key": "redis.host",
                "category": "服务配置",
                "value_type": "string",
                "description": "Redis主机地址",
                "default_value": "localhost",
                "is_system": True,
                "is_sensitive": False
            },
            "REDIS_PORT": {
                "config_key": "redis.port",
                "category": "服务配置",
                "value_type": "number",
                "description": "Redis端口",
                "default_value": "6379",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"min_value": 1, "max_value": 65535}
            },
            "REDIS_DB": {
                "config_key": "redis.db",
                "category": "服务配置",
                "value_type": "number",
                "description": "Redis数据库索引",
                "default_value": "0",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"min_value": 0, "max_value": 15}
            },
            "REDIS_PASSWORD": {
                "config_key": "redis.password",
                "category": "服务配置",
                "value_type": "string",
                "description": "Redis密码",
                "default_value": "",
                "is_system": True,
                "is_sensitive": True
            },
            
            # MinIO配置
            "MINIO_ENDPOINT": {
                "config_key": "storage.minio.endpoint",
                "category": "服务配置",
                "value_type": "string",
                "description": "MinIO服务端点",
                "default_value": "localhost:9000",
                "is_system": True,
                "is_sensitive": False
            },
            "MINIO_ACCESS_KEY": {
                "config_key": "storage.minio.access_key",
                "category": "服务配置",
                "value_type": "string",
                "description": "MinIO访问密钥",
                "default_value": "minioadmin",
                "is_system": True,
                "is_sensitive": True
            },
            "MINIO_SECRET_KEY": {
                "config_key": "storage.minio.secret_key",
                "category": "服务配置",
                "value_type": "string",
                "description": "MinIO秘密密钥",
                "default_value": "minioadmin",
                "is_system": True,
                "is_sensitive": True
            },
            "MINIO_SECURE": {
                "config_key": "storage.minio.secure",
                "category": "服务配置",
                "value_type": "boolean",
                "description": "MinIO是否使用HTTPS",
                "default_value": "False",
                "is_system": True,
                "is_sensitive": False
            },
            "MINIO_BUCKET": {
                "config_key": "storage.minio.bucket",
                "category": "服务配置",
                "value_type": "string",
                "description": "MinIO默认存储桶",
                "default_value": "knowledge-docs",
                "is_system": True,
                "is_sensitive": False
            },
            
            # Milvus配置
            "MILVUS_HOST": {
                "config_key": "vector_store.milvus.host",
                "category": "服务配置",
                "value_type": "string",
                "description": "Milvus主机地址",
                "default_value": "localhost",
                "is_system": True,
                "is_sensitive": False
            },
            "MILVUS_PORT": {
                "config_key": "vector_store.milvus.port",
                "category": "服务配置",
                "value_type": "number",
                "description": "Milvus端口",
                "default_value": "19530",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"min_value": 1, "max_value": 65535}
            },
            "MILVUS_COLLECTION": {
                "config_key": "vector_store.milvus.collection",
                "category": "服务配置",
                "value_type": "string",
                "description": "Milvus集合名",
                "default_value": "document_vectors",
                "is_system": True,
                "is_sensitive": False
            },
            
            # Elasticsearch配置
            "ELASTICSEARCH_URL": {
                "config_key": "elasticsearch.url",
                "category": "服务配置",
                "value_type": "string",
                "description": "Elasticsearch URL",
                "default_value": "http://localhost:9200",
                "is_system": True,
                "is_sensitive": False
            },
            "ELASTICSEARCH_USERNAME": {
                "config_key": "elasticsearch.username",
                "category": "服务配置",
                "value_type": "string",
                "description": "Elasticsearch用户名",
                "default_value": "",
                "is_system": True,
                "is_sensitive": False
            },
            "ELASTICSEARCH_PASSWORD": {
                "config_key": "elasticsearch.password",
                "category": "服务配置",
                "value_type": "string",
                "description": "Elasticsearch密码",
                "default_value": "",
                "is_system": True,
                "is_sensitive": True
            },
            "ELASTICSEARCH_INDEX": {
                "config_key": "elasticsearch.index",
                "category": "服务配置",
                "value_type": "string",
                "description": "Elasticsearch索引名",
                "default_value": "document_index",
                "is_system": True,
                "is_sensitive": False
            },
            
            # RabbitMQ配置
            "RABBITMQ_HOST": {
                "config_key": "rabbitmq.host",
                "category": "服务配置",
                "value_type": "string",
                "description": "RabbitMQ主机地址",
                "default_value": "localhost",
                "is_system": True,
                "is_sensitive": False
            },
            "RABBITMQ_PORT": {
                "config_key": "rabbitmq.port",
                "category": "服务配置",
                "value_type": "number",
                "description": "RabbitMQ端口",
                "default_value": "5672",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"min_value": 1, "max_value": 65535}
            },
            "RABBITMQ_USER": {
                "config_key": "rabbitmq.user",
                "category": "服务配置",
                "value_type": "string",
                "description": "RabbitMQ用户名",
                "default_value": "guest",
                "is_system": True,
                "is_sensitive": False
            },
            "RABBITMQ_PASSWORD": {
                "config_key": "rabbitmq.password",
                "category": "服务配置",
                "value_type": "string",
                "description": "RabbitMQ密码",
                "default_value": "guest",
                "is_system": True,
                "is_sensitive": True
            },
            
            # Nacos配置
            "NACOS_SERVER_ADDRESSES": {
                "config_key": "nacos.server_addresses",
                "category": "服务配置",
                "value_type": "string",
                "description": "Nacos服务器地址",
                "default_value": "127.0.0.1:8848",
                "is_system": True,
                "is_sensitive": False
            },
            "NACOS_NAMESPACE": {
                "config_key": "nacos.namespace",
                "category": "服务配置",
                "value_type": "string",
                "description": "Nacos命名空间",
                "default_value": "public",
                "is_system": True,
                "is_sensitive": False
            },
            "NACOS_GROUP": {
                "config_key": "nacos.group",
                "category": "服务配置",
                "value_type": "string",
                "description": "Nacos分组",
                "default_value": "DEFAULT_GROUP",
                "is_system": True,
                "is_sensitive": False
            },
            
            # InfluxDB配置
            "INFLUXDB_URL": {
                "config_key": "influxdb.url",
                "category": "服务配置",
                "value_type": "string",
                "description": "InfluxDB URL",
                "default_value": "http://localhost:8086",
                "is_system": True,
                "is_sensitive": False
            },
            "INFLUXDB_TOKEN": {
                "config_key": "influxdb.token",
                "category": "服务配置",
                "value_type": "string",
                "description": "InfluxDB访问令牌",
                "default_value": "",
                "is_system": True,
                "is_sensitive": True
            },
            "INFLUXDB_ORG": {
                "config_key": "influxdb.org",
                "category": "服务配置",
                "value_type": "string",
                "description": "InfluxDB组织",
                "default_value": "knowledge_qa_org",
                "is_system": True,
                "is_sensitive": False
            },
            "INFLUXDB_BUCKET": {
                "config_key": "influxdb.bucket",
                "category": "服务配置",
                "value_type": "string",
                "description": "InfluxDB存储桶",
                "default_value": "llm_metrics",
                "is_system": True,
                "is_sensitive": False
            },
            
            # ===============================================================================
            # 模型配置
            # ===============================================================================
            
            # 基础LLM配置
            "DEFAULT_MODEL": {
                "config_key": "llm.default_model",
                "category": "模型配置",
                "value_type": "string",
                "description": "默认LLM模型",
<<<<<<< HEAD
                "default_value": "gpt-4",
                "is_system": False,
=======
                "default_value": "gpt-3.5-turbo",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"required": True, "min_length": 1}
            },
            "DEFAULT_MODEL_PROVIDER": {
                "config_key": "llm.default_provider",
                "category": "模型配置",
                "value_type": "string",
                "description": "默认模型提供商",
                "default_value": "openai",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"required": True, "enum": ["openai", "zhipu", "anthropic", "ollama", "local"]}
            },
            "DEFAULT_MODEL_DESCRIPTION": {
                "config_key": "llm.default_model.description",
                "category": "模型配置",
                "value_type": "string",
                "description": "默认模型描述信息",
                "default_value": "系统内置工具使用的默认LLM模型",
                "is_system": True,
>>>>>>> origin/feature_20250604
                "is_sensitive": False
            },
            "EMBEDDING_MODEL": {
                "config_key": "llm.embedding_model",
                "category": "模型配置",
                "value_type": "string",
                "description": "默认嵌入模型",
                "default_value": "text-embedding-ada-002",
                "is_system": False,
                "is_sensitive": False
            },
            "CHAT_MODEL": {
                "config_key": "llm.chat_model",
                "category": "模型配置",
                "value_type": "string",
                "description": "默认聊天模型",
                "default_value": "gpt-3.5-turbo",
                "is_system": False,
                "is_sensitive": False
            },
            
            # OpenAI配置
            "OPENAI_API_KEY": {
                "config_key": "llm.openai.api_key",
                "category": "模型配置",
                "value_type": "string",
                "description": "OpenAI API密钥",
                "default_value": "",
                "is_system": False,
                "is_sensitive": True
            },
            "OPENAI_API_BASE": {
                "config_key": "llm.openai.api_base",
                "category": "模型配置",
                "value_type": "string",
                "description": "OpenAI API基础URL",
                "default_value": "https://api.openai.com/v1",
                "is_system": False,
                "is_sensitive": False
            },
            "OPENAI_ORGANIZATION": {
                "config_key": "llm.openai.organization",
                "category": "模型配置",
                "value_type": "string",
                "description": "OpenAI组织ID",
                "default_value": "",
                "is_system": False,
                "is_sensitive": True
            },
            
            # 其他模型提供商配置
            "ZHIPU_API_KEY": {
                "config_key": "llm.zhipu.api_key",
                "category": "模型配置",
                "value_type": "string",
                "description": "智谱AI API密钥",
                "default_value": "",
                "is_system": False,
                "is_sensitive": True
            },
            "BAIDU_API_KEY": {
                "config_key": "llm.baidu.api_key",
                "category": "模型配置",
                "value_type": "string",
                "description": "百度API密钥",
                "default_value": "",
                "is_system": False,
                "is_sensitive": True
            },
            "BAIDU_SECRET_KEY": {
                "config_key": "llm.baidu.secret_key",
                "category": "模型配置",
                "value_type": "string",
                "description": "百度API密钥",
                "default_value": "",
                "is_system": False,
                "is_sensitive": True
            },
            
            # ===============================================================================
            # 功能配置
            # ===============================================================================
            
            # 文档处理配置
            "DOCUMENT_CHUNK_SIZE": {
                "config_key": "document.chunk_size",
                "category": "功能配置",
                "value_type": "number",
                "description": "文档分块大小",
                "default_value": "1000",
                "is_system": False,
                "is_sensitive": False,
                "validation_rules": {"min_value": 100, "max_value": 10000}
            },
            "DOCUMENT_CHUNK_OVERLAP": {
                "config_key": "document.chunk_overlap",
                "category": "功能配置",
                "value_type": "number",
                "description": "文档分块重叠长度",
                "default_value": "200",
                "is_system": False,
                "is_sensitive": False,
                "validation_rules": {"min_value": 0, "max_value": 1000}
            },
            "DOCUMENT_SPLITTER_TYPE": {
                "config_key": "document.splitter_type",
                "category": "功能配置",
                "value_type": "string",
                "description": "文档分割器类型",
                "default_value": "sentence",
                "is_system": False,
                "is_sensitive": False,
                "validation_rules": {"enum": ["sentence", "chunk", "token"]}
            },
            "DOCUMENT_PROCESSING_CONCURRENCY": {
                "config_key": "document.processing_concurrency",
                "category": "功能配置",
                "value_type": "number",
                "description": "文档处理并发数",
                "default_value": "4",
                "is_system": False,
                "is_sensitive": False,
                "validation_rules": {"min_value": 1, "max_value": 32}
            },
            
            # 功能开关
            "VOICE_ENABLED": {
                "config_key": "features.voice.enabled",
                "category": "功能配置",
                "value_type": "boolean",
                "description": "是否启用语音功能",
                "default_value": "False",
                "is_system": False,
                "is_sensitive": False
            },
            "METRICS_ENABLED": {
                "config_key": "features.metrics.enabled",
                "category": "功能配置",
                "value_type": "boolean",
                "description": "是否启用指标统计",
                "default_value": "False",
                "is_system": False,
                "is_sensitive": False
            },
            "OWL_TOOLS_ENABLED": {
                "config_key": "features.owl_tools.enabled",
                "category": "功能配置",
                "value_type": "boolean",
                "description": "是否启用OWL工具系统",
                "default_value": "True",
                "is_system": False,
                "is_sensitive": False
            },
            "LIGHTRAG_ENABLED": {
                "config_key": "features.lightrag.enabled",
                "category": "功能配置",
                "value_type": "boolean",
                "description": "是否启用LightRAG",
                "default_value": "True",
                "is_system": False,
                "is_sensitive": False
            },
            "SEARXNG_ENABLED": {
                "config_key": "features.searxng.enabled",
                "category": "功能配置",
                "value_type": "boolean",
                "description": "是否启用SearxNG搜索",
                "default_value": "True",
                "is_system": False,
                "is_sensitive": False
            },
            "ADVANCED_TOOLS_ENABLED": {
                "config_key": "features.advanced_tools.enabled",
                "category": "功能配置",
                "value_type": "boolean",
                "description": "是否启用高级工具",
                "default_value": "True",
                "is_system": False,
                "is_sensitive": False
            },
            
            # ===============================================================================
            # 日志配置
            # ===============================================================================
            
            "LOG_LEVEL": {
                "config_key": "logging.level",
                "category": "系统配置",
                "value_type": "string",
                "description": "日志级别",
                "default_value": "INFO",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]}
            },
            "LOG_FORMAT": {
                "config_key": "logging.format",
                "category": "系统配置",
                "value_type": "string",
                "description": "日志格式",
                "default_value": "text",
                "is_system": True,
                "is_sensitive": False,
                "validation_rules": {"enum": ["text", "json"]}
            },
            "LOG_CONSOLE_ENABLED": {
                "config_key": "logging.console.enabled",
                "category": "系统配置",
                "value_type": "boolean",
                "description": "是否输出到控制台",
                "default_value": "True",
                "is_system": True,
                "is_sensitive": False
            },
            "LOG_FILE_ENABLED": {
                "config_key": "logging.file.enabled",
                "category": "系统配置",
                "value_type": "boolean",
                "description": "是否输出到文件",
                "default_value": "False",
                "is_system": True,
                "is_sensitive": False
            },
            "LOG_FILE_PATH": {
                "config_key": "logging.file.path",
                "category": "系统配置",
                "value_type": "string",
                "description": "日志文件路径",
                "default_value": "logs/app.log",
                "is_system": True,
                "is_sensitive": False
            },
        }
    
    @staticmethod
    def get_category_definitions() -> Dict[str, Dict[str, Any]]:
        """获取配置类别定义"""
        return {
            "系统配置": {
                "description": "系统核心配置项",
                "is_system": True,
                "order": 10
            },
            "安全配置": {
                "description": "安全和认证相关配置",
                "is_system": True,
                "order": 20
            },
            "数据库配置": {
                "description": "数据库连接和存储配置",
                "is_system": True,
                "order": 30
            },
            "服务配置": {
                "description": "外部服务连接配置",
                "is_system": True,
                "order": 40
            },
            "模型配置": {
                "description": "AI模型及提供商配置",
                "is_system": False,
                "order": 50
            },
            "功能配置": {
                "description": "功能开关和参数配置",
                "is_system": False,
                "order": 60
            },
            "框架配置": {
                "description": "AI框架集成配置",
                "is_system": False,
                "order": 70
            },
            "自定义配置": {
                "description": "用户自定义配置",
                "is_system": False,
                "order": 100
            },

    # === 高频关键配置映射（自动添加） ===
    "MINIMAX_GROUP_ID": {
        "category": "system",
        "description": "配置项: MINIMAX_GROUP_ID",
        "required": false,
        "sensitive": false,
        "type": "string",
        "default": ""
    },
    "LLAMAINDEX_DEFAULT_STORE": {
        "category": "frameworks",
        "description": "配置项: LLAMAINDEX_DEFAULT_STORE",
        "required": false,
        "sensitive": false,
        "type": "string",
        "default": ""
    },,

    # === 高频关键配置映射（自动添加） ===
    "MINIMAX_GROUP_ID": {
        "category": "system",
        "description": "配置项: MINIMAX_GROUP_ID",
        "required": false,
        "sensitive": false,
        "type": "string",
        "default": ""
    },
    "LLAMAINDEX_DEFAULT_STORE": {
        "category": "frameworks",
        "description": "配置项: LLAMAINDEX_DEFAULT_STORE",
        "required": false,
        "sensitive": false,
        "type": "string",
        "default": ""
    },
}
    
    @staticmethod
    def get_critical_configs() -> List[str]:
        """获取关键配置项列表（必须在启动前配置）"""
        return [
            "DATABASE_URL",
            "JWT_SECRET_KEY",
            "SERVICE_NAME",
            "SERVICE_PORT",
            "REDIS_HOST",
            "REDIS_PORT"
        ]
    
    @staticmethod
    def get_sensitive_configs() -> List[str]:
        """获取敏感配置项列表（需要加密存储）"""
        mapping = ConfigMapping.get_env_to_config_mapping()
        return [
            env_key for env_key, config in mapping.items()
            if config.get("is_sensitive", False)
        ] 