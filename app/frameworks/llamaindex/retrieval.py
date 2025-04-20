"""
LlamaIndex Retrieval Module: Handles advanced context-aware document retrieval
Leverages LlamaIndex's strengths in hierarchical retrieval and query engines
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

# Custom prompt templates for better control over response format
DEFAULT_TEXT_QA_PROMPT_TMPL = (
    "Context information is below.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Given the context information and not prior knowledge, "
    "answer the question: {query_str}\n"
    "If the answer cannot be found in the context, "
    "respond with 'I don't have enough information to answer this question.'\n"
    "Answer in a concise and helpful manner."
)

DEFAULT_REFINE_PROMPT_TMPL = (
    "The original question is: {query_str}\n"
    "We have provided an existing answer: {existing_answer}\n"
    "We have the opportunity to refine the existing answer "
    "with some more context below.\n"
    "------------\n"
    "{context_msg}\n"
    "------------\n"
    "If the context isn't useful, return the existing answer. "
    "Otherwise, refine the existing answer using the new context."
)

def get_retriever(index: VectorStoreIndex, similarity_top_k: int = 5):
    """Get a vector retriever with customized settings"""
    return VectorIndexRetriever(
        index=index,
        similarity_top_k=similarity_top_k
    )

def get_query_engine(
    index: VectorStoreIndex,
    similarity_top_k: int = 5,
    similarity_cutoff: Optional[float] = 0.7
):
    """Get a query engine with customized settings"""
    # Create retriever
    retriever = get_retriever(index, similarity_top_k)
    
    # Create prompt templates
    text_qa_template = PromptTemplate(DEFAULT_TEXT_QA_PROMPT_TMPL)
    refine_template = PromptTemplate(DEFAULT_REFINE_PROMPT_TMPL)
    
    # Define postprocessors
    postprocessors = []
    if similarity_cutoff is not None:
        postprocessors.append(SimilarityPostprocessor(similarity_cutoff=similarity_cutoff))
    
    # Create query engine
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
    Retrieve relevant documents using LlamaIndex
    
    Args:
        query: Query string to search for
        index: LlamaIndex to search in
        top_k: Number of documents to retrieve
        similarity_cutoff: Optional minimum similarity score
        
    Returns:
        List of document dictionaries with content and metadata
    """
    # Create retriever
    retriever = get_retriever(index, top_k)
    
    # Create query bundle
    query_bundle = QueryBundle(query)
    
    # Retrieve nodes
    nodes = retriever.retrieve(query_bundle)
    
    # Filter by similarity cutoff if specified
    if similarity_cutoff is not None:
        nodes = [node for node in nodes if node.score is None or node.score >= similarity_cutoff]
    
    # Format results
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
    Query documents and get a synthesized answer
    
    Args:
        query: Query string to search for
        index: LlamaIndex to search in
        top_k: Number of documents to retrieve
        similarity_cutoff: Optional minimum similarity score
        return_sources: Whether to include source documents in response
        
    Returns:
        Dictionary with answer and optional source documents
    """
    # Get query engine
    query_engine = get_query_engine(index, top_k, similarity_cutoff)
    
    # Set response mode to include source nodes if requested
    if return_sources:
        query_engine.response_mode = "tree_summarize"  # To get source nodes in response
    
    # Execute query
    response = await query_engine.aquery(query)
    
    # Prepare result
    result = {
        "answer": response.response,
    }
    
    # Include sources if requested
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
    Create a custom query engine with a specific template
    
    Args:
        index: LlamaIndex to use
        query_template: Custom prompt template for query
        stream: Whether to enable streaming response
        
    Returns:
        Custom query engine
    """
    # Create custom prompt template
    custom_prompt = PromptTemplate(query_template)
    
    # Create retriever
    retriever = get_retriever(index)
    
    # Create query engine with custom prompt
    query_engine = RetrieverQueryEngine.from_args(
        retriever=retriever,
        text_qa_template=custom_prompt,
        streaming=stream
    )
    
    return query_engine
