"""
Token计算与统计工具

提供基于InfluxDB的Token使用量计算与统计功能，作为对话的后置异步处理工具。
支持多种模型的token计算，并将结果存储到InfluxDB时序数据库中。
"""

import os
import time
import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from functools import lru_cache
import concurrent.futures

# InfluxDB客户端
try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import ASYNCHRONOUS
    INFLUXDB_AVAILABLE = True
except ImportError:
    INFLUXDB_AVAILABLE = False

# 各种token计算器
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

# 项目配置
from app.config import settings

# 日志配置
logger = logging.getLogger(__name__)


class TokenCounter:
    """Token计数器，支持多种模型的Token计算"""
    
    # 模型到编码器的映射
    MODEL_TO_ENCODING = {
        # OpenAI模型
        "gpt-3.5-turbo": "cl100k_base",
        "gpt-3.5-turbo-16k": "cl100k_base",
        "gpt-4": "cl100k_base",
        "gpt-4-32k": "cl100k_base",
        "gpt-4-turbo": "cl100k_base",
        "gpt-4-vision-preview": "cl100k_base",
        "text-embedding-ada-002": "cl100k_base",
        # Claude模型 (Anthropic)
        "claude-instant-1": "cl100k_base",  # 近似
        "claude-2": "cl100k_base",  # 近似
        "claude-3-opus": "cl100k_base",  # 近似
        "claude-3-sonnet": "cl100k_base",  # 近似
        "claude-3-haiku": "cl100k_base",  # 近似
        # 其他模型默认使用相同编码器
        "default": "cl100k_base"
    }

    @classmethod
    def get_encoder(cls, model_name: str):
        """获取模型对应的编码器"""
        if not TIKTOKEN_AVAILABLE:
            logger.warning("Tiktoken未安装，无法准确计算token数量")
            return None
        
        # 查找模型编码器
        encoding_name = cls.MODEL_TO_ENCODING.get(model_name, cls.MODEL_TO_ENCODING["default"])
        try:
            return tiktoken.get_encoding(encoding_name)
        except Exception as e:
            logger.warning(f"获取编码器失败: {e}，使用默认编码器")
            try:
                return tiktoken.get_encoding("cl100k_base")
            except Exception:
                return None

    @classmethod
    def count_tokens(cls, text: str, model_name: str = "gpt-3.5-turbo") -> int:
        """计算文本的token数量"""
        if not text:
            return 0
            
        encoder = cls.get_encoder(model_name)
        if encoder is None:
            # 如果无法获取编码器，使用近似计算方法
            # 英文约每4个字符1个token，中文约每1.5个字符1个token
            cn_char_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            en_char_count = len(text) - cn_char_count
            return int(cn_char_count / 1.5 + en_char_count / 4)
        
        try:
            # 使用编码器计算token
            tokens = encoder.encode(text)
            return len(tokens)
        except Exception as e:
            logger.warning(f"计算token失败: {e}，使用近似计算")
            # 回退到近似计算
            cn_char_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            en_char_count = len(text) - cn_char_count
            return int(cn_char_count / 1.5 + en_char_count / 4)

    @classmethod
    def count_messages_tokens(cls, messages: List[Dict[str, str]], model_name: str = "gpt-3.5-turbo") -> int:
        """计算消息列表的token数量"""
        total_tokens = 0
        
        for message in messages:
            # 每条消息有固定开销
            total_tokens += 4  # 消息开销
            
            # 计算内容tokens
            if "content" in message and message["content"]:
                total_tokens += cls.count_tokens(message["content"], model_name)
                
            # 计算名称tokens (如果有)
            if "name" in message and message["name"]:
                total_tokens += cls.count_tokens(message["name"], model_name)
                
            # 每个角色(role)也有tokens
            if "role" in message:
                total_tokens += 2  # 角色标识开销
                
        # 整体对话的基础开销
        total_tokens += 2  # 对话开销
        
        return total_tokens


