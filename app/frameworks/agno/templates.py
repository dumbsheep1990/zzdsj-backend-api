"""
Agno智能体模版定义
定义三种内置默认智能体模版：基础对话、知识库问答、深度思考
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from app.frameworks.agno.orchestration.types import AgentRole, ToolCategory


class TemplateType(Enum):
    """模版类型枚举"""
    BASIC_CONVERSATION = "basic_conversation"
    KNOWLEDGE_BASE = "knowledge_base"
    DEEP_THINKING = "deep_thinking"


@dataclass
class ExecutionNode:
    """执行图节点"""
    id: str
    type: str  # processor, classifier, retriever, generator, coordinator
    config: Dict[str, Any]


@dataclass
class ExecutionEdge:
    """执行图边"""
    from_node: str
    to_node: str
    condition: str = None
    weight: float = 1.0
    timeout: int = 30


@dataclass
class ExecutionGraph:
    """执行图定义"""
    nodes: List[ExecutionNode]
    edges: List[ExecutionEdge]


@dataclass
class AgentTemplate:
    """智能体模版定义"""
    template_id: str
    name: str
    role: AgentRole
    description: str
    use_cases: List[str]
    estimated_cost: str
    execution_graph: ExecutionGraph
    default_tools: List[str]
    model_config: Dict[str, Any]
    capabilities: List[str]
    instructions: List[str]


# ==================== 基础对话模版 ====================

BASIC_CONVERSATION_EXECUTION_GRAPH = ExecutionGraph(
    nodes=[
        ExecutionNode(
            id="input_analysis",
            type="processor",
            config={
                "max_context": 10,
                "extract_intent": True,
                "sentiment_analysis": True
            }
        ),
        ExecutionNode(
            id="intent_recognition", 
            type="classifier",
            config={
                "categories": ["question", "request", "chat", "task"],
                "confidence_threshold": 0.7
            }
        ),
        ExecutionNode(
            id="context_enrichment",
            type="processor",
            config={
                "include_history": True,
                "max_history_turns": 5
            }
        ),
        ExecutionNode(
            id="response_generation",
            type="generator", 
            config={
                "style": "friendly",
                "max_tokens": 500,
                "temperature": 0.7
            }
        ),
        ExecutionNode(
            id="output_formatting",
            type="formatter",
            config={
                "markdown": True,
                "include_citations": False
            }
        )
    ],
    edges=[
        ExecutionEdge("input_analysis", "intent_recognition"),
        ExecutionEdge("intent_recognition", "context_enrichment"),
        ExecutionEdge("context_enrichment", "response_generation"),
        ExecutionEdge("response_generation", "output_formatting")
    ]
)

BASIC_CONVERSATION_TEMPLATE = AgentTemplate(
    template_id=TemplateType.BASIC_CONVERSATION.value,
    name="基础对话助手",
    role=AgentRole.ASSISTANT,
    description="友好的多轮对话助手，提供自然流畅的交互体验",
    use_cases=["客户服务", "日常聊天", "简单咨询", "信息查询"],
    estimated_cost="低",
    execution_graph=BASIC_CONVERSATION_EXECUTION_GRAPH,
    default_tools=["search", "calculator", "datetime", "weather"],
    model_config={
        "preferred_models": ["gpt-4o-mini", "claude-3-haiku"],
        "temperature": 0.7,
        "max_tokens": 1000,
        "response_format": "text"
    },
    capabilities=[
        "多轮对话",
        "上下文理解", 
        "个性化回复",
        "情感识别",
        "意图理解"
    ],
    instructions=[
        "你是一个友好、专业的AI助手",
        "保持对话的自然流畅性",
        "准确理解用户意图并提供有帮助的回答",
        "在不确定时主动询问澄清",
        "保持积极正面的沟通态度"
    ]
)


# ==================== 知识库问答模版 ====================

KNOWLEDGE_BASE_EXECUTION_GRAPH = ExecutionGraph(
    nodes=[
        ExecutionNode(
            id="question_analysis",
            type="analyzer",
            config={
                "extract_entities": True,
                "extract_keywords": True,
                "query_expansion": True
            }
        ),
        ExecutionNode(
            id="kb_retrieval",
            type="retriever",
            config={
                "top_k": 5,
                "similarity_threshold": 0.8,
                "rerank": True
            }
        ),
        ExecutionNode(
            id="relevance_scoring",
            type="scorer",
            config={
                "algorithm": "semantic",
                "combine_scores": True,
                "min_relevance": 0.6
            }
        ),
        ExecutionNode(
            id="document_filtering",
            type="filter",
            config={
                "max_documents": 3,
                "diversity_threshold": 0.3
            }
        ),
        ExecutionNode(
            id="answer_synthesis",
            type="synthesizer",
            config={
                "include_citations": True,
                "max_synthesis_length": 1000,
                "preserve_sources": True
            }
        ),
        ExecutionNode(
            id="confidence_evaluation",
            type="evaluator",
            config={
                "min_confidence": 0.7,
                "uncertainty_handling": True
            }
        ),
        ExecutionNode(
            id="citation_formatting",
            type="formatter",
            config={
                "citation_style": "numbered",
                "include_urls": True
            }
        )
    ],
    edges=[
        ExecutionEdge("question_analysis", "kb_retrieval"),
        ExecutionEdge("kb_retrieval", "relevance_scoring"),
        ExecutionEdge("relevance_scoring", "document_filtering"),
        ExecutionEdge("document_filtering", "answer_synthesis"),
        ExecutionEdge("answer_synthesis", "confidence_evaluation"),
        ExecutionEdge("confidence_evaluation", "citation_formatting")
    ]
)

KNOWLEDGE_BASE_TEMPLATE = AgentTemplate(
    template_id=TemplateType.KNOWLEDGE_BASE.value,
    name="知识库问答专家",
    role=AgentRole.SPECIALIST,
    description="基于组织知识库的专业问答助手，提供准确可信的信息",
    use_cases=["技术支持", "产品咨询", "政策解读", "文档查询"],
    estimated_cost="中",
    execution_graph=KNOWLEDGE_BASE_EXECUTION_GRAPH,
    default_tools=["knowledge_search", "document_analyzer", "citation_generator", "fact_checker"],
    model_config={
        "preferred_models": ["gpt-4", "claude-3-opus"],
        "temperature": 0.3,
        "max_tokens": 2000,
        "response_format": "structured"
    },
    capabilities=[
        "知识检索",
        "文档分析",
        "引用生成",
        "可信度评估",
        "多源信息整合"
    ],
    instructions=[
        "你是一个基于知识库的专业问答助手",
        "始终基于检索到的文档内容回答问题",
        "为所有信息提供准确的引用来源",
        "当信息不确定或不完整时，明确说明",
        "优先使用最新、最权威的文档内容"
    ]
)


# ==================== 深度思考模版 ====================

DEEP_THINKING_EXECUTION_GRAPH = ExecutionGraph(
    nodes=[
        ExecutionNode(
            id="task_decomposition",
            type="decomposer",
            config={
                "max_subtasks": 10,
                "decomposition_strategy": "hierarchical"
            }
        ),
        ExecutionNode(
            id="complexity_assessment",
            type="assessor",
            config={
                "complexity_metrics": ["scope", "uncertainty", "dependencies"],
                "threshold": 0.8
            }
        ),
        ExecutionNode(
            id="planning",
            type="planner",
            config={
                "strategy": "priority_based",
                "resource_allocation": True
            }
        ),
        ExecutionNode(
            id="parallel_execution",
            type="executor",
            config={
                "max_parallel": 3,
                "load_balancing": True
            }
        ),
        ExecutionNode(
            id="result_synthesis",
            type="synthesizer",
            config={
                "method": "weighted_combination",
                "conflict_resolution": True
            }
        ),
        ExecutionNode(
            id="quality_check",
            type="validator",
            config={
                "validation_criteria": ["completeness", "consistency", "accuracy"]
            }
        ),
        ExecutionNode(
            id="team_coordination",
            type="coordinator",
            config={
                "team_size": 3,
                "collaboration_mode": "consensus"
            }
        ),
        ExecutionNode(
            id="final_reporting",
            type="reporter",
            config={
                "report_format": "comprehensive",
                "include_methodology": True
            }
        )
    ],
    edges=[
        ExecutionEdge("task_decomposition", "complexity_assessment"),
        ExecutionEdge("complexity_assessment", "planning"),
        ExecutionEdge("planning", "parallel_execution"),
        ExecutionEdge("parallel_execution", "result_synthesis"),
        ExecutionEdge("result_synthesis", "quality_check"),
        ExecutionEdge("quality_check", "team_coordination", condition="complexity > 0.8"),
        ExecutionEdge("quality_check", "final_reporting", condition="complexity <= 0.8"),
        ExecutionEdge("team_coordination", "final_reporting")
    ]
)

DEEP_THINKING_TEMPLATE = AgentTemplate(
    template_id=TemplateType.DEEP_THINKING.value,
    name="深度思考分析师",
    role=AgentRole.ANALYST,
    description="专业的复杂问题分析师，支持多步推理和团队协作",
    use_cases=["战略分析", "研究报告", "决策支持", "复杂问题解决"],
    estimated_cost="高",
    execution_graph=DEEP_THINKING_EXECUTION_GRAPH,
    default_tools=["reasoning", "research", "data_analysis", "collaboration", "planning"],
    model_config={
        "preferred_models": ["gpt-4", "claude-3-opus"],
        "temperature": 0.5,
        "max_tokens": 4000,
        "response_format": "structured"
    },
    capabilities=[
        "任务分解",
        "多步推理",
        "团队协作",
        "决策支持",
        "系统性分析"
    ],
    instructions=[
        "你是一个专业的深度分析师",
        "对复杂问题进行系统性分解和分析",
        "运用多种推理方法和工具",
        "在必要时协调团队共同解决问题",
        "提供详细的分析过程和结论"
    ]
)


# ==================== 模版注册表 ====================

AVAILABLE_TEMPLATES: Dict[str, AgentTemplate] = {
    TemplateType.BASIC_CONVERSATION.value: BASIC_CONVERSATION_TEMPLATE,
    TemplateType.KNOWLEDGE_BASE.value: KNOWLEDGE_BASE_TEMPLATE,
    TemplateType.DEEP_THINKING.value: DEEP_THINKING_TEMPLATE
}


def get_template(template_id: str) -> AgentTemplate:
    """获取指定的模版"""
    if template_id not in AVAILABLE_TEMPLATES:
        raise ValueError(f"Unknown template: {template_id}")
    return AVAILABLE_TEMPLATES[template_id]


def list_available_templates() -> List[AgentTemplate]:
    """列出所有可用的模版"""
    return list(AVAILABLE_TEMPLATES.values())


def get_template_by_use_case(use_case: str) -> List[AgentTemplate]:
    """根据使用场景推荐模版"""
    matching_templates = []
    for template in AVAILABLE_TEMPLATES.values():
        if any(use_case.lower() in uc.lower() for uc in template.use_cases):
            matching_templates.append(template)
    return matching_templates