from typing import Any, Dict, List, Optional, Tuple, Callable

class ToolOrchestrator:
    """工具编排器，管理工具的执行顺序和条件"""
    
    def __init__(self):
        """初始化工具编排器"""
        self.workflows = {}  # 工作流定义集合
        self.tools = {}  # 工具集合
        self.current_workflow = None  # 当前使用的工作流
        
    def register_tool(self, name: str, tool: Any, description: str = "") -> None:
        """注册工具
        
        Args:
            name: 工具名称
            tool: 工具实例
            description: 工具描述
        """
        self.tools[name] = {
            "instance": tool,
            "description": description,
            "usage_count": 0
        }
        
    def register_workflow(self, name: str, workflow_definition: Dict[str, Any]) -> None:
        """注册工作流
        
        Args:
            name: 工作流名称
            workflow_definition: 工作流定义
        """
        self.workflows[name] = workflow_definition
        
    def set_current_workflow(self, name: str) -> None:
        """设置当前使用的工作流
        
        Args:
            name: 工作流名称
        """
        if name not in self.workflows:
            raise ValueError(f"工作流 '{name}' 不存在")
            
        self.current_workflow = name
        
    async def execute_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行当前工作流
        
        Args:
            input_data: 输入数据
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        if not self.current_workflow:
            raise ValueError("未设置当前工作流")
            
        workflow = self.workflows[self.current_workflow]
        steps = workflow.get("steps", [])
        
        if not steps:
            raise ValueError("工作流没有定义步骤")
            
        # 上下文，用于在步骤之间传递数据
        context = dict(input_data)
        execution_history = []
        
        # 执行每个步骤
        for i, step in enumerate(steps):
            step_name = step.get("name", f"步骤{i+1}")
            tool_name = step.get("tool")
            input_mapping = step.get("input", {})
            condition = step.get("condition")
            
            # 检查条件
            if condition and not self._evaluate_condition(condition, context):
                # 条件不满足，跳过此步骤
                execution_history.append({
                    "step": step_name,
                    "tool": tool_name,
                    "skipped": True,
                    "reason": f"条件不满足: {condition}"
                })
                continue
                
            if not tool_name or tool_name not in self.tools:
                raise ValueError(f"步骤 '{step_name}' 指定的工具 '{tool_name}' 不存在")
                
            # 获取工具
            tool_info = self.tools[tool_name]
            tool = tool_info["instance"]
            
            # 准备输入参数
            params = {}
            for param_name, value_expr in input_mapping.items():
                params[param_name] = self._evaluate_expression(value_expr, context)
                
            # 执行工具
            try:
                result = await tool(**params) if callable(tool) else tool
                
                # 更新工具使用计数
                tool_info["usage_count"] += 1
                
                # 更新上下文
                output_mapping = step.get("output", {})
                for context_key, result_key in output_mapping.items():
                    if isinstance(result, dict) and result_key in result:
                        context[context_key] = result[result_key]
                    elif result_key == "$result":
                        context[context_key] = result
                        
                # 记录执行历史
                execution_record = {
                    "step": step_name,
                    "tool": tool_name,
                    "input": params,
                    "result": result,
                    "success": True
                }
            except Exception as e:
                # 记录执行错误
                execution_record = {
                    "step": step_name,
                    "tool": tool_name,
                    "input": params,
                    "error": str(e),
                    "success": False
                }
                
                # 处理错误
                error_handler = step.get("on_error")
                if error_handler == "fail":
                    # 失败终止
                    raise ValueError(f"工作流步骤 '{step_name}' 执行失败: {str(e)}")
                    
            execution_history.append(execution_record)
            
        # 返回结果
        return {
            "result": context.get("result"),
            "context": context,
            "execution_history": execution_history
        }
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """评估条件表达式
        
        Args:
            condition: 条件表达式
            context: 上下文数据
            
        Returns:
            bool: 条件是否满足
        """
        # 简单的条件评估，实际实现可能需要更复杂的逻辑
        try:
            # 创建安全的局部变量环境
            local_vars = dict(context)
            
            # 评估条件
            result = eval(condition, {"__builtins__": {}}, local_vars)
            return bool(result)
        except Exception as e:
            # 条件评估失败，视为不满足
            return False
    
    def _evaluate_expression(self, expression: Any, context: Dict[str, Any]) -> Any:
        """评估表达式
        
        Args:
            expression: 表达式
            context: 上下文数据
            
        Returns:
            Any: 评估结果
        """
        if isinstance(expression, str) and expression.startswith("${") and expression.endswith("}"):
            # 上下文变量引用
            var_name = expression[2:-1].strip()
            if "." in var_name:
                # 处理嵌套属性访问
                parts = var_name.split(".")
                value = context
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return None
                return value
            else:
                # 直接变量访问
                return context.get(var_name)
        else:
            # 字面量
            return expression
