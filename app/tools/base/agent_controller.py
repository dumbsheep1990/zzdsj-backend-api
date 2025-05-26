"""
智能体工具控制器

提供智能体层面集成子问题拆分和问答路由功能的控制器。
"""

from typing import Dict, Any, List, Optional, Union
import logging
import json
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class AgentToolController:
    """智能体工具控制器"""
    
    def __init__(self, 
                 agent_config: Dict[str, Any] = None,
                 subquestion_decomposer = None,
                 qa_router = None,
                 search_service = None,
                 llm_service = None,
                 base_tools_service = None,
                 db_session = None):
        """初始化智能体工具控制器
        
        Args:
            agent_config: 智能体配置
            subquestion_decomposer: 子问题拆分器实例
            qa_router: 问答路由器实例
            search_service: 搜索服务实例
            llm_service: LLM服务实例
            base_tools_service: 基础工具服务实例
            db_session: 数据库会话
        """
        self.agent_config = agent_config or {}
        self.subquestion_decomposer = subquestion_decomposer
        self.qa_router = qa_router
        self.search_service = search_service
        self.llm_service = llm_service
        self.base_tools_service = base_tools_service
        self.db_session = db_session
        
        # 从配置中获取工具设置
        self.tools_config = self._extract_tools_config()
        
        # 智能体ID
        self.agent_id = self.agent_config.get('id') if self.agent_config else None
        
    def _extract_tools_config(self) -> Dict[str, Any]:
        """从智能体配置中提取工具配置
        
        Returns:
            工具配置字典
        """
        tools_config = {
            "subquestion_decomposer": {
                "enabled": False,
                "mode": "basic",  # basic 或 tool
                "max_subquestions": 5,
                "threshold": 0.6,  # 复杂度阈值，超过此值才会拆分
            },
            "qa_router": {
                "enabled": False,
                "mode": "sequential",  # sequential, parallel, single
                "use_llm": True,
                "refine_query": True,
            }
        }
        
        # 如果有智能体配置，使用其覆盖默认配置
        if self.agent_config:
            agent_tools = self.agent_config.get("tools", {})
            
            # 子问题拆分器配置
            if "subquestion_decomposer" in agent_tools:
                tools_config["subquestion_decomposer"].update(
                    agent_tools.get("subquestion_decomposer", {})
                )
                
            # 问答路由器配置
            if "qa_router" in agent_tools:
                tools_config["qa_router"].update(
                    agent_tools.get("qa_router", {})
                )
        
        return tools_config
        
    async def process_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理查询，应用子问题拆分和问答路由
        
        Args:
            query: 用户查询
            context: 上下文信息
            
        Returns:
            处理结果，包含:
            - original_query: 原始查询
            - processed_query: 处理后的查询
            - subquestions: 拆分的子问题列表
            - route_info: 路由信息
            - search_results: 搜索结果
            - answer: 最终答案
            - qa_pair_match: 匹配到的问答对
            - metadata: 元数据
        """
        context = context or {}
        result = {
            "original_query": query,
            "processed_query": query,
            "subquestions": [],
            "route_info": None,
            "search_results": [],
            "answer": None,
            "qa_pair_match": None,
            "metadata": {
                "subquestion_decomposer_applied": False,
                "qa_router_applied": False,
                "process_steps": [],
                "session_id": context.get("session_id")
            }
        }
        
        # 处理步骤1: 判断是否需要拆分子问题
        if self._should_decompose_subquestions(query):
            await self._apply_subquestion_decomposition(query, result)
            
        # 处理步骤2: 应用问答路由
        if self._should_apply_qa_routing(query, result):
            await self._apply_qa_routing(query, result)
            
        # 处理步骤3: 如果有子问题，处理每个子问题
        if result["subquestions"] and not result["qa_pair_match"]:
            await self._process_subquestions(result)
            
        # 处理步骤4: 如果没有子问题或没有匹配到问答对，执行标准搜索
        if not result["subquestions"] and not result["qa_pair_match"] and not result["search_results"]:
            await self._perform_standard_search(query, result)
            
        # 处理步骤5: 如果有搜索结果，生成最终答案
        if result["search_results"] and not result["answer"]:
            await self._generate_answer(result)
        
        # 保存处理记录到数据库
        if self.base_tools_service:
            try:
                from app.schemas.base_tools import ProcessQueryRecordCreate
                session_id = result.get("metadata", {}).get("session_id")
                
                # 创建记录
                record_data = ProcessQueryRecordCreate(
                    agent_id=self.agent_id,
                    session_id=session_id,
                    original_query=query,
                    processed_query=result.get("processed_query"),
                    answer=result.get("answer"),
                    subquestion_record_id=result.get("metadata", {}).get("subquestion_record_id"),
                    qa_route_record_id=result.get("metadata", {}).get("qa_route_record_id"),
                    metadata=result.get("metadata")
                )
                
                # 保存到数据库
                record = await self.base_tools_service.create_process_query_record(record_data)
                
                # 保存记录ID到结果元数据
                result["metadata"]["process_query_record_id"] = record.id
                
            except Exception as e:
                logger.error(f"记录查询处理数据失败: {str(e)}")
            
        return result
        
    def _should_decompose_subquestions(self, query: str) -> bool:
        """判断是否应该拆分子问题
        
        Args:
            query: 用户查询
            
        Returns:
            是否应该拆分
        """
        # 检查子问题拆分器是否可用
        if not self.subquestion_decomposer:
            return False
            
        # 检查子问题拆分是否启用
        subq_config = self.tools_config["subquestion_decomposer"]
        if not subq_config.get("enabled", False):
            return False
            
        # 简单的复杂度启发式判断（可以根据需要扩展）
        # 例如：长度、问号数量、连接词数量等
        complexity_score = self._calculate_query_complexity(query)
        threshold = subq_config.get("threshold", 0.6)
        
        return complexity_score >= threshold
        
    def _calculate_query_complexity(self, query: str) -> float:
        """计算查询的复杂度分数
        
        Args:
            query: 用户查询
            
        Returns:
            复杂度分数 (0.0-1.0)
        """
        # 基本启发式规则
        score = 0.0
        
        # 长度因素
        length = len(query)
        if length > 100:
            score += 0.4
        elif length > 50:
            score += 0.2
            
        # 问号数量
        question_marks = query.count('?') + query.count('？')
        if question_marks > 1:
            score += 0.3
            
        # 连接词检测
        connection_words = ['和', '与', '以及', '并且', '还有', '同时', 
                           '不仅', '而且', '首先', '其次', '最后', 
                           '一方面', '另一方面', '此外', '除了']
        connection_count = sum(1 for word in connection_words if word in query)
        if connection_count > 2:
            score += 0.3
        elif connection_count > 0:
            score += 0.1
            
        # 限制最大值为1.0
        return min(score, 1.0)
        
    async def _apply_subquestion_decomposition(self, query: str, result: Dict[str, Any]) -> None:
        """应用子问题拆分
        
        Args:
            query: 用户查询
            result: 结果字典，将被修改
        """
        try:
            # 获取子问题拆分配置
            subq_config = self.tools_config["subquestion_decomposer"]
            mode = subq_config.get("mode", "basic")
            max_subquestions = subq_config.get("max_subquestions", 5)
            
            # 设置子问题拆分器模式
            self.subquestion_decomposer.mode = mode
            self.subquestion_decomposer.max_subquestions = max_subquestions
            
            # 执行子问题拆分
            decomposition_result = await self.subquestion_decomposer.decompose(query)
            
            # 更新结果
            result["subquestions"] = [sq.dict() for sq in decomposition_result.subquestions]
            result["metadata"]["subquestion_decomposer_applied"] = True
            result["metadata"]["process_steps"].append({
                "step": "subquestion_decomposition",
                "timestamp": str(import_time()),
                "details": {
                    "mode": mode,
                    "reasoning": decomposition_result.reasoning,
                    "execution_order": decomposition_result.execution_order
                }
            })
            
            # 如果有基础工具服务，记录子问题拆分数据
            if self.base_tools_service:
                session_id = result.get("metadata", {}).get("session_id")
                try:
                    from app.schemas.base_tools import SubQuestionRecordCreate, SubQuestionCreate
                    # 准备子问题数据
                    subquestions = []
                    for i, sq in enumerate(decomposition_result.subquestions):
                        subquestions.append(SubQuestionCreate(
                            id=sq.id,
                            question=sq.question,
                            order=i,
                            status="pending",
                            answer=None,
                            search_results=[]
                        ))
                    
                    # 创建记录
                    record_data = SubQuestionRecordCreate(
                        agent_id=self.agent_id,
                        session_id=session_id,
                        original_question=query,
                        reasoning=decomposition_result.reasoning,
                        mode=mode,
                        execution_order=decomposition_result.execution_order,
                        subquestions=subquestions
                    )
                    
                    # 保存到数据库
                    record = await self.base_tools_service.create_subquestion_record(record_data)
                    
                    # 保存记录ID到结果元数据
                    result["metadata"]["subquestion_record_id"] = record.id
                    
                except Exception as e:
                    logger.error(f"记录子问题拆分数据失败: {str(e)}")
            
        except Exception as e:
            logger.error(f"子问题拆分失败: {str(e)}")
            result["metadata"]["process_steps"].append({
                "step": "subquestion_decomposition",
                "timestamp": str(import_time()),
                "error": str(e)
            })
            
    def _should_apply_qa_routing(self, query: str, result: Dict[str, Any]) -> bool:
        """判断是否应该应用问答路由
        
        Args:
            query: 用户查询
            result: 当前结果
            
        Returns:
            是否应该应用问答路由
        """
        # 检查问答路由器是否可用
        if not self.qa_router:
            return False
            
        # 检查问答路由是否启用
        qa_config = self.tools_config["qa_router"]
        if not qa_config.get("enabled", False):
            return False
            
        return True
        
    async def _apply_qa_routing(self, query: str, result: Dict[str, Any]) -> None:
        """应用问答路由
        
        Args:
            query: 用户查询
            result: 结果字典，将被修改
        """
        try:
            # 获取问答路由配置
            qa_config = self.tools_config["qa_router"]
            
            # 获取可用知识库列表
            available_knowledge_bases = self.agent_config.get("knowledge_bases", [])
            
            # 执行问答路由
            if self.search_service:
                # 使用整合的搜索方法
                routing_result = await self.qa_router.execute_search_with_routing(
                    query=query,
                    agent_config=self.agent_config,
                    available_knowledge_bases=available_knowledge_bases,
                    search_service=self.search_service
                )
                
                # 更新结果
                if "route_info" in routing_result:
                    result["route_info"] = routing_result["route_info"]
                    
                if "results" in routing_result:
                    result["search_results"] = routing_result["results"]
                    
                if "qa_pair_match" in routing_result and routing_result["qa_pair_match"]:
                    result["qa_pair_match"] = routing_result["qa_pair_match"]
                    result["answer"] = routing_result["qa_pair_match"]["answer"]
                    
                if "used_query" in routing_result:
                    result["processed_query"] = routing_result["used_query"]
                    
            else:
                # 仅执行路由，不执行搜索
                route_result = await self.qa_router.route(
                    query=query,
                    agent_config=self.agent_config,
                    available_knowledge_bases=available_knowledge_bases
                )
                
                # 更新结果
                result["route_info"] = route_result.dict()
                if route_result.qa_pair_match:
                    result["qa_pair_match"] = route_result.qa_pair_match.dict()
                    result["answer"] = route_result.qa_pair_match.answer
                    
                if route_result.refined_query:
                    result["processed_query"] = route_result.refined_query
                
            # 更新元数据
            result["metadata"]["qa_router_applied"] = True
            result["metadata"]["process_steps"].append({
                "step": "qa_routing",
                "timestamp": str(import_time()),
                "details": {
                    "mode": qa_config.get("mode", "sequential"),
                    "selected_kbs": [kb["kb_id"] for kb in result["route_info"]["selected_knowledge_bases"]] if result["route_info"] else []
                }
            })
            
            # 如果有基础工具服务，记录问答路由数据
            if self.base_tools_service and result["route_info"]:
                session_id = result.get("metadata", {}).get("session_id")
                try:
                    from app.schemas.base_tools import (
                        QARouteRecordCreate, 
                        QARouteKnowledgeBaseCreate,
                        QARouteSearchResultCreate,
                        QARoutePairMatchCreate
                    )
                    
                    # 准备知识库数据
                    selected_kbs = []
                    if "selected_knowledge_bases" in result["route_info"]:
                        for i, kb in enumerate(result["route_info"]["selected_knowledge_bases"]):
                            selected_kbs.append(QARouteKnowledgeBaseCreate(
                                kb_id=kb.get("kb_id"),
                                kb_name=kb.get("kb_name"),
                                confidence=kb.get("confidence", 1.0),
                                order=i
                            ))
                    
                    # 准备搜索结果数据
                    search_results = []
                    if "search_results" in result:
                        for sr in result["search_results"]:
                            search_results.append(QARouteSearchResultCreate(
                                doc_id=sr.get("id") or sr.get("doc_id"),
                                kb_id=sr.get("kb_id"),
                                title=sr.get("title"),
                                content=sr.get("content"),
                                source=sr.get("source"),
                                score=sr.get("score"),
                                metadata=sr.get("metadata")
                            ))
                    
                    # 准备QA对匹配数据
                    qa_pair_match = None
                    if result["qa_pair_match"]:
                        qa_pair_match = QARoutePairMatchCreate(
                            qa_id=result["qa_pair_match"].get("id") or result["qa_pair_match"].get("qa_id") or "unknown",
                            question=result["qa_pair_match"].get("question"),
                            answer=result["qa_pair_match"].get("answer"),
                            score=result["qa_pair_match"].get("score")
                        )
                    
                    # 创建记录
                    record_data = QARouteRecordCreate(
                        agent_id=self.agent_id,
                        session_id=session_id,
                        original_query=query,
                        processed_query=result.get("processed_query"),
                        reasoning=result["route_info"].get("reasoning"),
                        mode=qa_config.get("mode", "sequential"),
                        selected_knowledge_bases=selected_kbs,
                        search_results=search_results,
                        qa_pair_match=qa_pair_match
                    )
                    
                    # 保存到数据库
                    record = await self.base_tools_service.create_qa_route_record(record_data)
                    
                    # 保存记录ID到结果元数据
                    result["metadata"]["qa_route_record_id"] = record.id
                    
                except Exception as e:
                    logger.error(f"记录问答路由数据失败: {str(e)}")
            
        except Exception as e:
            logger.error(f"问答路由失败: {str(e)}")
            result["metadata"]["process_steps"].append({
                "step": "qa_routing",
                "timestamp": str(import_time()),
                "error": str(e)
            })
            
    async def _process_subquestions(self, result: Dict[str, Any]) -> None:
        """处理子问题
        
        Args:
            result: 结果字典，将被修改
        """
        if not self.subquestion_decomposer or not self.search_service:
            return
            
        try:
            # 构造DecompositionResult对象
            from app.tools.base.subquestion_decomposer import DecompositionResult, SubQuestion
            
            subquestions = []
            for sq_dict in result["subquestions"]:
                sq = SubQuestion(**sq_dict)
                subquestions.append(sq)
                
            decomposition_result = DecompositionResult(
                original_question=result["original_query"],
                subquestions=subquestions,
                reasoning="",
                execution_order=[sq.id for sq in subquestions]
            )
            
            # 获取知识库ID列表
            knowledge_base_ids = []
            if result["route_info"] and "selected_knowledge_bases" in result["route_info"]:
                knowledge_base_ids = [kb["kb_id"] for kb in result["route_info"]["selected_knowledge_bases"]]
            
            # 回答子问题
            decomposition_result = await self.subquestion_decomposer.answer_subquestions(
                decomposition_result=decomposition_result,
                search_service=self.search_service,
                knowledge_base_ids=knowledge_base_ids
            )
            
            # 合成最终答案
            final_answer = await self.subquestion_decomposer.synthesize_final_answer(decomposition_result)
            
            # 更新结果
            result["subquestions"] = [sq.dict() for sq in decomposition_result.subquestions]
            result["answer"] = final_answer
            
            # 合并所有子问题的搜索结果
            all_search_results = []
            for sq in decomposition_result.subquestions:
                if sq.search_results:
                    all_search_results.extend(sq.search_results)
                    
            # 去重并限制数量
            unique_results = {}
            for sr in all_search_results:
                doc_id = sr.get("id", "")
                if doc_id and doc_id not in unique_results:
                    unique_results[doc_id] = sr
                    
            result["search_results"] = list(unique_results.values())
            
            # 更新元数据
            result["metadata"]["process_steps"].append({
                "step": "subquestion_processing",
                "timestamp": str(import_time()),
                "details": {
                    "subquestions_answered": len([sq for sq in decomposition_result.subquestions if sq.answer]),
                    "total_subquestions": len(decomposition_result.subquestions)
                }
            })
            
        except Exception as e:
            logger.error(f"子问题处理失败: {str(e)}")
            result["metadata"]["process_steps"].append({
                "step": "subquestion_processing",
                "timestamp": str(import_time()),
                "error": str(e)
            })
            
    async def _perform_standard_search(self, query: str, result: Dict[str, Any]) -> None:
        """执行标准搜索
        
        Args:
            query: 用户查询
            result: 结果字典，将被修改
        """
        if not self.search_service:
            return
            
        try:
            # 使用处理后的查询（如果有）
            search_query = result["processed_query"]
            
            # 获取知识库ID列表
            knowledge_base_ids = []
            if result["route_info"] and "selected_knowledge_bases" in result["route_info"]:
                knowledge_base_ids = [kb["kb_id"] for kb in result["route_info"]["selected_knowledge_bases"]]
                
            # 如果没有指定知识库，使用智能体配置中的知识库
            if not knowledge_base_ids and self.agent_config:
                kb_list = self.agent_config.get("knowledge_bases", [])
                knowledge_base_ids = [kb.get("id") for kb in kb_list if "id" in kb]
                
            # 执行搜索
            search_results = await self.search_service.search(
                query=search_query,
                knowledge_base_ids=knowledge_base_ids,
                limit=5
            )
            
            # 更新结果
            result["search_results"] = search_results
            
            # 更新元数据
            result["metadata"]["process_steps"].append({
                "step": "standard_search",
                "timestamp": str(import_time()),
                "details": {
                    "query": search_query,
                    "knowledge_base_ids": knowledge_base_ids,
                    "results_count": len(search_results) if search_results else 0
                }
            })
            
        except Exception as e:
            logger.error(f"标准搜索失败: {str(e)}")
            result["metadata"]["process_steps"].append({
                "step": "standard_search",
                "timestamp": str(import_time()),
                "error": str(e)
            })
            
    async def _generate_answer(self, result: Dict[str, Any]) -> None:
        """生成最终答案
        
        Args:
            result: 结果字典，将被修改
        """
        if not self.llm_service:
            return
            
        try:
            # 获取搜索结果
            search_results = result["search_results"]
            if not search_results:
                return
                
            # 构建上下文
            context_parts = []
            for i, sr in enumerate(search_results):
                content = sr.get("content", "")
                source = sr.get("source", "")
                if content:
                    context_parts.append(f"[{i+1}] {content}\n来源: {source}")
                    
            context = "\n\n".join(context_parts)
            
            # 生成答案
            response = await self.llm_service.chat_completion(
                messages=[
                    {"role": "system", "content": "你是一个专业的问答助手。请基于提供的上下文回答问题。如果上下文中没有相关信息，请说明无法回答。"},
                    {"role": "user", "content": f"问题：{result['original_query']}\n\n上下文：{context}"}
                ]
            )
            
            # 更新结果
            result["answer"] = response["choices"][0]["message"]["content"]
            
            # 更新元数据
            result["metadata"]["process_steps"].append({
                "step": "answer_generation",
                "timestamp": str(import_time()),
                "details": {
                    "context_length": len(context),
                    "answer_length": len(result["answer"])
                }
            })
            
        except Exception as e:
            logger.error(f"答案生成失败: {str(e)}")
            result["metadata"]["process_steps"].append({
                "step": "answer_generation",
                "timestamp": str(import_time()),
                "error": str(e)
            })


def import_time():
    """导入时间模块并返回当前时间
    
    Returns:
        当前时间
    """
    from datetime import datetime
    return datetime.now()
