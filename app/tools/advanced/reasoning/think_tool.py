"""
Agno Think工具实现
基于Agno官方ReasoningTools的think()方法
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.tools.agno_tool_base import AgnoToolBase, AgnoToolSchema, AgnoToolParameter
from app.tools.agno_registry import ToolMetadata, ToolCategory

logger = logging.getLogger(__name__)


class AgnoThinkTool(AgnoToolBase):
    """
    Agno Think工具 - 实现step-by-step思考过程
    
    基于Agno官方文档的ReasoningTools.think()方法设计，
    帮助Agent分解复杂问题并逐步思考。
    """
    
    def __init__(self, name: str = "think", llm=None):
        """
        初始化Think工具
        
        Args:
            name: 工具名称
            llm: 语言模型实例（可选）
        """
        super().__init__(
            name=name,
            description="使用结构化的思维过程来分析和解决问题，展示清晰的推理步骤",
            category=ToolCategory.REASONING
        )
        self.llm = llm
        self.max_steps = 10  # 最大思考步骤数
    
    def _init_dependencies(self):
        """初始化依赖"""
        # 如果没有提供LLM，使用系统默认配置
        if not self.llm:
            try:
                from app.frameworks.agno.config import get_default_llm
                self.llm = get_default_llm()
            except Exception as e:
                logger.warning(f"Failed to get default LLM: {e}")
    
    def _get_metadata(self) -> ToolMetadata:
        """获取工具元数据"""
        return ToolMetadata(
            name=self.name,
            description=self.description,
            category=self.category,
            version="1.0.0",
            capabilities=[
                "step_by_step_thinking",
                "problem_decomposition",
                "structured_reasoning",
                "thought_process_tracking"
            ],
            tags=["reasoning", "thinking", "analysis", "step-by-step"]
        )
    
    def _get_schema(self) -> AgnoToolSchema:
        """获取工具模式"""
        return AgnoToolSchema(
            parameters=[
                AgnoToolParameter(
                    name="problem",
                    type="string",
                    description="需要思考和分析的问题",
                    required=True
                ),
                AgnoToolParameter(
                    name="context",
                    type="string",
                    description="问题的上下文信息",
                    required=False,
                    default=""
                ),
                AgnoToolParameter(
                    name="max_steps",
                    type="integer",
                    description="最大思考步骤数",
                    required=False,
                    default=5
                ),
                AgnoToolParameter(
                    name="depth",
                    type="string",
                    description="思考深度：shallow/normal/deep",
                    required=False,
                    default="normal"
                ),
                AgnoToolParameter(
                    name="focus_areas",
                    type="array",
                    description="需要重点关注的方面",
                    required=False,
                    default=[]
                )
            ],
            returns={
                "type": "object",
                "description": "包含思考过程和结论的结果"
            },
            examples=[
                {
                    "input": {
                        "problem": "如何提高代码质量？",
                        "max_steps": 5,
                        "depth": "normal"
                    },
                    "output": {
                        "thought_process": [
                            {"step": 1, "thought": "定义代码质量的标准"},
                            {"step": 2, "thought": "分析当前代码的问题"},
                            {"step": 3, "thought": "制定改进策略"},
                            {"step": 4, "thought": "实施最佳实践"},
                            {"step": 5, "thought": "建立持续改进机制"}
                        ],
                        "conclusion": "通过建立标准、分析问题、实施最佳实践和持续改进来提高代码质量"
                    }
                }
            ]
        )
    
    async def _execute_async(self, **kwargs) -> Dict[str, Any]:
        """异步执行思考过程"""
        problem = kwargs.get("problem", "")
        context = kwargs.get("context", "")
        max_steps = min(kwargs.get("max_steps", 5), self.max_steps)
        depth = kwargs.get("depth", "normal")
        focus_areas = kwargs.get("focus_areas", [])
        
        # 构建思考提示
        thinking_prompt = self._build_thinking_prompt(
            problem, context, max_steps, depth, focus_areas
        )
        
        # 执行思考过程
        thought_process = []
        current_context = f"问题: {problem}\n"
        if context:
            current_context += f"背景: {context}\n"
        
        for step in range(1, max_steps + 1):
            # 生成当前步骤的思考
            step_thought = await self._generate_step_thought(
                current_context, step, thought_process, depth
            )
            
            thought_process.append({
                "step": step,
                "thought": step_thought,
                "timestamp": datetime.now().isoformat()
            })
            
            # 更新上下文
            current_context += f"\n步骤{step}: {step_thought}"
            
            # 检查是否已经得出结论
            if self._is_conclusion_reached(step_thought):
                break
        
        # 生成最终结论
        conclusion = await self._generate_conclusion(problem, thought_process)
        
        # 构建结果
        result = {
            "problem": problem,
            "thought_process": thought_process,
            "conclusion": conclusion,
            "total_steps": len(thought_process),
            "depth": depth,
            "metadata": {
                "context_provided": bool(context),
                "focus_areas": focus_areas,
                "thinking_complete": True
            }
        }
        
        return result
    
    def _build_thinking_prompt(self, problem: str, context: str, 
                             max_steps: int, depth: str, focus_areas: List[str]) -> str:
        """构建思考提示"""
        prompt = f"""请对以下问题进行深入思考，采用step-by-step的方式：

