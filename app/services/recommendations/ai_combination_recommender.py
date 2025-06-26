"""
AI驱动的工具组合推荐器
使用大语言模型分析工具组合效果，预测成功率，优化工具链
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from .recommendation_types import (
    ToolChainRecommendation, 
    ToolChainStep,
    RecommendationContext,
    RecommendationType,
    RecommendationReason
)

# 集成现有的LLM服务
from app.frameworks.llamaindex.chat import LlamaIndexChatServiceConfig
from core.model_manager import ModelManager
from app.frameworks.integration.factory import get_llm_service
from app.services.tools.tool_service import ToolService
from app.utils.version.tool_usage_stats import ToolUsageStatsManager

# 集成现有的工具注册系统
from app.tools.zzdsj_tool_registry import get_tool_registry, ToolCategory

logger = logging.getLogger(__name__)

@dataclass
class ToolCombinationAnalysis:
    """工具组合分析结果"""
    tool_chain: List[str]
    compatibility_score: float  # 工具兼容性评分 (0-1)
    effectiveness_score: float  # 组合效果评分 (0-1)
    success_probability: float  # 预测成功率 (0-1)
    optimization_suggestions: List[str]
    risk_factors: List[str]
    synergy_effects: List[str]
    estimated_execution_time: float  # 预估执行时间(秒)
    complexity_level: str  # 复杂度等级: "low", "medium", "high"
    
@dataclass 
class OptimizedToolChain:
    """优化后的工具链"""
    original_chain: List[str]
    optimized_chain: List[str]
    optimization_reasons: List[str]
    performance_improvement: float  # 性能提升百分比
    risk_reduction: float  # 风险降低百分比
    
class AIToolCombinationRecommender:
    """AI驱动的工具组合推荐器"""
    
    def __init__(self, tool_service: ToolService, usage_stats: ToolUsageStatsManager):
        self.tool_service = tool_service
        self.usage_stats = usage_stats
        self.model_manager = ModelManager()
        self._llm = None
        
        # AI分析模型配置
        self.analysis_model = "gpt-4o"
        self.analysis_temperature = 0.3
        self.max_retries = 3
        
    async def initialize(self):
        """初始化AI服务"""
        if self._llm is None:
            config = LlamaIndexChatServiceConfig()
            self._llm = await get_llm_service(config)
            logger.info("AI工具组合推荐器初始化完成")
    
    async def analyze_tool_combinations(
        self, 
        tools: List[str], 
        objective: str,
        context: Optional[RecommendationContext] = None
    ) -> ToolCombinationAnalysis:
        """
        使用AI分析工具组合效果
        
        Args:
            tools: 工具名称列表
            objective: 目标描述
            context: 推荐上下文
            
        Returns:
            ToolCombinationAnalysis: 分析结果
        """
        await self.initialize()
        
        try:
            # 获取工具详细信息
            tool_details = await self._get_tool_details(tools)
            
            # 获取历史使用数据
            usage_data = await self._get_usage_data(tools, context.user_id if context else None)
            
            # 构建分析提示词
            analysis_prompt = self._build_combination_analysis_prompt(
                tool_details, objective, usage_data
            )
            
            # 调用AI进行分析
            response = await self._call_llm_for_analysis(analysis_prompt)
            
            # 解析响应并构建分析结果
            analysis_result = self._parse_combination_analysis(response, tools)
            
            logger.info(f"工具组合分析完成: {tools} -> 成功率: {analysis_result.success_probability:.2f}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"工具组合分析失败: {str(e)}", exc_info=True)
            # 返回默认分析结果
            return ToolCombinationAnalysis(
                tool_chain=tools,
                compatibility_score=0.5,
                effectiveness_score=0.5,
                success_probability=0.5,
                optimization_suggestions=["请检查工具配置"],
                risk_factors=["分析失败，建议手动检查"],
                synergy_effects=[],
                estimated_execution_time=60.0,
                complexity_level="medium"
            )
    
    async def predict_success_rate(
        self, 
        tool_chain: List[str], 
        task_description: str,
        user_id: Optional[str] = None
    ) -> float:
        """
        预测工具链成功率
        
        Args:
            tool_chain: 工具链
            task_description: 任务描述
            user_id: 用户ID
            
        Returns:
            float: 预测成功率 (0-1)
        """
        await self.initialize()
        
        try:
            # 获取历史成功数据
            historical_data = await self._get_historical_success_data(tool_chain, user_id)
            
            # 获取工具性能数据
            performance_data = await self._get_tool_performance_data(tool_chain)
            
            # 构建预测提示词
            prediction_prompt = self._build_success_prediction_prompt(
                tool_chain, task_description, historical_data, performance_data
            )
            
            # 调用AI进行预测
            response = await self._call_llm_for_prediction(prediction_prompt)
            
            # 解析预测结果
            success_rate = self._parse_success_prediction(response)
            
            logger.info(f"成功率预测完成: {tool_chain} -> {success_rate:.2f}")
            return success_rate
            
        except Exception as e:
            logger.error(f"成功率预测失败: {str(e)}", exc_info=True)
            # 基于历史数据返回保守估计
            return await self._calculate_fallback_success_rate(tool_chain, user_id)
    
    async def optimize_tool_sequence(
        self, 
        tools: List[str], 
        objective: str,
        constraints: Optional[Dict[str, Any]] = None
    ) -> OptimizedToolChain:
        """
        优化工具执行顺序
        
        Args:
            tools: 原始工具列表
            objective: 目标描述
            constraints: 约束条件（如时间限制、资源限制等）
            
        Returns:
            OptimizedToolChain: 优化后的工具链
        """
        await self.initialize()
        
        try:
            # 分析工具依赖关系
            dependencies = await self._analyze_tool_dependencies(tools)
            
            # 获取工具性能数据
            performance_data = await self._get_tool_performance_data(tools)
            
            # 构建优化提示词
            optimization_prompt = self._build_optimization_prompt(
                tools, objective, dependencies, performance_data, constraints
            )
            
            # 调用AI进行优化
            response = await self._call_llm_for_optimization(optimization_prompt)
            
            # 解析优化结果
            optimized_chain = self._parse_optimization_result(response, tools)
            
            logger.info(f"工具链优化完成: {tools} -> {optimized_chain.optimized_chain}")
            return optimized_chain
            
        except Exception as e:
            logger.error(f"工具链优化失败: {str(e)}", exc_info=True)
            # 返回基于规则的简单优化
            return await self._rule_based_optimization(tools, objective)
    
    async def generate_intelligent_tool_chains(
        self,
        objective: str,
        context: RecommendationContext,
        max_chains: int = 5,
        complexity_preference: str = "balanced"  # "simple", "balanced", "complex"
    ) -> List[ToolChainRecommendation]:
        """
        基于AI生成智能工具链推荐
        
        Args:
            objective: 目标描述
            context: 推荐上下文
            max_chains: 最大工具链数量
            complexity_preference: 复杂度偏好
            
        Returns:
            List[ToolChainRecommendation]: 智能生成的工具链推荐
        """
        await self.initialize()
        
        try:
            # 获取可用工具
            available_tools = await self.tool_service.get_user_accessible_tools(context.user_id)
            
            # 分析目标并识别所需能力
            required_capabilities = await self._analyze_objective_capabilities(objective)
            
            # 构建智能生成提示词
            generation_prompt = self._build_intelligent_generation_prompt(
                objective, available_tools, required_capabilities, complexity_preference
            )
            
            # 调用AI生成工具链
            response = await self._call_llm_for_generation(generation_prompt)
            
            # 解析并验证生成的工具链
            generated_chains = self._parse_generated_chains(response)
            
            # 对每个工具链进行AI分析评估
            evaluated_chains = []
            for chain_data in generated_chains[:max_chains]:
                analysis = await self.analyze_tool_combinations(
                    chain_data['tools'], objective, context
                )
                
                # 构建工具链推荐
                chain_recommendation = ToolChainRecommendation(
                    chain_id=f"ai_generated_{len(evaluated_chains)}",
                    objective=objective,
                    steps=[
                        ToolChainStep(
                            step_number=i+1,
                            tool_id=tool,
                            tool_name=tool,
                            action_description=chain_data['step_descriptions'][i],
                            expected_input=chain_data.get('expected_inputs', [{}])[i],
                            expected_output=chain_data.get('expected_outputs', [{}])[i]
                        ) for i, tool in enumerate(chain_data['tools'])
                    ],
                    confidence_score=analysis.success_probability,
                    estimated_duration=analysis.estimated_execution_time,
                    complexity_level=analysis.complexity_level,
                    success_probability=analysis.success_probability,
                    recommendation_type=RecommendationType.AI_GENERATED,
                    reasons=[
                        RecommendationReason.AI_ANALYSIS,
                        RecommendationReason.CAPABILITY_MATCH
                    ],
                    explanation=chain_data.get('explanation', ''),
                    ai_analysis=analysis
                )
                
                evaluated_chains.append(chain_recommendation)
            
            # 按置信度排序
            evaluated_chains.sort(key=lambda x: x.confidence_score, reverse=True)
            
            logger.info(f"智能工具链生成完成: {len(evaluated_chains)} 个工具链")
            return evaluated_chains
            
        except Exception as e:
            logger.error(f"智能工具链生成失败: {str(e)}", exc_info=True)
            return []
    
    # ========== 私有方法 ==========
    
    async def _get_tool_details(self, tool_names: List[str]) -> List[Dict[str, Any]]:
        """获取工具详细信息"""
        tool_details = []
        tool_registry = get_tool_registry()
        
        for tool_name in tool_names:
            try:
                # 优先从工具注册系统获取元数据
                metadata = tool_registry.get_tool_metadata(tool_name)
                if metadata:
                    tool_details.append({
                        'name': metadata.name,
                        'description': metadata.description,
                        'category': metadata.category.value,
                        'capabilities': metadata.capabilities,
                        'input_schema': {},  # 从工具注册系统扩展
                        'output_schema': {},  # 从工具注册系统扩展
                        'version': metadata.version,
                        'author': metadata.author,
                        'tags': metadata.tags
                    })
                else:
                    # 回退到工具服务
                    tool = await self.tool_service.get_tool_by_name(tool_name)
                    if tool:
                        tool_details.append({
                            'name': tool.name,
                            'description': tool.description,
                            'category': getattr(tool, 'category', 'general'),
                            'capabilities': getattr(tool, 'capabilities', []),
                            'input_schema': getattr(tool, 'input_schema', {}),
                            'output_schema': getattr(tool, 'output_schema', {})
                        })
            except Exception as e:
                logger.warning(f"获取工具详情失败: {tool_name} - {str(e)}")
        return tool_details
    
    async def _get_usage_data(self, tools: List[str], user_id: Optional[str]) -> Dict[str, Any]:
        """获取工具使用历史数据"""
        usage_data = {}
        for tool in tools:
            try:
                stats = await self.usage_stats.get_tool_stats(tool, user_id)
                usage_data[tool] = {
                    'success_rate': stats.get('success_rate', 0.0),
                    'avg_execution_time': stats.get('avg_execution_time', 0.0),
                    'usage_count': stats.get('usage_count', 0),
                    'last_used': stats.get('last_used')
                }
            except Exception as e:
                logger.warning(f"获取使用数据失败: {tool} - {str(e)}")
                usage_data[tool] = {
                    'success_rate': 0.5,
                    'avg_execution_time': 30.0,
                    'usage_count': 0,
                    'last_used': None
                }
        return usage_data
    
    def _build_combination_analysis_prompt(
        self, 
        tool_details: List[Dict], 
        objective: str, 
        usage_data: Dict
    ) -> str:
        """构建工具组合分析提示词"""
        tools_info = json.dumps(tool_details, ensure_ascii=False, indent=2)
        usage_info = json.dumps(usage_data, ensure_ascii=False, indent=2)
        
        return f"""
