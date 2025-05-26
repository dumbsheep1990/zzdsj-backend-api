from typing import List, Dict, Any, Optional, Union
import logging
import httpx
import os
from pydantic import BaseModel, Field
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

class RerankRequest(BaseModel):
    """重排序请求"""
    query: str
    documents: List[str]
    metadata: Optional[List[Dict[str, Any]]] = None

class UniversalRerankAdapter:
    """通用重排序适配器，从系统配置读取模型配置"""
    
    def __init__(self, model_name: str = None):
        """初始化适配器"""
        self.model_name = model_name
        self.model_config = None
        self.client = None
        self.model = None
        self.initialized = False
    
    async def initialize(self) -> bool:
        """从系统配置初始化模型"""
        if self.initialized:
            return True
            
        try:
            # 如果没有指定模型名称，使用默认模型
            if not self.model_name:
                self.model_name = getattr(settings, "DEFAULT_RERANK_MODEL", "default")
            
            # 从配置中获取模型配置
            self.model_config = self._get_model_config(self.model_name)
            
            if not self.model_config:
                logger.error(f"找不到重排序模型配置: {self.model_name}")
                return False
            
            # 如果模型类型是cross_encoder，初始化本地模型
            if self.model_config.get("type") == "cross_encoder":
                try:
                    from sentence_transformers import CrossEncoder
                    self.model = CrossEncoder(self.model_config.get("model_path"))
                    logger.info(f"本地跨编码器模型初始化成功: {self.model_name}")
                except Exception as e:
                    logger.error(f"本地跨编码器模型初始化失败: {str(e)}")
                    return False
            
            # 对于API类型的模型，初始化HTTP客户端
            elif self.model_config.get("type") in ["api", "openai", "openai_compatible"]:
                api_base = self.model_config.get("api_base")
                api_key = self.model_config.get("api_key")
                
                if not api_base:
                    logger.error(f"API基础URL未配置: {self.model_name}")
                    return False
                
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                
                self.client = httpx.AsyncClient(
                    base_url=api_base,
                    headers=headers,
                    timeout=30.0
                )
                logger.info(f"API客户端初始化成功: {self.model_name}")
            
            # 其他类型的模型，如bm25
            else:
                logger.info(f"使用默认重排序方法: {self.model_name}")
            
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"重排序适配器初始化失败: {str(e)}")
            return False
    
    async def rerank(self, query: str, documents: List[str]) -> List[float]:
        """执行重排序"""
        if not self.initialized:
            if not await self.initialize():
                logger.warning("模型初始化失败，返回默认分数")
                return [0.5] * len(documents)
        
        try:
            model_type = self.model_config.get("type", "default")
            
            # 根据模型类型选择不同的重排序方法
            if model_type == "cross_encoder":
                return await self._rerank_with_cross_encoder(query, documents)
            elif model_type in ["api", "openai", "openai_compatible"]:
                return await self._rerank_with_api(query, documents)
            else:
                return await self._rerank_with_default(query, documents)
                
        except Exception as e:
            logger.error(f"重排序失败: {str(e)}")
            return [0.5] * len(documents)  # 默认分数
    
    async def _rerank_with_cross_encoder(self, query: str, documents: List[str]) -> List[float]:
        """使用本地跨编码器模型重排序"""
        try:
            # 创建查询-文档对
            pairs = [(query, doc) for doc in documents]
            
            # 计算相关性分数
            scores = self.model.predict(pairs)
            
            # 确保返回列表格式
            return scores.tolist() if hasattr(scores, "tolist") else scores
            
        except Exception as e:
            logger.error(f"跨编码器重排序失败: {str(e)}")
            return await self._rerank_with_default(query, documents)
    
    async def _rerank_with_api(self, query: str, documents: List[str]) -> List[float]:
        """使用API重排序"""
        try:
            if not self.client:
                logger.error("API客户端未初始化")
                return await self._rerank_with_default(query, documents)
            
            # 获取API配置
            api_path = self.model_config.get("api_path", "/reranking")
            request_format = self.model_config.get("request_format", "openai")
            response_format = self.model_config.get("response_format", "openai")
            
            # 根据请求格式构建请求体
            payload = self._build_request_payload(query, documents, request_format)
            
            # 发送请求
            response = await self.client.post(api_path, json=payload)
            response.raise_for_status()
            result = response.json()
            
            # 根据响应格式解析结果
            scores = self._parse_response(result, documents, response_format)
            
            return scores
            
        except Exception as e:
            logger.error(f"API重排序失败: {str(e)}")
            return await self._rerank_with_default(query, documents)
    
    async def _rerank_with_default(self, query: str, documents: List[str]) -> List[float]:
        """使用默认BM25方法重排序"""
        try:
            from rank_bm25 import BM25Okapi
            import jieba
            
            # 分词
            tokenized_query = list(jieba.cut(query))
            tokenized_docs = [list(jieba.cut(doc)) for doc in documents]
            
            # 创建BM25模型
            bm25 = BM25Okapi(tokenized_docs)
            
            # 计算分数
            scores = bm25.get_scores(tokenized_query)
            
            # 标准化到[0,1]区间
            max_score = max(scores) if len(scores) > 0 else 1.0
            min_score = min(scores) if len(scores) > 0 else 0.0
            score_range = max_score - min_score
            
            if score_range > 0:
                scores = [(s - min_score) / score_range for s in scores]
            else:
                scores = [0.5] * len(scores)
            
            return scores
            
        except Exception as e:
            logger.error(f"默认重排序失败: {str(e)}")
            return [0.5] * len(documents)  # 默认分数
    
    def _build_request_payload(self, query: str, documents: List[str], format_type: str) -> Dict[str, Any]:
        """根据不同格式构建请求体"""
        if format_type == "openai":
            return {
                "model": self.model_config.get("model_id", self.model_name),
                "query": query,
                "documents": documents
            }
        elif format_type == "baidu":
            return {
                "query": query,
                "documents": [{"text": doc} for doc in documents],
                "return_documents": False
            }
        elif format_type == "zhipu":
            return {
                "model": self.model_config.get("model_id", self.model_name),
                "query": query,
                "documents": documents
            }
        elif format_type == "xunfei":
            return {
                "header": {
                    "app_id": self.model_config.get("app_id"),
                    "uid": "rerank_user"
                },
                "parameter": {
                    "rerank": {
                        "domain": self.model_config.get("model_id", "general")
                    }
                },
                "payload": {
                    "query": query,
                    "documents": documents
                }
            }
        else:
            # 默认格式
            return {
                "query": query,
                "documents": documents,
                "model": self.model_config.get("model_id", self.model_name)
            }
    
    def _parse_response(self, response: Dict[str, Any], documents: List[str], format_type: str) -> List[float]:
        """根据不同格式解析响应"""
        scores = [0.0] * len(documents)
        
        try:
            if format_type == "openai":
                # OpenAI格式: {"data": [{"document_index": 0, "relevance_score": 0.92}, ...]}
                if "data" in response:
                    for item in response["data"]:
                        if "document_index" in item and "relevance_score" in item:
                            idx = item["document_index"]
                            if 0 <= idx < len(scores):
                                scores[idx] = item["relevance_score"]
            
            elif format_type == "baidu":
                # 百度格式: {"results": [{"document_idx": 0, "relevance_score": 0.92}, ...]}
                if "results" in response:
                    for item in response["results"]:
                        if "document_idx" in item and "relevance_score" in item:
                            idx = item["document_idx"]
                            if 0 <= idx < len(scores):
                                scores[idx] = item["relevance_score"]
            
            elif format_type == "zhipu":
                # 智谱格式: {"data": {"results": [{"document_index": 0, "relevance_score": 0.92}, ...]}}
                if "data" in response and "results" in response["data"]:
                    for item in response["data"]["results"]:
                        if "document_index" in item and "relevance_score" in item:
                            idx = item["document_index"]
                            if 0 <= idx < len(scores):
                                scores[idx] = item["relevance_score"]
            
            elif format_type == "xunfei":
                # 讯飞格式: {"payload": {"results": [{"index": 0, "score": 0.92}, ...]}}
                if "payload" in response and "results" in response["payload"]:
                    for item in response["payload"]["results"]:
                        if "index" in item and "score" in item:
                            idx = item["index"]
                            if 0 <= idx < len(scores):
                                scores[idx] = item["score"]
            
            else:
                # 通用格式，尝试多种可能的格式
                # 尝试格式1: 有data数组
                if "data" in response:
                    data = response["data"]
                    if isinstance(data, list):
                        for item in data:
                            idx = item.get("document_index", item.get("index", -1))
                            score = item.get("relevance_score", item.get("score", 0.0))
                            if 0 <= idx < len(scores):
                                scores[idx] = score
                
                # 尝试格式2: 有results数组
                elif "results" in response:
                    results = response["results"]
                    if isinstance(results, list):
                        for item in results:
                            idx = item.get("document_index", item.get("index", -1))
                            score = item.get("relevance_score", item.get("score", 0.0))
                            if 0 <= idx < len(scores):
                                scores[idx] = score
        
        except Exception as e:
            logger.error(f"解析响应失败: {str(e)}")
        
        return scores
    
    def _get_model_config(self, model_name: str) -> Dict[str, Any]:
        """从环境变量获取模型配置"""
        # 标准化模型名称，将连字符和点替换为下划线
        normalized_name = model_name.replace('-', '_').replace('.', '_').lower()
        
        # 检查是否是跨编码器模型
        if normalized_name.startswith('cross_encoder'):
            # 处理跨编码器模型
            if normalized_name == 'cross_encoder_miniml' or 'miniml' in normalized_name:
                return self._get_cross_encoder_miniml_config()
            elif normalized_name == 'cross_encoder_multilingual' or 'multilingual' in normalized_name:
                return self._get_cross_encoder_multilingual_config()
            else:
                # 通用跨编码器模型处理
                return {
                    "type": "cross_encoder",
                    "name": f"跨编码器模型 {model_name}",
                    "description": "本地跨编码器重排序模型",
                    "model_path": model_name if '/' in model_name else f"cross-encoder/{model_name}"
                }
        
        # 检查是否是OpenAI模型
        elif normalized_name.startswith('openai') or model_name == 'text-embedding-3-large':
            return self._get_openai_config()
        
        # 检查是否是百度模型
        elif normalized_name.startswith('baidu') or normalized_name == 'ernie_rerank':
            return self._get_baidu_config()
        
        # 检查是否是智谱模型
        elif normalized_name.startswith('zhipu') or normalized_name == 'rerank_8k':
            return self._get_zhipu_config()
        
        # 使用默认BM25模型
        else:
            logger.warning(f"找不到模型 '{model_name}'，使用默认BM25模型")
            return {
                "type": "default",
                "name": "BM25重排序",
                "description": "基于BM25的本地重排序"
            }
    
    def _get_cross_encoder_miniml_config(self) -> Dict[str, Any]:
        """获取MiniLM跨编码器模型配置"""
        enabled = getattr(settings, "RERRANK_CROSS_ENCODER_MINIML_ENABLED", True)
        if not enabled:
            logger.warning("MiniLM跨编码器模型未启用，使用默认模型")
            return self._get_default_config()
        
        model_path = getattr(settings, "RERRANK_CROSS_ENCODER_MINIML_PATH", 
                            "cross-encoder/ms-marco-MiniLM-L-6-v2")
        
        return {
            "type": "cross_encoder",
            "name": "MiniLM-L6 检索重排序模型",
            "description": "轻量级英文检索重排序模型",
            "model_path": model_path
        }
    
    def _get_cross_encoder_multilingual_config(self) -> Dict[str, Any]:
        """获取多语言跨编码器模型配置"""
        enabled = getattr(settings, "RERRANK_CROSS_ENCODER_MULTILINGUAL_ENABLED", True)
        if not enabled:
            logger.warning("多语言跨编码器模型未启用，使用默认模型")
            return self._get_cross_encoder_miniml_config()
        
        model_path = getattr(settings, "RERRANK_CROSS_ENCODER_MULTILINGUAL_PATH", 
                            "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
        
        return {
            "type": "cross_encoder",
            "name": "多语言检索重排序模型",
            "description": "支持中英文的多语言检索重排序模型",
            "model_path": model_path
        }
    
    def _get_openai_config(self) -> Dict[str, Any]:
        """获取OpenAI重排序模型配置"""
        enabled = getattr(settings, "RERRANK_OPENAI_ENABLED", False)
        if not enabled:
            logger.warning("OpenAI重排序模型未启用，使用默认模型")
            return self._get_cross_encoder_miniml_config()
        
        api_base = getattr(settings, "RERRANK_OPENAI_API_BASE", "https://api.openai.com")
        api_key = getattr(settings, "OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
        api_path = getattr(settings, "RERRANK_OPENAI_API_PATH", "/v1/reranking")
        model_id = getattr(settings, "RERRANK_OPENAI_MODEL_ID", "text-embedding-3-large")
        
        return {
            "type": "api",
            "name": "OpenAI重排序",
            "description": "OpenAI重排序API",
            "api_base": api_base,
            "api_key": api_key,
            "api_path": api_path,
            "model_id": model_id,
            "request_format": "openai",
            "response_format": "openai"
        }
    
    def _get_baidu_config(self) -> Dict[str, Any]:
        """获取百度文心重排序模型配置"""
        enabled = getattr(settings, "RERRANK_BAIDU_ENABLED", False)
        if not enabled:
            logger.warning("百度文心重排序模型未启用，使用默认模型")
            return self._get_cross_encoder_miniml_config()
        
        api_base = getattr(settings, "RERRANK_BAIDU_API_BASE", 
                         "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/rerank")
        api_key = getattr(settings, "RERRANK_BAIDU_API_KEY", "")
        secret_key = getattr(settings, "RERRANK_BAIDU_SECRET_KEY", "")
        model_id = getattr(settings, "RERRANK_BAIDU_MODEL_ID", "ernie-rerank")
        
        return {
            "type": "api",
            "name": "百度文心重排序",
            "description": "百度文心一言重排序API",
            "api_base": api_base,
            "api_key": api_key,
            "model_id": model_id,
            "params": {
                "secret_key": secret_key
            },
            "request_format": "baidu",
            "response_format": "baidu"
        }
    
    def _get_zhipu_config(self) -> Dict[str, Any]:
        """获取智谱重排序模型配置"""
        enabled = getattr(settings, "RERRANK_ZHIPU_ENABLED", False)
        if not enabled:
            logger.warning("智谱重排序模型未启用，使用默认模型")
            return self._get_cross_encoder_miniml_config()
        
        api_base = getattr(settings, "RERRANK_ZHIPU_API_BASE", "https://open.bigmodel.cn/api/paas/v4")
        api_key = getattr(settings, "RERRANK_ZHIPU_API_KEY", "")
        api_path = getattr(settings, "RERRANK_ZHIPU_API_PATH", "/rerank")
        model_id = getattr(settings, "RERRANK_ZHIPU_MODEL_ID", "rerank-8k")
        
        return {
            "type": "api",
            "name": "智谱重排序",
            "description": "智谱重排序API",
            "api_base": api_base,
            "api_key": api_key,
            "api_path": api_path,
            "model_id": model_id,
            "request_format": "zhipu",
            "response_format": "zhipu"
        }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "type": "default",
            "name": "BM25重排序",
            "description": "基于BM25的本地重排序实现"
        }