问题：{problem}
"""
        
        if context:
            prompt += f"\n背景信息：{context}\n"
        
        if focus_areas:
            prompt += f"\n重点关注领域：{', '.join(focus_areas)}\n"
        
        depth_instructions = {
            "shallow": "进行快速的表层分析",
            "normal": "进行标准深度的分析",
            "deep": "进行深入细致的分析，考虑各种可能性和细节"
        }
        
        prompt += f"""
思考要求：
1. {depth_instructions.get(depth, depth_instructions['normal'])}
2. 最多进行{max_steps}个思考步骤
3. 每个步骤都要有明确的逻辑关系
4. 最后给出明确的结论
"""
        
        return prompt
    
    async def _generate_step_thought(self, context: str, step: int, 
                                   previous_thoughts: List[Dict], depth: str) -> str:
        """生成单个步骤的思考"""
        # 这里应该调用LLM生成思考
        # 为了演示，返回模拟的思考内容
        if self.llm:
            prompt = f"""基于以下信息，生成第{step}步的思考：

{context}

之前的思考步骤：
{self._format_previous_thoughts(previous_thoughts)}

请生成第{step}步的思考内容（一句话）："""
            
            # 调用LLM（这里需要根据实际的LLM接口调整）
            # response = await self.llm.agenerate(prompt)
            # return response.text
        
        # 模拟返回
        return f"分析问题的第{step}个方面，考虑相关因素和可能的解决方案"
    
    async def _generate_conclusion(self, problem: str, thought_process: List[Dict]) -> str:
        """生成最终结论"""
        if self.llm:
            thoughts_summary = self._format_previous_thoughts(thought_process)
            prompt = f"""基于以下思考过程，给出问题的最终结论：

问题：{problem}

思考过程：
{thoughts_summary}

请给出简洁明确的结论："""
            
            # 调用LLM
            # response = await self.llm.agenerate(prompt)
            # return response.text
        
        # 模拟返回
        return "基于以上分析，建议采用系统化的方法来解决问题，关注关键因素并持续优化"
    
    def _format_previous_thoughts(self, thoughts: List[Dict]) -> str:
        """格式化之前的思考步骤"""
        if not thoughts:
            return "无"
        
        formatted = []
        for thought in thoughts:
            formatted.append(f"步骤{thought['step']}: {thought['thought']}")
        
        return "\n".join(formatted)
    
    def _is_conclusion_reached(self, thought: str) -> bool:
        """检查是否已经得出结论"""
        # 检查思考内容中是否包含结论性词汇
        conclusion_keywords = [
            "因此", "所以", "综上所述", "结论是", "最终",
            "总结", "归纳", "得出", "确定"
        ]
        
        return any(keyword in thought for keyword in conclusion_keywords)


# 工厂函数
def create_agno_think_tool(name: str = "think", llm=None) -> AgnoThinkTool:
    """
    创建Agno Think工具实例
    
    Args:
        name: 工具名称
        llm: 语言模型实例
        
    Returns:
        Think工具实例
    """
    return AgnoThinkTool(name=name, llm=llm)


# 便捷函数 - 符合Agno官方文档的使用方式
def think(problem: str, context: str = "", max_steps: int = 5, 
          depth: str = "normal", **kwargs) -> Dict[str, Any]:
    """
    使用Think工具进行思考
    
    这是一个便捷函数，模拟Agno官方ReasoningTools.think()的使用方式
    
    Args:
        problem: 需要思考的问题
        context: 上下文信息
        max_steps: 最大思考步骤
        depth: 思考深度
        **kwargs: 其他参数
        
    Returns:
        思考结果
    """
    tool = AgnoThinkTool()
    return tool.execute(
        problem=problem,
        context=context,
        max_steps=max_steps,
        depth=depth,
        **kwargs
    ) 