你是一个专业的AI工具链分析专家。请分析以下工具组合用于完成特定目标的效果。

目标: {objective}

工具详情:
{tools_info}

历史使用数据:
{usage_info}

请从以下维度进行深度分析：

1. **兼容性分析** (0-1评分):
   - 工具间输入输出匹配度
   - 数据格式兼容性
   - 依赖关系合理性

2. **效果预测** (0-1评分):
   - 组合是否能有效完成目标
   - 工具能力覆盖程度
   - 预期质量水平

3. **成功率预测** (0-1评分):
   - 基于历史数据的成功概率
   - 技术风险评估
   - 用户能力匹配度

4. **优化建议**:
   - 具体的改进方案
   - 替代工具推荐
   - 参数调优建议

5. **风险识别**:
   - 潜在失败点
   - 性能瓶颈
   - 依赖风险

6. **协同效应**:
   - 工具间的正向互动
   - 组合优势
   - 增值效果

请以以下JSON格式返回分析结果：
{{
    "compatibility_score": 0.85,
    "effectiveness_score": 0.78,
    "success_probability": 0.82,
    "optimization_suggestions": ["建议1", "建议2"],
    "risk_factors": ["风险1", "风险2"],
    "synergy_effects": ["协同1", "协同2"],
    "estimated_execution_time": 45.5,
    "complexity_level": "medium",
    "detailed_analysis": "详细分析说明..."
}}
"""

    async def _call_llm_for_analysis(self, prompt: str) -> Dict[str, Any]:
        """调用LLM进行分析"""
        response = await self._llm.chat_completion(
            messages=[
                {
                    "role": "system", 
                    "content": "你是一个专业的AI工具链分析专家，具有深度的技术理解和预测能力。"
                },
                {"role": "user", "content": prompt}
            ],
            model=self.analysis_model,
            temperature=self.analysis_temperature
        )
        return response
    
    def _parse_combination_analysis(self, response: Dict, tools: List[str]) -> ToolCombinationAnalysis:
        """解析组合分析结果"""
        try:
            content = response.get("message", {}).get("content", "")
            # 提取JSON部分
            json_str = self._extract_json_from_text(content)
            result = json.loads(json_str)
            
            return ToolCombinationAnalysis(
                tool_chain=tools,
                compatibility_score=result.get('compatibility_score', 0.5),
                effectiveness_score=result.get('effectiveness_score', 0.5),
                success_probability=result.get('success_probability', 0.5),
                optimization_suggestions=result.get('optimization_suggestions', []),
                risk_factors=result.get('risk_factors', []),
                synergy_effects=result.get('synergy_effects', []),
                estimated_execution_time=result.get('estimated_execution_time', 60.0),
                complexity_level=result.get('complexity_level', 'medium')
            )
        except Exception as e:
            logger.error(f"解析分析结果失败: {str(e)}")
            # 返回默认结果
            return ToolCombinationAnalysis(
                tool_chain=tools,
                compatibility_score=0.5,
                effectiveness_score=0.5,
                success_probability=0.5,
                optimization_suggestions=[],
                risk_factors=["解析失败"],
                synergy_effects=[],
                estimated_execution_time=60.0,
                complexity_level="medium"
            )
    
    def _extract_json_from_text(self, text: str) -> str:
        """从文本中提取JSON字符串"""
        # 寻找JSON代码块
        start_markers = ["```json", "```", "{"]
        end_markers = ["```", "}"]
        
        for start_marker in start_markers:
            start_idx = text.find(start_marker)
            if start_idx != -1:
                if start_marker == "{":
                    # 寻找匹配的结束大括号
                    brace_count = 0
                    for i, char in enumerate(text[start_idx:], start_idx):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                return text[start_idx:i+1]
                else:
                    # 寻找代码块结束
                    start_idx += len(start_marker)
                    end_idx = text.find("```", start_idx)
                    if end_idx != -1:
                        return text[start_idx:end_idx].strip()
        
        # 如果没有找到代码块，尝试整个文本
        return text.strip()

    # ... 其他私有方法的实现
    async def _get_historical_success_data(self, tools: List[str], user_id: Optional[str]) -> Dict:
        """获取历史成功数据"""
        historical_data = {}
        for tool in tools:
            try:
                stats = await self.usage_stats.get_tool_stats(tool, user_id)
                historical_data[tool] = {
                    'historical_success_rate': stats.get('success_rate', 0.5),
                    'recent_performance': stats.get('recent_performance', 0.5),
                    'failure_patterns': stats.get('failure_patterns', [])
                }
            except:
                historical_data[tool] = {
                    'historical_success_rate': 0.5,
                    'recent_performance': 0.5,
                    'failure_patterns': []
                }
        return historical_data
    
    async def _get_tool_performance_data(self, tools: List[str]) -> Dict:
        """获取工具性能数据"""
        performance_data = {}
        for tool in tools:
            try:
                perf_stats = await self.usage_stats.get_performance_stats(tool)
                performance_data[tool] = {
                    'avg_response_time': perf_stats.get('avg_response_time', 30.0),
                    'error_rate': perf_stats.get('error_rate', 0.1),
                    'resource_usage': perf_stats.get('resource_usage', 'medium')
                }
            except:
                performance_data[tool] = {
                    'avg_response_time': 30.0,
                    'error_rate': 0.1,
                    'resource_usage': 'medium'
                }
        return performance_data
    
    def _build_success_prediction_prompt(self, tool_chain, task_description, historical_data, performance_data) -> str:
        """构建成功率预测提示词"""
        historical_info = json.dumps(historical_data, ensure_ascii=False, indent=2)
        performance_info = json.dumps(performance_data, ensure_ascii=False, indent=2)
        
        return f"""
