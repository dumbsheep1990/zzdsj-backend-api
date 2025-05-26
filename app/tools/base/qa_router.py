"""
问答路由绑定工具

提供针对知识库的路由选择功能，根据问题类型自动选择合适的知识库进行检索。
支持三种检索模式：
1. 顺序检索：按照预定义顺序依次检索各知识库
2. 同步检索：同时检索所有相关知识库
3. 单知识库检索：仅检索最相关的知识库
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import logging
from pydantic import BaseModel, Field
import json
import re

logger = logging.getLogger(__name__)

class KnowledgeBaseRoute(BaseModel):
    """知识库路由定义"""
    kb_id: str = Field(..., description="知识库ID")
    name: str = Field(..., description="知识库名称")
    description: str = Field(..., description="知识库描述")
    domain: str = Field(..., description="知识库领域")
    keywords: List[str] = Field(default_factory=list, description="关键词列表")
    patterns: List[str] = Field(default_factory=list, description="匹配模式列表")
    priority: int = Field(default=0, description="优先级，数值越大优先级越高")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

class QAPair(BaseModel):
    """问答对定义"""
    question: str = Field(..., description="问题")
    answer: str = Field(..., description="答案")
    kb_id: Optional[str] = Field(None, description="关联的知识库ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

class RouteResult(BaseModel):
    """路由结果"""
    original_query: str = Field(..., description="原始查询")
    mode: str = Field(..., description="检索模式: sequential, parallel, single")
    selected_knowledge_bases: List[KnowledgeBaseRoute] = Field(..., description="选中的知识库路由")
    qa_pair_match: Optional[QAPair] = Field(None, description="匹配到的问答对")
    reasoning: str = Field("", description="路由推理过程")
    refined_query: Optional[str] = Field(None, description="优化后的查询")

class QARouter:
    """问答路由器"""
    
    def __init__(self, 
                 llm_service=None,
                 kb_service=None,
                 qa_dataset_service=None,
                 default_mode: str = "sequential",
                 use_llm_for_routing: bool = True,
                 prompts: Dict[str, str] = None):
        """初始化问答路由器
        
        Args:
            llm_service: LLM服务实例
            kb_service: 知识库服务实例
            qa_dataset_service: 问答数据集服务实例
            default_mode: 默认检索模式，可选 'sequential', 'parallel', 'single'
            use_llm_for_routing: 是否使用LLM进行路由决策
            prompts: 提示词配置
        """
        self.llm_service = llm_service
        self.kb_service = kb_service
        self.qa_dataset_service = qa_dataset_service
        self.default_mode = default_mode
        self.use_llm_for_routing = use_llm_for_routing
        
        # 默认提示词配置
        self.default_prompts = {
            "router_system": """你是一个专业的问题路由专家。你的任务是将用户的问题路由到最合适的知识库进行检索。
分析用户问题，确定它属于哪个领域，然后选择最合适的知识库。
如果问题涉及多个领域，可以选择多个知识库。
如果问题非常明确地属于某个领域，则只选择一个最相关的知识库。
如果问题不属于任何提供的知识库领域，请选择最通用的知识库或明确说明无法找到合适的知识库。""",
            
            "router_user": """用户问题：{query}

可用的知识库:
{kb_descriptions}

请分析问题并确定应该使用哪些知识库来检索信息。解释你的选择理由。
格式要求：
1. 分析：[分析问题属于哪个领域]
2. 推荐知识库：[选择的知识库ID列表]
3. 推荐模式：[sequential/parallel/single]
4. 理由：[解释为什么选择这些知识库]""",

            "query_refine_system": """你是一个专业的查询优化专家。你的任务是优化用户的查询，使其更适合在知识库中检索。
分析用户的原始查询，并根据选择的知识库领域重新构建一个更明确、更有针对性的查询。
优化后的查询应该：
1. 保留原始查询的核心意图
2. 使用更专业、更精确的术语
3. 去除不必要的修饰词
4. 适当扩展相关概念
5. 符合选定知识库的领域特点""",
            
            "query_refine_user": """原始查询：{query}

已选择的知识库：
{selected_kbs}

