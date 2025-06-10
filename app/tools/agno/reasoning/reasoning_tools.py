# Agno ReasoningTools 封装管理器
from typing import Dict, Any, Optional
from agno import ReasoningTools

class AgnoReasoningManager:
    """Agno推理工具管理器 - 直接使用Agno框架的ReasoningTools"""
    
    def __init__(self, structured: bool = True, **kwargs):
        """
        初始化Agno推理工具管理器
        
        Args:
            structured: 是否启用结构化推理
            **kwargs: 其他Agno ReasoningTools参数
        """
        # 直接使用Agno框架的ReasoningTools
        self.reasoning_tools = ReasoningTools(
            structured=structured,
            **kwargs
        )
        self.name = "agno_reasoning"
        self.description = "基于Agno框架的结构化推理工具"
    
    async def reason(self, problem: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行推理任务
        
        Args:
            problem: 推理问题
            context: 上下文信息
            
        Returns:
            推理结果
        """
        try:
            # 使用Agno ReasoningTools进行推理
            result = await self.reasoning_tools.reason(problem, context=context)
            
            return {
                'tool': 'agno_reasoning',
                'problem': problem,
                'result': result,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_reasoning',
                'problem': problem,
                'error': str(e),
                'status': 'error'
            }
    
    async def analyze(self, data: Any, analysis_type: str = "general") -> Dict[str, Any]:
        """
        执行分析任务
        
        Args:
            data: 待分析数据
            analysis_type: 分析类型
            
        Returns:
            分析结果
        """
        try:
            # 使用Agno ReasoningTools进行分析
            result = await self.reasoning_tools.analyze(data, type=analysis_type)
            
            return {
                'tool': 'agno_reasoning',
                'data_type': type(data).__name__,
                'analysis_type': analysis_type,
                'result': result,
                'status': 'success'
            }
        except Exception as e:
            return {
                'tool': 'agno_reasoning',
                'error': str(e),
                'status': 'error'
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取推理工具能力"""
        return {
            'tool_name': self.name,
            'description': self.description,
            'capabilities': [
                'structured_reasoning',
                'logical_analysis', 
                'problem_solving',
                'data_analysis'
            ],
            'framework': 'agno'
        } 