请预测以下工具链完成任务的成功率：

任务描述: {task_description}
工具链: {tool_chain}

历史成功数据:
{historical_info}

性能数据:
{performance_info}

请基于以下因素评估成功率（0-1之间的小数）：
1. 历史成功率
2. 工具性能表现
3. 任务复杂度匹配
4. 工具链逻辑合理性

请仅返回一个0到1之间的数字作为预测成功率。
"""
    
    async def _call_llm_for_prediction(self, prompt: str) -> Dict:
        """调用LLM进行预测"""
        response = await self._llm.chat_completion(
            messages=[
                {"role": "system", "content": "你是一个数据分析专家，擅长基于历史数据预测成功率。"},
                {"role": "user", "content": prompt}
            ],
            model=self.analysis_model,
            temperature=0.1  # 更低的温度以获得更稳定的预测
        )
        return response
    
    def _parse_success_prediction(self, response: Dict) -> float:
        """解析成功率预测结果"""
        try:
            content = response.get("message", {}).get("content", "")
            # 使用正则表达式提取数字
            import re
            numbers = re.findall(r'0\.\d+|\d*\.\d+', content)
            if numbers:
                rate = float(numbers[0])
                return min(max(rate, 0.0), 1.0)  # 确保在0-1范围内
        except Exception as e:
            logger.warning(f"解析成功率失败: {str(e)}")
        return 0.5
    
    async def _calculate_fallback_success_rate(self, tools: List[str], user_id: Optional[str]) -> float:
        """计算保守的成功率估计"""
        if not tools:
            return 0.5
        
        total_rate = 0.0
        for tool in tools:
            try:
                stats = await self.usage_stats.get_tool_stats(tool, user_id)
                total_rate += stats.get('success_rate', 0.5)
            except:
                total_rate += 0.5
        
        return total_rate / len(tools)

    async def _analyze_tool_dependencies(self, tools: List[str]) -> Dict:
        """分析工具依赖关系"""
        dependencies = {}
        for i, tool in enumerate(tools):
            dependencies[tool] = {
                'position': i,
                'dependencies': [],  # 简化实现
                'outputs_to': [],
                'required_inputs': []
            }
        return dependencies
    
    def _build_optimization_prompt(self, tools, objective, dependencies, performance_data, constraints) -> str:
        """构建优化提示词"""
        deps_info = json.dumps(dependencies, ensure_ascii=False, indent=2)
        perf_info = json.dumps(performance_data, ensure_ascii=False, indent=2)
        constraints_info = json.dumps(constraints or {}, ensure_ascii=False, indent=2)
        
        return f"""
