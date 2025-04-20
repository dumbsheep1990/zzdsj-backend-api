"""
LlamaIndex检索模块: 处理高级上下文感知文档检索
利用LlamaIndex在分层检索和查询引擎方面的优势
"""

from typing import List, Dict, Any, Optional, Union
import json

from llama_index.core import (
    VectorStoreIndex, 
    Response,
    QueryBundle
)
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.prompts import PromptTemplate
from app.config import settings

# 自定义提示模板，更好地控制响应格式
DEFAULT_TEXT_QA_PROMPT_TMPL = (
    "以下是上下文信息。\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "仅根据上下文信息，不使用先验知识，"
    "回答问题: {query_str}\n"
    "如果在上下文中找不到答案，"
    "请回答'我没有足够的信息来回答这个问题。'\n"
    "以简洁有帮助的方式回答。"
)

DEFAULT_REFINE_PROMPT_TMPL = (
    "原始问题是: {query_str}\n"
    "我们已经提供了现有答案: {existing_answer}\n"
    "我们有机会使用下面的更多上下文来完善现有答案。\n"
    "------------\n"
    "{context_msg}\n"
    "------------\n"
    "如果上下文没有用，返回现有答案。"
    "否则，使用新上下文完善现有答案。"
)

def get_retriever(index: VectorStoreIndex, similarity_top_k: int = 5):
    """获取具有自定义设置的向量检索器"""
    return VectorIndexRetriever(
        index=index,
        similarity_top_k=similarity_top_k
    )

def get_query_engine(
    index: VectorStoreIndex,
    similarity_top_k: int = 5,
    similarity_cutoff: Optional[float] = 0.7
):
    """获取具有自定义设置的查询引擎"""
    # 创建检索器
    retriever = get_retriever(index, similarity_top_k)
    
    # 创建提示模板
    text_qa_template = PromptTemplate(DEFAULT_TEXT_QA_PROMPT_TMPL)
    refine_template = PromptTemplate(DEFAULT_REFINE_PROMPT_TMPL)
    
    # 定义后处理器
    postprocessors = []
    if similarity_cutoff is not None:
        postprocessors.append(SimilarityPostprocessor(similarity_cutoff=similarity_cutoff))
    
    # 创建查询引擎
    query_engine = RetrieverQueryEngine.from_args(
        retriever=retriever,
        text_qa_template=text_qa_template,
        refine_template=refine_template,
        node_postprocessors=postprocessors
    )
    
    return query_engine

async def retrieve_documents(
    query: str,
    index: VectorStoreIndex,
    top_k: int = 5,
    similarity_cutoff: Optional[float] = 0.7
) -> List[Dict[str, Any]]:
    """
    使用LlamaIndex检索相关文档
    
    参数:
        query: 要搜索的查询字符串
        index: 要搜索的LlamaIndex
        top_k: 要检索的文档数量
        similarity_cutoff: 可选的最小相似度分数
        
    返回:
        文档字典列表，包含内容和元数据
    """
    # 创建检索器
    retriever = get_retriever(index, top_k)
    
    # 创建查询包
    query_bundle = QueryBundle(query)
    
    # 检索节点
    nodes = retriever.retrieve(query_bundle)
    
    # 如果指定了相似度阈值，则过滤
    if similarity_cutoff is not None:
        nodes = [node for node in nodes if node.score is None or node.score >= similarity_cutoff]
    
    # 格式化结果
    results = []
    for node in nodes:
        results.append({
            "content": node.text,
            "metadata": node.metadata,
            "score": node.score if node.score is not None else 1.0,
            "node_id": node.node_id
        })
    
    return results

async def query_documents(
    query: str,
    index: VectorStoreIndex,
    top_k: int = 5,
    similarity_cutoff: Optional[float] = 0.7,
    return_sources: bool = True
) -> Dict[str, Any]:
    """
    查询文档并获取综合答案
    
    参数:
        query: 要搜索的查询字符串
        index: 要搜索的LlamaIndex
        top_k: 要检索的文档数量
        similarity_cutoff: 可选的最小相似度分数
        return_sources: 是否在响应中包含源文档
        
    返回:
        包含答案和可选源文档的字典
    """
    # 获取查询引擎
    query_engine = get_query_engine(index, top_k, similarity_cutoff)
    
    # 如果请求，设置响应模式以包含源节点
    if return_sources:
        query_engine.response_mode = "tree_summarize"  # 在响应中获取源节点
    
    # 执行查询
    response = await query_engine.aquery(query)
    
    # 准备结果
    result = {
        "answer": response.response,
    }
    
    # 如果请求，包含源
    if return_sources and hasattr(response, "source_nodes"):
        sources = []
        for node in response.source_nodes:
            sources.append({
                "content": node.text,
                "metadata": node.metadata,
                "score": node.score if node.score is not None else 1.0,
                "node_id": node.node_id
            })
        result["sources"] = sources
    
    return result

def create_custom_query_engine(
    index: VectorStoreIndex,
    query_template: str,
    stream: bool = False
):
    """
    创建具有特定模板的自定义查询引擎
    
    参数:
        index: 要使用的LlamaIndex
        query_template: 自定义查询提示模板
        stream: 是否启用流式响应
        
    返回:
        自定义查询引擎
    """
    # 创建自定义提示模板
    custom_prompt = PromptTemplate(query_template)
    
    # 创建检索器
    retriever = get_retriever(index)
    
    # 创建具有自定义提示的查询引擎
    query_engine = RetrieverQueryEngine.from_args(
        retriever=retriever,
        text_qa_template=custom_prompt,
        streaming=stream
    )
    
    return query_engine
