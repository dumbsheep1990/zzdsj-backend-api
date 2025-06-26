"""
自然语言工具编排器
将自然语言描述转换为可执行的工具链，支持对话式优化和智能执行计划生成
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

# 集成现有组件
from app.frameworks.llamaindex.chat import LlamaIndexChatServiceConfig
from core.model_manager import ModelManager
from app.frameworks.integration.factory import get_llm_service
from app.services.tools.tool_service import ToolService
from app.services.recommendations.ai_combination_recommender import (
    AIToolCombinationRecommender,
    ToolCombinationAnalysis
)
from core.nl_config.parser import NLConfigParser

# 集成现有的工具注册系统
from app.tools.zzdsj_tool_registry import get_tool_registry, ToolCategory

logger = logging.getLogger(__name__)

class TaskComplexity(str, Enum):
    """任务复杂度枚举"""
    SIMPLE = "simple"           # 1-2个工具
    MODERATE = "moderate"       # 3-5个工具
    COMPLEX = "complex"         # 6-10个工具
    ENTERPRISE = "enterprise"   # 10+个工具

class ExecutionStrategy(str, Enum):
    """执行策略枚举"""
    SEQUENTIAL = "sequential"    # 顺序执行
    PARALLEL = "parallel"       # 并行执行
    CONDITIONAL = "conditional"  # 条件执行
    ADAPTIVE = "adaptive"       # 自适应执行

@dataclass
class ToolChainStep:
    """工具链步骤"""
    step_id: str
    tool_name: str
    tool_description: str
    action_description: str
    input_requirements: Dict[str, Any]
    output_expectations: Dict[str, Any]
    dependencies: List[str]  # 依赖的步骤ID
    execution_strategy: ExecutionStrategy
    timeout_seconds: int
    retry_count: int
    fallback_tools: List[str]

@dataclass
class ExecutionPlan:
    """执行计划"""
    plan_id: str
    objective: str
    total_steps: int
    estimated_duration: float  # 预估执行时间（分钟）
    complexity: TaskComplexity
    success_probability: float  # 预测成功率
    steps: List[ToolChainStep]
    execution_order: List[str]  # 步骤执行顺序
    parallel_groups: List[List[str]]  # 并行执行组
    checkpoints: List[int]  # 检查点位置
    rollback_strategy: Dict[str, Any]
    resource_requirements: Dict[str, Any]

@dataclass
class ToolChain:
    """完整工具链"""
    chain_id: str
    name: str
    description: str
    objective: str
    tools: List[str]
    execution_plan: ExecutionPlan
    ai_analysis: Optional[ToolCombinationAnalysis]
    created_at: datetime
    updated_at: datetime
    creator_id: str
    status: str  # "draft", "validated", "optimized", "ready"

@dataclass
class ConversationContext:
    """对话上下文"""
    conversation_id: str
    user_id: str
    current_objective: str
    current_chain: Optional[ToolChain]
    conversation_history: List[Dict[str, Any]]
    user_preferences: Dict[str, Any]
    domain_context: Optional[str]

class NaturalLanguageOrchestrator:
    """自然语言工具编排器"""
    
    def __init__(
        self,
        tool_service: ToolService,
        ai_recommender: AIToolCombinationRecommender,
        nl_parser: NLConfigParser
    ):
        self.tool_service = tool_service
        self.ai_recommender = ai_recommender
        self.nl_parser = nl_parser
        self.model_manager = ModelManager()
        self._llm = None
        
        # 配置
        self.orchestration_model = "gpt-4o"
        self.planning_temperature = 0.3
        self.conversation_temperature = 0.7
        
        # 缓存
        self._conversation_contexts: Dict[str, ConversationContext] = {}
        
    async def initialize(self):
        """初始化编排器"""
        if self._llm is None:
            config = LlamaIndexChatServiceConfig()
            self._llm = await get_llm_service(config)
            await self.ai_recommender.initialize()
            await self.nl_parser.initialize()
            logger.info("自然语言工具编排器初始化完成")
    
    async def text_to_tool_chain(
        self,
        description: str,
        user_id: str,
        domain_context: Optional[str] = None,
        complexity_preference: str = "balanced",
        execution_strategy: ExecutionStrategy = ExecutionStrategy.ADAPTIVE
    ) -> ToolChain:
        """
        将自然语言描述转换为工具链
        
        Args:
            description: 自然语言任务描述
            user_id: 用户ID
            domain_context: 领域上下文
            complexity_preference: 复杂度偏好
            execution_strategy: 执行策略偏好
            
        Returns:
            ToolChain: 生成的工具链
        """
        await self.initialize()
        
        try:
            # 1. 分析任务需求
            task_analysis = await self._analyze_task_requirements(
                description, domain_context
            )
            
            # 2. 获取可用工具
            available_tools = await self.tool_service.get_user_accessible_tools(user_id)
            
            # 3. 生成候选工具链
            candidate_chains = await self._generate_candidate_tool_chains(
                task_analysis, available_tools, complexity_preference
            )
            
            # 4. 选择最佳工具链
            selected_tools = await self._select_optimal_tool_chain(
                candidate_chains, task_analysis
            )
            
            # 5. 生成执行计划
            execution_plan = await self.generate_execution_plan(
                selected_tools, description, execution_strategy
            )
            
            # 6. AI分析工具组合
            ai_analysis = await self.ai_recommender.analyze_tool_combinations(
                selected_tools, description
            )
            
            # 7. 创建工具链对象
            tool_chain = ToolChain(
                chain_id=str(uuid.uuid4()),
                name=self._generate_chain_name(description),
                description=description,
                objective=description,
                tools=selected_tools,
                execution_plan=execution_plan,
                ai_analysis=ai_analysis,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                creator_id=user_id,
                status="draft"
            )
            
            logger.info(f"成功生成工具链: {tool_chain.name} (工具数量: {len(selected_tools)})")
            return tool_chain
            
        except Exception as e:
            logger.error(f"自然语言转工具链失败: {str(e)}", exc_info=True)
            # 返回简单的单工具链作为fallback
            return await self._create_fallback_chain(description, user_id)
    
    async def generate_execution_plan(
        self,
        tools: List[str],
        objective: str,
        strategy: ExecutionStrategy = ExecutionStrategy.ADAPTIVE
    ) -> ExecutionPlan:
        """
        生成执行计划
        
        Args:
            tools: 工具列表
            objective: 目标描述
            strategy: 执行策略
            
        Returns:
            ExecutionPlan: 生成的执行计划
        """
        await self.initialize()
        
        try:
            # 1. 分析工具依赖关系
            dependencies = await self._analyze_tool_dependencies(tools)
            
            # 2. 估算复杂度
            complexity = self._estimate_task_complexity(tools, objective)
            
            # 3. 生成执行步骤
            steps = await self._generate_execution_steps(
                tools, objective, dependencies, strategy
            )
            
            # 4. 确定执行顺序
            execution_order, parallel_groups = self._determine_execution_order(
                steps, strategy
            )
            
            # 5. 设置检查点
            checkpoints = self._set_checkpoints(steps, complexity)
            
            # 6. 预测性能
            estimated_duration = await self._estimate_execution_duration(steps)
            success_probability = await self.ai_recommender.predict_success_rate(
                tools, objective
            )
            
            # 7. 生成回滚策略
            rollback_strategy = self._generate_rollback_strategy(steps)
            
            execution_plan = ExecutionPlan(
                plan_id=str(uuid.uuid4()),
                objective=objective,
                total_steps=len(steps),
                estimated_duration=estimated_duration,
                complexity=complexity,
                success_probability=success_probability,
                steps=steps,
                execution_order=execution_order,
                parallel_groups=parallel_groups,
                checkpoints=checkpoints,
                rollback_strategy=rollback_strategy,
                resource_requirements=self._calculate_resource_requirements(steps)
            )
            
            logger.info(f"生成执行计划: {len(steps)}步骤, 预估{estimated_duration:.1f}分钟")
            return execution_plan
            
        except Exception as e:
            logger.error(f"生成执行计划失败: {str(e)}", exc_info=True)
            return await self._create_simple_execution_plan(tools, objective)
    
    async def interactive_refinement(
        self,
        chain: ToolChain,
        user_feedback: str,
        conversation_id: Optional[str] = None
    ) -> ToolChain:
        """
        对话式工具链优化
        
        Args:
            chain: 当前工具链
            user_feedback: 用户反馈
            conversation_id: 对话ID
            
        Returns:
            ToolChain: 优化后的工具链
        """
        await self.initialize()
        
        try:
            # 1. 获取或创建对话上下文
            if not conversation_id:
                conversation_id = str(uuid.uuid4())
            
            context = self._get_or_create_conversation_context(
                conversation_id, chain.creator_id, chain.objective, chain
            )
            
            # 2. 分析用户反馈
            feedback_analysis = await self._analyze_user_feedback(
                user_feedback, chain, context
            )
            
            # 3. 生成优化建议
            optimization_suggestions = await self._generate_optimization_suggestions(
                feedback_analysis, chain, context
            )
            
            # 4. 应用优化
            optimized_chain = await self._apply_optimizations(
                chain, optimization_suggestions, feedback_analysis
            )
            
            # 5. 重新分析优化后的工具链
            if optimized_chain.tools != chain.tools:
                optimized_chain.ai_analysis = await self.ai_recommender.analyze_tool_combinations(
                    optimized_chain.tools, optimized_chain.objective
                )
                
                # 重新生成执行计划
                optimized_chain.execution_plan = await self.generate_execution_plan(
                    optimized_chain.tools, optimized_chain.objective
                )
            
            # 6. 更新对话历史
            self._update_conversation_history(
                context, user_feedback, optimized_chain, optimization_suggestions
            )
            
            optimized_chain.updated_at = datetime.now()
            optimized_chain.status = "optimized"
            
            logger.info(f"工具链优化完成: {chain.name} -> {len(optimized_chain.tools)}个工具")
            return optimized_chain
            
        except Exception as e:
            logger.error(f"工具链优化失败: {str(e)}", exc_info=True)
            return chain  # 返回原始工具链
    
    async def explain_tool_chain(
        self,
        chain: ToolChain,
        detail_level: str = "medium"  # "brief", "medium", "detailed"
    ) -> Dict[str, Any]:
        """
        解释工具链的执行逻辑
        
        Args:
            chain: 工具链
            detail_level: 详细程度
            
        Returns:
            Dict: 解释内容
        """
        await self.initialize()
        
        try:
            explanation_prompt = self._build_explanation_prompt(chain, detail_level)
            
            response = await self._llm.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的工具链解释专家，能够清晰地解释复杂的自动化流程。"
                    },
                    {"role": "user", "content": explanation_prompt}
                ],
                model=self.orchestration_model,
                temperature=0.3
            )
            
            explanation_content = response.get("message", {}).get("content", "")
            
            return {
                "chain_id": chain.chain_id,
                "explanation": explanation_content,
                "detail_level": detail_level,
                "step_count": len(chain.execution_plan.steps),
                "estimated_duration": chain.execution_plan.estimated_duration,
                "success_probability": chain.execution_plan.success_probability,
                "complexity": chain.execution_plan.complexity.value,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"解释工具链失败: {str(e)}", exc_info=True)
            return {
                "chain_id": chain.chain_id,
                "explanation": "暂无法生成详细解释",
                "error": str(e)
            }
    
    # ========== 私有方法 ==========
    
    async def _analyze_task_requirements(
        self, 
        description: str, 
        domain_context: Optional[str]
    ) -> Dict[str, Any]:
        """分析任务需求"""
        analysis_prompt = f"""
