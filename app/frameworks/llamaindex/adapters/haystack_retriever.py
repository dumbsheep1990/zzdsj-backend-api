"""
HayStack适配器模块: 将HayStack问答能力封装为LlamaIndex检索器
实现SOLID原则中的接口隔离和单一职责
"""

from typing import List, Dict, Any, Optional, Tuple
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, Document, TextNode
from llama_index.core.query_engine import RetrieverQueryEngine
from app.frameworks.haystack.reader import extract_answers, answer_with_references

class HaystackRetriever(BaseRetriever):
    """
    基于Haystack的LlamaIndex检索器
    将HayStack的提取式问答能力封装为LlamaIndex检索器
    """
    
    def __init__(
        self, 
        knowledge_base_id: Optional[int] = None, 
        model_name: Optional[str] = None, 
        top_k: int = 3,
        similarity_cutoff: float = 0.7
    ):
        """
        初始化Haystack检索器
        
        参数:
            knowledge_base_id: 知识库ID，用于获取文档
            model_name: 模型名称，用于问答
            top_k: 返回的最大结果数
            similarity_cutoff: 相似度阈值，低于此值的结果将被过滤
        """
        self.model_name = model_name
        self.top_k = top_k
        self.knowledge_base_id = knowledge_base_id
        self.similarity_cutoff = similarity_cutoff
        super().__init__()
    
    async def _aretrieve(
        self, 
        query_str: str, 
        contexts: List[Dict[str, Any]] = None, 
        **kwargs
    ) -> List[NodeWithScore]:
        """
        使用Haystack执行提取式问答检索
        
        参数:
            query_str: 查询文本
            contexts: 预先提供的上下文，如果为None则从知识库获取
            **kwargs: 额外参数
            
        返回:
            包含答案的NodeWithScore列表
        """
        try:
            # 如果未提供上下文，可以从知识库获取
            if contexts is None and hasattr(self, "_get_contexts"):
                contexts = await self._get_contexts(
                    query_str, 
                    self.knowledge_base_id, 
                    self.top_k
                )
                
            if not contexts:
                return []
            
            # 使用Haystack提取答案
            answers = extract_answers(
                question=query_str,
                contexts=contexts,
                model_name=self.model_name,
                top_k=self.top_k
            )
            
            # 转换为LlamaIndex节点
            nodes = []
            for ans in answers:
                # 将分数限制在0-1范围
                score = min(max(float(ans["score"]), 0.0), 1.0)
                
                # 跳过低于阈值的结果
                if score < self.similarity_cutoff:
                    continue
                
                # 创建节点
                node = NodeWithScore(
                    node=TextNode(
                        text=ans["context"],
                        metadata={
                            "answer": ans["answer"],
                            "document_id": ans.get("document_id"),
                            "start_idx": ans.get("start_idx"),
                            "end_idx": ans.get("end_idx")
                        }
                    ),
                    score=score
                )
                nodes.append(node)
            
            return nodes
        except Exception as e:
            import logging
            logging.error(f"Haystack检索器错误: {str(e)}")
            return []
    
    def as_query_engine(
        self, 
        **kwargs
    ) -> RetrieverQueryEngine:
        """
        将检索器转换为查询引擎
        
        参数:
            **kwargs: 传递给查询引擎的参数
            
        返回:
            配置好的查询引擎
        """
        return RetrieverQueryEngine.from_args(
            retriever=self,
            **kwargs
        )


async def _get_contexts_from_knowledge_base(
    query: str, 
    knowledge_base_id: int, 
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    从知识库获取上下文
    这是一个辅助函数，用于在没有提供上下文时从知识库获取
    
    参数:
        query: 查询文本
        knowledge_base_id: 知识库ID
        top_k: 返回的最大结果数
        
    返回:
        上下文列表
    """
    from app.frameworks.llamaindex.retrieval import query_index
    
    try:
        # 使用LlamaIndex检索相关文档
        results = await query_index(
            query=query,
            knowledge_base_id=knowledge_base_id,
            top_k=top_k
        )
        
        # 转换为所需格式
        contexts = []
        for result in results:
            contexts.append({
                "content": result.get("content", ""),
                "metadata": {
                    "document_id": result.get("document_id"),
                    "segment_id": result.get("segment_id")
                }
            })
        
        return contexts
    except Exception as e:
        import logging
        logging.error(f"获取知识库上下文错误: {str(e)}")
        return []


def create_haystack_retriever(
    knowledge_base_id: Optional[int] = None,
    model_name: Optional[str] = None,
    top_k: int = 3,
    similarity_cutoff: float = 0.7
) -> HaystackRetriever:
    """
    创建Haystack检索器的工厂函数
    
    参数:
        knowledge_base_id: 知识库ID
        model_name: 模型名称
        top_k: 返回的最大结果数
        similarity_cutoff: 相似度阈值
        
    返回:
        配置好的Haystack检索器
    """
    retriever = HaystackRetriever(
        knowledge_base_id=knowledge_base_id,
        model_name=model_name,
        top_k=top_k,
        similarity_cutoff=similarity_cutoff
    )
    
    # 添加获取上下文的方法
    setattr(retriever, "_get_contexts", _get_contexts_from_knowledge_base)
    
    return retriever
