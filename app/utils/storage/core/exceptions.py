"""
存储模块异常定义
"""


class StorageError(Exception):
    """
    存储模块基础异常类
    """
    
    def __init__(self, message: str, code: str = None, component: str = None):
        """
        初始化异常
        
        参数:
            message: 错误消息
            code: 错误代码
            component: 组件名称
        """
        super().__init__(message)
        self.message = message
        self.code = code or "STORAGE_ERROR"
        self.component = component


class ConnectionError(StorageError):
    """
    存储连接异常
    """
    
    def __init__(self, message: str = "Storage connection failed", endpoint: str = None, **kwargs):
        """
        初始化异常
        
        参数:
            message: 错误消息
            endpoint: 连接端点
        """
        super().__init__(message, "STORAGE_CONNECTION_ERROR", **kwargs)
        self.endpoint = endpoint


class ConfigurationError(StorageError):
    """
    存储配置异常
    """
    
    def __init__(self, message: str = "Storage configuration error", config_key: str = None, **kwargs):
        """
        初始化异常
        
        参数:
            message: 错误消息
            config_key: 配置键名
        """
        super().__init__(message, "STORAGE_CONFIG_ERROR", **kwargs)
        self.config_key = config_key


class VectorStoreError(StorageError):
    """
    向量存储异常
    """
    
    def __init__(self, message: str = "Vector store operation failed", collection: str = None, **kwargs):
        """
        初始化异常
        
        参数:
            message: 错误消息
            collection: 集合名称
        """
        super().__init__(message, "VECTOR_STORE_ERROR", **kwargs)
        self.collection = collection


class ObjectStoreError(StorageError):
    """
    对象存储异常
    """
    
    def __init__(self, message: str = "Object store operation failed", bucket: str = None, key: str = None, **kwargs):
        """
        初始化异常
        
        参数:
            message: 错误消息
            bucket: 存储桶名称
            key: 对象键
        """
        super().__init__(message, "OBJECT_STORE_ERROR", **kwargs)
        self.bucket = bucket
        self.key = key