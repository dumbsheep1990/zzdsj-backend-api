"""
Agno前端参数解析器
解析和标准化前端传递的任意配置格式，支持配置验证和合并
"""

import logging
from typing import Any, Dict, List, Optional, Union
import json
import re
from datetime import datetime

from .types import (
    IConfigParser, AgentConfig, AgentRole, ToolCategory,
    DEFAULT_AGENT_MAX_LOOPS, DEFAULT_EXECUTION_TIMEOUT
)

logger = logging.getLogger(__name__)

class AgnoConfigParser(IConfigParser):
    """Agno配置解析器
    
    解析前端配置，支持多种格式和智能转换
    """
    
    def __init__(self):
        """初始化解析器"""
        self._default_config = {
            'name': 'AI Assistant',
            'role': 'assistant',
            'description': '智能助手',
            'instructions': [],
            'model_config': {'type': 'chat'},
            'tools': [],
            'knowledge_bases': [],
            'memory_config': {},
            'max_loops': DEFAULT_AGENT_MAX_LOOPS,
            'timeout': DEFAULT_EXECUTION_TIMEOUT,
            'show_tool_calls': True,
            'markdown': True,
            'custom_params': {}
        }
    
    async def parse_frontend_config(self, config: Dict[str, Any]) -> AgentConfig:
        """解析前端配置"""
        try:
            # 处理不同的前端配置格式
            normalized_config = await self._normalize_config(config)
            
            # 解析基础信息
            agent_config = AgentConfig(
                name=normalized_config.get('name', self._default_config['name']),
                role=self._parse_role(normalized_config.get('role', self._default_config['role'])),
                description=normalized_config.get('description', self._default_config['description']),
                instructions=await self._parse_instructions(normalized_config.get('instructions', [])),
                model_config=await self._parse_model_config(normalized_config.get('model_config', {})),
                tools=await self._parse_tools(normalized_config.get('tools', [])),
                knowledge_bases=await self._parse_knowledge_bases(normalized_config.get('knowledge_bases', [])),
                memory_config=await self._parse_memory_config(normalized_config.get('memory_config', {})),
                max_loops=normalized_config.get('max_loops', self._default_config['max_loops']),
                timeout=normalized_config.get('timeout', self._default_config['timeout']),
                show_tool_calls=normalized_config.get('show_tool_calls', self._default_config['show_tool_calls']),
                markdown=normalized_config.get('markdown', self._default_config['markdown']),
                custom_params=normalized_config.get('custom_params', {})
            )
            
            logger.debug(f"成功解析Agent配置: {agent_config.name}")
            return agent_config
            
        except Exception as e:
            logger.error(f"解析前端配置失败: {str(e)}", exc_info=True)
            # 返回默认配置
            return await self._create_default_config()
    
    async def _normalize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """标准化配置格式"""
        normalized = {}
        
        # 处理各种可能的配置键名
        key_mappings = {
            # Agent基础信息
            'name': ['name', 'agent_name', 'agentName', 'title'],
            'role': ['role', 'agent_role', 'agentRole', 'type', 'agent_type'],
            'description': ['description', 'desc', 'summary', 'info'],
            
            # 指令和提示
            'instructions': ['instructions', 'prompts', 'system_prompt', 'guidelines'],
            
            # 模型配置
            'model_config': ['model_config', 'model', 'llm_config', 'ai_model'],
            
            # 工具配置
            'tools': ['tools', 'tool_list', 'available_tools', 'enabled_tools'],
            
            # 知识库配置
            'knowledge_bases': ['knowledge_bases', 'knowledge', 'kb_list', 'databases'],
            
            # 内存配置
            'memory_config': ['memory_config', 'memory', 'context_config'],
            
            # 执行配置
            'max_loops': ['max_loops', 'max_iterations', 'loop_limit'],
            'timeout': ['timeout', 'time_limit', 'max_time'],
            
            # 显示配置
            'show_tool_calls': ['show_tool_calls', 'show_tools', 'debug_tools'],
            'markdown': ['markdown', 'use_markdown', 'format_markdown'],
            
            # 自定义参数
            'custom_params': ['custom_params', 'extra_config', 'advanced_options']
        }
        
        # 应用键名映射
        for standard_key, possible_keys in key_mappings.items():
            for key in possible_keys:
                if key in config:
                    normalized[standard_key] = config[key]
                    break
            
            # 如果没有找到，使用默认值
            if standard_key not in normalized:
                normalized[standard_key] = self._default_config.get(standard_key)
        
        # 处理嵌套配置
        await self._handle_nested_config(config, normalized)
        
        return normalized
    
    async def _handle_nested_config(self, original: Dict[str, Any], normalized: Dict[str, Any]):
        """处理嵌套配置"""
        try:
            # 处理模块化配置（如orchestration系统的配置）
            if 'modules' in original:
                await self._parse_modules_config(original['modules'], normalized)
            
            # 处理工作流配置
            if 'workflow' in original:
                await self._parse_workflow_config(original['workflow'], normalized)
            
            # 处理能力配置
            if 'capabilities' in original:
                await self._parse_capabilities_config(original['capabilities'], normalized)
                
        except Exception as e:
            logger.warning(f"处理嵌套配置失败: {str(e)}")
    
    async def _parse_modules_config(self, modules: List[Dict], normalized: Dict[str, Any]):
        """解析模块配置"""
        try:
            tools_from_modules = []
            instructions_from_modules = []
            
            for module in modules:
                module_type = module.get('type', '').lower()
                
                # 根据模块类型映射到工具
                if module_type == 'information_retrieval':
                    tools_from_modules.extend(['search', 'knowledge'])
                elif module_type == 'content_processing':
                    tools_from_modules.extend(['chunking', 'processing'])
                elif module_type == 'data_analysis_reasoning':
                    tools_from_modules.extend(['reasoning', 'analysis'])
                elif module_type == 'output_generation':
                    tools_from_modules.extend(['formatting', 'generation'])
                
                # 提取模块配置中的指令
                if 'config' in module and 'instructions' in module['config']:
                    instructions_from_modules.extend(module['config']['instructions'])
            
            # 合并到normalized配置
            if tools_from_modules:
                existing_tools = normalized.get('tools', [])
                normalized['tools'] = list(set(existing_tools + tools_from_modules))
            
            if instructions_from_modules:
                existing_instructions = normalized.get('instructions', [])
                normalized['instructions'] = existing_instructions + instructions_from_modules
                
        except Exception as e:
            logger.warning(f"解析模块配置失败: {str(e)}")
    
    async def _parse_workflow_config(self, workflow: Dict[str, Any], normalized: Dict[str, Any]):
        """解析工作流配置"""
        try:
            # 从工作流配置中提取Agent相关信息
            if 'strategy' in workflow:
                strategy = workflow['strategy'].lower()
                if strategy == 'parallel':
                    normalized['custom_params']['execution_strategy'] = 'parallel'
                elif strategy == 'sequential':
                    normalized['custom_params']['execution_strategy'] = 'sequential'
            
            # 从步骤中提取工具需求
            if 'steps' in workflow:
                tools_from_steps = []
                for step in workflow['steps']:
                    if 'tools' in step:
                        tools_from_steps.extend(step['tools'])
                
                if tools_from_steps:
                    existing_tools = normalized.get('tools', [])
                    normalized['tools'] = list(set(existing_tools + tools_from_steps))
                    
        except Exception as e:
            logger.warning(f"解析工作流配置失败: {str(e)}")
    
    async def _parse_capabilities_config(self, capabilities: List[str], normalized: Dict[str, Any]):
        """解析能力配置"""
        try:
            tools_from_capabilities = []
            
            for capability in capabilities:
                capability_lower = capability.lower()
                
                # 能力到工具的映射
                if any(keyword in capability_lower for keyword in ['search', 'find', 'retrieve']):
                    tools_from_capabilities.append('search')
                if any(keyword in capability_lower for keyword in ['reason', 'analyze', 'think']):
                    tools_from_capabilities.append('reasoning')
                if any(keyword in capability_lower for keyword in ['knowledge', 'qa', 'question']):
                    tools_from_capabilities.append('knowledge')
                if any(keyword in capability_lower for keyword in ['process', 'chunk', 'split']):
                    tools_from_capabilities.append('chunking')
            
            if tools_from_capabilities:
                existing_tools = normalized.get('tools', [])
                normalized['tools'] = list(set(existing_tools + tools_from_capabilities))
                
        except Exception as e:
            logger.warning(f"解析能力配置失败: {str(e)}")
    
    def _parse_role(self, role: Union[str, Dict]) -> AgentRole:
        """解析Agent角色"""
        try:
            if isinstance(role, dict):
                role = role.get('type', role.get('name', 'assistant'))
            
            role_str = str(role).lower()
            
            # 角色映射
            role_mapping = {
                'assistant': AgentRole.ASSISTANT,
                'researcher': AgentRole.RESEARCHER,
                'analyst': AgentRole.ANALYST,
                'coordinator': AgentRole.COORDINATOR,
                'specialist': AgentRole.SPECIALIST,
                'ai_assistant': AgentRole.ASSISTANT,
                'research_agent': AgentRole.RESEARCHER,
                'data_analyst': AgentRole.ANALYST,
                'team_coordinator': AgentRole.COORDINATOR,
                'expert': AgentRole.SPECIALIST
            }
            
            return role_mapping.get(role_str, AgentRole.ASSISTANT)
            
        except Exception as e:
            logger.warning(f"解析角色失败: {str(e)}")
            return AgentRole.ASSISTANT
    
    async def _parse_instructions(self, instructions: Union[str, List[str], Dict]) -> List[str]:
        """解析指令"""
        try:
            if isinstance(instructions, str):
                # 字符串形式，按行分割
                return [line.strip() for line in instructions.split('\n') if line.strip()]
            elif isinstance(instructions, list):
                # 列表形式，直接返回
                return [str(inst) for inst in instructions]
            elif isinstance(instructions, dict):
                # 字典形式，提取各种可能的键
                result = []
                for key in ['system', 'prompt', 'guidelines', 'rules', 'instructions']:
                    if key in instructions:
                        value = instructions[key]
                        if isinstance(value, str):
                            result.extend([line.strip() for line in value.split('\n') if line.strip()])
                        elif isinstance(value, list):
                            result.extend([str(item) for item in value])
                return result
            else:
                return []
                
        except Exception as e:
            logger.warning(f"解析指令失败: {str(e)}")
            return []
    
    async def _parse_model_config(self, model_config: Union[str, Dict]) -> Dict[str, Any]:
        """解析模型配置"""
        try:
            if isinstance(model_config, str):
                # 字符串形式，假设是模型ID
                return {'model_id': model_config, 'type': 'chat'}
            elif isinstance(model_config, dict):
                # 字典形式，标准化键名
                normalized = {}
                
                # 标准化模型ID
                for key in ['model_id', 'model', 'llm', 'ai_model', 'name']:
                    if key in model_config:
                        normalized['model_id'] = model_config[key]
                        break
                
                # 标准化模型类型
                for key in ['type', 'model_type', 'category']:
                    if key in model_config:
                        normalized['type'] = model_config[key]
                        break
                else:
                    normalized['type'] = 'chat'
                
                # 复制其他参数
                for key, value in model_config.items():
                    if key not in ['model_id', 'model', 'llm', 'ai_model', 'name', 'type', 'model_type', 'category']:
                        normalized[key] = value
                
                return normalized
            else:
                return {'type': 'chat'}
                
        except Exception as e:
            logger.warning(f"解析模型配置失败: {str(e)}")
            return {'type': 'chat'}
    
    async def _parse_tools(self, tools: Union[str, List, Dict]) -> List[str]:
        """解析工具配置"""
        try:
            if isinstance(tools, str):
                # 字符串形式，按逗号分割
                return [tool.strip() for tool in tools.split(',') if tool.strip()]
            elif isinstance(tools, list):
                # 列表形式
                result = []
                for tool in tools:
                    if isinstance(tool, str):
                        result.append(tool)
                    elif isinstance(tool, dict):
                        # 从字典中提取工具ID
                        tool_id = tool.get('id') or tool.get('name') or tool.get('tool_id')
                        if tool_id:
                            result.append(str(tool_id))
                return result
            elif isinstance(tools, dict):
                # 字典形式，提取所有值
                result = []
                for key, value in tools.items():
                    if isinstance(value, bool) and value:
                        result.append(key)
                    elif isinstance(value, str):
                        result.append(value)
                return result
            else:
                return []
                
        except Exception as e:
            logger.warning(f"解析工具配置失败: {str(e)}")
            return []
    
    async def _parse_knowledge_bases(self, kb_config: Union[str, List, Dict]) -> List[str]:
        """解析知识库配置"""
        try:
            if isinstance(kb_config, str):
                # 字符串形式，按逗号分割
                return [kb.strip() for kb in kb_config.split(',') if kb.strip()]
            elif isinstance(kb_config, list):
                # 列表形式
                result = []
                for kb in kb_config:
                    if isinstance(kb, str):
                        result.append(kb)
                    elif isinstance(kb, dict):
                        kb_id = kb.get('id') or kb.get('name') or kb.get('kb_id')
                        if kb_id:
                            result.append(str(kb_id))
                return result
            elif isinstance(kb_config, dict):
                # 字典形式，提取ID列表
                if 'ids' in kb_config:
                    return await self._parse_knowledge_bases(kb_config['ids'])
                elif 'list' in kb_config:
                    return await self._parse_knowledge_bases(kb_config['list'])
                else:
                    # 假设字典的键是知识库ID
                    return list(kb_config.keys())
            else:
                return []
                
        except Exception as e:
            logger.warning(f"解析知识库配置失败: {str(e)}")
            return []
    
    async def _parse_memory_config(self, memory_config: Dict[str, Any]) -> Dict[str, Any]:
        """解析内存配置"""
        try:
            normalized = {}
            
            # 标准化内存类型
            for key in ['type', 'memory_type', 'backend']:
                if key in memory_config:
                    normalized['type'] = memory_config[key]
                    break
            else:
                normalized['type'] = 'session'
            
            # 标准化容量配置
            for key in ['max_size', 'capacity', 'limit']:
                if key in memory_config:
                    normalized['max_size'] = memory_config[key]
                    break
            
            # 复制其他参数
            for key, value in memory_config.items():
                if key not in ['type', 'memory_type', 'backend', 'max_size', 'capacity', 'limit']:
                    normalized[key] = value
            
            return normalized
            
        except Exception as e:
            logger.warning(f"解析内存配置失败: {str(e)}")
            return {}
    
    async def _create_default_config(self) -> AgentConfig:
        """创建默认配置"""
        return AgentConfig(
            name=self._default_config['name'],
            role=AgentRole.ASSISTANT,
            description=self._default_config['description'],
            instructions=self._default_config['instructions'],
            model_config=self._default_config['model_config'],
            tools=self._default_config['tools'],
            knowledge_bases=self._default_config['knowledge_bases'],
            memory_config=self._default_config['memory_config'],
            max_loops=self._default_config['max_loops'],
            timeout=self._default_config['timeout'],
            show_tool_calls=self._default_config['show_tool_calls'],
            markdown=self._default_config['markdown'],
            custom_params=self._default_config['custom_params']
        )
    
    async def validate_config(self, config: AgentConfig) -> List[str]:
        """验证配置"""
        errors = []
        
        try:
            # 验证基础信息
            if not config.name or not config.name.strip():
                errors.append("Agent名称不能为空")
            
            if len(config.name) > 100:
                errors.append("Agent名称过长（最大100字符）")
            
            # 验证超时设置
            if config.timeout <= 0:
                errors.append("超时时间必须大于0")
            elif config.timeout > 3600:  # 1小时
                errors.append("超时时间不能超过3600秒")
            
            # 验证循环次数
            if config.max_loops <= 0:
                errors.append("最大循环次数必须大于0")
            elif config.max_loops > 100:
                errors.append("最大循环次数不能超过100")
            
            # 验证工具列表
            if len(config.tools) > 50:
                errors.append("工具数量不能超过50个")
            
            # 验证知识库列表
            if len(config.knowledge_bases) > 20:
                errors.append("知识库数量不能超过20个")
            
            # 验证指令长度
            total_instruction_length = sum(len(inst) for inst in config.instructions)
            if total_instruction_length > 10000:
                errors.append("指令总长度不能超过10000字符")
                
        except Exception as e:
            errors.append(f"配置验证失败: {str(e)}")
        
        return errors
    
    async def merge_configs(self, base_config: AgentConfig, override_config: Dict[str, Any]) -> AgentConfig:
        """合并配置"""
        try:
            # 解析覆盖配置
            override_agent_config = await self.parse_frontend_config(override_config)
            
            # 创建合并后的配置
            merged_config = AgentConfig(
                name=override_agent_config.name if override_agent_config.name != self._default_config['name'] else base_config.name,
                role=override_agent_config.role if override_agent_config.role != AgentRole.ASSISTANT else base_config.role,
                description=override_agent_config.description if override_agent_config.description != self._default_config['description'] else base_config.description,
                instructions=base_config.instructions + override_agent_config.instructions,
                model_config={**base_config.model_config, **override_agent_config.model_config},
                tools=list(set(base_config.tools + override_agent_config.tools)),
                knowledge_bases=list(set(base_config.knowledge_bases + override_agent_config.knowledge_bases)),
                memory_config={**base_config.memory_config, **override_agent_config.memory_config},
                max_loops=override_agent_config.max_loops if override_agent_config.max_loops != self._default_config['max_loops'] else base_config.max_loops,
                timeout=override_agent_config.timeout if override_agent_config.timeout != self._default_config['timeout'] else base_config.timeout,
                show_tool_calls=override_agent_config.show_tool_calls if hasattr(override_config, 'show_tool_calls') else base_config.show_tool_calls,
                markdown=override_agent_config.markdown if hasattr(override_config, 'markdown') else base_config.markdown,
                custom_params={**base_config.custom_params, **override_agent_config.custom_params}
            )
            
            return merged_config
            
        except Exception as e:
            logger.error(f"合并配置失败: {str(e)}")
            return base_config

# 全局解析器实例
_parser: Optional[AgnoConfigParser] = None

def get_config_parser() -> AgnoConfigParser:
    """获取配置解析器实例"""
    global _parser
    
    if _parser is None:
        _parser = AgnoConfigParser()
    
    return _parser 