"""
嵌入向量工具模块
提供文本到向量的转换功能，支持多种模型和服务
"""

import logging
import numpy as np
from typing import List, Optional, Union, Dict, Any
import os
import json

from app.config import settings

logger = logging.getLogger(__name__)

# 全局缓存，避免频繁加载模型
_models_cache = {}

async def get_embedding(text: str, model_name: Optional[str] = None) -> List[float]:
    """
    获取文本的嵌入向量，支持多种模型和配置
    
    参数:
        text: 要嵌入的文本
        model_name: 可选的模型名称，如果为None则使用默认模型
        
    返回:
        嵌入向量（1536维度的浮点数列表）
    """
    if not text or not text.strip():
        # 如果文本为空，返回全零向量
        dimension = getattr(settings, "VECTOR_DIMENSION", 1536)
        return [0.0] * dimension
    
    # 使用默认模型（如果未指定）
    _model_name = model_name or getattr(settings, "DEFAULT_EMBEDDING_MODEL", "text-embedding-ada-002")
    
    try:
        # 根据模型名称前缀判断提供商
        if _model_name.startswith("openai:") or "text-embedding" in _model_name:
            return await _get_openai_embedding(text, _model_name.replace("openai:", ""))
        elif _model_name.startswith("huggingface:") or _model_name.startswith("sentence-transformers/"):
            return await _get_huggingface_embedding(text, _model_name.replace("huggingface:", ""))
        elif _model_name.startswith("zhipu:") or _model_name.startswith("glm-"):
            return await _get_zhipu_embedding(text, _model_name.replace("zhipu:", ""))
        elif _model_name.startswith("bce:") or _model_name.startswith("bce-"):
            return await _get_bce_embedding(text, _model_name.replace("bce:", ""))
        else:
            # 默认使用OpenAI
            return await _get_openai_embedding(text, _model_name)
    except Exception as e:
        logger.error(f"获取嵌入向量时出错: {str(e)}")
        # 返回全零向量作为兜底方案
        dimension = getattr(settings, "VECTOR_DIMENSION", 1536)
        return [0.0] * dimension

async def _get_openai_embedding(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """使用OpenAI API获取嵌入向量"""
    try:
        # 动态导入，减少不必要的依赖加载
        from openai import AsyncOpenAI
        
        # 准备API密钥和基础URL
        api_key = settings.OPENAI_API_KEY
        api_base = settings.OPENAI_API_BASE
        
        if not api_key:
            raise ValueError("缺少OpenAI API密钥")
        
        # 创建客户端
        client = AsyncOpenAI(api_key=api_key, base_url=api_base)
        
        # 调用API获取嵌入
        response = await client.embeddings.create(
            model=model,
            input=text,
            encoding_format="float"
        )
        
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"获取OpenAI嵌入向量时出错: {str(e)}")
        raise

async def _get_huggingface_embedding(text: str, model: str = "sentence-transformers/all-MiniLM-L6-v2") -> List[float]:
    """使用HuggingFace模型获取嵌入向量"""
    global _models_cache
    
    try:
        # 检查模型是否已加载到缓存中
        if model not in _models_cache:
            # 使用sentence-transformers库获取嵌入向量
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"加载HuggingFace模型: {model}")
            _models_cache[model] = SentenceTransformer(model)
        
        # 获取嵌入模型
        embedding_model = _models_cache[model]
        
        # 获取嵌入向量
        embedding = embedding_model.encode(text)
        
        # 确保向量维度符合要求
        desired_dim = getattr(settings, "VECTOR_DIMENSION", 1536)
        current_dim = embedding.shape[0]
        
        if current_dim == desired_dim:
            return embedding.tolist()
        elif current_dim > desired_dim:
            # 截断
            return embedding[:desired_dim].tolist()
        else:
            # 填充
            padding = np.zeros(desired_dim - current_dim)
            return np.concatenate([embedding, padding]).tolist()
    except Exception as e:
        logger.error(f"获取HuggingFace嵌入向量时出错: {str(e)}")
        raise

