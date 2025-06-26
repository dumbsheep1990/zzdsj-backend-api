"""
Agno智能体模版管理器
负责模版的管理、配置解析和Agent创建
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from app.frameworks.agno.templates import (
    AgentTemplate, 
    TemplateType,
    AVAILABLE_TEMPLATES,
    get_template,
    list_available_templates
)
from app.frameworks.agno.config import get_user_agno_config, get_system_agno_config
from app.frameworks.agno.dynamic_agent_factory import get_agent_factory, create_dynamic_agent
from app.frameworks.agno.agent import DynamicAgnoKnowledgeAgent

logger = logging.getLogger(__name__)


class AgnoTemplateManager:
    """智能体模版管理器"""
    
    def __init__(self):
        """初始化模版管理器"""
        self.templates = AVAILABLE_TEMPLATES
        self.agent_factory = get_agent_factory()
        self._template_cache = {}
    
    def get_available_templates(self) -> List[Dict[str, Any]]:
        """获取所有可用模版的信息"""
        template_info = []
        for template in list_available_templates():
            template_info.append({
                "template_id": template.template_id,
                "name": template.name,
                "description": template.description,
                "role": template.role.value,
                "use_cases": template.use_cases,
                "estimated_cost": template.estimated_cost,
                "capabilities": template.capabilities,
                "default_tools": template.default_tools
            })
        return template_info
    
    def get_template_details(self, template_id: str) -> Dict[str, Any]:
        """获取指定模版的详细信息"""
        try:
            template = get_template(template_id)
            return {
                "template_id": template.template_id,
                "name": template.name,
                "description": template.description,
                "role": template.role.value,
                "use_cases": template.use_cases,
                "estimated_cost": template.estimated_cost,
                "capabilities": template.capabilities,
                "default_tools": template.default_tools,
                "model_config": template.model_config,
                "instructions": template.instructions,
                "execution_graph": {
                    "nodes": [
                        {
                            "id": node.id,
                            "type": node.type,
                            "config": node.config
                        } for node in template.execution_graph.nodes
                    ],
                    "edges": [
                        {
                            "from": edge.from_node,
                            "to": edge.to_node,
                            "condition": edge.condition,
                            "weight": edge.weight,
                            "timeout": edge.timeout
                        } for edge in template.execution_graph.edges
                    ]
                }
            }
        except ValueError as e:
            logger.error(f"获取模版详情失败: {str(e)}")
            return None
    
    def recommend_templates(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """根据需求推荐模版"""
        recommendations = []
        
        # 获取用户需求
        use_case = requirements.get("use_case", "").lower()
        complexity = requirements.get("complexity", "medium").lower()
        budget = requirements.get("budget", "medium").lower()
        
        for template in list_available_templates():
            score = 0
            reasons = []
            
            # 基于使用场景匹配
            if use_case:
                for uc in template.use_cases:
                    if use_case in uc.lower():
                        score += 3
                        reasons.append(f"匹配使用场景: {uc}")
                        break
            
            # 基于复杂度匹配
            if complexity == "low" and template.template_id == TemplateType.BASIC_CONVERSATION.value:
                score += 2
                reasons.append("适合低复杂度需求")
            elif complexity == "medium" and template.template_id == TemplateType.KNOWLEDGE_BASE.value:
                score += 2
                reasons.append("适合中等复杂度需求")
            elif complexity == "high" and template.template_id == TemplateType.DEEP_THINKING.value:
                score += 2
                reasons.append("适合高复杂度需求")
            
            # 基于预算匹配
            cost_map = {"低": 1, "中": 2, "高": 3}
            budget_map = {"low": 1, "medium": 2, "high": 3}
            
            template_cost = cost_map.get(template.estimated_cost, 2)
            user_budget = budget_map.get(budget, 2)
            
            if template_cost <= user_budget:
                score += 1
                reasons.append("符合预算要求")
            
            if score > 0:
                recommendations.append({
                    "template": {
                        "template_id": template.template_id,
                        "name": template.name,
                        "description": template.description,
                        "estimated_cost": template.estimated_cost
                    },
                    "score": score,
                    "reasons": reasons
                })
        
        # 按分数排序
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations
    
    async def create_agent_from_template(
        self,
        template_id: str,
        frontend_config: Dict[str, Any],
        user_id: str,
        session_id: Optional[str] = None
    ) -> DynamicAgnoKnowledgeAgent:
        """根据模版和前端配置创建Agent"""
        
        try:
            # 1. 获取模版配置
            template = get_template(template_id)
            logger.info(f"使用模版创建Agent: {template.name}")
            
            # 2. 解析前端配置为Agent配置
            agent_config = await self._build_agent_config_from_template(
                template, frontend_config, user_id
            )
            
            # 3. 创建Agent实例
            agent = await create_dynamic_agent(
                agent_config=agent_config,
                user_id=user_id,
                session_id=session_id
            )
            
            if agent:
                logger.info(f"成功创建模版化Agent: {agent_config['name']}")
                return agent
            else:
                logger.error("Agent创建失败")
                return None
                
        except Exception as e:
            logger.error(f"从模版创建Agent失败: {str(e)}", exc_info=True)
            return None
    
    async def _build_agent_config_from_template(
        self,
        template: AgentTemplate,
        frontend_config: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """基于模版和前端配置构建Agent配置"""
        
        # 获取用户或系统配置
        if user_id:
            agno_config = await get_user_agno_config(user_id)
        else:
            agno_config = await get_system_agno_config()
        
        # 解析前端配置
        basic_config = frontend_config.get("basic_configuration", {})
        model_config = frontend_config.get("model_configuration", {})
        capability_config = frontend_config.get("capability_configuration", {})
        advanced_config = frontend_config.get("advanced_configuration", {})
        
        # 构建Agent配置
        agent_config = {
            # 基础信息
            "name": basic_config.get("agent_name", template.name),
            "role": template.role.value,
            "description": basic_config.get("agent_description", template.description),
            
            # 模型配置
            "model_config": {
                "model_id": model_config.get("model_name", template.model_config["preferred_models"][0]),
                "type": "chat",
                "temperature": model_config.get("temperature", template.model_config["temperature"]),
                "max_tokens": model_config.get("max_tokens", template.model_config["max_tokens"])
            },
            
            # 工具配置 - 合并模版默认工具和用户选择
            "tools": self._merge_tools(
                template.default_tools,
                capability_config.get("enabled_tools", []),
                agno_config.tools.enabled_tools
            ),
            
            # 知识库配置
            "knowledge_bases": capability_config.get("knowledge_bases", []),
            
            # 指令配置 - 合并模版指令和用户自定义指令
            "instructions": self._merge_instructions(
                template.instructions,
                capability_config.get("custom_instructions", []),
                basic_config.get("personality", "professional")
            ),
            
            # 执行图配置
            "execution_graph": self._convert_execution_graph(template.execution_graph),
            
            # 高级配置
            "max_loops": advanced_config.get("max_iterations", 10),
            "show_tool_calls": advanced_config.get("show_tool_calls", True),
            "markdown": True,
            "add_history_to_messages": True,
            
            # 模版元信息
            "template_id": template.template_id,
            "template_name": template.name,
            "capabilities": template.capabilities
        }
        
        return agent_config
    
    def _merge_tools(
        self, 
        template_tools: List[str], 
        user_tools: List[str], 
        system_tools: List[str]
    ) -> List[Dict[str, Any]]:
        """合并模版工具、用户选择和系统可用工具"""
        # 优先使用用户选择的工具，回退到模版默认工具
        selected_tools = user_tools if user_tools else template_tools
        
        # 过滤出系统中实际可用的工具
        available_tools = []
        for tool_id in selected_tools:
            if tool_id in system_tools:
                available_tools.append({
                    "tool_id": tool_id,
                    "params": {}
                })
        
        logger.info(f"为Agent配置工具: {[t['tool_id'] for t in available_tools]}")
        return available_tools
    
    def _merge_instructions(
        self,
        template_instructions: List[str],
        custom_instructions: List[str],
        personality: str
    ) -> List[str]:
        """合并模版指令和用户自定义指令"""
        instructions = template_instructions.copy()
        
        # 根据个性化设置调整指令
        personality_instructions = {
            "professional": "保持专业、正式的沟通风格",
            "friendly": "保持友好、亲切的沟通风格", 
            "creative": "发挥创意思维，提供创新性的回答"
        }
        
        if personality in personality_instructions:
            instructions.append(personality_instructions[personality])
        
        # 添加用户自定义指令
        instructions.extend(custom_instructions)
        
        return instructions
    
    def _convert_execution_graph(self, execution_graph) -> Dict[str, Any]:
        """将模版执行图转换为Agent配置格式"""
        return {
            "nodes": [
                {
                    "id": node.id,
                    "type": node.type,
                    "config": node.config
                } for node in execution_graph.nodes
            ],
            "edges": [
                {
                    "from": edge.from_node,
                    "to": edge.to_node,
                    "condition": edge.condition,
                    "weight": edge.weight,
                    "timeout": edge.timeout
                } for edge in execution_graph.edges
            ]
        }
    
    async def validate_template_config(
        self,
        template_id: str,
        frontend_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证模版配置"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            # 1. 验证模版存在
            template = get_template(template_id)
            
            # 2. 验证必需配置
            required_sections = ["basic_configuration", "model_configuration"]
            for section in required_sections:
                if section not in frontend_config:
                    validation_result["errors"].append(f"缺少必需配置部分: {section}")
            
            # 3. 验证基础配置
            basic_config = frontend_config.get("basic_configuration", {})
            if not basic_config.get("agent_name"):
                validation_result["errors"].append("Agent名称不能为空")
            
            # 4. 验证模型配置
            model_config = frontend_config.get("model_configuration", {})
            if not model_config.get("model_name"):
                validation_result["warnings"].append("未指定模型，将使用模版默认模型")
            
            # 5. 验证工具配置
            capability_config = frontend_config.get("capability_configuration", {})
            tools = capability_config.get("enabled_tools", [])
            if not tools:
                validation_result["warnings"].append("未选择工具，将使用模版默认工具")
            
            if validation_result["errors"]:
                validation_result["valid"] = False
                
        except ValueError as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"无效的模版ID: {template_id}")
        
        return validation_result
    
    def get_template_usage_stats(self) -> Dict[str, Any]:
        """获取模版使用统计"""
        # 这里可以集成实际的使用统计数据
        return {
            "total_templates": len(self.templates),
            "most_popular": TemplateType.BASIC_CONVERSATION.value,
            "usage_by_template": {
                TemplateType.BASIC_CONVERSATION.value: 45,
                TemplateType.KNOWLEDGE_BASE.value: 35,
                TemplateType.DEEP_THINKING.value: 20
            },
            "last_updated": datetime.now().isoformat()
        }


# 全局模版管理器实例
_global_template_manager: Optional[AgnoTemplateManager] = None

def get_template_manager() -> AgnoTemplateManager:
    """获取全局模版管理器实例"""
    global _global_template_manager
    if _global_template_manager is None:
        _global_template_manager = AgnoTemplateManager()
    return _global_template_manager


# 便利函数
async def create_agent_from_template(
    template_id: str,
    frontend_config: Dict[str, Any],
    user_id: str,
    session_id: Optional[str] = None
) -> DynamicAgnoKnowledgeAgent:
    """便利函数：从模版创建Agent"""
    manager = get_template_manager()
    return await manager.create_agent_from_template(
        template_id, frontend_config, user_id, session_id
    )


def get_available_templates() -> List[Dict[str, Any]]:
    """便利函数：获取可用模版列表"""
    manager = get_template_manager()
    return manager.get_available_templates()


def recommend_templates(requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
    """便利函数：推荐模版"""
    manager = get_template_manager()
    return manager.recommend_templates(requirements)