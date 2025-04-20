"""
Haystack Reader Module: Handles precise question answering over documents
Leverages Haystack's strength in extractive QA for factual answers
"""

from typing import List, Dict, Any, Optional, Tuple
from haystack.document_stores import FAISSDocumentStore
from haystack.nodes import FARMReader, TransformersReader
from haystack.schema import Document
from app.config import settings

def get_reader(model_name: Optional[str] = None):
    """Get a Haystack reader model for extractive QA"""
    model = model_name or settings.HAYSTACK_READER_MODEL
    
    # Choose reader implementation based on model
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
    Extract precise answers from contexts using Haystack's extractive QA
    
    Args:
        question: Question to answer
        contexts: List of context dictionaries with 'content' and 'metadata' keys
        model_name: Optional model name override
        top_k: Number of answers to return
        
    Returns:
        List of answer dictionaries with text, score, and context
    """
    # Initialize reader
    reader = get_reader(model_name)
    
    # Convert contexts to Haystack Document objects
    documents = []
    for i, ctx in enumerate(contexts):
        doc = Document(
            content=ctx.get("content", ""),
            meta=ctx.get("metadata", {})
        )
        documents.append(doc)
    
    # Get answers from reader
    predictions = reader.predict(
        query=question,
        documents=documents,
        top_k=top_k
    )
    
    # Format answers
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
    Get an answer with supporting references
    
    Args:
        question: Question to answer
        contexts: List of context dictionaries
        model_name: Optional model name override
        top_k: Number of answers to consider
        
    Returns:
        Tuple of (best answer text, list of supporting reference dictionaries)
    """
    # Get extractive answers
    answers = extract_answers(question, contexts, model_name, top_k)
    
    if not answers:
        return "I couldn't find an answer to that question in the available information.", []
    
    # Best answer
    best_answer = answers[0]["answer"]
    
    # Supporting references
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