async def _get_zhipu_embedding(text: str, model: str = "embedding-2") -> List[float]:
    """使用智谱AI的模型获取嵌入向量"""
    try:
        # 导入智谱AI SDK
        import zhipuai
        
        # 配置API密钥
        api_key = settings.ZHIPU_API_KEY
        if not api_key:
            raise ValueError("缺少智谱AI API密钥")
        
        # 初始化客户端
        client = zhipuai.ZhipuAI(api_key=api_key)
        
        # 调用嵌入接口
        response = client.embeddings.create(
            model=model,
            input=text
        )
        
        # 提取嵌入向量
        embedding = response.data[0].embedding
        
        # 确保维度符合要求
        desired_dim = getattr(settings, "VECTOR_DIMENSION", 1536)
        current_dim = len(embedding)
        
        if current_dim == desired_dim:
            return embedding
        elif current_dim > desired_dim:
            # 截断
            return embedding[:desired_dim]
        else:
            # 填充
            padding = [0.0] * (desired_dim - current_dim)
            return embedding + padding
    except Exception as e:
        logger.error(f"获取智谱AI嵌入向量时出错: {str(e)}")
        raise

async def _get_bce_embedding(text: str, model: str = "bce-embedding-base_v1") -> List[float]:
    """使用百度智能云的嵌入模型获取向量"""
    try:
        import requests
        import time
        
        # 获取百度API配置
        api_key = settings.BAIDU_API_KEY
        secret_key = settings.BAIDU_SECRET_KEY
        if not api_key or not secret_key:
            raise ValueError("缺少百度智能云API密钥")
        
        # 获取鉴权token
        token_url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
        token_response = requests.post(token_url)
        token = token_response.json().get("access_token")
        
        if not token:
            raise ValueError("获取百度智能云API令牌失败")
        
        # 构建请求
        url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/embeddings/{model}?access_token={token}"
        headers = {'Content-Type': 'application/json'}
        payload = {"input": text}
        
        # 发送请求
        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
        
        if "error_code" in result:
            raise ValueError(f"百度智能云API错误: {result}")
        
        # 提取嵌入向量
        embedding = result.get("data", [{}])[0].get("embedding", [])
        
        # 确保维度符合要求
        desired_dim = getattr(settings, "VECTOR_DIMENSION", 1536)
        current_dim = len(embedding)
        
        if current_dim == desired_dim:
            return embedding
        elif current_dim > desired_dim:
            # 截断
            return embedding[:desired_dim]
        else:
            # 填充
            padding = [0.0] * (desired_dim - current_dim)
            return embedding + padding
    except Exception as e:
        logger.error(f"获取百度智能云嵌入向量时出错: {str(e)}")
        raise

async def batch_get_embeddings(texts: List[str], model_name: Optional[str] = None, batch_size: int = 16) -> List[List[float]]:
    """
    批量获取文本的嵌入向量
    
    参数:
        texts: 要嵌入的文本列表
        model_name: 可选的模型名称
        batch_size: 批处理大小
        
    返回:
        嵌入向量列表
    """
    results = []
    
    # 分批处理
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        
        # 并行处理当前批次
        import asyncio
        batch_results = await asyncio.gather(*[get_embedding(text, model_name) for text in batch])
        
        results.extend(batch_results)
        
        # 记录进度
        logger.debug(f"嵌入向量批处理进度: {min(i+batch_size, len(texts))}/{len(texts)}")
    
    return results

# 测试函数，便于快速验证
async def test_embedding(text: str = "这是一个测试文本，用于验证嵌入功能"):
    """测试嵌入功能"""
    try:
        # 生成嵌入向量
        embedding = await get_embedding(text)
        
        # 输出向量长度及前5个元素
        print(f"向量维度: {len(embedding)}")
        print(f"向量样本: {embedding[:5]}...")
        
        return {
            "status": "success",
            "dimension": len(embedding),
            "sample": embedding[:5]
        }
    except Exception as e:
        logger.error(f"嵌入测试失败: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
