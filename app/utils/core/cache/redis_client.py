"""
Redis客户端模块
提供Redis连接和操作的核心功能
"""

import redis
import logging
from typing import Optional, Any, Union, Dict, List
import json
import pickle
from datetime import timedelta

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis客户端管理器"""
    
    def __init__(
        self, 
        host: str = "localhost", 
        port: int = 6379, 
        db: int = 0, 
        password: Optional[str] = None,
        decode_responses: bool = True,
        **kwargs
    ):
        """
        初始化Redis客户端
        
        Args:
            host: Redis服务器地址
            port: Redis端口
            db: 数据库索引
            password: 密码
            decode_responses: 是否解码响应
            **kwargs: 其他Redis连接参数
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.decode_responses = decode_responses
        
        # 连接参数
        self.connection_kwargs = {
            "host": host,
            "port": port,
            "db": db,
            "password": password,
            "decode_responses": decode_responses,
            **kwargs
        }
        
        # 创建连接池
        self.pool = redis.ConnectionPool(**self.connection_kwargs)
        self.client = redis.Redis(connection_pool=self.pool)
        
        logger.info(f"Redis客户端已初始化: {host}:{port}/{db}")
    
    def get(self, key: str) -> Optional[str]:
        """
        获取键值
        
        Args:
            key: 键名
            
        Returns:
            键值或None
        """
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET操作失败 {key}: {str(e)}")
            return None
    
    def set(
        self, 
        key: str, 
        value: Union[str, int, float, bytes], 
        ttl: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """
        设置键值
        
        Args:
            key: 键名
            value: 键值
            ttl: 过期时间（秒或timedelta）
            
        Returns:
            操作是否成功
        """
        try:
            if ttl:
                return bool(self.client.setex(key, ttl, value))
            else:
                return bool(self.client.set(key, value))
        except Exception as e:
            logger.error(f"Redis SET操作失败 {key}: {str(e)}")
            return False
    
    def delete(self, *keys: str) -> int:
        """
        删除键
        
        Args:
            *keys: 要删除的键名列表
            
        Returns:
            删除的键数量
        """
        try:
            return self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE操作失败 {keys}: {str(e)}")
            return 0
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 键名
            
        Returns:
            键是否存在
        """
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS操作失败 {key}: {str(e)}")
            return False
    
    def expire(self, key: str, ttl: Union[int, timedelta]) -> bool:
        """
        设置键的过期时间
        
        Args:
            key: 键名
            ttl: 过期时间（秒或timedelta）
            
        Returns:
            操作是否成功
        """
        try:
            return bool(self.client.expire(key, ttl))
        except Exception as e:
            logger.error(f"Redis EXPIRE操作失败 {key}: {str(e)}")
            return False
    
    def ttl(self, key: str) -> int:
        """
        获取键的剩余生存时间
        
        Args:
            key: 键名
            
        Returns:
            剩余生存时间（秒），-1表示永不过期，-2表示键不存在
        """
        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL操作失败 {key}: {str(e)}")
            return -2
    
    def hget(self, name: str, key: str) -> Optional[str]:
        """
        获取哈希表中的字段值
        
        Args:
            name: 哈希表名
            key: 字段名
            
        Returns:
            字段值或None
        """
        try:
            return self.client.hget(name, key)
        except Exception as e:
            logger.error(f"Redis HGET操作失败 {name}.{key}: {str(e)}")
            return None
    
    def hset(self, name: str, key: str, value: Union[str, int, float, bytes]) -> bool:
        """
        设置哈希表中的字段值
        
        Args:
            name: 哈希表名
            key: 字段名
            value: 字段值
            
        Returns:
            操作是否成功
        """
        try:
            return bool(self.client.hset(name, key, value))
        except Exception as e:
            logger.error(f"Redis HSET操作失败 {name}.{key}: {str(e)}")
            return False
    
    def hdel(self, name: str, *keys: str) -> int:
        """
        删除哈希表中的字段
        
        Args:
            name: 哈希表名
            *keys: 要删除的字段名列表
            
        Returns:
            删除的字段数量
        """
        try:
            return self.client.hdel(name, *keys)
        except Exception as e:
            logger.error(f"Redis HDEL操作失败 {name}.{keys}: {str(e)}")
            return 0
    
    def hgetall(self, name: str) -> Dict[str, str]:
        """
        获取哈希表中的所有字段和值
        
        Args:
            name: 哈希表名
            
        Returns:
            字段和值的字典
        """
        try:
            return self.client.hgetall(name)
        except Exception as e:
            logger.error(f"Redis HGETALL操作失败 {name}: {str(e)}")
            return {}
    
    def lpush(self, name: str, *values: Union[str, int, float, bytes]) -> int:
        """
        将值插入列表头部
        
        Args:
            name: 列表名
            *values: 要插入的值列表
            
        Returns:
            列表长度
        """
        try:
            return self.client.lpush(name, *values)
        except Exception as e:
            logger.error(f"Redis LPUSH操作失败 {name}: {str(e)}")
            return 0
    
    def rpush(self, name: str, *values: Union[str, int, float, bytes]) -> int:
        """
        将值插入列表尾部
        
        Args:
            name: 列表名
            *values: 要插入的值列表
            
        Returns:
            列表长度
        """
        try:
            return self.client.rpush(name, *values)
        except Exception as e:
            logger.error(f"Redis RPUSH操作失败 {name}: {str(e)}")
            return 0
    
    def lpop(self, name: str) -> Optional[str]:
        """
        移除并返回列表头部元素
        
        Args:
            name: 列表名
            
        Returns:
            头部元素或None
        """
        try:
            return self.client.lpop(name)
        except Exception as e:
            logger.error(f"Redis LPOP操作失败 {name}: {str(e)}")
            return None
    
    def rpop(self, name: str) -> Optional[str]:
        """
        移除并返回列表尾部元素
        
        Args:
            name: 列表名
            
        Returns:
            尾部元素或None
        """
        try:
            return self.client.rpop(name)
        except Exception as e:
            logger.error(f"Redis RPOP操作失败 {name}: {str(e)}")
            return None
    
    def lrange(self, name: str, start: int, end: int) -> List[str]:
        """
        获取列表中指定范围的元素
        
        Args:
            name: 列表名
            start: 开始索引
            end: 结束索引
            
        Returns:
            元素列表
        """
        try:
            return self.client.lrange(name, start, end)
        except Exception as e:
            logger.error(f"Redis LRANGE操作失败 {name}: {str(e)}")
            return []
    
    def sadd(self, name: str, *values: Union[str, int, float, bytes]) -> int:
        """
        向集合添加成员
        
        Args:
            name: 集合名
            *values: 要添加的成员列表
            
        Returns:
            成功添加的成员数量
        """
        try:
            return self.client.sadd(name, *values)
        except Exception as e:
            logger.error(f"Redis SADD操作失败 {name}: {str(e)}")
            return 0
    
    def srem(self, name: str, *values: Union[str, int, float, bytes]) -> int:
        """
        从集合删除成员
        
        Args:
            name: 集合名
            *values: 要删除的成员列表
            
        Returns:
            成功删除的成员数量
        """
        try:
            return self.client.srem(name, *values)
        except Exception as e:
            logger.error(f"Redis SREM操作失败 {name}: {str(e)}")
            return 0
    
    def smembers(self, name: str) -> set:
        """
        获取集合的所有成员
        
        Args:
            name: 集合名
            
        Returns:
            成员集合
        """
        try:
            return self.client.smembers(name)
        except Exception as e:
            logger.error(f"Redis SMEMBERS操作失败 {name}: {str(e)}")
            return set()
    
    def sismember(self, name: str, value: Union[str, int, float, bytes]) -> bool:
        """
        检查成员是否在集合中
        
        Args:
            name: 集合名
            value: 要检查的成员
            
        Returns:
            成员是否在集合中
        """
        try:
            return bool(self.client.sismember(name, value))
        except Exception as e:
            logger.error(f"Redis SISMEMBER操作失败 {name}: {str(e)}")
            return False
    
    def incr(self, key: str, amount: int = 1) -> int:
        """
        递增键的值
        
        Args:
            key: 键名
            amount: 递增量
            
        Returns:
            递增后的值
        """
        try:
            return self.client.incr(key, amount)
        except Exception as e:
            logger.error(f"Redis INCR操作失败 {key}: {str(e)}")
            return 0
    
    def decr(self, key: str, amount: int = 1) -> int:
        """
        递减键的值
        
        Args:
            key: 键名
            amount: 递减量
            
        Returns:
            递减后的值
        """
        try:
            return self.client.decr(key, amount)
        except Exception as e:
            logger.error(f"Redis DECR操作失败 {key}: {str(e)}")
            return 0
    
    def keys(self, pattern: str = "*") -> List[str]:
        """
        查找匹配模式的键
        
        Args:
            pattern: 匹配模式
            
        Returns:
            匹配的键列表
        """
        try:
            return self.client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis KEYS操作失败 {pattern}: {str(e)}")
            return []
    
    def flushdb(self) -> bool:
        """
        清空当前数据库
        
        Returns:
            操作是否成功
        """
        try:
            return bool(self.client.flushdb())
        except Exception as e:
            logger.error(f"Redis FLUSHDB操作失败: {str(e)}")
            return False
    
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            连接是否正常
        """
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis健康检查失败: {str(e)}")
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取Redis服务器信息
        
        Returns:
            服务器信息字典
        """
        try:
            return self.client.info()
        except Exception as e:
            logger.error(f"获取Redis信息失败: {str(e)}")
            return {}
    
    def get_json(self, key: str) -> Optional[Any]:
        """
        获取JSON格式的值
        
        Args:
            key: 键名
            
        Returns:
            反序列化后的对象或None
        """
        value = self.get(key)
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"JSON反序列化失败 {key}: {str(e)}")
            return None
    
    def set_json(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """
        设置JSON格式的值
        
        Args:
            key: 键名
            value: 要序列化的对象
            ttl: 过期时间
            
        Returns:
            操作是否成功
        """
        try:
            json_value = json.dumps(value, ensure_ascii=False)
            return self.set(key, json_value, ttl)
        except (TypeError, ValueError) as e:
            logger.error(f"JSON序列化失败 {key}: {str(e)}")
            return False
    
    def close(self):
        """关闭连接"""
        try:
            self.client.close()
            logger.info("Redis连接已关闭")
        except Exception as e:
            logger.error(f"关闭Redis连接失败: {str(e)}")


# 全局Redis客户端实例
_redis_client = None


def get_redis_client(
    host: str = None, 
    port: int = None, 
    db: int = None, 
    password: str = None,
    **kwargs
) -> RedisClient:
    """
    获取全局Redis客户端实例
    
    Args:
        host: Redis服务器地址
        port: Redis端口
        db: 数据库索引
        password: 密码
        **kwargs: 其他连接参数
        
    Returns:
        Redis客户端实例
    """
    global _redis_client
    
    if _redis_client is None:
        # 从配置获取默认值
        from app.utils.core.config import get_config
        
        host = host or get_config("redis", "host", default="localhost")
        port = port or get_config("redis", "port", default=6379)
        db = db or get_config("redis", "db", default=0)
        password = password or get_config("redis", "password", default=None)
        
        _redis_client = RedisClient(
            host=host,
            port=port,
            db=db,
            password=password,
            **kwargs
        )
    
    return _redis_client 