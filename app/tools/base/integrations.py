"""
基础工具集成层

提供与现有系统集成的接口和功能。
"""

from typing import Dict, Any, List, Optional, Union
import logging
from fastapi import Request, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class SubquestionRequest(BaseModel):
    """子问题拆分请求"""
    query: str = Field(..., description="用户查询")
    agent_id: Optional[str] = Field(None, description="智能体ID")
    mode: Optional[str] = Field("basic", description="拆分模式: basic 或 tool")
    max_subquestions: Optional[int] = Field(5, description="最大子问题数量")
    answer_subquestions: Optional[bool] = Field(False, description="是否回答子问题")
    knowledge_base_ids: Optional[List[str]] = Field(None, description="知识库ID列表")

class SubquestionResponse(BaseModel):
    """子问题拆分响应"""
    original_query: str = Field(..., description="原始查询")
    subquestions: List[Dict[str, Any]] = Field(..., description="子问题列表")
    reasoning: str = Field(..., description="拆分推理过程")
    execution_order: List[str] = Field(..., description="执行顺序")
    final_answer: Optional[str] = Field(None, description="最终合成答案")

class QARoutingRequest(BaseModel):
    """问答路由请求"""
    query: str = Field(..., description="用户查询")
    agent_id: Optional[str] = Field(None, description="智能体ID")
    mode: Optional[str] = Field(None, description="检索模式: sequential, parallel, single")
    knowledge_base_ids: Optional[List[str]] = Field(None, description="可用知识库ID列表")
    refine_query: Optional[bool] = Field(True, description="是否优化查询")
    perform_search: Optional[bool] = Field(True, description="是否执行搜索")

class QARoutingResponse(BaseModel):
    """问答路由响应"""
    original_query: str = Field(..., description="原始查询")
    processed_query: Optional[str] = Field(None, description="处理后的查询")
    selected_knowledge_bases: List[Dict[str, Any]] = Field(..., description="选中的知识库")
    reasoning: str = Field(..., description="路由推理过程")
    qa_pair_match: Optional[Dict[str, Any]] = Field(None, description="匹配到的问答对")
    search_results: Optional[List[Dict[str, Any]]] = Field(None, description="搜索结果")
    answer: Optional[str] = Field(None, description="最终答案")

