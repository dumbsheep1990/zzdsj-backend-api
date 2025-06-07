try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

from pydantic import Field, validator
from typing import List, Dict, Any, Optional
import os
import secrets
import warnings
import json
from core.system_config import get_config_manager

# 获取配置管理器实例
config_manager = get_config_manager()

def generate_secure_key() -> str:
    """生成安全的密钥"""
    return secrets.token_hex(32)

def get_jwt_secret_key() -> str:
    """获取JWT密钥，优先使用环境变量，否则生成安全密钥"""
    key = os.getenv("JWT_SECRET_KEY")
    if not key:
        warnings.warn(
            "JWT_SECRET_KEY环境变量未设置！正在生成临时密钥。"
            "生产环境中请设置JWT_SECRET_KEY环境变量。",
            UserWarning
        )
        return generate_secure_key()
    
    # 检查是否是默认的不安全密钥
    if key == "23f0767704249cd7be7181a0dad23c74e0739c98ce54d7140fc2e94dfa584fb0":
        warnings.warn(
            "检测到默认JWT密钥！这在生产环境中不安全。"
            "请设置一个新的随机JWT_SECRET_KEY。",
            UserWarning
        )
    
    return key

def get_database_url() -> str:
    """获取数据库连接URL，优先使用环境变量"""
    url = os.getenv("DATABASE_URL")
    if not url:
        # 从单独的配置项构建URL
        host = os.getenv("POSTGRES_HOST", config_manager.get("postgres_host", "localhost"))
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        db = os.getenv("POSTGRES_DB", "knowledge_qa")
        
        url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
        
        if password == "postgres":
            warnings.warn(
                "检测到默认数据库密码！生产环境中请设置强密码。",
                UserWarning
            )
    
    return url

def get_celery_broker_url() -> str:
    """获取Celery代理URL，优先使用环境变量"""
    url = os.getenv("CELERY_BROKER_URL")
    if not url:
        # 从RabbitMQ配置构建URL
        host = os.getenv("RABBITMQ_HOST", "localhost")
        port = os.getenv("RABBITMQ_PORT", "5672")
        user = os.getenv("RABBITMQ_USER", "guest")
        password = os.getenv("RABBITMQ_PASSWORD", "guest")
        
        url = f"amqp://{user}:{password}@{host}:{port}//"
        
        if password == "guest":
            warnings.warn(
                "检测到默认RabbitMQ密码！生产环境中请设置强密码。",
                UserWarning
            )
    
    return url

def get_celery_result_backend() -> str:
    """获取Celery结果后端URL，优先使用环境变量"""
    url = os.getenv("CELERY_RESULT_BACKEND")
    if not url:
        # 从Redis配置构建URL
        host = os.getenv("REDIS_HOST", "localhost")
        port = os.getenv("REDIS_PORT", "6379")
        password = os.getenv("REDIS_PASSWORD", "")
        db = os.getenv("REDIS_DB", "0")
        
        if password:
            url = f"redis://:{password}@{host}:{port}/{db}"
        else:
            url = f"redis://{host}:{port}/{db}"
    
    return url