class InfluxDBMetricsClient:
    """InfluxDB指标客户端，用于存储Token计算结果"""
    
    def __init__(self):
        """初始化InfluxDB客户端"""
        self._initialized = False
        self._client = None
        self._write_api = None
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        
        # 初始化客户端
        self._initialize()
    
    def _initialize(self):
        """初始化InfluxDB连接"""
        if not INFLUXDB_AVAILABLE:
            logger.warning("InfluxDB客户端未安装，请安装influxdb-client包")
            return
        
        if not settings.metrics.enabled:
            logger.info("指标统计功能未启用")
            return
            
        if not settings.metrics.influxdb_token:
            logger.warning("InfluxDB Token未设置，无法连接到InfluxDB")
            return
            
        try:
            # 创建InfluxDB客户端
            self._client = InfluxDBClient(
                url=settings.metrics.influxdb_url,
                token=settings.metrics.influxdb_token,
                org=settings.metrics.influxdb_org
            )
            
            # 创建写入API
            self._write_api = self._client.write_api(write_options=ASYNCHRONOUS)
            
            # 检查bucket是否存在，不存在则创建
            self._create_bucket_if_not_exists()
            
            self._initialized = True
            logger.info(f"InfluxDB客户端初始化成功: {settings.metrics.influxdb_url}")
        except Exception as e:
            logger.error(f"InfluxDB客户端初始化失败: {e}")
    
    def _create_bucket_if_not_exists(self):
        """检查并创建bucket如果不存在"""
        try:
            buckets_api = self._client.buckets_api()
            bucket_list = buckets_api.find_buckets().buckets
            bucket_names = [bucket.name for bucket in bucket_list]
            
            if settings.metrics.influxdb_bucket not in bucket_names:
                logger.info(f"创建InfluxDB bucket: {settings.metrics.influxdb_bucket}")
                buckets_api.create_bucket(
                    bucket_name=settings.metrics.influxdb_bucket,
                    org=settings.metrics.influxdb_org
                )
        except Exception as e:
            logger.error(f"创建bucket失败: {e}")
    
    async def write_metrics(self, 
                           user_id: str,
                           model_name: str, 
                           input_tokens: int,
                           output_tokens: int,
                           conversation_id: Optional[str] = None,
                           execution_time: Optional[float] = None,
                           additional_tags: Optional[Dict[str, str]] = None,
                           additional_fields: Optional[Dict[str, Any]] = None):
        """
        异步写入指标数据
        
        参数:
            user_id: 用户ID
            model_name: 模型名称
            input_tokens: 输入token数
            output_tokens: 输出token数
            conversation_id: 对话ID
            execution_time: 执行时间(毫秒)
            additional_tags: 额外标签
            additional_fields: 额外字段
        """
        if not self._initialized or self._write_api is None:
            return
        
        try:
            # 创建数据点
            point = Point("llm_token_usage")
            
            # 添加标签 (索引)
            point.tag("user_id", user_id)
            point.tag("model", model_name)
            if conversation_id:
                point.tag("conversation_id", conversation_id)
            
            # 添加额外标签
            if additional_tags:
                for tag_name, tag_value in additional_tags.items():
                    if tag_value:
                        point.tag(tag_name, tag_value)
            
            # 添加指标字段
            point.field("input_tokens", input_tokens)
            point.field("output_tokens", output_tokens)
            point.field("total_tokens", input_tokens + output_tokens)
            
            if execution_time is not None:
                point.field("execution_time_ms", execution_time)
            
            # 添加额外字段
            if additional_fields:
                for field_name, field_value in additional_fields.items():
                    if field_value is not None:
                        if isinstance(field_value, (int, float, bool, str)):
                            point.field(field_name, field_value)
                        else:
                            # 对于复杂类型，转换为字符串
                            point.field(field_name, str(field_value))
            
            # 设置时间戳
            point.time(datetime.utcnow())
            
            # 异步写入数据
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,
                self._write_api.write,
                settings.metrics.influxdb_bucket,
                settings.metrics.influxdb_org,
                point
            )
            
            logger.debug(f"Token统计数据已写入InfluxDB: {user_id}, {model_name}, {input_tokens+output_tokens} tokens")
            return True
        except Exception as e:
            logger.error(f"写入Token统计数据失败: {e}")
            return False


@lru_cache(maxsize=1)
def get_influxdb_client() -> InfluxDBMetricsClient:
    """获取InfluxDB客户端单例"""
    return InfluxDBMetricsClient()


class TokenMetricsService:
    """Token指标服务，提供Token计算和统计功能"""
    
    def __init__(self):
        """初始化Token指标服务"""
        self._counter = TokenCounter()
        self._db_client = get_influxdb_client()
    
    async def record_conversation_metrics(self,
                                         user_id: str,
                                         model_name: str,
                                         messages: List[Dict[str, str]],
                                         response_text: str,
                                         conversation_id: Optional[str] = None,
                                         execution_time: Optional[float] = None,
                                         additional_tags: Optional[Dict[str, str]] = None,
                                         additional_fields: Optional[Dict[str, Any]] = None):
        """
        记录对话指标
        
        参数:
            user_id: 用户ID
            model_name: 模型名称
            messages: 输入消息列表
            response_text: 响应文本
            conversation_id: 对话ID
            execution_time: 执行时间(ms) 
            additional_tags: 额外标签
            additional_fields: 额外字段
        """
        try:
            # 初始化token计数
            input_tokens = 0
            output_tokens = 0
            
            # 仅当token统计功能开启时计算token
            if settings.metrics.token_statistics:
                # 计算输入token
                input_tokens = self._counter.count_messages_tokens(messages, model_name)
                
                # 计算输出token
                output_tokens = self._counter.count_tokens(response_text, model_name)
            
            # 无论是否开启token统计，都写入基本指标数据
            await self._db_client.write_metrics(
                user_id=user_id,
                model_name=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                conversation_id=conversation_id,
                execution_time=execution_time,
                additional_tags=additional_tags,
                additional_fields=additional_fields
            )
            
            return {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            }
        except Exception as e:
            logger.error(f"记录对话指标失败: {e}")
            # 返回空结果，不中断主流程
            return {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0
            }


# 单例服务
_metrics_service = None

def get_token_metrics_service() -> TokenMetricsService:
    """获取Token指标服务实例"""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = TokenMetricsService()
    return _metrics_service


async def record_llm_usage(user_id: str,
                          model_name: str,
                          messages: List[Dict[str, str]],
                          response_text: str,
                          conversation_id: Optional[str] = None,
                          execution_time: Optional[float] = None,
                          **kwargs):
    """
    记录LLM使用情况的便捷函数
    
    参数:
        user_id: 用户ID
        model_name: 模型名称
        messages: 输入消息列表
        response_text: 响应文本
        conversation_id: 对话ID
        execution_time: 执行时间(ms)
        **kwargs: 额外参数，将被分为tags和fields
    """
    # 区分额外的tags和fields
    additional_tags = {}
    additional_fields = {}
    
    for k, v in kwargs.items():
        # 标签通常是字符串类型，用于索引
        if isinstance(v, str) and len(v) < 100:  # 标签通常较短
            additional_tags[k] = v
        else:
            # 其他类型作为字段
            additional_fields[k] = v
    
    # 获取服务并记录
    service = get_token_metrics_service()
    return await service.record_conversation_metrics(
        user_id=user_id,
        model_name=model_name,
        messages=messages,
        response_text=response_text,
        conversation_id=conversation_id,
        execution_time=execution_time,
        additional_tags=additional_tags,
        additional_fields=additional_fields
    )
