"""
基础工具注册模块

提供将基础工具注册到系统中的功能。
"""

from typing import Dict, Any, List, Optional
import logging
from fastapi import FastAPI

logger = logging.getLogger(__name__)

def register_base_tools(app: FastAPI, settings: Dict[str, Any]) -> None:
    """注册基础工具到系统中
    
    Args:
        app: FastAPI应用实例
        settings: 系统设置
    """
    from app.tools.base.subquestion_decomposer import SubQuestionDecomposer
    from app.tools.base.qa_router import QARouter
    
    logger.info("注册基础工具...")
    
    # 获取服务实例
    try:
        from app.services.llm_service import get_llm_service
        llm_service = get_llm_service()
    except ImportError:
        logger.warning("LLM服务不可用，部分基础工具功能将受限")
        llm_service = None
        
    try:
        from app.services.mcp_service import get_mcp_service
        mcp_service = get_mcp_service()
    except ImportError:
        logger.warning("MCP服务不可用，部分基础工具功能将受限")
        mcp_service = None
        
    try:
        from app.services.knowledge_base_service import get_knowledge_base_service
        kb_service = get_knowledge_base_service()
    except ImportError:
        logger.warning("知识库服务不可用，部分基础工具功能将受限")
        kb_service = None
        
    try:
        from app.services.qa_dataset_service import get_qa_dataset_service
        qa_dataset_service = get_qa_dataset_service()
    except ImportError:
        logger.warning("问答数据集服务不可用，部分基础工具功能将受限")
        qa_dataset_service = None
        
    try:
        from app.services.search_service import get_search_service
        search_service = get_search_service()
    except ImportError:
        logger.warning("搜索服务不可用，部分基础工具功能将受限")
        search_service = None
    
    # 初始化工具实例
    try:
        # 创建子问题拆分器实例
        subquestion_decomposer = SubQuestionDecomposer(
            llm_service=llm_service,
            mcp_service=mcp_service,
            mode=settings.get("SUBQUESTION_DECOMPOSER_MODE", "basic"),
            max_subquestions=settings.get("SUBQUESTION_DECOMPOSER_MAX_SUBQUESTIONS", 5),
            structured_output=settings.get("SUBQUESTION_DECOMPOSER_STRUCTURED_OUTPUT", True)
        )
        
        # 创建问答路由器实例
        qa_router = QARouter(
            llm_service=llm_service,
            kb_service=kb_service,
            qa_dataset_service=qa_dataset_service,
            default_mode=settings.get("QA_ROUTER_DEFAULT_MODE", "sequential"),
            use_llm_for_routing=settings.get("QA_ROUTER_USE_LLM", True)
        )
        
        # 注册到应用状态
        app.state.subquestion_decomposer = subquestion_decomposer
        app.state.qa_router = qa_router
        
        logger.info("基础工具注册完成")
        
    except Exception as e:
        logger.error(f"基础工具注册失败: {str(e)}")
        
def get_subquestion_decomposer(app: FastAPI) -> Optional["SubQuestionDecomposer"]:
    """获取子问题拆分器实例
    
    Args:
        app: FastAPI应用实例
        
    Returns:
        子问题拆分器实例
    """
    return getattr(app.state, "subquestion_decomposer", None)
    
def get_qa_router(app: FastAPI) -> Optional["QARouter"]:
    """获取问答路由器实例
    
    Args:
        app: FastAPI应用实例
        
    Returns:
        问答路由器实例
    """
    return getattr(app.state, "qa_router", None)
