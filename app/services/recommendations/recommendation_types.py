"""
推荐系统数据类型定义
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

class RecommendationType(Enum):
    """推荐类型"""
    SIMILAR_TOOLS = "similar_tools"
    TASK_BASED = "task_based"
    USER_PREFERENCE = "user_preference"
    COLLABORATIVE = "collaborative"
    TOOL_CHAIN = "tool_chain"
    CONTEXT_AWARE = "context_aware"

class RecommendationReason(Enum):
    """推荐原因"""
    HIGH_SUCCESS_RATE = "high_success_rate"
    FREQUENTLY_USED = "frequently_used"
    SIMILAR_USERS = "similar_users"
    COMPLEMENTARY_TOOLS = "complementary_tools"
    TASK_PATTERN = "task_pattern"
    PERFORMANCE_OPTIMIZED = "performance_optimized"

@dataclass
class RecommendationContext:
    """推荐上下文"""
    user_id: str
    task_description: Optional[str] = None
    current_tools: List[str] = None
    user_role: Optional[str] = None
    project_context: Optional[str] = None
    time_constraint: Optional[int] = None  # 时间限制（秒）
    performance_priority: bool = False  # 是否优先考虑性能
    cost_sensitive: bool = False  # 是否对成本敏感
    
    def __post_init__(self):
        if self.current_tools is None:
            self.current_tools = []

@dataclass
class ToolRecommendation:
    """工具推荐结果"""
    tool_id: str
    tool_name: str
    tool_description: str
    confidence_score: float  # 推荐置信度 0-1
    recommendation_type: RecommendationType
    reasons: List[RecommendationReason]
    explanation: str  # 推荐解释
    expected_performance: Optional[Dict[str, Any]] = None  # 预期性能指标
    usage_statistics: Optional[Dict[str, Any]] = None  # 使用统计
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        # 确保置信度在有效范围内
        self.confidence_score = max(0.0, min(1.0, self.confidence_score))

@dataclass 
class ToolChainStep:
    """工具链步骤"""
    order: int
    tool_id: str
    tool_name: str
    input_mapping: Dict[str, str]  # 输入参数映射
    output_mapping: Dict[str, str]  # 输出结果映射
    condition: Optional[str] = None  # 执行条件
    error_handling: str = "fail"  # 错误处理策略

@dataclass
class ToolChainRecommendation:
    """工具链推荐结果"""
    chain_id: str
    chain_name: str
    description: str
    steps: List[ToolChainStep]
    confidence_score: float
    expected_success_rate: float  # 预期成功率
    estimated_duration: Optional[int] = None  # 预估执行时间（秒）
    complexity_level: str = "medium"  # 复杂度：low, medium, high
    use_cases: List[str] = None  # 适用场景
    prerequisites: List[str] = None  # 前置条件
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.use_cases is None:
            self.use_cases = []
        if self.prerequisites is None:
            self.prerequisites = []
        self.confidence_score = max(0.0, min(1.0, self.confidence_score))
        self.expected_success_rate = max(0.0, min(1.0, self.expected_success_rate))

@dataclass
class RecommendationResult:
    """推荐结果集合"""
    tool_recommendations: List[ToolRecommendation]
    chain_recommendations: List[ToolChainRecommendation]
    context: RecommendationContext
    timestamp: datetime
    total_recommendations: int
    processing_time_ms: float
    
    def __post_init__(self):
        self.total_recommendations = len(self.tool_recommendations) + len(self.chain_recommendations)

class RecommendationMetrics:
    """推荐指标"""
    
    @staticmethod
    def calculate_precision(recommended: List[str], actually_used: List[str]) -> float:
        """计算推荐精确率"""
        if not recommended:
            return 0.0
        
        recommended_set = set(recommended)
        used_set = set(actually_used)
        true_positives = len(recommended_set.intersection(used_set))
        
        return true_positives / len(recommended_set)
    
    @staticmethod
    def calculate_recall(recommended: List[str], actually_used: List[str]) -> float:
        """计算推荐召回率"""
        if not actually_used:
            return 0.0
        
        recommended_set = set(recommended)
        used_set = set(actually_used)
        true_positives = len(recommended_set.intersection(used_set))
        
        return true_positives / len(used_set)
    
    @staticmethod
    def calculate_f1_score(precision: float, recall: float) -> float:
        """计算F1分数"""
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall) 