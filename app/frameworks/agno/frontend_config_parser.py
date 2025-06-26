"""
Agno前端配置解析器
解析5步前端配置为Agent配置，支持配置验证和默认值填充
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from app.frameworks.agno.templates import get_template, TemplateType
from app.frameworks.agno.orchestration.types import AgentConfig, AgentRole

logger = logging.getLogger(__name__)


class PersonalityType(Enum):
    """个性类型"""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CREATIVE = "creative"


class ResponseLength(Enum):
    """回复长度"""
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class CostTier(Enum):
    """成本等级"""
    ECONOMY = "economy"
    STANDARD = "standard"
    PREMIUM = "premium"


class PrivacyLevel(Enum):
    """隐私级别"""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"


@dataclass
class TemplateSelection:
    """步骤1: 模版选择配置"""
    template_id: str
    template_name: Optional[str] = None
    description: Optional[str] = None
    use_cases: Optional[List[str]] = None
    estimated_cost: Optional[str] = None


@dataclass
class BasicConfiguration:
    """步骤2: 基础配置"""
    agent_name: str
    agent_description: str
    personality: PersonalityType = PersonalityType.PROFESSIONAL
    language: str = "zh-CN"
    response_length: ResponseLength = ResponseLength.MEDIUM


@dataclass
class ModelConfiguration:
    """步骤3: 模型配置"""
    model_provider: str  # "openai" | "anthropic" | "local"
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 1000
    cost_tier: CostTier = CostTier.STANDARD


@dataclass
class CapabilityConfiguration:
    """步骤4: 能力配置"""
    enabled_tools: List[str]
    knowledge_bases: List[str]
    external_integrations: List[str]
    custom_instructions: List[str]


@dataclass
class AdvancedConfiguration:
    """步骤5: 高级配置"""
    execution_timeout: int = 300
    max_iterations: int = 10
    enable_team_mode: bool = False
    enable_streaming: bool = True
    enable_citations: bool = True
    privacy_level: PrivacyLevel = PrivacyLevel.STANDARD


@dataclass
class FrontendConfig:
    """完整的前端配置"""
    template_selection: TemplateSelection
    basic_configuration: BasicConfiguration
    model_configuration: ModelConfiguration
    capability_configuration: CapabilityConfiguration
    advanced_configuration: AdvancedConfiguration


class AgnoConfigParser:
    """Agno前端配置解析器"""
    
    def __init__(self):
        self.response_length_tokens = {
            ResponseLength.SHORT: 300,
            ResponseLength.MEDIUM: 1000,
            ResponseLength.LONG: 2000
        }
        
        self.personality_instructions = {
            PersonalityType.PROFESSIONAL: [
                "保持专业、正式的沟通风格",
                "使用准确的术语和清晰的表达",
                "专注于提供有价值的信息"
            ],
            PersonalityType.FRIENDLY: [
                "保持友好、亲切的沟通风格",
                "使用轻松自然的语言",
                "展现同理心和关怀"
            ],
            PersonalityType.CREATIVE: [
                "发挥创意思维，提供创新性的回答",
                "使用生动的比喻和例子",
                "鼓励探索不同的解决方案"
            ]
        }
    
    async def parse_frontend_config(self, config_dict: Dict[str, Any]) -> AgentConfig:
        """解析前端配置字典为Agent配置"""
        
        try:
            # 解析各个配置部分
            frontend_config = self._parse_config_dict(config_dict)
            
            # 获取模版信息
            template = get_template(frontend_config.template_selection.template_id)
            
            # 构建Agent配置
            agent_config = AgentConfig(
                name=frontend_config.basic_configuration.agent_name,
                role=template.role,
                description=frontend_config.basic_configuration.agent_description,
                instructions=self._build_instructions(frontend_config, template),
                model_config=self._build_model_config(frontend_config, template),
                tools=frontend_config.capability_configuration.enabled_tools,
                knowledge_bases=frontend_config.capability_configuration.knowledge_bases,
                max_loops=frontend_config.advanced_configuration.max_iterations,
                timeout=frontend_config.advanced_configuration.execution_timeout,
                show_tool_calls=True,
                markdown=True,
                custom_params={
                    "template_id": template.template_id,
                    "template_name": template.name,
                    "personality": frontend_config.basic_configuration.personality.value,
                    "language": frontend_config.basic_configuration.language,
                    "response_length": frontend_config.basic_configuration.response_length.value,
                    "enable_team_mode": frontend_config.advanced_configuration.enable_team_mode,
                    "enable_streaming": frontend_config.advanced_configuration.enable_streaming,
                    "enable_citations": frontend_config.advanced_configuration.enable_citations,
                    "privacy_level": frontend_config.advanced_configuration.privacy_level.value,
                    "execution_graph": self._convert_execution_graph(template.execution_graph),
                    "capabilities": template.capabilities
                }
            )
            
            logger.info(f"成功解析前端配置: {agent_config.name}")
            return agent_config
            
        except Exception as e:
            logger.error(f"解析前端配置失败: {str(e)}", exc_info=True)
            raise ValueError(f"配置解析失败: {str(e)}")
    
    def _parse_config_dict(self, config_dict: Dict[str, Any]) -> FrontendConfig:
        """将配置字典解析为结构化配置对象"""
        
        # 解析模版选择
        template_data = config_dict.get("template_selection", {})
        template_selection = TemplateSelection(
            template_id=template_data.get("template_id"),
            template_name=template_data.get("template_name"),
            description=template_data.get("description"),
            use_cases=template_data.get("use_cases"),
            estimated_cost=template_data.get("estimated_cost")
        )
        
        # 解析基础配置
        basic_data = config_dict.get("basic_configuration", {})
        basic_configuration = BasicConfiguration(
            agent_name=basic_data.get("agent_name", "AI助手"),
            agent_description=basic_data.get("agent_description", "智能助手"),
            personality=PersonalityType(basic_data.get("personality", "professional")),
            language=basic_data.get("language", "zh-CN"),
            response_length=ResponseLength(basic_data.get("response_length", "medium"))
        )
        
        # 解析模型配置
        model_data = config_dict.get("model_configuration", {})
        model_configuration = ModelConfiguration(
            model_provider=model_data.get("model_provider", "openai"),
            model_name=model_data.get("model_name", "gpt-4o-mini"),
            temperature=float(model_data.get("temperature", 0.7)),
            max_tokens=int(model_data.get("max_tokens", 1000)),
            cost_tier=CostTier(model_data.get("cost_tier", "standard"))
        )
        
        # 解析能力配置
        capability_data = config_dict.get("capability_configuration", {})
        capability_configuration = CapabilityConfiguration(
            enabled_tools=capability_data.get("enabled_tools", []),
            knowledge_bases=capability_data.get("knowledge_bases", []),
            external_integrations=capability_data.get("external_integrations", []),
            custom_instructions=capability_data.get("custom_instructions", [])
        )
        
        # 解析高级配置
        advanced_data = config_dict.get("advanced_configuration", {})
        advanced_configuration = AdvancedConfiguration(
            execution_timeout=int(advanced_data.get("execution_timeout", 300)),
            max_iterations=int(advanced_data.get("max_iterations", 10)),
            enable_team_mode=bool(advanced_data.get("enable_team_mode", False)),
            enable_streaming=bool(advanced_data.get("enable_streaming", True)),
            enable_citations=bool(advanced_data.get("enable_citations", True)),
            privacy_level=PrivacyLevel(advanced_data.get("privacy_level", "standard"))
        )
        
        return FrontendConfig(
            template_selection=template_selection,
            basic_configuration=basic_configuration,
            model_configuration=model_configuration,
            capability_configuration=capability_configuration,
            advanced_configuration=advanced_configuration
        )
    
    def _build_instructions(self, config: FrontendConfig, template) -> List[str]:
        """构建指令列表"""
        instructions = template.instructions.copy()
        
        # 添加个性化指令
        personality_instructions = self.personality_instructions.get(
            config.basic_configuration.personality, []
        )
        instructions.extend(personality_instructions)
        
        # 添加语言指令
        if config.basic_configuration.language != "zh-CN":
            instructions.append(f"请用{config.basic_configuration.language}回复")
        
        # 添加回复长度指令
        length_instructions = {
            ResponseLength.SHORT: "请保持回复简洁明了",
            ResponseLength.MEDIUM: "请提供适中长度的详细回复",
            ResponseLength.LONG: "请提供详细全面的回复"
        }
        instructions.append(length_instructions[config.basic_configuration.response_length])
        
        # 添加引用指令
        if config.advanced_configuration.enable_citations:
            instructions.append("在使用外部信息时提供准确的引用来源")
        
        # 添加隐私指令
        privacy_instructions = {
            PrivacyLevel.BASIC: "注意保护基本隐私信息",
            PrivacyLevel.STANDARD: "严格保护用户隐私和敏感信息",
            PrivacyLevel.STRICT: "采用最高级别的隐私保护措施"
        }
        instructions.append(privacy_instructions[config.advanced_configuration.privacy_level])
        
        # 添加用户自定义指令
        instructions.extend(config.capability_configuration.custom_instructions)
        
        return instructions
    
    def _build_model_config(self, config: FrontendConfig, template) -> Dict[str, Any]:
        """构建模型配置"""
        # 根据回复长度调整最大token数
        max_tokens = self.response_length_tokens[config.basic_configuration.response_length]
        
        # 如果用户指定了token数，使用用户指定的值
        if config.model_configuration.max_tokens != 1000:  # 1000是默认值
            max_tokens = config.model_configuration.max_tokens
        
        return {
            "model_id": config.model_configuration.model_name,
            "type": "chat",
            "temperature": config.model_configuration.temperature,
            "max_tokens": max_tokens,
            "provider": config.model_configuration.model_provider,
            "cost_tier": config.model_configuration.cost_tier.value
        }
    
    def _convert_execution_graph(self, execution_graph) -> Dict[str, Any]:
        """转换执行图格式"""
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
    
    async def validate_config(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """验证前端配置"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            # 验证必需字段
            required_sections = [
                "template_selection",
                "basic_configuration", 
                "model_configuration"
            ]
            
            for section in required_sections:
                if section not in config_dict:
                    validation_result["errors"].append(f"缺少必需配置部分: {section}")
            
            # 验证模版选择
            template_data = config_dict.get("template_selection", {})
            template_id = template_data.get("template_id")
            if not template_id:
                validation_result["errors"].append("必须选择智能体模版")
            else:
                try:
                    get_template(template_id)
                except ValueError:
                    validation_result["errors"].append(f"无效的模版ID: {template_id}")
            
            # 验证基础配置
            basic_data = config_dict.get("basic_configuration", {})
            if not basic_data.get("agent_name"):
                validation_result["errors"].append("Agent名称不能为空")
            
            # 验证模型配置
            model_data = config_dict.get("model_configuration", {})
            if not model_data.get("model_name"):
                validation_result["errors"].append("必须选择模型")
            
            temperature = model_data.get("temperature")
            if temperature is not None:
                try:
                    temp_val = float(temperature)
                    if not 0 <= temp_val <= 2:
                        validation_result["warnings"].append("Temperature应在0-2之间")
                except ValueError:
                    validation_result["errors"].append("Temperature必须是数值")
            
            max_tokens = model_data.get("max_tokens")
            if max_tokens is not None:
                try:
                    token_val = int(max_tokens)
                    if token_val <= 0:
                        validation_result["errors"].append("Max tokens必须大于0")
                    elif token_val > 8192:
                        validation_result["warnings"].append("Max tokens设置较高，可能影响性能")
                except ValueError:
                    validation_result["errors"].append("Max tokens必须是整数")
            
            # 验证能力配置
            capability_data = config_dict.get("capability_configuration", {})
            tools = capability_data.get("enabled_tools", [])
            if not tools:
                validation_result["warnings"].append("未选择任何工具，将使用模版默认工具")
            
            # 验证高级配置
            advanced_data = config_dict.get("advanced_configuration", {})
            timeout = advanced_data.get("execution_timeout")
            if timeout is not None:
                try:
                    timeout_val = int(timeout)
                    if timeout_val <= 0:
                        validation_result["errors"].append("执行超时时间必须大于0")
                    elif timeout_val > 1800:  # 30分钟
                        validation_result["warnings"].append("执行超时时间设置较长")
                except ValueError:
                    validation_result["errors"].append("执行超时时间必须是整数")
            
            if validation_result["errors"]:
                validation_result["valid"] = False
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"配置验证失败: {str(e)}")
        
        return validation_result
    
    async def merge_configs(self, base_config: AgentConfig, override_config: Dict[str, Any]) -> AgentConfig:
        """合并配置"""
        # 创建新的配置对象
        merged_config = AgentConfig(
            name=override_config.get("name", base_config.name),
            role=AgentRole(override_config.get("role", base_config.role.value)),
            description=override_config.get("description", base_config.description),
            instructions=override_config.get("instructions", base_config.instructions),
            model_config={**base_config.model_config, **override_config.get("model_config", {})},
            tools=override_config.get("tools", base_config.tools),
            knowledge_bases=override_config.get("knowledge_bases", base_config.knowledge_bases),
            memory_config={**base_config.memory_config, **override_config.get("memory_config", {})},
            max_loops=override_config.get("max_loops", base_config.max_loops),
            timeout=override_config.get("timeout", base_config.timeout),
            show_tool_calls=override_config.get("show_tool_calls", base_config.show_tool_calls),
            markdown=override_config.get("markdown", base_config.markdown),
            custom_params={**base_config.custom_params, **override_config.get("custom_params", {})}
        )
        
        return merged_config
    
    def get_default_config_for_template(self, template_id: str) -> Dict[str, Any]:
        """获取指定模版的默认配置"""
        try:
            template = get_template(template_id)
            
            return {
                "template_selection": {
                    "template_id": template.template_id,
                    "template_name": template.name,
                    "description": template.description,
                    "use_cases": template.use_cases,
                    "estimated_cost": template.estimated_cost
                },
                "basic_configuration": {
                    "agent_name": template.name,
                    "agent_description": template.description,
                    "personality": "professional",
                    "language": "zh-CN",
                    "response_length": "medium"
                },
                "model_configuration": {
                    "model_provider": "openai",
                    "model_name": template.model_config["preferred_models"][0],
                    "temperature": template.model_config["temperature"],
                    "max_tokens": template.model_config["max_tokens"],
                    "cost_tier": "standard"
                },
                "capability_configuration": {
                    "enabled_tools": template.default_tools,
                    "knowledge_bases": [],
                    "external_integrations": [],
                    "custom_instructions": []
                },
                "advanced_configuration": {
                    "execution_timeout": 300,
                    "max_iterations": 10,
                    "enable_team_mode": False,
                    "enable_streaming": True,
                    "enable_citations": True,
                    "privacy_level": "standard"
                }
            }
            
        except ValueError as e:
            logger.error(f"获取模版默认配置失败: {str(e)}")
            return None


# 全局配置解析器实例
_global_config_parser: Optional[AgnoConfigParser] = None

def get_config_parser() -> AgnoConfigParser:
    """获取全局配置解析器实例"""
    global _global_config_parser
    if _global_config_parser is None:
        _global_config_parser = AgnoConfigParser()
    return _global_config_parser


# 便利函数
async def parse_frontend_config(config_dict: Dict[str, Any]) -> AgentConfig:
    """便利函数：解析前端配置"""
    parser = get_config_parser()
    return await parser.parse_frontend_config(config_dict)


async def validate_frontend_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """便利函数：验证前端配置"""
    parser = get_config_parser()
    return await parser.validate_config(config_dict)