"""
推荐系统类型定义
包含工具链推荐相关的数据结构和枚举
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

class RecommendationType(str, Enum):
    """推荐类型枚举"""
    USAGE_BASED = "usage_based"        # 基于使用历史的推荐
    SIMILARITY = "similarity"          # 基于相似性的推荐
    COLLABORATIVE = "collaborative"    # 协同过滤推荐
    AI_GENERATED = "ai_generated"      # AI生成的推荐
    RULE_BASED = "rule_based"         # 基于规则的推荐
    HYBRID = "hybrid"                 # 混合推荐

class RecommendationReason(str, Enum):
    """推荐原因枚举"""
    HIGH_SUCCESS_RATE = "high_success_rate"      # 高成功率
    FREQUENT_USAGE = "frequent_usage"            # 高使用频率
    SIMILAR_TASKS = "similar_tasks"              # 相似任务
    USER_PREFERENCE = "user_preference"          # 用户偏好
    EXPERT_RECOMMENDATION = "expert_recommendation"  # 专家推荐
    AI_ANALYSIS = "ai_analysis"                  # AI分析
    CAPABILITY_MATCH = "capability_match"        # 能力匹配
    PERFORMANCE_OPTIMIZED = "performance_optimized"  # 性能优化

@dataclass
class RecommendationContext:
    """推荐上下文"""
    user_id: str
    task_description: str
    domain: Optional[str] = None
    complexity_preference: str = "balanced"  # "simple", "balanced", "complex"
    time_constraint: Optional[int] = None  # 时间限制（分钟）
    resource_constraint: Optional[Dict[str, Any]] = None  # 资源限制
    previous_chains: List[str] = None  # 之前使用的工具链ID
    user_preferences: Dict[str, Any] = None  # 用户偏好
    
    def __post_init__(self):
        if self.previous_chains is None:
            self.previous_chains = []
        if self.user_preferences is None:
            self.user_preferences = {}

@dataclass
class ToolChainStep:
    """工具链步骤"""
    step_number: int
    tool_id: str
    tool_name: str
    action_description: str
    expected_input: Dict[str, Any]
    expected_output: Dict[str, Any]
    estimated_duration: Optional[float] = None  # 预估时间（分钟）
    dependencies: List[int] = None  # 依赖的步骤号
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

@dataclass
class ToolChainRecommendation:
    """工具链推荐"""
    chain_id: str
    objective: str
    steps: List[ToolChainStep]
    confidence_score: float  # 置信度评分 (0-1)
    estimated_duration: float  # 预估总时间（分钟）
    complexity_level: str  # "low", "medium", "high"
    success_probability: float  # 成功率预测 (0-1)
    recommendation_type: RecommendationType
    reasons: List[RecommendationReason]
    explanation: str  # 推荐说明
    created_at: datetime = None
    updated_at: datetime = None
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    ai_analysis: Optional[Any] = None  # AI分析结果
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

@dataclass 
class ToolRecommendation:
    """单个工具推荐"""
    tool_id: str
    tool_name: str
    description: str
    category: str
    confidence_score: float
    reasons: List[RecommendationReason]
    estimated_performance: Dict[str, float]  # 预估性能指标
    compatibility_score: float  # 与其他工具的兼容性
    
@dataclass
class RecommendationResult:
    """推荐结果"""
    request_id: str
    context: RecommendationContext
    tool_chain_recommendations: List[ToolChainRecommendation]
    individual_tool_recommendations: List[ToolRecommendation]
    total_recommendations: int
    processing_time: float  # 处理时间（秒）
    recommendation_quality: float  # 推荐质量评分 (0-1)
    generated_at: datetime = None
    
    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now()

@dataclass
class UserFeedback:
    """用户反馈"""
    feedback_id: str
    user_id: str
    recommendation_id: str
    rating: int  # 1-5评分
    comments: Optional[str] = None
    used_recommendation: bool = False
    execution_success: Optional[bool] = None
    actual_duration: Optional[float] = None
    suggested_improvements: List[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.suggested_improvements is None:
            self.suggested_improvements = []
        if self.created_at is None:
            self.created_at = datetime.now()

class RecommendationFilter:
    """推荐过滤器"""
    
    def __init__(
        self,
        min_confidence: float = 0.5,
        max_complexity: Optional[str] = None,
        max_duration: Optional[float] = None,
        required_capabilities: List[str] = None,
        excluded_tools: List[str] = None,
        preferred_categories: List[str] = None
    ):
        self.min_confidence = min_confidence
        self.max_complexity = max_complexity
        self.max_duration = max_duration
        self.required_capabilities = required_capabilities or []
        self.excluded_tools = excluded_tools or []
        self.preferred_categories = preferred_categories or []
    
    def apply(self, recommendations: List[ToolChainRecommendation]) -> List[ToolChainRecommendation]:
        """应用过滤器"""
        filtered = []
        
        for rec in recommendations:
            # 置信度过滤
            if rec.confidence_score < self.min_confidence:
                continue
            
            # 复杂度过滤
            if self.max_complexity:
                complexity_levels = {"low": 1, "medium": 2, "high": 3}
                if complexity_levels.get(rec.complexity_level, 3) > complexity_levels.get(self.max_complexity, 3):
                    continue
            
            # 时间过滤
            if self.max_duration and rec.estimated_duration > self.max_duration:
                continue
            
            # 排除工具过滤
            step_tools = [step.tool_id for step in rec.steps]
            if any(tool in self.excluded_tools for tool in step_tools):
                continue
            
            filtered.append(rec)
        
        return filtered

@dataclass
class RecommendationMetrics:
    """推荐指标"""
    total_requests: int
    successful_recommendations: int
    user_satisfaction_avg: float
    execution_success_rate: float
    avg_processing_time: float
    recommendation_diversity: float
    top_performing_chains: List[Dict[str, Any]]
    
@dataclass
class ToolUsagePattern:
    """工具使用模式"""
    pattern_id: str
    user_segment: str
    common_tool_sequences: List[List[str]]
    success_rate: float
    avg_execution_time: float
    domain_context: Optional[str] = None
    frequency: int = 0 