请优化以下工具链的执行顺序：

目标: {objective}
当前工具链: {tools}

依赖关系:
{deps_info}

性能数据:
{perf_info}

约束条件:
{constraints_info}

请根据以下原则优化工具顺序：
1. 满足依赖关系
2. 最小化总执行时间
3. 降低失败风险
4. 考虑约束条件

请以JSON格式返回：
{{
    "optimized_chain": ["tool1", "tool2", "tool3"],
    "optimization_reasons": ["原因1", "原因2"],
    "performance_improvement": 0.15,
    "risk_reduction": 0.10
}}
"""
    
    async def _call_llm_for_optimization(self, prompt: str) -> Dict:
        """调用LLM进行优化"""
        response = await self._llm.chat_completion(
            messages=[
                {"role": "system", "content": "你是一个工作流优化专家，擅长分析和优化工具执行序列。"},
                {"role": "user", "content": prompt}
            ],
            model=self.analysis_model,
            temperature=0.2
        )
        return response
    
    def _parse_optimization_result(self, response: Dict, original_tools: List[str]) -> OptimizedToolChain:
        """解析优化结果"""
        try:
            content = response.get("message", {}).get("content", "")
            json_str = self._extract_json_from_text(content)
            result = json.loads(json_str)
            
            return OptimizedToolChain(
                original_chain=original_tools,
                optimized_chain=result.get('optimized_chain', original_tools),
                optimization_reasons=result.get('optimization_reasons', []),
                performance_improvement=result.get('performance_improvement', 0.0),
                risk_reduction=result.get('risk_reduction', 0.0)
            )
        except Exception as e:
            logger.error(f"解析优化结果失败: {str(e)}")
            return OptimizedToolChain(
                original_chain=original_tools,
                optimized_chain=original_tools,
                optimization_reasons=["优化解析失败，保持原有顺序"],
                performance_improvement=0.0,
                risk_reduction=0.0
            )
    
    async def _rule_based_optimization(self, tools: List[str], objective: str) -> OptimizedToolChain:
        """基于规则的简单优化"""
        # 简单的规则：将搜索工具放在前面，分析工具放在后面
        search_tools = [t for t in tools if 'search' in t.lower()]
        analysis_tools = [t for t in tools if any(word in t.lower() for word in ['analyze', 'process', 'generate'])]
        other_tools = [t for t in tools if t not in search_tools and t not in analysis_tools]
        
        optimized = search_tools + other_tools + analysis_tools
        
        return OptimizedToolChain(
            original_chain=tools,
            optimized_chain=optimized,
            optimization_reasons=["应用基于规则的优化：搜索->处理->分析"],
            performance_improvement=0.05,
            risk_reduction=0.03
        )

    async def _analyze_objective_capabilities(self, objective: str) -> List[str]:
        """分析目标所需能力"""
        return []
    
    def _build_intelligent_generation_prompt(self, objective, available_tools, required_capabilities, complexity_preference) -> str:
        """构建智能生成提示词"""
        return f"为目标 '{objective}' 生成工具链"
    
    async def _call_llm_for_generation(self, prompt: str) -> Dict:
        """调用LLM生成工具链"""
        response = await self._llm.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=self.analysis_model,
            temperature=self.analysis_temperature
        )
        return response
    
    def _parse_generated_chains(self, response: Dict) -> List[Dict]:
        """解析生成的工具链"""
        return []


# 工厂函数
def get_ai_combination_recommender(
    tool_service: ToolService, 
    usage_stats: ToolUsageStatsManager
) -> AIToolCombinationRecommender:
    """获取AI工具组合推荐器实例"""
    return AIToolCombinationRecommender(tool_service, usage_stats) 