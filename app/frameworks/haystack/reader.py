"""
Haystack阅读器模块：处理文档上的精确问答
利用Haystack在提取式问答方面的优势提供事实性回答
"""

from typing import List, Dict, Any, Optional, Tuple
from haystack.document_stores import FAISSDocumentStore
from haystack.nodes import FARMReader, TransformersReader
from haystack.schema import Document
from app.config import settings

def get_reader(model_name: Optional[str] = None):
    """获取用于提取式问答的Haystack阅读器模型"""
    model = model_name or settings.HAYSTACK_READER_MODEL
    
    # 根据模型选择阅读器实现
    if "farm" in model.lower() or "bert" in model.lower() or "roberta" in model.lower():
        return FARMReader(model_name_or_path=model, use_gpu=True)
    else:
        return TransformersReader(model_name_or_path=model, use_gpu=True)

def extract_answers(
    question: str,
    contexts: List[Dict[str, Any]],
    model_name: Optional[str] = None,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    使用Haystack的提取式问答从上下文中提取精确答案
    
    参数:
        question: 要回答的问题
        contexts: 上下文字典列表，包含'content'和'metadata'键
        model_name: 可选的模型名称覆盖
        top_k: 返回的答案数量
        
    返回:
        答案字典列表，包含文本、分数和上下文
    """
    # 初始化阅读器
    reader = get_reader(model_name)
    
    # 将上下文转换为Haystack文档对象
    documents = []
    for i, ctx in enumerate(contexts):
        doc = Document(
            content=ctx.get("content", ""),
            meta=ctx.get("metadata", {})
        )
        documents.append(doc)
    
    # 从阅读器获取答案
    predictions = reader.predict(
        query=question,
        documents=documents,
        top_k=top_k
    )
    
    # 格式化答案
    answers = []
    for ans in predictions["answers"]:
        answers.append({
            "answer": ans.answer,
            "score": float(ans.score),
            "context": ans.context,
            "document_id": ans.meta.get("document_id", None) if ans.meta else None,
            "start_idx": ans.offsets_in_document[0].start if ans.offsets_in_document else None,
            "end_idx": ans.offsets_in_document[0].end if ans.offsets_in_document else None
        })
    
    return answers

def answer_with_references(
    question: str,
    contexts: List[Dict[str, Any]],
    model_name: Optional[str] = None,
    top_k: int = 3
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    获取带有支持参考的答案
    
    参数:
        question: 要回答的问题
        contexts: 上下文字典列表
        model_name: 可选的模型名称覆盖
        top_k: 要考虑的答案数量
        
    返回:
        (最佳答案文本, 支持参考字典列表)的元组
    """
    # 获取提取式答案
    answers = extract_answers(question, contexts, model_name, top_k)
    
    if not answers:
        return "我在可用信息中找不到该问题的答案。", []
    
    # 最佳答案
    best_answer = answers[0]["answer"]
    
    # 支持参考
    references = []
    for ans in answers:
        references.append({
            "content": ans["context"],
            "relevance": ans["score"],
            "document_id": ans["document_id"],
            "highlight_start": ans["start_idx"],
            "highlight_end": ans["end_idx"]
        })
    
    return best_answer, references