请分析以下任务需求：

任务描述: {description}
领域上下文: {domain_context or "通用"}

请从以下维度分析任务：
1. 主要目标和子目标
2. 所需的核心能力
3. 输入和输出要求
4. 执行复杂度评估
5. 可能的技术挑战
6. 推荐的工具类型

请以JSON格式返回分析结果：
{{
    "main_objectives": ["目标1", "目标2"],
    "sub_objectives": ["子目标1", "子目标2"],
    "required_capabilities": ["能力1", "能力2"],
    "input_requirements": {{"type": "text", "format": "json"}},
    "output_expectations": {{"type": "report", "format": "markdown"}},
    "complexity_level": "medium",
    "technical_challenges": ["挑战1", "挑战2"],
    "recommended_tool_types": ["search", "analysis", "generation"]
}}
"""

        response = await self._llm.chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的任务分析专家，擅长分解复杂任务并识别技术需求。"
                },
                {"role": "user", "content": analysis_prompt}
            ],
            model=self.orchestration_model,
            temperature=self.planning_temperature
        )
        
        try:
            content = response.get("message", {}).get("content", "")
            json_str = self._extract_json_from_text(content)
            return json.loads(json_str)
        except Exception as e:
            logger.warning(f"任务分析解析失败: {str(e)}")
            return {
                "main_objectives": [description],
                "required_capabilities": ["general"],
                "complexity_level": "medium",
                "recommended_tool_types": ["general"]
            }
    
    async def _generate_candidate_tool_chains(
        self,
        task_analysis: Dict[str, Any],
        available_tools: List[Any],
        complexity_preference: str
        ) -> List[List[str]]:
        """生成候选工具链"""
        
        # 根据推荐的工具类型筛选工具
        recommended_types = task_analysis.get("recommended_tool_types", [])
        suitable_tools = []
        
        # 首先从工具注册系统中查找
        tool_registry = get_tool_registry()
        for rec_type in recommended_types:
            # 尝试匹配工具分类
            for category in ToolCategory:
                if rec_type.lower() in category.value.lower():
                    category_tools = tool_registry.get_tools_by_category(category)
                    suitable_tools.extend(category_tools)
        
        # 补充从工具服务获取的工具
        for tool in available_tools:
            tool_category = getattr(tool, 'category', 'general').lower()
            if any(rec_type.lower() in tool_category for rec_type in recommended_types):
                if tool.name not in suitable_tools:
                    suitable_tools.append(tool.name)
        
        # 如果没有合适的工具，使用所有可用工具
        if not suitable_tools:
            suitable_tools = [tool.name for tool in available_tools]
            # 补充注册系统中的活跃工具
            all_registered_tools = tool_registry.list_all_tools()
            suitable_tools.extend([t for t in all_registered_tools if t not in suitable_tools])
        
        # 根据复杂度偏好生成不同长度的工具链
        candidates = []
        
        if complexity_preference == "simple":
            max_tools = 3
        elif complexity_preference == "complex":
            max_tools = 8
        else:  # balanced
            max_tools = 5
        
        # 生成不同组合
        import itertools
        for length in range(1, min(max_tools + 1, len(suitable_tools) + 1)):
            for combo in itertools.combinations(suitable_tools, length):
                candidates.append(list(combo))
                if len(candidates) >= 10:  # 限制候选数量
                    break
            if len(candidates) >= 10:
                break
        
        return candidates[:5]  # 返回前5个候选
    
    async def _select_optimal_tool_chain(
        self,
        candidates: List[List[str]],
        task_analysis: Dict[str, Any]
    ) -> List[str]:
        """选择最优工具链"""
        
        if not candidates:
            return []
        
        best_score = -1
        best_chain = candidates[0]
        
        for candidate in candidates:
            # 使用AI分析评估候选工具链
            analysis = await self.ai_recommender.analyze_tool_combinations(
                candidate, 
                " ".join(task_analysis.get("main_objectives", []))
            )
            
            # 计算综合评分
            score = (
                analysis.compatibility_score * 0.3 +
                analysis.effectiveness_score * 0.4 +
                analysis.success_probability * 0.3
            )
            
            if score > best_score:
                best_score = score
                best_chain = candidate
        
        return best_chain
    
    def _extract_json_from_text(self, text: str) -> str:
        """从文本中提取JSON字符串"""
        # 复用AI推荐器中的方法
        start_markers = ["```json", "```", "{"]
        
        for start_marker in start_markers:
            start_idx = text.find(start_marker)
            if start_idx != -1:
                if start_marker == "{":
                    brace_count = 0
                    for i, char in enumerate(text[start_idx:], start_idx):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                return text[start_idx:i+1]
                else:
                    start_idx += len(start_marker)
                    end_idx = text.find("```", start_idx)
                    if end_idx != -1:
                        return text[start_idx:end_idx].strip()
        
        return text.strip()

    # 其他辅助方法实现
    async def _analyze_tool_dependencies(self, tools: List[str]) -> Dict[str, List[str]]:
        """分析工具依赖关系"""
        dependencies = {}
        for tool in tools:
            dependencies[tool] = []  # 简化实现
        return dependencies
    
    def _estimate_task_complexity(self, tools: List[str], objective: str) -> TaskComplexity:
        """估算任务复杂度"""
        tool_count = len(tools)
        if tool_count <= 2:
            return TaskComplexity.SIMPLE
        elif tool_count <= 5:
            return TaskComplexity.MODERATE
        elif tool_count <= 10:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.ENTERPRISE
    
    async def _generate_execution_steps(
        self,
        tools: List[str],
        objective: str,
        dependencies: Dict[str, List[str]],
        strategy: ExecutionStrategy
    ) -> List[ToolChainStep]:
        """生成执行步骤"""
        steps = []
        for i, tool in enumerate(tools):
            step = ToolChainStep(
                step_id=f"step_{i+1}",
                tool_name=tool,
                tool_description=f"执行工具: {tool}",
                action_description=f"使用{tool}处理任务",
                input_requirements={},
                output_expectations={},
                dependencies=dependencies.get(tool, []),
                execution_strategy=strategy,
                timeout_seconds=300,
                retry_count=3,
                fallback_tools=[]
            )
            steps.append(step)
        return steps
    
    def _determine_execution_order(
        self, 
        steps: List[ToolChainStep], 
        strategy: ExecutionStrategy
    ) -> Tuple[List[str], List[List[str]]]:
        """确定执行顺序"""
        execution_order = [step.step_id for step in steps]
        parallel_groups = []  # 简化实现，不设置并行组
        return execution_order, parallel_groups
    
    def _set_checkpoints(self, steps: List[ToolChainStep], complexity: TaskComplexity) -> List[int]:
        """设置检查点"""
        checkpoint_interval = {
            TaskComplexity.SIMPLE: len(steps),
            TaskComplexity.MODERATE: max(2, len(steps) // 2),
            TaskComplexity.COMPLEX: max(3, len(steps) // 3),
            TaskComplexity.ENTERPRISE: max(5, len(steps) // 5)
        }
        
        interval = checkpoint_interval[complexity]
        return list(range(interval - 1, len(steps), interval))
    
    async def _estimate_execution_duration(self, steps: List[ToolChainStep]) -> float:
        """估算执行时间（分钟）"""
        total_seconds = sum(step.timeout_seconds for step in steps)
        return total_seconds / 60.0
    
    def _generate_rollback_strategy(self, steps: List[ToolChainStep]) -> Dict[str, Any]:
        """生成回滚策略"""
        return {
            "enabled": True,
            "checkpoint_rollback": True,
            "auto_retry": True,
            "max_rollback_attempts": 3
        }
    
    def _calculate_resource_requirements(self, steps: List[ToolChainStep]) -> Dict[str, Any]:
        """计算资源需求"""
        return {
            "memory_mb": len(steps) * 100,  # 简化计算
            "cpu_cores": min(4, len(steps)),
            "network_bandwidth": "medium",
            "storage_mb": len(steps) * 50
        }
    
    async def _create_simple_execution_plan(self, tools: List[str], objective: str) -> ExecutionPlan:
        """创建简单执行计划"""
        steps = []
        for i, tool in enumerate(tools):
            step = ToolChainStep(
                step_id=f"step_{i+1}",
                tool_name=tool,
                tool_description=f"执行工具: {tool}",
                action_description=f"使用{tool}处理任务",
                input_requirements={},
                output_expectations={},
                dependencies=[],
                execution_strategy=ExecutionStrategy.SEQUENTIAL,
                timeout_seconds=300,
                retry_count=3,
                fallback_tools=[]
            )
            steps.append(step)
        
        return ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            objective=objective,
            total_steps=len(steps),
            estimated_duration=len(steps) * 5.0,  # 5分钟每个步骤
            complexity=TaskComplexity.SIMPLE,
            success_probability=0.7,
            steps=steps,
            execution_order=[step.step_id for step in steps],
            parallel_groups=[],
            checkpoints=[],
            rollback_strategy={"enabled": False},
            resource_requirements={"memory_mb": 500, "cpu_cores": 1}
        )
    
    def _generate_chain_name(self, description: str) -> str:
        """生成工具链名称"""
        # 简单的名称生成逻辑
        words = description.split()[:3]
        return "工具链-" + "-".join(words)
    
    async def _create_fallback_chain(self, description: str, user_id: str) -> ToolChain:
        """创建fallback工具链"""
        execution_plan = await self._create_simple_execution_plan(["通用工具"], description)
        
        return ToolChain(
            chain_id=str(uuid.uuid4()),
            name="简单工具链",
            description=description,
            objective=description,
            tools=["通用工具"],
            execution_plan=execution_plan,
            ai_analysis=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            creator_id=user_id,
            status="draft"
        )
    
    def _get_or_create_conversation_context(
        self,
        conversation_id: str,
        user_id: str,
        objective: str,
        chain: Optional[ToolChain]
    ) -> ConversationContext:
        """获取或创建对话上下文"""
        if conversation_id not in self._conversation_contexts:
            self._conversation_contexts[conversation_id] = ConversationContext(
                conversation_id=conversation_id,
                user_id=user_id,
                current_objective=objective,
                current_chain=chain,
                conversation_history=[],
                user_preferences={},
                domain_context=None
            )
        return self._conversation_contexts[conversation_id]
    
    async def _analyze_user_feedback(
        self,
        feedback: str,
        chain: ToolChain,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """分析用户反馈"""
        # 简化实现
        return {
            "feedback_type": "optimization_request",
            "requested_changes": [feedback],
            "sentiment": "neutral",
            "specific_tools": [],
            "general_preferences": []
        }
    
    async def _generate_optimization_suggestions(
        self,
        feedback_analysis: Dict[str, Any],
        chain: ToolChain,
        context: ConversationContext
    ) -> List[Dict[str, Any]]:
        """生成优化建议"""
        # 简化实现
        return [
            {
                "type": "tool_replacement",
                "description": "根据反馈优化工具选择",
                "confidence": 0.8
            }
        ]
    
    async def _apply_optimizations(
        self,
        chain: ToolChain,
        suggestions: List[Dict[str, Any]],
        feedback_analysis: Dict[str, Any]
    ) -> ToolChain:
        """应用优化建议"""
        # 创建优化后的工具链副本
        optimized_chain = ToolChain(
            chain_id=str(uuid.uuid4()),
            name=chain.name + " (优化版)",
            description=chain.description,
            objective=chain.objective,
            tools=chain.tools.copy(),  # 简化实现，保持相同工具
            execution_plan=chain.execution_plan,
            ai_analysis=chain.ai_analysis,
            created_at=chain.created_at,
            updated_at=datetime.now(),
            creator_id=chain.creator_id,
            status="optimized"
        )
        return optimized_chain
    
    def _update_conversation_history(
        self,
        context: ConversationContext,
        feedback: str,
        optimized_chain: ToolChain,
        suggestions: List[Dict[str, Any]]
    ):
        """更新对话历史"""
        context.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "user_feedback": feedback,
            "applied_suggestions": suggestions,
            "chain_id": optimized_chain.chain_id
        })
    
    def _build_explanation_prompt(self, chain: ToolChain, detail_level: str) -> str:
        """构建解释提示词"""
        tools_info = ", ".join(chain.tools)
        
        return f"""
请解释以下工具链的执行逻辑：

工具链名称: {chain.name}
目标: {chain.objective}
包含工具: {tools_info}
步骤数量: {chain.execution_plan.total_steps}
预估时间: {chain.execution_plan.estimated_duration:.1f}分钟

详细程度: {detail_level}

请提供：
1. 工具链的整体目标和价值
2. 各个步骤的执行逻辑
3. 工具间的协作关系
4. 预期的输出结果
5. 可能的风险点和应对策略

请使用通俗易懂的语言，确保非技术用户也能理解。
"""


# 工厂函数
def get_natural_language_orchestrator(
    tool_service: ToolService,
    ai_recommender: AIToolCombinationRecommender,
    nl_parser: NLConfigParser
) -> NaturalLanguageOrchestrator:
    """获取自然语言工具编排器实例"""
    return NaturalLanguageOrchestrator(tool_service, ai_recommender, nl_parser) 