"""
Haystack适配器模块: 将Haystack的问答能力封装为LlamaIndex检索器
实现框架间的无缝集成
"""

from typing import Any, Dict, List, Optional, Callable, Union
from llama_index.core.schema import NodeWithScore, TextNode, Document
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.query_engine import BaseQueryEngine
from llama_index.core.callbacks import CallbackManager
from app.frameworks.haystack.reader import extract_answers, answer_with_references

class HaystackRetriever(BaseRetriever):
    """
    将Haystack的问答能力封装为LlamaIndex检索器
    遵循适配器设计模式，将Haystack框架的能力集成到LlamaIndex工具链中
    """
    
    def __init__(
        self, 
        knowledge_base_id: Optional[int] = None,
        model_name: Optional[str] = None,
        top_k: int = 3,
        callback_manager: Optional[CallbackManager] = None
    ):
        """
        初始化Haystack检索器
        
        参数:
            knowledge_base_id: 知识库ID
            model_name: 模型名称
            top_k: 返回的最大答案数量
            callback_manager: 回调管理器
        """
        self.knowledge_base_id = knowledge_base_id
        self.model_name = model_name
        self.top_k = top_k
        callback_manager = callback_manager or CallbackManager([])
        super().__init__(callback_manager)
    
    async def _aretrieve(self, query_str: str, contexts: List[Dict[str, Any]] = None, **kwargs):
        """
        异步检索方法
        
        参数:
            query_str: 查询文本
            contexts: 可选的上下文列表
            **kwargs: 额外参数
            
        返回:
            检索到的节点列表
        """
        # 如果没有提供上下文且有知识库ID，则从知识库获取
        if contexts is None and self.knowledge_base_id is not None:
            contexts = await get_contexts_from_knowledge_base(
                knowledge_base_id=self.knowledge_base_id,
                query=query_str,
                top_k=self.top_k
            )
        
        # 确保有上下文
        if not contexts:
            return []
        
        # 使用Haystack提取答案
        answers = extract_answers(
            question=query_str,
            contexts=contexts,
            model_name=self.model_name,
            top_k=self.top_k
        )
        
        # 转换为NodeWithScore对象
        nodes = []
        for answer in answers:
            # 创建节点
            node = NodeWithScore(
                node=TextNode(
                    text=answer.get("answer", ""),
                    metadata={
                        "document_id": answer.get("document_id"),
                        "context": answer.get("context"),
                        "start_idx": answer.get("start_idx"),
                        "end_idx": answer.get("end_idx")
                    }
                ),
                score=answer.get("score", 0.0)
            )
            nodes.append(node)
        
        return nodes
    
    def as_query_engine(self) -> BaseQueryEngine:
        """
        将检索器转换为查询引擎
        
        返回:
            配置好的查询引擎
        """
        # 创建一个自定义查询引擎类
        class HaystackQueryEngine(BaseQueryEngine):
            def __init__(self, retriever: HaystackRetriever):
                self.retriever = retriever
                super().__init__()
            
            async def aquery(self, query_str: str):
                from llama_index.core.response.schema import Response
                
                # 使用检索器获取节点
                nodes = await self.retriever._aretrieve(query_str)
                
                if not nodes:
                    return Response(response="未找到答案")
                
                # 组合所有答案和上下文
                answers = []
                contexts = []
                
                for node in nodes:
                    answers.append(node.text)
                    context = node.metadata.get("context", "")
                    if context and context not in contexts:
                        contexts.append(context)
                
                # 构建响应
                if contexts:
                    # 如果有上下文，使用带引用的响应格式
                    response_with_refs = answer_with_references(
                        answers[0] if answers else "未找到答案",
                        contexts
                    )
                    return Response(response=response_with_refs)
                else:
                    # 否则返回简单响应
                    return Response(response=answers[0] if answers else "未找到答案")
            
            def query(self, query_str: str):
                import asyncio
                return asyncio.run(self.aquery(query_str))
        
        # 返回查询引擎实例
        return HaystackQueryEngine(self)


async def get_contexts_from_knowledge_base(
    knowledge_base_id: int,
    query: str,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    从知识库获取相关上下文
    
    参数:
        knowledge_base_id: 知识库ID
        query: 查询文本
        top_k: 返回的最大结果数量
        
    返回:
        上下文列表
    """
    from app.core.knowledge.knowledge_base_service import KnowledgeBaseService
    from app.frameworks.llamaindex.retrieval import query_index
    
    # 获取知识库信息
    kb_service = KnowledgeBaseService()
    kb = kb_service.get_by_id(knowledge_base_id)
    
    if not kb:
        return []
    
    # 获取索引名称
    index_name = kb.get("config", {}).get("index_name")
    
    if not index_name:
        return []
    
    # 查询索引
    results = await query_index(
        index_name=index_name,
        query_text=query,
        top_k=top_k
    )
    
    return results


def create_haystack_retriever(
    knowledge_base_id: Optional[int] = None,
    model_name: Optional[str] = None,
    top_k: int = 3
) -> HaystackRetriever:
    """
    创建Haystack检索器的工厂函数
    
    参数:
        knowledge_base_id: 知识库ID
        model_name: 模型名称
        top_k: 返回的最大答案数量
        
    返回:
        配置好的Haystack检索器
    """
    return HaystackRetriever(
        knowledge_base_id=knowledge_base_id,
        model_name=model_name,
        top_k=top_k
    )