class ProcessQueryRequest(BaseModel):
    """处理查询请求"""
    query: str = Field(..., description="用户查询")
    agent_id: Optional[str] = Field(None, description="智能体ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    tools_config: Optional[Dict[str, Any]] = Field(None, description="工具配置")
    knowledge_base_ids: Optional[List[str]] = Field(None, description="知识库ID列表")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")

class ProcessQueryResponse(BaseModel):
    """处理查询响应"""
    original_query: str = Field(..., description="原始查询")
    processed_query: str = Field(..., description="处理后的查询")
    subquestions: List[Dict[str, Any]] = Field(default_factory=list, description="子问题列表")
    route_info: Optional[Dict[str, Any]] = Field(None, description="路由信息")
    search_results: List[Dict[str, Any]] = Field(default_factory=list, description="搜索结果")
    answer: Optional[str] = Field(None, description="最终答案")
    qa_pair_match: Optional[Dict[str, Any]] = Field(None, description="匹配到的问答对")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

class BaseToolsIntegration:
    """基础工具集成类"""
    
    def __init__(self, request: Request):
        """初始化基础工具集成
        
        Args:
            request: FastAPI请求对象
        """
        self.request = request
        self.app = request.app
        
        # 获取工具实例
        from app.tools.base.register import get_subquestion_decomposer, get_qa_router
        self.subquestion_decomposer = get_subquestion_decomposer(self.app)
        self.qa_router = get_qa_router(self.app)
        
        # 获取其他服务
        self.agent_service = getattr(self.app.state, "agent_service", None)
        self.kb_service = getattr(self.app.state, "knowledge_base_service", None)
        self.search_service = getattr(self.app.state, "search_service", None)
        self.llm_service = getattr(self.app.state, "llm_service", None)
        
        # 获取数据库会话和基础工具服务
        try:
            from app.utils.database import get_db
            from app.services.base_tools_service import get_base_tools_service
            from fastapi import Depends
            
            # 获取数据库会话
            self.db = next(get_db())
            
            # 创建基础工具服务实例
            self.base_tools_service = get_base_tools_service(self.db)
        except Exception as e:
            logger.warning(f"无法初始化数据库会话或基础工具服务: {str(e)}")
            self.db = None
            self.base_tools_service = None
        
    async def decompose_query(self, request: SubquestionRequest) -> SubquestionResponse:
        """拆分查询为子问题
        
        Args:
            request: 子问题拆分请求
            
        Returns:
            子问题拆分响应
        """
        if not self.subquestion_decomposer:
            raise ValueError("子问题拆分器不可用")
            
        # 获取智能体配置（如果有）
        agent_config = None
        if request.agent_id and self.agent_service:
            try:
                agent_config = await self.agent_service.get_agent_config(request.agent_id)
            except Exception as e:
                logger.warning(f"获取智能体配置失败: {str(e)}")
        
        # 设置子问题拆分器模式
        self.subquestion_decomposer.mode = request.mode
        self.subquestion_decomposer.max_subquestions = request.max_subquestions
        
        # 执行子问题拆分
        decomposition_result = await self.subquestion_decomposer.decompose(request.query)
        
        # 如果需要回答子问题
        final_answer = None
        if request.answer_subquestions and self.search_service:
            # 获取知识库ID列表
            kb_ids = request.knowledge_base_ids or []
            
            # 回答子问题
            decomposition_result = await self.subquestion_decomposer.answer_subquestions(
                decomposition_result=decomposition_result,
                search_service=self.search_service,
                knowledge_base_ids=kb_ids
            )
            
            # 合成最终答案
            final_answer = await self.subquestion_decomposer.synthesize_final_answer(decomposition_result)
        
        # 构建响应
        return SubquestionResponse(
            original_query=decomposition_result.original_question,
            subquestions=[sq.dict() for sq in decomposition_result.subquestions],
            reasoning=decomposition_result.reasoning,
            execution_order=decomposition_result.execution_order,
            final_answer=final_answer
        )
        
    async def route_query(self, request: QARoutingRequest) -> QARoutingResponse:
        """为查询选择合适的知识库路由
        
        Args:
            request: 问答路由请求
            
        Returns:
            问答路由响应
        """
        if not self.qa_router:
            raise ValueError("问答路由器不可用")
            
        # 获取智能体配置（如果有）
        agent_config = None
        if request.agent_id and self.agent_service:
            try:
                agent_config = await self.agent_service.get_agent_config(request.agent_id)
                
                # 设置检索模式（如果请求中指定了）
                if request.mode and agent_config.get("retrieval_config"):
                    agent_config["retrieval_config"]["mode"] = request.mode
                    
            except Exception as e:
                logger.warning(f"获取智能体配置失败: {str(e)}")
        
        # 准备可用知识库列表
        available_kbs = []
        if request.knowledge_base_ids and self.kb_service:
            try:
                for kb_id in request.knowledge_base_ids:
                    kb = await self.kb_service.get_knowledge_base(kb_id)
                    if kb:
                        available_kbs.append(kb)
            except Exception as e:
                logger.warning(f"获取知识库信息失败: {str(e)}")
                
        # 如果请求中指定了执行搜索
        if request.perform_search and self.search_service:
            # 使用整合的搜索方法
            routing_result = await self.qa_router.execute_search_with_routing(
                query=request.query,
                agent_config=agent_config,
                available_knowledge_bases=available_kbs,
                search_service=self.search_service
            )
            
            # 构建响应
            return QARoutingResponse(
                original_query=request.query,
                processed_query=routing_result.get("used_query"),
                selected_knowledge_bases=routing_result.get("route_info", {}).get("selected_knowledge_bases", []),
                reasoning=routing_result.get("route_info", {}).get("reasoning", ""),
                qa_pair_match=routing_result.get("qa_pair_match"),
                search_results=routing_result.get("results"),
                answer=routing_result.get("qa_pair_match", {}).get("answer") if routing_result.get("qa_pair_match") else None
            )
        else:
            # 仅执行路由，不执行搜索
            route_result = await self.qa_router.route(
                query=request.query,
                agent_config=agent_config,
                available_knowledge_bases=available_kbs
            )
            
            # 构建响应
            return QARoutingResponse(
                original_query=request.query,
                processed_query=route_result.refined_query,
                selected_knowledge_bases=[kb.dict() for kb in route_result.selected_knowledge_bases],
                reasoning=route_result.reasoning,
                qa_pair_match=route_result.qa_pair_match.dict() if route_result.qa_pair_match else None
            )
            
    async def process_query(self, request: ProcessQueryRequest) -> ProcessQueryResponse:
        """处理查询，应用子问题拆分和问答路由
        
        Args:
            request: 处理查询请求
            
        Returns:
            处理查询响应
        """
        # 获取智能体配置（如果有）
        agent_config = None
        if request.agent_id and self.agent_service:
            try:
                agent_config = await self.agent_service.get_agent_config(request.agent_id)
            except Exception as e:
                logger.warning(f"获取智能体配置失败: {str(e)}")
                
        # 使用请求中的工具配置覆盖智能体配置
        if request.tools_config and agent_config:
            if "tools" not in agent_config:
                agent_config["tools"] = {}
            agent_config["tools"].update(request.tools_config)
            
        # 创建工具控制器
        from app.tools.base.agent_controller import AgentToolController
        controller = AgentToolController(
            agent_config=agent_config,
            subquestion_decomposer=self.subquestion_decomposer,
            qa_router=self.qa_router,
            search_service=self.search_service,
            llm_service=self.llm_service,
            base_tools_service=self.base_tools_service,
            db_session=self.db
        )
        
        # 处理查询
        result = await controller.process_query(
            query=request.query,
            context=request.context
        )
        
        # 构建响应
        return ProcessQueryResponse(**result)

def get_base_tools_integration(request: Request) -> BaseToolsIntegration:
    """获取基础工具集成实例
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        基础工具集成实例
    """
    return BaseToolsIntegration(request)
