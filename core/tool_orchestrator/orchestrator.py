from typing import Any, Dict, List, Optional, Callable
import logging

logger = logging.getLogger(__name__)

class ToolOrchestrator:
    """工具链编排引擎，管理工具调用顺序和条件"""
    
    def __init__(self):
        self.tools = []  # 存储(工具, 顺序)元组
        self.conditions = {}  # 工具 -> 条件表达式
        self.default_params = {}  # 工具 -> 默认参数
        
    def add_tool(self, tool: Any, order: int, 
                condition: Optional[str] = None, 
                default_params: Optional[Dict[str, Any]] = None) -> None:
        """添加工具到编排引擎
        
        Args:
            tool: 工具实例
            order: 调用顺序
            condition: 条件表达式
            default_params: 默认参数
        """
        self.tools.append((tool, order))
        if condition:
            self.conditions[tool] = condition
        if default_params:
            self.default_params[tool] = default_params
        
        # 按顺序排序工具
        self.tools.sort(key=lambda x: x[1])
        
    def remove_tool(self, tool: Any) -> bool:
        """移除工具
        
        Args:
            tool: 要移除的工具实例
            
        Returns:
            bool: 是否成功移除
        """
        for t, order in self.tools:
            if t == tool:
                self.tools.remove((t, order))
                if tool in self.conditions:
                    del self.conditions[tool]
                if tool in self.default_params:
                    del self.default_params[tool]
                return True
        return False
    
    def get_tools(self) -> List[Any]:
        """获取所有工具
        
        Returns:
            List[Any]: 工具列表(按顺序)
        """
        return [tool for tool, _ in self.tools]
    
    def get_next_tool(self, context: Dict[str, Any]) -> Optional[Any]:
        """根据上下文获取下一个要调用的工具
        
        Args:
            context: 当前执行上下文
            
        Returns:
            Optional[Any]: 下一个要调用的工具，如果没有则返回None
        """
        for tool, _ in self.tools:
            # 如果有条件，评估条件
            if tool in self.conditions:
                condition = self.conditions[tool]
                try:
                    if not self._evaluate_condition(condition, context):
                        continue
                except Exception as e:
                    logger.error(f"条件评估错误: {e}", exc_info=True)
                    continue
            
            return tool
        
        return None
    
    def prepare_params(self, tool: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """准备工具调用参数
        
        Args:
            tool: 工具实例
            context: 当前执行上下文
            
        Returns:
            Dict[str, Any]: 准备好的参数
        """
        params = {}
        
        # 使用默认参数
        if tool in self.default_params:
            params.update(self.default_params[tool])
        
        # 从上下文中提取参数
        if hasattr(tool, "__annotations__"):
            # 获取工具预期的参数
            for param_name, param_type in tool.__annotations__.items():
                if param_name in context:
                    params[param_name] = context[param_name]
        
        # 如果工具有get_required_params方法
        if hasattr(tool, "get_required_params"):
            required_params = tool.get_required_params()
            for param_name in required_params:
                if param_name in context:
                    params[param_name] = context[param_name]
        
        return params
    
    async def execute_tool(self, tool: Any, context: Dict[str, Any]) -> Any:
        """执行工具
        
        Args:
            tool: 工具实例
            context: 当前执行上下文
            
        Returns:
            Any: 工具执行结果
            
        Raises:
            Exception: 工具执行错误
        """
        params = self.prepare_params(tool, context)
        
        try:
            if hasattr(tool, "async_run"):
                result = await tool.async_run(**params)
            elif hasattr(tool, "run"):
                result = tool.run(**params)
            elif callable(tool):
                result = tool(**params)
            else:
                raise ValueError(f"工具 {tool} 不可调用")
                
            return result
        except Exception as e:
            logger.error(f"工具执行错误: {e}", exc_info=True)
            raise
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """评估条件表达式
        
        Args:
            condition: 条件表达式
            context: 当前执行上下文
            
        Returns:
            bool: 条件是否满足
        """
        # 使用安全的条件评估方法
        try:
            # 创建一个安全的命名空间
            safe_globals = {
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "min": min,
                "max": max,
                "sum": sum,
                "abs": abs,
                "round": round,
                "any": any,
                "all": all
            }
            
            # 加载上下文作为局部变量
            local_vars = dict(context)
            
            # 评估条件
            return eval(condition, safe_globals, local_vars)
        except Exception as e:
            logger.error(f"条件评估错误: {e}")
            return False
