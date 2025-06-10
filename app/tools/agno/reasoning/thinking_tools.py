# Agno ThinkingTools 封装管理器
from typing import Dict, Any, Optional
from agno import ThinkingTools

class AgnoThinkingManager:
    """Agno思考工具管理器 - 直接使用Agno框架的ThinkingTools"""
    
    def __init__(self, max_iterations: int = 5, **kwargs):
        """
        初始化Agno思考工具管理器
        
        Args:
            max_iterations: 最大思考迭代次数
            **kwargs: 其他Agno ThinkingTools参数
        """
        # 直接使用Agno框架的ThinkingTools
        self.thinking_tools = ThinkingTools(
            max_iterations=max_iterations,
            **kwargs
        )
        self.name = "agno_thinking"
        self.description = "基于Agno框架的迭代思考工具"
    
    async def think(self, topic: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行思考任务
        
        Args:
            topic: 思考主题
            context: 上下文信息
            
        Returns:
            思考结果
        """
        try:
            # 使用Agno ThinkingTools进行思考
            result = await self.thinking_tools.think(topic, context=context)
            
            return {
                'tool': 'agno_thinking',
                'topic': topic,
                'result': result,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_thinking',
                'topic': topic,
                'error': str(e),
                'status': 'error'
            }
    
    async def plan(self, goal: str, constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行规划任务
        
        Args:
            goal: 目标
            constraints: 约束条件
            
        Returns:
            规划结果
        """
        try:
            # 使用Agno ThinkingTools进行规划
            result = await self.thinking_tools.plan(goal, constraints=constraints)
            
            return {
                'tool': 'agno_thinking',
                'goal': goal,
                'constraints': constraints,
                'result': result,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_thinking',
                'goal': goal,
                'error': str(e),
                'status': 'error'
            }
    
    async def reflect(self, content: str, focus: Optional[str] = None) -> Dict[str, Any]:
        """
        执行反思任务
        
        Args:
            content: 反思内容
            focus: 反思焦点
            
        Returns:
            反思结果
        """
        try:
            # 使用Agno ThinkingTools进行反思
            result = await self.thinking_tools.reflect(content, focus=focus)
            
            return {
                'tool': 'agno_thinking',
                'content': content,
                'focus': focus,
                'result': result,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_thinking',
                'content': content,
                'error': str(e),
                'status': 'error'
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取思考工具能力"""
        return {
            'tool_name': self.name,
            'description': self.description,
            'capabilities': [
                'iterative_thinking',
                'goal_planning',
                'reflection',
                'step_by_step_analysis'
            ],
            'framework': 'agno'
        } 