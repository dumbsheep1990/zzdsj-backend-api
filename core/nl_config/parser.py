from typing import Dict, Any, List, Optional
import json
import logging
from app.frameworks.llamaindex.chat import LlamaIndexChatServiceConfig
from core.model_manager import ModelManager
from app.frameworks.integration.factory import get_llm_service
from app.repositories.tool_repository import ToolRepository

logger = logging.getLogger(__name__)

class NLConfigParser:
    """自然语言配置解析器，将自然语言描述转换为结构化智能体配置"""
    
    def __init__(self):
        self.model_manager = ModelManager()
        self.tool_repo = ToolRepository()
        self._llm = None
        
    async def initialize(self):
        """初始化解析器"""
        if self._llm is None:
            # 获取LLM服务
            config = LlamaIndexChatServiceConfig()
            self._llm = await get_llm_service(config)
            
    async def parse_description(self, description: str) -> Dict[str, Any]:
        """将自然语言描述解析为智能体配置
        
        Args:
            description: 自然语言描述
            
        Returns:
            Dict[str, Any]: 智能体配置
        """
        await self.initialize()
        
        # 构建提示词
        prompt = self._build_parsing_prompt(description)
        
        # 调用LLM进行解析
        response = await self._llm.chat_completion(
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4",
            temperature=0.2
        )
        
        # 提取并解析JSON
        try:
            content = response.get("message", {}).get("content", "")
            # 提取JSON部分
            json_str = self._extract_json(content)
            config = json.loads(json_str)
            
            # 验证和修复配置
            config = await self._validate_and_fix_config(config)
            
            return config
        except Exception as e:
            logger.error(f"解析配置失败: {str(e)}", exc_info=True)
            return {
                "error": f"无法解析配置: {str(e)}",
                "raw_response": response.get("message", {}).get("content", "")
            }
    
    async def suggest_improvements(self, current_config: Dict[str, Any]) -> Dict[str, Any]:
        """基于部分配置提供优化建议
        
        Args:
            current_config: 当前配置
            
        Returns:
            Dict[str, Any]: 改进建议
        """
        await self.initialize()
        
        # 构建提示词
        prompt = self._build_suggestion_prompt(current_config)
        
        # 调用LLM获取建议
        response = await self._llm.chat_completion(
            messages=[
                {"role": "system", "content": self._get_suggestion_prompt()},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4",
            temperature=0.3
        )
        
        # 提取并解析建议
        try:
            content = response.get("message", {}).get("content", "")
            # 提取JSON部分
            json_str = self._extract_json(content)
            suggestions = json.loads(json_str)
            
            return suggestions
        except Exception as e:
            logger.error(f"生成建议失败: {str(e)}", exc_info=True)
            return {
                "error": f"无法生成建议: {str(e)}",
                "raw_response": response.get("message", {}).get("content", "")
            }
    
    def _build_parsing_prompt(self, description: str) -> str:
        """构建解析提示词
        
        Args:
            description: 自然语言描述
            
        Returns:
            str: 提示词
        """
        return f"""
请分析以下智能体需求描述，并创建一个结构化的智能体配置JSON：

用户需求：
{description}

请将此需求转换为包含以下元素的JSON配置：
1. 基础智能体类型（base_agent_type）- 选择最适合的类型：PlannerAgent、ExecutorAgent、DebateAgent等
2. 系统提示词（system_prompt）- 为智能体提供明确的指导
3. 配置参数（configuration）- 智能体特定的配置参数
4. 推荐工具（recommended_tools）- 列出智能体需要的工具
5. 工作流建议（workflow_suggestion）- 如果需要，提供工作流建议

请以JSON格式返回配置。
"""
    
    def _build_suggestion_prompt(self, current_config: Dict[str, Any]) -> str:
        """构建建议提示词
        
        Args:
            current_config: 当前配置
            
        Returns:
            str: 提示词
        """
        config_str = json.dumps(current_config, ensure_ascii=False, indent=2)
        
        return f"""
请分析以下智能体配置，并提供改进建议：

当前配置：
{config_str}

请提供以下方面的改进建议：
1. 系统提示词优化 - 如何改进提示词使其更有效
2. 工具建议 - 是否需要添加或删除工具
3. 工作流优化 - 如何改进工具调用顺序和条件
4. 参数优化 - 如何调整配置参数以提高性能

请以JSON格式返回建议。
"""
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词
        
        Returns:
            str: 系统提示词
        """
        return """
你是一个专业的智能体配置解析专家。你的任务是将用户的自然语言需求转换为结构化的智能体配置。
请仔细分析用户需求，并提取关键信息以创建合适的配置。
你的输出必须是有效的JSON格式，且包含所有必要的字段。
请注意以下几点：
1. 基础智能体类型要根据任务特点选择最合适的
2. 系统提示词要简洁明了，且能有效指导智能体行为
3. 工具选择要精准，避免不必要的工具
4. 工作流要考虑工具间的逻辑依赖关系

请确保输出格式为JSON，不要添加任何其他解释或评论。
"""
    
    def _get_suggestion_prompt(self) -> str:
        """获取建议系统提示词
        
        Returns:
            str: 系统提示词
        """
        return """
你是一个专业的智能体配置优化专家。你的任务是分析现有智能体配置，并提供改进建议。
请仔细评估配置的各个方面，包括系统提示词、工具选择、工作流配置和参数设置。
你的输出必须是有效的JSON格式，包含具体的改进建议。
请确保你的建议：
1. 具体且可操作
2. 有明确的改进理由
3. 保持与原始配置的兼容性
4. 遵循最佳实践

请确保输出格式为JSON，不要添加任何其他解释或评论。
"""
    
    def _extract_json(self, text: str) -> str:
        """从文本中提取JSON字符串
        
        Args:
            text: 包含JSON的文本
            
        Returns:
            str: JSON字符串
        """
        # 寻找JSON开始和结束标记
        start_markers = ["{", "["]
        end_markers = ["}", "]"]
        
        # 首先尝试寻找代码块标记
        start = text.find("```json")
        if start != -1:
            start = text.find("{", start)
            end = text.rfind("}")
            if start != -1 and end != -1:
                return text[start:end+1]
        
        # 尝试直接寻找JSON
        start = min([text.find(m) for m in start_markers if text.find(m) != -1], default=-1)
        end = max([text.rfind(m) for m in end_markers if text.rfind(m) != -1], default=-1)
        
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        
        raise ValueError("无法在文本中找到有效的JSON")
    
    async def _validate_and_fix_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证和修复配置
        
        Args:
            config: 原始配置
            
        Returns:
            Dict[str, Any]: 修复后的配置
        """
        # 确保基础字段存在
        if "base_agent_type" not in config:
            config["base_agent_type"] = "ExecutorAgent"
            
        if "system_prompt" not in config:
            config["system_prompt"] = "你是一个通用智能助手，帮助用户完成各种任务。"
            
        if "configuration" not in config:
            config["configuration"] = {}
            
        # 验证工具
        if "recommended_tools" in config:
            validated_tools = []
            for tool in config["recommended_tools"]:
                # 如果只是字符串名称，转换为字典
                if isinstance(tool, str):
                    tool = {"name": tool}
                    
                # 确保至少有name字段
                if "name" not in tool:
                    continue
                    
                # 添加到验证过的工具列表
                validated_tools.append(tool)
                
            config["recommended_tools"] = validated_tools
            
        return config