请优化这个查询，使其更适合在上述知识库中检索信息。"""
        }
        
        # 使用自定义提示词覆盖默认提示词
        if prompts:
            self.prompts = {**self.default_prompts, **prompts}
        else:
            self.prompts = self.default_prompts
    
    async def route(self, 
                   query: str, 
                   agent_config: Dict[str, Any] = None, 
                   available_knowledge_bases: List[Dict[str, Any]] = None) -> RouteResult:
        """为查询选择合适的知识库路由
        
        Args:
            query: 用户查询
            agent_config: 智能体配置
            available_knowledge_bases: 可用知识库列表
            
        Returns:
            路由结果
        """
        # 获取可用知识库路由
        kb_routes = await self._get_knowledge_base_routes(available_knowledge_bases)
        
        # 获取检索模式
        mode = self._get_retrieval_mode(agent_config)
        
        # 检查是否有匹配的问答对
        qa_pair_match = await self._find_matching_qa_pair(query, agent_config)
        
        # 如果找到匹配的问答对，直接返回
        if qa_pair_match:
            # 如果问答对关联了知识库，添加到选中的知识库
            selected_kbs = []
            if qa_pair_match.kb_id:
                for kb in kb_routes:
                    if kb.kb_id == qa_pair_match.kb_id:
                        selected_kbs.append(kb)
                        break
                
            return RouteResult(
                original_query=query,
                mode=mode,
                selected_knowledge_bases=selected_kbs,
                qa_pair_match=qa_pair_match,
                reasoning="直接匹配到预定义问答对，无需进一步路由。"
            )
        
        # 基于规则进行初步路由
        rule_based_kbs, rule_reasoning = self._rule_based_routing(query, kb_routes)
        
        # 如果启用了LLM路由并且基于规则没有找到路由，使用LLM进行路由
        final_kbs = rule_based_kbs
        reasoning = rule_reasoning
        
        if self.use_llm_for_routing and (not rule_based_kbs or len(rule_based_kbs) == 0):
            llm_based_kbs, llm_mode, llm_reasoning = await self._llm_based_routing(query, kb_routes)
            
            # 合并结果
            final_kbs = llm_based_kbs
            if llm_mode:
                mode = llm_mode
            reasoning = f"{rule_reasoning}\n\nLLM路由结果：\n{llm_reasoning}"
        
        # 如果没有选中任何知识库，选择第一个作为默认值
        if not final_kbs and kb_routes:
            final_kbs = [kb_routes[0]]
            reasoning += "\n\n未找到匹配的知识库，使用默认知识库。"
            
        # 优化查询（如果需要）
        refined_query = await self._refine_query(query, final_kbs) if final_kbs else None
            
        return RouteResult(
            original_query=query,
            mode=mode,
            selected_knowledge_bases=final_kbs,
            qa_pair_match=None,
            reasoning=reasoning,
            refined_query=refined_query
        )
        
    async def _get_knowledge_base_routes(self, available_knowledge_bases: List[Dict[str, Any]]) -> List[KnowledgeBaseRoute]:
        """获取知识库路由定义
        
        Args:
            available_knowledge_bases: 可用知识库列表
            
        Returns:
            知识库路由列表
        """
        if available_knowledge_bases:
            # 使用提供的知识库列表
            kb_routes = []
            for kb in available_knowledge_bases:
                try:
                    kb_route = KnowledgeBaseRoute(
                        kb_id=kb.get("id", ""),
                        name=kb.get("name", ""),
                        description=kb.get("description", ""),
                        domain=kb.get("domain", ""),
                        keywords=kb.get("keywords", []),
                        patterns=kb.get("patterns", []),
                        priority=kb.get("priority", 0),
                        metadata=kb.get("metadata", {})
                    )
                    kb_routes.append(kb_route)
                except Exception as e:
                    logger.error(f"Error creating knowledge base route: {str(e)}")
            
            return kb_routes
        elif self.kb_service:
            # 从知识库服务获取
            try:
                kbs = await self.kb_service.list_knowledge_bases()
                kb_routes = []
                
                for kb in kbs:
                    # 提取知识库元数据
                    metadata = kb.get("metadata", {})
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except:
                            metadata = {}
                    
                    # 创建路由定义
                    kb_route = KnowledgeBaseRoute(
                        kb_id=kb.get("id", ""),
                        name=kb.get("name", ""),
                        description=kb.get("description", ""),
                        domain=metadata.get("domain", ""),
                        keywords=metadata.get("keywords", []),
                        patterns=metadata.get("patterns", []),
                        priority=metadata.get("priority", 0),
                        metadata=metadata
                    )
                    kb_routes.append(kb_route)
                
                return kb_routes
            except Exception as e:
                logger.error(f"Error getting knowledge bases: {str(e)}")
                return []
        else:
            # 没有可用的知识库
            return []
    
    def _get_retrieval_mode(self, agent_config: Dict[str, Any]) -> str:
        """获取检索模式
        
        Args:
            agent_config: 智能体配置
            
        Returns:
            检索模式
        """
        if not agent_config:
            return self.default_mode
            
        # 从智能体配置中获取检索模式
        retrieval_config = agent_config.get("retrieval_config", {})
        mode = retrieval_config.get("mode", self.default_mode)
        
        # 验证模式是否有效
        valid_modes = ["sequential", "parallel", "single"]
        if mode not in valid_modes:
            return self.default_mode
            
        return mode
    
    async def _find_matching_qa_pair(self, query: str, agent_config: Dict[str, Any]) -> Optional[QAPair]:
        """查找匹配的问答对
        
        Args:
            query: 用户查询
            agent_config: 智能体配置
            
        Returns:
            匹配的问答对，如果没有找到则返回None
        """
        if not self.qa_dataset_service:
            return None
            
        try:
            # 从智能体配置中获取关联的问答数据集ID
            qa_dataset_ids = []
            if agent_config:
                retrieval_config = agent_config.get("retrieval_config", {})
                qa_dataset_ids = retrieval_config.get("qa_dataset_ids", [])
            
            if not qa_dataset_ids:
                return None
                
            # 查询匹配的问答对
            match_result = await self.qa_dataset_service.find_matching_qa_pair(
                query=query,
                dataset_ids=qa_dataset_ids,
                threshold=0.85  # 匹配阈值
            )
            
            if match_result and match_result.get("match_found", False):
                qa_pair = match_result.get("qa_pair", {})
                return QAPair(
                    question=qa_pair.get("question", ""),
                    answer=qa_pair.get("answer", ""),
                    kb_id=qa_pair.get("kb_id"),
                    metadata=qa_pair.get("metadata", {})
                )
                
            return None
        except Exception as e:
            logger.error(f"Error finding matching QA pair: {str(e)}")
            return None
    
    def _rule_based_routing(self, query: str, kb_routes: List[KnowledgeBaseRoute]) -> Tuple[List[KnowledgeBaseRoute], str]:
        """基于规则的路由
        
        Args:
            query: 用户查询
            kb_routes: 知识库路由列表
            
        Returns:
            选中的知识库路由列表和推理过程
        """
        matched_kbs = []
        reasoning = "基于规则的路由分析：\n"
        
        # 查询预处理
        clean_query = query.lower()
        
        # 遍历所有知识库路由
        for kb in kb_routes:
            matched = False
            match_reason = []
            
            # 检查关键词匹配
            for keyword in kb.keywords:
                if keyword.lower() in clean_query:
                    matched = True
                    match_reason.append(f"关键词匹配: '{keyword}'")
            
            # 检查模式匹配
            for pattern in kb.patterns:
                try:
                    if re.search(pattern, query, re.IGNORECASE):
                        matched = True
                        match_reason.append(f"模式匹配: '{pattern}'")
                except Exception as e:
                    logger.error(f"Error in pattern matching: {str(e)}")
            
            # 如果匹配，添加到结果列表
            if matched:
                matched_kbs.append(kb)
                reasoning += f"- 知识库 '{kb.name}' 匹配成功: {', '.join(match_reason)}\n"
        
        # 根据优先级排序
        matched_kbs.sort(key=lambda x: x.priority, reverse=True)
        
        if not matched_kbs:
            reasoning += "未找到基于规则匹配的知识库。\n"
            
        return matched_kbs, reasoning
    
    async def _llm_based_routing(self, query: str, kb_routes: List[KnowledgeBaseRoute]) -> Tuple[List[KnowledgeBaseRoute], Optional[str], str]:
        """基于LLM的路由
        
        Args:
            query: 用户查询
            kb_routes: 知识库路由列表
            
        Returns:
            选中的知识库路由列表、推荐模式和推理过程
        """
        if not self.llm_service or not kb_routes:
            return [], None, "LLM路由未执行：LLM服务不可用或没有知识库。"
            
        try:
            # 准备知识库描述
            kb_descriptions = ""
            for i, kb in enumerate(kb_routes):
                kb_descriptions += f"{i+1}. ID: {kb.kb_id}, 名称: {kb.name}, 描述: {kb.description}, 领域: {kb.domain}\n"
            
            # 准备提示词
            system_prompt = self.prompts["router_system"]
            user_prompt = self.prompts["router_user"].format(
                query=query,
                kb_descriptions=kb_descriptions
            )
            
            # 调用LLM服务
            response = await self.llm_service.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            content = response["choices"][0]["message"]["content"]
            
            # 解析LLM响应
            selected_kb_ids = []
            recommended_mode = None
            reasoning = content
            
            # 提取推荐的知识库ID
            kb_id_match = re.search(r'推荐知识库：\s*\[([^\]]+)\]', content)
            if kb_id_match:
                kb_ids_str = kb_id_match.group(1)
                # 分割并清理ID
                selected_kb_ids = [id.strip() for id in re.split(r'[,，、\s]+', kb_ids_str) if id.strip()]
            
            # 提取推荐的检索模式
            mode_match = re.search(r'推荐模式：\s*\[([^\]]+)\]', content)
            if mode_match:
                mode = mode_match.group(1).strip().lower()
                if mode in ["sequential", "parallel", "single"]:
                    recommended_mode = mode
            
            # 查找匹配的知识库路由
            selected_kbs = []
            for kb_id in selected_kb_ids:
                for kb in kb_routes:
                    # 支持通过ID或名称匹配
                    if kb_id == kb.kb_id or kb_id == kb.name:
                        selected_kbs.append(kb)
                        break
            
            return selected_kbs, recommended_mode, reasoning
            
        except Exception as e:
            logger.error(f"Error in LLM-based routing: {str(e)}")
            return [], None, f"LLM路由失败: {str(e)}"
    
    async def _refine_query(self, query: str, selected_kbs: List[KnowledgeBaseRoute]) -> Optional[str]:
        """优化查询
        
        Args:
            query: 原始查询
            selected_kbs: 选中的知识库路由列表
            
        Returns:
            优化后的查询
        """
        if not self.llm_service or not selected_kbs:
            return None
            
        try:
            # 准备知识库描述
            kb_descriptions = ""
            for i, kb in enumerate(selected_kbs):
                kb_descriptions += f"{i+1}. 名称: {kb.name}, 描述: {kb.description}, 领域: {kb.domain}\n"
            
            # 准备提示词
            system_prompt = self.prompts["query_refine_system"]
            user_prompt = self.prompts["query_refine_user"].format(
                query=query,
                selected_kbs=kb_descriptions
            )
            
            # 调用LLM服务
            response = await self.llm_service.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            refined_query = response["choices"][0]["message"]["content"].strip()
            
            # 如果优化后的查询没有实质变化，返回None
            if refined_query.lower() == query.lower():
                return None
                
            return refined_query
            
        except Exception as e:
            logger.error(f"Error refining query: {str(e)}")
            return None
    
    async def execute_search_with_routing(self, 
                                         query: str, 
                                         agent_config: Dict[str, Any] = None,
                                         available_knowledge_bases: List[Dict[str, Any]] = None,
                                         search_service=None) -> Dict[str, Any]:
        """使用路由执行搜索
        
        Args:
            query: 用户查询
            agent_config: 智能体配置
            available_knowledge_bases: 可用知识库列表
            search_service: 搜索服务实例
            
        Returns:
            搜索结果和路由信息
        """
        if not search_service:
            return {
                "error": "搜索服务不可用",
                "results": [],
                "route_info": None
            }
            
        # 获取路由结果
        route_result = await self.route(query, agent_config, available_knowledge_bases)
        
        # 如果匹配到问答对，直接返回
        if route_result.qa_pair_match:
            return {
                "results": [],
                "route_info": route_result.dict(),
                "qa_pair_match": route_result.qa_pair_match.dict()
            }
            
        # 获取要搜索的知识库ID列表
        kb_ids = [kb.kb_id for kb in route_result.selected_knowledge_bases]
        
        if not kb_ids:
            return {
                "results": [],
                "route_info": route_result.dict(),
                "error": "没有选择任何知识库"
            }
            
        # 使用优化后的查询（如果有）
        search_query = route_result.refined_query or query
        
        # 根据模式执行搜索
        search_results = []
        
        try:
            if route_result.mode == "sequential":
                # 顺序检索：依次搜索每个知识库，直到找到足够的结果
                for kb_id in kb_ids:
                    kb_results = await search_service.search(
                        query=search_query,
                        knowledge_base_ids=[kb_id],
                        limit=5
                    )
                    
                    # 如果找到结果，添加到结果列表
                    if kb_results:
                        search_results.extend(kb_results)
                        
                    # 如果已经有足够的结果，停止搜索
                    if len(search_results) >= 5:
                        break
                        
            elif route_result.mode == "parallel":
                # 同步检索：同时搜索所有知识库，然后合并结果
                all_results = await search_service.search(
                    query=search_query,
                    knowledge_base_ids=kb_ids,
                    limit=10
                )
                
                search_results = all_results
                
            else:  # "single"
                # 单知识库检索：只搜索优先级最高的知识库
                if kb_ids:
                    top_kb_id = kb_ids[0]
                    search_results = await search_service.search(
                        query=search_query,
                        knowledge_base_ids=[top_kb_id],
                        limit=5
                    )
        except Exception as e:
            logger.error(f"Error executing search: {str(e)}")
            return {
                "error": f"搜索执行失败: {str(e)}",
                "results": [],
                "route_info": route_result.dict()
            }
            
        return {
            "results": search_results,
            "route_info": route_result.dict(),
            "used_query": search_query
        }
