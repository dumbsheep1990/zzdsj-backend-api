"""
服务健康检查工具 - 负责检查依赖服务的可用性
"""
import logging
import socket
import time
from typing import Dict, Any, List, Optional, Tuple
import asyncio
import aiohttp
from app.config import settings
from app.utils.database import check_connection as check_db_connection

logger = logging.getLogger(__name__)

class ServiceHealthChecker:
    """服务健康检查器，负责检查依赖服务的可用性"""
    
    @staticmethod
    async def check_tcp_service(host: str, port: int, timeout: float = 3.0) -> Tuple[bool, int, Optional[str]]:
        """检查TCP服务是否可访问，返回(状态, 响应时间ms, 错误信息)"""
        start_time = time.time()
        error_msg = None
        
        try:
            future = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(future, timeout=timeout)
            writer.close()
            await writer.wait_closed()
            status = True
        except (socket.gaierror, ConnectionRefusedError) as e:
            error_msg = f"连接被拒绝: {str(e)}"
            status = False
        except asyncio.TimeoutError:
            error_msg = f"连接超时 (>{timeout}秒)"
            status = False
        except Exception as e:
            error_msg = f"连接错误: {str(e)}"
            status = False
        
        response_time = int((time.time() - start_time) * 1000)  # 毫秒
        return status, response_time, error_msg
    
    @staticmethod
    async def check_http_service(url: str, timeout: float = 3.0) -> Tuple[bool, int, Optional[str]]:
        """检查HTTP服务是否可访问，返回(状态, 响应时间ms, 错误信息)"""
        start_time = time.time()
        error_msg = None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout) as response:
                    status = response.status < 500
                    if not status:
                        error_msg = f"HTTP错误: {response.status}"
        except aiohttp.ClientError as e:
            error_msg = f"HTTP客户端错误: {str(e)}"
            status = False
        except asyncio.TimeoutError:
            error_msg = f"HTTP请求超时 (>{timeout}秒)"
            status = False
        except Exception as e:
            error_msg = f"HTTP请求错误: {str(e)}"
            status = False
        
        response_time = int((time.time() - start_time) * 1000)  # 毫秒
        return status, response_time, error_msg
    
    @classmethod
    async def check_database(cls) -> Dict[str, Any]:
        """检查数据库连接"""
        start_time = time.time()
        try:
            status = check_db_connection()
            error_msg = None if status else "数据库连接失败"
        except Exception as e:
            status = False
            error_msg = f"数据库连接异常: {str(e)}"
        
        response_time = int((time.time() - start_time) * 1000)  # 毫秒
        return {
            "status": status,
            "response_time_ms": response_time,
            "error": error_msg,
            "details": {
                "url": settings.DATABASE_URL.split("@")[-1].split("/")[0]  # 仅显示主机/数据库名，隐藏凭据
            }
        }
    
    @classmethod
    async def check_redis(cls) -> Dict[str, Any]:
        """检查Redis连接"""
        host = settings.REDIS_HOST
        port = settings.REDIS_PORT
        
        status, response_time, error_msg = await cls.check_tcp_service(host, port)
        
        # 尝试进一步验证Redis功能
        if status:
            try:
                import redis
                r = redis.Redis(
                    host=host, 
                    port=port,
                    password=settings.REDIS_PASSWORD,
                    db=settings.REDIS_DB,
                    socket_timeout=2
                )
                r.ping()  # 验证连接
            except Exception as e:
                status = False
                error_msg = f"Redis功能验证失败: {str(e)}"
        
        return {
            "status": status,
            "response_time_ms": response_time,
            "error": error_msg,
            "details": {
                "host": host,
                "port": port
            }
        }
    
    @classmethod
    async def check_milvus(cls) -> Dict[str, Any]:
        """检查Milvus连接"""
        host = settings.MILVUS_HOST
        port = int(settings.MILVUS_PORT)
        
        status, response_time, error_msg = await cls.check_tcp_service(host, port)
        
        # 尝试进一步验证Milvus功能
        if status:
            try:
                from pymilvus import connections, utility
                connections.connect(
                    alias="default",
                    host=host,
                    port=port
                )
                # 检查是否能获取集合
                has_collection = utility.has_collection(settings.MILVUS_COLLECTION)
                connections.disconnect("default")
            except Exception as e:
                status = False
                error_msg = f"Milvus功能验证失败: {str(e)}"
        
        return {
            "status": status,
            "response_time_ms": response_time,
            "error": error_msg,
            "details": {
                "host": host,
                "port": port,
                "collection": settings.MILVUS_COLLECTION
            }
        }
    
    @classmethod
    async def check_minio(cls) -> Dict[str, Any]:
        """检查MinIO连接"""
        endpoint = settings.MINIO_ENDPOINT
        if ":" in endpoint:
            host, port_str = endpoint.split(":")
            port = int(port_str)
        else:
            host = endpoint
            port = 9000  # 默认端口
        
        status, response_time, error_msg = await cls.check_tcp_service(host, port)
        
        # 尝试进一步验证MinIO功能
        if status:
            try:
                from minio import Minio
                client = Minio(
                    endpoint,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=settings.MINIO_SECURE
                )
                
                # 检查bucket是否存在
                bucket_exists = client.bucket_exists(settings.MINIO_BUCKET)
                if not bucket_exists:
                    logger.warning(f"MinIO存储桶不存在: {settings.MINIO_BUCKET}")
            except Exception as e:
                status = False
                error_msg = f"MinIO功能验证失败: {str(e)}"
        
        return {
            "status": status,
            "response_time_ms": response_time,
            "error": error_msg,
            "details": {
                "endpoint": endpoint,
                "bucket": settings.MINIO_BUCKET
            }
        }
    
    @classmethod
    async def check_rabbitmq(cls) -> Dict[str, Any]:
        """检查RabbitMQ连接"""
        host = settings.RABBITMQ_HOST
        port = settings.RABBITMQ_PORT
        
        status, response_time, error_msg = await cls.check_tcp_service(host, port)
        
        # 尝试进一步验证RabbitMQ功能
        if status:
            try:
                import pika
                credentials = pika.PlainCredentials(
                    settings.RABBITMQ_USER, 
                    settings.RABBITMQ_PASSWORD
                )
                connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=host,
                        port=port,
                        credentials=credentials,
                        connection_attempts=1,
                        socket_timeout=2
                    )
                )
                connection.close()
            except Exception as e:
                status = False
                error_msg = f"RabbitMQ功能验证失败: {str(e)}"
        
        return {
            "status": status,
            "response_time_ms": response_time,
            "error": error_msg,
            "details": {
                "host": host,
                "port": port
            }
        }
    
    @classmethod
    async def check_nacos(cls) -> Dict[str, Any]:
        """检查Nacos连接"""
        host, port = settings.NACOS_SERVER_ADDRESSES.split(':')
        port = int(port)
        
        status, response_time, error_msg = await cls.check_tcp_service(host, port)
        
        # 尝试进一步验证Nacos API
        if status:
            try:
                nacos_url = f"http://{host}:{port}/nacos/v1/ns/instance/list"
                status_resp, resp_time, http_err = await cls.check_http_service(nacos_url)
                if not status_resp:
                    status = False
                    error_msg = http_err
            except Exception as e:
                status = False
                error_msg = f"Nacos API验证失败: {str(e)}"
        
        return {
            "status": status,
            "response_time_ms": response_time,
            "error": error_msg,
            "details": {
                "server_addresses": settings.NACOS_SERVER_ADDRESSES,
                "namespace": settings.NACOS_NAMESPACE,
                "group": settings.NACOS_GROUP
            }
        }
    
    @classmethod
    async def check_all_services(cls) -> Dict[str, Dict[str, Any]]:
        """检查所有关键依赖服务"""
        results = {}
        
        # 创建所有检查任务
        tasks = [
            ("database", cls.check_database()),
            ("redis", cls.check_redis()),
            ("milvus", cls.check_milvus()),
            ("minio", cls.check_minio()),
            ("rabbitmq", cls.check_rabbitmq()),
            ("nacos", cls.check_nacos())
        ]
        
        # 并行执行所有检查
        for name, task in tasks:
            try:
                results[name] = await task
            except Exception as e:
                logger.error(f"检查服务 {name} 时出错: {str(e)}")
                results[name] = {
                    "status": False,
                    "response_time_ms": 0,
                    "error": f"检查过程异常: {str(e)}",
                    "details": {}
                }
        
        return results
