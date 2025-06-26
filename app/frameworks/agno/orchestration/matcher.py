"""
Agno智能匹配引擎
根据任务需求、能力描述和上下文自动匹配最合适的工具组合
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import defaultdict
import asyncio

from .types import (
    IMatchingEngine, ToolMetadata, ToolCategory, AgentConfig
)

logger = logging.getLogger(__name__)

class AgnoMatchingEngine(IMatchingEngine):
    """Agno智能匹配引擎
    
    使用多种策略匹配工具：
    1. 关键词匹配
    2. 语义相似度匹配  
    3. 能力覆盖度分析
    4. 工具组合优化
    """
    
    def __init__(self):
        """初始化匹配引擎"""
        self._keyword_mappings = self._build_keyword_mappings()
        self._capability_weights = self._build_capability_weights()
        self._tool_compatibility = self._build_tool_compatibility()
        
    def _build_keyword_mappings(self) -> Dict[str, List[str]]:
        """构建关键词映射表"""
        return {
            'reasoning': [
                'reason', 'think', 'analyze', 'logic', 'infer', 'deduce',
                'conclude', 'solve', 'problem', 'decision', 'judgment',
                '推理', '思考', '分析', '逻辑', '推断', '解决', '判断'
            ],
            'search': [
                'search', 'find', 'query', 'retrieve', 'lookup', 'discover',
                'explore', 'investigate', 'browse', 'scan', 'index',
                '搜索', '查找', '检索', '查询', '发现', '探索', '调查'
            ],
            'knowledge': [
                'knowledge', 'know', 'information', 'data', 'fact', 'answer',
                'question', 'qa', 'database', 'repository', 'learn',
                '知识', '信息', '数据', '问答', '学习', '了解', '知道'
            ],
            'chunking': [
                'chunk', 'split', 'divide', 'segment', 'break', 'parse',
                'process', 'extract', 'organize', 'structure', 'format',
                '分块', '分割', '处理', '解析', '提取', '组织', '格式化'
            ],
            'file_management': [
                'file', 'document', 'upload', 'download', 'save', 'load',
                'manage', 'organize', 'storage', 'folder', 'directory',
                '文件', '文档', '上传', '下载', '保存', '管理', '存储'
            ],
            'system': [
                'system', 'config', 'setting', 'admin', 'manage', 'control',
                'monitor', 'status', 'health', 'performance', 'maintenance',
                '系统', '配置', '设置', '管理', '控制', '监控', '状态'
            ]
        }
    
    def _build_capability_weights(self) -> Dict[str, float]:
        """构建能力权重表"""
        return {
            # 核心能力
            'reasoning': 1.0,
            'search': 1.0,
            'knowledge': 1.0,
            'analysis': 0.9,
            
            # 辅助能力
            'chunking': 0.7,
            'processing': 0.7,
            'formatting': 0.6,
            
            # 管理能力
            'file_management': 0.8,
            'system': 0.5,
            'integration': 0.6,
            
            # 专业能力
            'qa': 0.9,
            'retrieval': 0.8,
            'logic': 0.9,
            'thinking': 0.9,
        }
    
    def _build_tool_compatibility(self) -> Dict[str, List[str]]:
        """构建工具兼容性表"""
        return {
            'reasoning': ['knowledge', 'search', 'analysis'],
            'search': ['reasoning', 'knowledge', 'chunking'],
            'knowledge': ['reasoning', 'search', 'qa'],
            'chunking': ['search', 'file_management', 'processing'],
            'file_management': ['chunking', 'system'],
            'system': ['file_management', 'integration']
        }
    
    async def match_tools(self, requirements: List[str], available_tools: List[ToolMetadata]) -> List[str]:
        """匹配工具"""
        try:
            matches = []
            
            for requirement in requirements:
                # 对每个需求进行匹配
                tool_scores = await self._score_tools_for_requirement(requirement, available_tools)
                
                # 选择得分最高的工具
                if tool_scores:
                    best_tool = max(tool_scores, key=tool_scores.get)
                    if tool_scores[best_tool] > 0.3:  # 最低匹配阈值
                        matches.append(best_tool)
            
            # 去重并优化工具组合
            unique_matches = list(dict.fromkeys(matches))  # 保持顺序去重
            optimized_matches = await self.optimize_tool_chain(unique_matches)
            
            logger.debug(f"匹配到 {len(optimized_matches)} 个工具: {optimized_matches}")
            return optimized_matches
            
        except Exception as e:
            logger.error(f"工具匹配失败: {str(e)}")
            return []
    
    async def _score_tools_for_requirement(self, requirement: str, available_tools: List[ToolMetadata]) -> Dict[str, float]:
        """为单个需求计算工具得分"""
        scores = {}
        requirement_lower = requirement.lower()
        
        for tool in available_tools:
            score = 0.0
            
            # 1. 关键词匹配
            keyword_score = self._calculate_keyword_score(requirement_lower, tool)
            score += keyword_score * 0.4
            
            # 2. 能力匹配
            capability_score = self._calculate_capability_score(requirement_lower, tool)
            score += capability_score * 0.3
            
            # 3. 名称和描述匹配
            name_desc_score = self._calculate_name_desc_score(requirement_lower, tool)
            score += name_desc_score * 0.2
            
            # 4. 类别匹配
            category_score = self._calculate_category_score(requirement_lower, tool)
            score += category_score * 0.1
            
            if score > 0:
                scores[tool.id] = score
        
        return scores
    
    def _calculate_keyword_score(self, requirement: str, tool: ToolMetadata) -> float:
        """计算关键词匹配得分"""
        score = 0.0
        
        # 检查工具类别对应的关键词
        category_keywords = self._keyword_mappings.get(tool.category.value, [])
        
        for keyword in category_keywords:
            if keyword in requirement:
                score += 1.0
        
        # 标准化得分
        if category_keywords:
            score = min(score / len(category_keywords), 1.0)
        
        return score
    
    def _calculate_capability_score(self, requirement: str, tool: ToolMetadata) -> float:
        """计算能力匹配得分"""
        score = 0.0
        
        for capability in tool.capabilities:
            capability_lower = capability.lower()
            
            # 直接匹配
            if capability_lower in requirement:
                weight = self._capability_weights.get(capability_lower, 0.5)
                score += weight
            
            # 部分匹配
            elif any(part in requirement for part in capability_lower.split('_')):
                weight = self._capability_weights.get(capability_lower, 0.5)
                score += weight * 0.5
        
        # 标准化得分
        if tool.capabilities:
            score = min(score / len(tool.capabilities), 1.0)
        
        return score
    
    def _calculate_name_desc_score(self, requirement: str, tool: ToolMetadata) -> float:
        """计算名称和描述匹配得分"""
        score = 0.0
        
        # 名称匹配
        tool_name_lower = tool.name.lower()
        if any(word in tool_name_lower for word in requirement.split()):
            score += 0.5
        
        # 描述匹配
        tool_desc_lower = tool.description.lower()
        requirement_words = requirement.split()
        matching_words = sum(1 for word in requirement_words if word in tool_desc_lower)
        
        if requirement_words:
            score += (matching_words / len(requirement_words)) * 0.5
        
        return min(score, 1.0)
    
    def _calculate_category_score(self, requirement: str, tool: ToolMetadata) -> float:
        """计算类别匹配得分"""
        category_name = tool.category.value.lower()
        
        if category_name in requirement:
            return 1.0
        elif any(part in requirement for part in category_name.split('_')):
            return 0.5
        else:
            return 0.0
    
    async def recommend_tools(self, task_description: str, context: Dict[str, Any]) -> List[str]:
        """推荐工具"""
        try:
            # 分析任务描述，提取关键需求
            requirements = await self._extract_requirements(task_description, context)
            
            # 从注册中心获取可用工具
            from .registry import get_tool_registry
            registry = await get_tool_registry()
            available_tools = await registry.list_tools()
            
            # 匹配工具
            recommended_tools = await self.match_tools(requirements, available_tools)
            
            # 根据上下文调整推荐
            adjusted_tools = await self._adjust_recommendations(recommended_tools, context)
            
            logger.info(f"为任务推荐了 {len(adjusted_tools)} 个工具")
            return adjusted_tools
            
        except Exception as e:
            logger.error(f"工具推荐失败: {str(e)}")
            return []
    
    async def _extract_requirements(self, task_description: str, context: Dict[str, Any]) -> List[str]:
        """从任务描述中提取需求"""
        requirements = []
        task_lower = task_description.lower()
        
        # 基于关键词提取需求
        for category, keywords in self._keyword_mappings.items():
            if any(keyword in task_lower for keyword in keywords):
                requirements.append(category)
        
        # 从上下文中提取额外需求
        if context.get('user_preferences'):
            preferences = context['user_preferences']
            if isinstance(preferences, dict):
                for key, value in preferences.items():
                    if isinstance(value, bool) and value:
                        requirements.append(key)
        
        # 如果没有明确需求，添加默认需求
        if not requirements:
            requirements = ['reasoning', 'knowledge']  # 默认核心能力
        
        return requirements
    
    async def _adjust_recommendations(self, tools: List[str], context: Dict[str, Any]) -> List[str]:
        """根据上下文调整推荐"""
        try:
            adjusted_tools = tools.copy()
            
            # 根据用户偏好调整
            user_preferences = context.get('user_preferences', {})
            if user_preferences.get('prefer_simple_tools'):
                # 优先选择简单工具，移除复杂工具
                adjusted_tools = [tool for tool in adjusted_tools if 'manager' not in tool.lower()]
            
            # 根据性能要求调整
            performance_requirements = context.get('performance_requirements', {})
            if performance_requirements.get('high_speed'):
                # 优先选择高速工具
                speed_priority = ['search', 'chunking', 'file_management']
                adjusted_tools.sort(key=lambda x: speed_priority.index(x.split('_')[1]) if len(x.split('_')) > 1 and x.split('_')[1] in speed_priority else 999)
            
            # 根据资源限制调整
            resource_limits = context.get('resource_limits', {})
            max_tools = resource_limits.get('max_tools', 10)
            if len(adjusted_tools) > max_tools:
                adjusted_tools = adjusted_tools[:max_tools]
            
            return adjusted_tools
            
        except Exception as e:
            logger.warning(f"调整推荐失败: {str(e)}")
            return tools
    
    async def optimize_tool_chain(self, tool_ids: List[str]) -> List[str]:
        """优化工具链"""
        try:
            if not tool_ids:
                return tool_ids
            
            # 获取工具元数据
            from .registry import get_tool_registry
            registry = await get_tool_registry()
            
            tool_metadata = {}
            for tool_id in tool_ids:
                metadata = await registry.get_tool_metadata(tool_id)
                if metadata:
                    tool_metadata[tool_id] = metadata
            
            # 分析工具兼容性
            optimized_chain = await self._build_optimal_chain(tool_metadata)
            
            # 移除冗余工具
            deduplicated_chain = await self._remove_redundant_tools(optimized_chain, tool_metadata)
            
            logger.debug(f"工具链优化：{len(tool_ids)} -> {len(deduplicated_chain)}")
            return deduplicated_chain
            
        except Exception as e:
            logger.error(f"工具链优化失败: {str(e)}")
            return tool_ids
    
    async def _build_optimal_chain(self, tool_metadata: Dict[str, ToolMetadata]) -> List[str]:
        """构建最优工具链"""
        if not tool_metadata:
            return []
        
        # 按优先级排序工具
        priority_order = ['knowledge', 'reasoning', 'search', 'chunking', 'file_management', 'system']
        
        sorted_tools = []
        remaining_tools = list(tool_metadata.keys())
        
        # 按优先级分组
        for priority_category in priority_order:
            category_tools = []
            for tool_id in remaining_tools.copy():
                metadata = tool_metadata[tool_id]
                if priority_category in metadata.category.value.lower():
                    category_tools.append(tool_id)
                    remaining_tools.remove(tool_id)
            
            # 在同一类别内按兼容性排序
            if category_tools:
                sorted_category_tools = await self._sort_by_compatibility(category_tools, tool_metadata)
                sorted_tools.extend(sorted_category_tools)
        
        # 添加剩余工具
        sorted_tools.extend(remaining_tools)
        
        return sorted_tools
    
    async def _sort_by_compatibility(self, tool_ids: List[str], tool_metadata: Dict[str, ToolMetadata]) -> List[str]:
        """按兼容性排序工具"""
        if len(tool_ids) <= 1:
            return tool_ids
        
        # 计算工具间的兼容性得分
        compatibility_scores = {}
        
        for i, tool1 in enumerate(tool_ids):
            score = 0
            metadata1 = tool_metadata[tool1]
            
            for j, tool2 in enumerate(tool_ids):
                if i != j:
                    metadata2 = tool_metadata[tool2]
                    compatibility = self._calculate_tool_compatibility(metadata1, metadata2)
                    score += compatibility
            
            compatibility_scores[tool1] = score
        
        # 按兼容性得分排序
        return sorted(tool_ids, key=lambda x: compatibility_scores[x], reverse=True)
    
    def _calculate_tool_compatibility(self, tool1: ToolMetadata, tool2: ToolMetadata) -> float:
        """计算两个工具的兼容性"""
        score = 0.0
        
        # 类别兼容性
        category1 = tool1.category.value
        category2 = tool2.category.value
        
        compatible_categories = self._tool_compatibility.get(category1, [])
        if category2 in compatible_categories:
            score += 0.5
        
        # 能力互补性
        capabilities1 = set(tool1.capabilities)
        capabilities2 = set(tool2.capabilities)
        
        # 避免能力重复过多
        overlap = len(capabilities1 & capabilities2)
        total = len(capabilities1 | capabilities2)
        
        if total > 0:
            overlap_ratio = overlap / total
            if overlap_ratio < 0.3:  # 低重复度更好
                score += 0.3
            elif overlap_ratio < 0.5:
                score += 0.1
        
        return score
    
    async def _remove_redundant_tools(self, tool_chain: List[str], tool_metadata: Dict[str, ToolMetadata]) -> List[str]:
        """移除冗余工具"""
        if len(tool_chain) <= 1:
            return tool_chain
        
        deduplicated = []
        covered_capabilities = set()
        
        for tool_id in tool_chain:
            if tool_id not in tool_metadata:
                continue
                
            metadata = tool_metadata[tool_id]
            tool_capabilities = set(metadata.capabilities)
            
            # 检查是否提供新能力
            new_capabilities = tool_capabilities - covered_capabilities
            
            if new_capabilities:
                # 有新能力，保留这个工具
                deduplicated.append(tool_id)
                covered_capabilities.update(tool_capabilities)
            else:
                # 检查是否是更好的实现
                better_implementation = await self._is_better_implementation(
                    tool_id, deduplicated, tool_metadata, tool_capabilities
                )
                
                if better_implementation:
                    # 替换为更好的实现
                    for i, existing_tool in enumerate(deduplicated):
                        existing_metadata = tool_metadata[existing_tool]
                        if set(existing_metadata.capabilities) & tool_capabilities:
                            deduplicated[i] = tool_id
                            break
        
        return deduplicated
    
    async def _is_better_implementation(
        self, 
        new_tool: str, 
        existing_tools: List[str], 
        tool_metadata: Dict[str, ToolMetadata],
        capabilities: Set[str]
    ) -> bool:
        """检查是否是更好的实现"""
        try:
            new_metadata = tool_metadata[new_tool]
            
            for existing_tool in existing_tools:
                existing_metadata = tool_metadata[existing_tool]
                
                # 检查能力重叠
                if set(existing_metadata.capabilities) & capabilities:
                    # 比较实现质量（简单启发式）
                    if 'manager' in new_tool.lower() and 'manager' not in existing_tool.lower():
                        return True  # 管理器通常更全面
                    elif len(new_metadata.capabilities) > len(existing_metadata.capabilities):
                        return True  # 能力更多
            
            return False
            
        except Exception:
            return False
    
    async def analyze_tool_requirements(self, agent_config: AgentConfig) -> Dict[str, Any]:
        """分析Agent配置的工具需求"""
        try:
            analysis = {
                'required_categories': set(),
                'required_capabilities': set(),
                'recommended_tools': [],
                'missing_tools': [],
                'optimization_suggestions': []
            }
            
            # 从指令中分析需求
            for instruction in agent_config.instructions:
                requirements = await self._extract_requirements(instruction, {})
                for req in requirements:
                    analysis['required_categories'].add(req)
            
            # 从任务描述中分析需求
            if agent_config.description:
                requirements = await self._extract_requirements(agent_config.description, {})
                for req in requirements:
                    analysis['required_categories'].add(req)
            
            # 获取可用工具
            from .registry import get_tool_registry
            registry = await get_tool_registry()
            available_tools = await registry.list_tools()
            
            # 分析现有工具配置
            configured_tools = set(agent_config.tools)
            available_tool_ids = {tool.id for tool in available_tools}
            
            # 检查缺失的工具
            for category in analysis['required_categories']:
                category_tools = [tool.id for tool in available_tools if category in tool.category.value.lower()]
                if not any(tool in configured_tools for tool in category_tools):
                    analysis['missing_tools'].extend(category_tools[:1])  # 推荐一个
            
            # 转换为列表以便JSON序列化
            analysis['required_categories'] = list(analysis['required_categories'])
            analysis['required_capabilities'] = list(analysis['required_capabilities'])
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析工具需求失败: {str(e)}")
            return {}

# 全局匹配引擎实例
_matcher: Optional[AgnoMatchingEngine] = None

def get_matching_engine() -> AgnoMatchingEngine:
    """获取匹配引擎实例"""
    global _matcher
    
    if _matcher is None:
        _matcher = AgnoMatchingEngine()
    
    return _matcher 