class Settings(BaseSettings):
    """应用配置类"""
    
    # ===============================================================================
    # 部署模式配置 (基础必需)
    # ===============================================================================
    
    # 部署模式：minimal, standard, production
    DEPLOYMENT_MODE: str = Field(default="standard", description="部署模式")
    
    # 基础应用配置
    APP_ENV: str = Field(default="development", description="应用环境")
    SERVICE_NAME: str = Field(default="智政知识库系统", description="服务名称")
    SERVICE_IP: str = Field(default="127.0.0.1", description="服务IP")
    SERVICE_PORT: int = Field(default=8000, description="服务端口")
    BASE_URL: str = Field(default="http://127.0.0.1:8000", description="基础URL")
    
    # 调试和开发配置
    DEBUG_MODE: bool = Field(default=True, description="调试模式")
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    
    # 安全配置
    ALLOWED_HOSTS: List[str] = Field(default=["localhost", "127.0.0.1", "*"], description="允许的主机")
    CORS_ENABLED: bool = Field(default=True, description="CORS启用状态")
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000"],
        description="CORS允许的来源"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="CORS允许凭证")
    
    # ===============================================================================
    # 安全配置 (基础必需)
    # ===============================================================================
    
    JWT_SECRET_KEY: str = Field(default="your-secret-jwt-key-here-change-in-production", description="JWT密钥")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT算法")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="访问令牌过期时间(分钟)")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="刷新令牌过期时间(天)")
    
    ENCRYPTION_KEY: str = Field(default="your-encryption-key-here-change-in-production", description="加密密钥")
    
    # ===============================================================================
    # 基础数据库配置 (基础必需)
    # ===============================================================================
    
    # PostgreSQL配置
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL主机")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL端口")
    POSTGRES_USER: str = Field(default="postgres", description="PostgreSQL用户")
    POSTGRES_PASSWORD: str = Field(default="postgres", description="PostgreSQL密码")
    POSTGRES_DB: str = Field(default="knowledge_qa", description="PostgreSQL数据库")
    
    # 数据库连接URL (自动生成)
    DATABASE_URL: Optional[str] = Field(default=None, description="数据库连接URL")
    
    @validator('DATABASE_URL', pre=True, always=True)
    def assemble_db_url(cls, v, values):
        if isinstance(v, str):
            return v
        return f"postgresql://{values.get('POSTGRES_USER')}:{values.get('POSTGRES_PASSWORD')}@{values.get('POSTGRES_HOST')}:{values.get('POSTGRES_PORT')}/{values.get('POSTGRES_DB')}"
    
    # ===============================================================================
    # 存储引擎配置
    # ===============================================================================
    
    # Elasticsearch配置 (基础必需) - 文档分片和混合检索引擎
    ELASTICSEARCH_URL: str = Field(default="http://localhost:9200", description="Elasticsearch URL")
    ELASTICSEARCH_USERNAME: Optional[str] = Field(default=None, description="Elasticsearch用户名")
    ELASTICSEARCH_PASSWORD: Optional[str] = Field(default=None, description="Elasticsearch密码")
    ELASTICSEARCH_API_KEY: Optional[str] = Field(default=None, description="Elasticsearch API密钥")
    ELASTICSEARCH_CLOUD_ID: Optional[str] = Field(default=None, description="Elasticsearch Cloud ID")
    ELASTICSEARCH_INDEX: str = Field(default="document_index", description="Elasticsearch索引名")
    ELASTICSEARCH_DEFAULT_ANALYZER: str = Field(default="ik_max_word", description="默认分析器")
    ELASTICSEARCH_EMBEDDING_DIM: int = Field(default=1536, description="嵌入向量维度")
    ELASTICSEARCH_SIMILARITY: str = Field(default="cosine", description="相似度算法")
    
    # 混合检索配置 (基础必需) - 系统核心功能，强制启用
    ELASTICSEARCH_HYBRID_SEARCH: bool = Field(default=True, description="混合检索启用状态")
    ELASTICSEARCH_HYBRID_WEIGHT: float = Field(default=0.7, description="混合检索语义搜索权重")
    
    # 用户文件存储配置 (基础必需)
    FILE_STORAGE_TYPE: str = Field(default="local", description="文件存储类型")
    FILE_STORAGE_PATH: str = Field(default="./data/uploads", description="本地文件存储路径")
    FILE_STORAGE_BASE_URL: str = Field(default="http://localhost:8000/files", description="文件访问基础URL")
    
    # MinIO对象存储配置 (可选增强) - 作为Milvus依赖或高级文件存储
    MINIO_ENDPOINT: str = Field(default="localhost:9000", description="MinIO端点")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin", description="MinIO访问密钥")
    MINIO_SECRET_KEY: str = Field(default="minioadmin", description="MinIO密钥")
    MINIO_SECURE: bool = Field(default=False, description="MinIO安全连接")
    MINIO_BUCKET: str = Field(default="knowledge-docs", description="MinIO存储桶")
    MINIO_ENABLED: bool = Field(default=False, description="MinIO启用状态")
    
    @validator('MINIO_ENABLED', pre=True, always=True)
    def check_minio_enabled(cls, v, values):
        # MinIO主要作为Milvus依赖启用
        if values.get('MILVUS_ENABLED', False):
            return True
        # 或者在高级文件存储模式下启用
        if values.get('FILE_STORAGE_TYPE') == 'minio':
            return True
        return v
    
    # ===============================================================================
    # 缓存和消息队列配置 (基础必需)
    # ===============================================================================
    
    # Redis配置 (基础必需)
    REDIS_HOST: str = Field(default="localhost", description="Redis主机")
    REDIS_PORT: int = Field(default=6379, description="Redis端口")
    REDIS_DB: int = Field(default=0, description="Redis数据库")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis密码")
    REDIS_URL: Optional[str] = Field(default=None, description="Redis连接URL")
    
    @validator('REDIS_URL', pre=True, always=True)
    def assemble_redis_url(cls, v, values):
        if isinstance(v, str):
            return v
        password_part = f":{values.get('REDIS_PASSWORD')}@" if values.get('REDIS_PASSWORD') else ""
        return f"redis://{password_part}{values.get('REDIS_HOST')}:{values.get('REDIS_PORT')}/{values.get('REDIS_DB')}"
    
    # RabbitMQ配置 (基础必需)
    RABBITMQ_HOST: str = Field(default="localhost", description="RabbitMQ主机")
    RABBITMQ_PORT: int = Field(default=5672, description="RabbitMQ端口")
    RABBITMQ_USER: str = Field(default="guest", description="RabbitMQ用户")
    RABBITMQ_PASSWORD: str = Field(default="guest", description="RabbitMQ密码")
    
    # Celery配置 (基础必需)
    CELERY_BROKER_URL: Optional[str] = Field(default=None, description="Celery Broker URL")
    CELERY_RESULT_BACKEND: Optional[str] = Field(default=None, description="Celery结果后端")
    CELERY_TIMEZONE: str = Field(default="Asia/Shanghai", description="Celery时区")
    
    @validator('CELERY_BROKER_URL', pre=True, always=True)
    def assemble_celery_broker_url(cls, v, values):
        if isinstance(v, str):
            return v
        return f"amqp://{values.get('RABBITMQ_USER')}:{values.get('RABBITMQ_PASSWORD')}@{values.get('RABBITMQ_HOST')}:{values.get('RABBITMQ_PORT')}//"
    
    @validator('CELERY_RESULT_BACKEND', pre=True, always=True)
    def assemble_celery_result_backend(cls, v, values):
        if isinstance(v, str):
            return v
        return values.get('REDIS_URL')
    
    # ===============================================================================
    # 高性能向量搜索配置 (可选增强)
    # ===============================================================================
    
    # Milvus配置 (在minimal模式下自动禁用)
    MILVUS_HOST: str = Field(default="localhost", description="Milvus主机")
    MILVUS_PORT: int = Field(default=19530, description="Milvus端口")
    MILVUS_COLLECTION: str = Field(default="document_vectors", description="Milvus集合名")
    MILVUS_ENABLED: bool = Field(default=True, description="Milvus启用状态")
    
    @validator('MILVUS_ENABLED', pre=True, always=True)
    def check_milvus_enabled(cls, v, values):
        # 在最小化模式下自动禁用Milvus
        if values.get('DEPLOYMENT_MODE') == 'minimal':
            return False
        return v
    
    # ===============================================================================
    # 图数据库配置 (知识图谱功能)
    # ===============================================================================
    
    # 图数据库类型配置
    GRAPH_DATABASE_TYPE: str = Field(default="arangodb", description="图数据库类型")
    GRAPH_DATABASE_ENABLED: bool = Field(default=True, description="图数据库启用状态")
    
    # ArangoDB配置
    ARANGO_HOSTS: str = Field(default="http://localhost:8529", description="ArangoDB主机列表")
    ARANGO_USERNAME: str = Field(default="root", description="ArangoDB用户名")
    ARANGO_PASSWORD: str = Field(default="password", description="ArangoDB密码")
    ARANGO_DB_PREFIX: str = Field(default="kg_tenant_", description="ArangoDB数据库前缀")
    ARANGO_GRAPH_NAME: str = Field(default="knowledge_graph", description="ArangoDB图名称")
    ARANGO_USE_NATIVE: bool = Field(default=True, description="ArangoDB使用原生算法")
    ARANGO_ENABLE_NETWORKX: bool = Field(default=True, description="ArangoDB启用NetworkX增强")
    ARANGO_BATCH_SIZE: int = Field(default=1000, description="ArangoDB批量处理大小")
    ARANGO_POOL_SIZE: int = Field(default=10, description="ArangoDB连接池大小")
    ARANGO_QUERY_TIMEOUT: int = Field(default=30, description="ArangoDB查询超时时间(秒)")
    
    # PostgreSQL + AGE配置
    GRAPH_DATABASE_URL: Optional[str] = Field(default=None, description="图数据库连接URL")
    PG_SCHEMA_PREFIX: str = Field(default="kg_tenant_", description="PostgreSQL Schema前缀")
    PG_GRAPH_NAME: str = Field(default="knowledge_graph", description="PostgreSQL图名称")
    
    # NetworkX配置
    NETWORKX_CACHE: bool = Field(default=True, description="NetworkX缓存启用")
    NETWORKX_CACHE_TIMEOUT: int = Field(default=3600, description="NetworkX缓存超时时间(秒)")
    NETWORKX_MAX_CACHE: int = Field(default=100, description="NetworkX最大缓存数")
    
    # 租户隔离配置
    TENANT_SHARDING_STRATEGY: str = Field(default="user_group", description="租户分片策略")
    
    @validator('GRAPH_DATABASE_URL', pre=True, always=True)
    def assemble_graph_db_url(cls, v, values):
        if isinstance(v, str):
            return v
        # 如果是PostgreSQL+AGE方案，使用主数据库URL
        if values.get('GRAPH_DATABASE_TYPE') == 'postgresql_age':
            return values.get('DATABASE_URL')
        return None
    
    @validator('GRAPH_DATABASE_ENABLED', pre=True, always=True)
    def check_graph_database_enabled(cls, v, values):
        # 在最小化模式下可选择禁用图数据库
        if values.get('DEPLOYMENT_MODE') == 'minimal':
            return v  # 保持用户配置
        return v
    
    # ===============================================================================
    # 服务发现和配置中心 (完整版功能)
    # ===============================================================================
    
    # Nacos配置 (仅在standard/production模式启用)
    NACOS_SERVER_ADDRESSES: str = Field(default="127.0.0.1:8848", description="Nacos服务器地址")
    NACOS_NAMESPACE: str = Field(default="public", description="Nacos命名空间")
    NACOS_GROUP: str = Field(default="DEFAULT_GROUP", description="Nacos组")
    NACOS_ENABLED: bool = Field(default=True, description="Nacos启用状态")
    
    @validator('NACOS_ENABLED', pre=True, always=True)
    def check_nacos_enabled(cls, v, values):
        # 在最小化模式下自动禁用Nacos
        if values.get('DEPLOYMENT_MODE') == 'minimal':
            return False
        return v
    
    # ===============================================================================
    # AI模型配置 (基础必需)
    # ===============================================================================
    
    # 基础模型配置
    DEFAULT_MODEL: str = Field(default="gpt-4", description="默认模型")
    EMBEDDING_MODEL: str = Field(default="text-embedding-ada-002", description="嵌入模型")
    CHAT_MODEL: str = Field(default="gpt-3.5-turbo", description="聊天模型")
    
    # OpenAI配置
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API密钥")
    OPENAI_API_BASE: str = Field(default="https://api.openai.com/v1", description="OpenAI API基础URL")
    OPENAI_ORGANIZATION: Optional[str] = Field(default=None, description="OpenAI组织ID")
    
    # 其他AI服务配置
    ZHIPU_API_KEY: Optional[str] = Field(default=None, description="智谱AI API密钥")
    GLM_API_KEY: Optional[str] = Field(default=None, description="GLM API密钥")
    GLM_API_BASE: str = Field(default="https://open.bigmodel.cn/api/paas/v4", description="GLM API基础URL")
    
    # ===============================================================================
    # 功能开关配置
    # ===============================================================================
    
    # 文件上传功能 (基础功能)
    FILE_UPLOAD_ENABLED: bool = Field(default=True, description="文件上传启用状态")
    MAX_FILE_SIZE_MB: int = Field(default=50, description="最大文件大小(MB)")
    ALLOWED_FILE_TYPES: List[str] = Field(
        default=["pdf", "docx", "txt", "md", "html", "rtf", "csv", "json", "xml"],
        description="允许的文件类型"
    )
    
    # 图片上传功能
    IMAGE_UPLOAD_ENABLED: bool = Field(default=True, description="图片上传启用状态")
    MAX_IMAGE_SIZE_MB: int = Field(default=10, description="最大图片大小(MB)")
    ALLOWED_IMAGE_TYPES: List[str] = Field(
        default=["jpg", "jpeg", "png", "gif", "bmp", "webp"],
        description="允许的图片类型"
    )
    
    # 音视频上传功能 (可选功能)
    MEDIA_UPLOAD_ENABLED: bool = Field(default=False, description="音视频上传启用状态")
    MAX_AUDIO_SIZE_MB: int = Field(default=100, description="最大音频大小(MB)")
    MAX_VIDEO_SIZE_MB: int = Field(default=500, description="最大视频大小(MB)")
    
    # 搜索功能
    SEARCH_SUGGESTIONS_ENABLED: bool = Field(default=True, description="搜索建议启用状态")
    SEARCH_HISTORY_ENABLED: bool = Field(default=True, description="搜索历史启用状态")
    
    # 实时功能
    REAL_TIME_NOTIFICATIONS_ENABLED: bool = Field(default=True, description="实时通知启用状态")
    WEBSOCKET_ENABLED: bool = Field(default=True, description="WebSocket启用状态")
    
    # 数据导出功能
    DATA_EXPORT_ENABLED: bool = Field(default=True, description="数据导出启用状态")
    BATCH_EXPORT_ENABLED: bool = Field(default=True, description="批量导出启用状态")
    
    # ===============================================================================
    # 安全和权限配置
    # ===============================================================================
    
    # API安全
    API_KEY_REQUIRED: bool = Field(default=False, description="API密钥必需状态")
    API_RATE_LIMITING_ENABLED: bool = Field(default=True, description="API限流启用状态")
    API_MAX_REQUESTS_PER_MINUTE: int = Field(default=100, description="API每分钟最大请求数")
    
    # 用户权限
    USER_REGISTRATION_ENABLED: bool = Field(default=True, description="用户注册启用状态")
    EMAIL_VERIFICATION_REQUIRED: bool = Field(default=False, description="邮箱验证必需状态")
    PASSWORD_STRENGTH_CHECK_ENABLED: bool = Field(default=True, description="密码强度检查启用状态")
    
    # 数据安全
    DATA_ENCRYPTION_ENABLED: bool = Field(default=False, description="数据加密启用状态")
    AUDIT_LOG_ENABLED: bool = Field(default=True, description="审计日志启用状态")
    GDPR_COMPLIANCE_ENABLED: bool = Field(default=False, description="GDPR合规启用状态")
    
    # IP白名单
    IP_WHITELIST_ENABLED: bool = Field(default=False, description="IP白名单启用状态")
    ALLOWED_IPS: List[str] = Field(default=["127.0.0.1", "::1"], description="允许的IP列表")
    
    # ===============================================================================
    # 监控和运维配置
    # ===============================================================================
    
    # 监控配置
    PERFORMANCE_MONITORING_ENABLED: bool = Field(default=True, description="性能监控启用状态")
    SLOW_QUERY_THRESHOLD: int = Field(default=1000, description="慢查询阈值(毫秒)")
    REQUEST_TRACKING_ENABLED: bool = Field(default=True, description="请求跟踪启用状态")
    
    # 日志配置
    LOG_FORMAT: str = Field(default="json", description="日志格式")
    LOG_FILE_ENABLED: bool = Field(default=True, description="日志文件启用状态")
    LOG_FILE_PATH: str = Field(default="logs/app.log", description="日志文件路径")
    LOG_FILE_MAX_SIZE: str = Field(default="10MB", description="日志文件最大大小")
    LOG_FILE_BACKUP_COUNT: int = Field(default=5, description="日志文件备份数量")
    
    # Flower配置
    FLOWER_PORT: int = Field(default=5555, description="Flower端口")
    FLOWER_BASIC_AUTH: str = Field(default="admin:password", description="Flower基础认证")
    FLOWER_URL_PREFIX: str = Field(default="/flower", description="Flower URL前缀")
    FLOWER_ENABLE_EVENTS: bool = Field(default=True, description="Flower事件启用状态")
    
    # 邮件通知配置
    SMTP_HOST: str = Field(default="smtp.gmail.com", description="SMTP主机")
    SMTP_PORT: int = Field(default=587, description="SMTP端口")
    SMTP_USE_TLS: bool = Field(default=True, description="SMTP使用TLS")
    SMTP_USERNAME: Optional[str] = Field(default=None, description="SMTP用户名")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP密码")
    EMAIL_FROM: str = Field(default="system@yourcompany.com", description="发件人邮箱")
    
    # 系统告警配置
    ALERT_EMAIL_RECIPIENTS: str = Field(default="admin@yourcompany.com", description="告警邮件收件人")
    ALERT_WEBHOOK_URL: Optional[str] = Field(default=None, description="告警WebHook URL")
    ALERT_CPU_THRESHOLD: int = Field(default=80, description="CPU告警阈值")
    ALERT_MEMORY_THRESHOLD: int = Field(default=85, description="内存告警阈值")
    ALERT_DISK_THRESHOLD: int = Field(default=90, description="磁盘告警阈值")
    
    # 系统维护配置
    CLEANUP_TEMP_FILES_DAYS: int = Field(default=1, description="临时文件清理天数")
    CLEANUP_TASK_HISTORY_DAYS: int = Field(default=30, description="任务历史清理天数")
    CLEANUP_LOG_FILES_DAYS: int = Field(default=30, description="日志文件清理天数")
    SYSTEM_HEALTH_CHECK_INTERVAL: int = Field(default=300, description="系统健康检查间隔(秒)")
    DISK_SPACE_CHECK_INTERVAL: int = Field(default=3600, description="磁盘空间检查间隔(秒)")
    
    # InfluxDB配置
    INFLUXDB_URL: str = Field(default="http://localhost:8086", description="InfluxDB URL")
    INFLUXDB_TOKEN: Optional[str] = Field(default=None, description="InfluxDB令牌")
    INFLUXDB_ORG: Optional[str] = Field(default=None, description="InfluxDB组织")
    INFLUXDB_BUCKET: Optional[str] = Field(default=None, description="InfluxDB存储桶")
    
    # ===============================================================================
    # 配置验证和元数据
    # ===============================================================================
    
    # 配置版本和验证
    CONFIG_VERSION: str = Field(default="2.0.0", description="配置版本")
    CONFIG_VALIDATION_ENABLED: bool = Field(default=True, description="配置验证启用状态")
    REQUIRED_CONFIG_CHECK_ENABLED: bool = Field(default=True, description="必需配置检查启用状态")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"
    
    def get_storage_architecture_info(self) -> Dict[str, Any]:
        """获取存储架构信息"""
        return {
            "deployment_mode": self.DEPLOYMENT_MODE,
            "storage_engines": {
                "elasticsearch": {
                    "enabled": True,  # 始终启用
                    "url": self.ELASTICSEARCH_URL,
                    "hybrid_search": self.ELASTICSEARCH_HYBRID_SEARCH,
                    "role": "文档分片存储和混合检索引擎"
                },
                "file_storage": {
                    "enabled": True,  # 始终启用
                    "type": self.FILE_STORAGE_TYPE,
                    "path": self.FILE_STORAGE_PATH,
                    "base_url": self.FILE_STORAGE_BASE_URL,
                    "role": "用户文件上传和存储"
                },
                "minio": {
                    "enabled": self.MINIO_ENABLED,
                    "endpoint": self.MINIO_ENDPOINT,
                    "bucket": self.MINIO_BUCKET,
                    "role": "Milvus依赖或高级文件存储" if self.MINIO_ENABLED else "未启用"
                },
                "milvus": {
                    "enabled": self.MILVUS_ENABLED,
                    "host": self.MILVUS_HOST,
                    "port": self.MILVUS_PORT,
                    "role": "高性能向量搜索引擎 (可选增强)"
                }
            },
            "architecture_description": f"Elasticsearch核心检索引擎 + {self.FILE_STORAGE_TYPE.upper()}文件存储" + 
                                      (f" + Milvus高性能向量搜索" if self.MILVUS_ENABLED else "")
        }
    
    def get_required_services(self) -> List[str]:
        """获取必需服务列表"""
        required = ["postgresql", "elasticsearch", "redis", "rabbitmq"]
        
        if self.DEPLOYMENT_MODE in ["standard", "production"]:
            if self.MILVUS_ENABLED:
                required.extend(["milvus", "etcd", "minio"])  # Milvus依赖MinIO和etcd
            if self.NACOS_ENABLED:
                required.append("nacos")
        
        return required
    
    def validate_required_config(self) -> List[str]:
        """验证必需配置并返回错误列表"""
        errors = []
        
        # 检查基础必需配置
        if not self.POSTGRES_HOST or not self.POSTGRES_USER or not self.POSTGRES_PASSWORD:
            errors.append("PostgreSQL配置不完整")
        
        if not self.ELASTICSEARCH_URL:
            errors.append("Elasticsearch URL未配置")
        
        if not self.REDIS_HOST:
            errors.append("Redis主机未配置")
        
        if not self.RABBITMQ_HOST or not self.RABBITMQ_USER or not self.RABBITMQ_PASSWORD:
            errors.append("RabbitMQ配置不完整")
        
        # 检查文件存储配置
        if self.FILE_STORAGE_TYPE == "local" and not self.FILE_STORAGE_PATH:
            errors.append("本地文件存储路径未配置")
        elif self.FILE_STORAGE_TYPE == "minio":
            if not self.MINIO_ENDPOINT or not self.MINIO_ACCESS_KEY or not self.MINIO_SECRET_KEY:
                errors.append("MinIO配置不完整")
        
        # 检查可选组件配置
        if self.MILVUS_ENABLED:
            if not self.MILVUS_HOST:
                errors.append("Milvus主机未配置")
            if not self.MINIO_ENABLED:
                errors.append("Milvus需要MinIO作为存储后端")
        
        # 检查AI模型配置
        if not self.OPENAI_API_KEY and not self.ZHIPU_API_KEY and not self.GLM_API_KEY:
            errors.append("至少需要配置一个AI服务提供商的API密钥")
        
        return errors


# 创建全局设置实例
settings = Settings()

# 导出常用配置
__all__ = ["settings", "Settings"]


