from typing import Any, Dict, List, Optional, Tuple

from app.frameworks.owl.agents.base import BaseAgent

class ExecutorAgent(BaseAgent):
    """执行智能体，负责执行具体任务步骤"""
    
    def __init__(self, model_config: Dict[str, Any]):
        """初始化执行智能体
        
        Args:
            model_config: 模型配置
        """
        system_message = (
            "你是一个专业的任务执行专家，擅长按照计划完成具体操作。\n"
            "你需要逐步执行给定的计划，并提供每一步的执行结果。\n"
            "如果执行过程中遇到问题，你应当尝试解决问题或提供清晰的错误说明。\n"
            "使用工具时，请明确说明工具名称、输入参数和期望输出。\n"
            "输出应当简洁明了，重点展示执行结果和关键信息。"
        )
        
        super().__init__(model_config, system_message)
        self.tool_map = {}  # 工具名称到工具实例的映射
        self.execution_history = []  # 执行历史记录
        
    def add_tools(self, tools: List[Any]) -> None:
        """添加工具并建立工具映射
        
        Args:
            tools: 要添加的工具列表
        """
        super().add_tools(tools)
        
        # 建立工具名称到工具实例的映射
        for tool in tools:
            if hasattr(tool, 'name'):
                self.tool_map[tool.name] = tool
    
    async def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个计划步骤
        
        Args:
            step: 步骤信息，包含描述和可能的工具
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        description = step['description']
        tool_name = step.get('tool')
        parameters = step.get('parameters', {})
        
        # 记录步骤开始执行
        step_record = {
            "description": description,
            "tool": tool_name,
            "parameters": parameters,
            "start_time": None,  # 将在实际实现中添加时间戳
            "end_time": None,
            "status": "pending",
            "result": None,
            "error": None
        }
        
        # 构建执行提示
        prompt = f"执行步骤: {description}"
        if tool_name:
            prompt += f"\n使用工具: {tool_name}"
            if parameters:
                param_str = json.dumps(parameters, ensure_ascii=False, indent=2)
                prompt += f"\n参数: {param_str}"
        
        # 更新状态为运行中
        step_record["status"] = "running"
        
        # 如果有指定工具且工具可用，尝试使用工具执行
        tool_result = None
        if tool_name and tool_name in self.tool_map:
            try:
                tool = self.tool_map[tool_name]
                
                # 让智能体决定如何使用工具
                tool_usage_prompt = (
                    f"请为步骤 '{description}' 生成调用工具 '{tool_name}' 的指令\n"
                    f"工具描述: {getattr(tool, 'description', '')}\n"
                    f"参数: {json.dumps(parameters, ensure_ascii=False) if parameters else '{}'}\n\n"
                    f"请返回JSON格式的工具调用参数，包含这些参数以及其他必要参数"
                )
                
                # 获取工具使用指令
                tool_params_str = await self.chat(tool_usage_prompt)
                
                # 解析JSON参数
                try:
                    tool_params = json.loads(tool_params_str)
                except json.JSONDecodeError:
                    # 如果无法解析JSON，尝试从文本中提取JSON
                    import re
                    json_match = re.search(r'\{.*\}', tool_params_str, re.DOTALL)
                    if json_match:
                        try:
                            tool_params = json.loads(json_match.group(0))
                        except:
                            tool_params = parameters
                    else:
                        tool_params = parameters
                        
                # 调用工具
                if asyncio.iscoroutinefunction(tool.__call__):
                    tool_result = await tool(**tool_params)
                else:
                    tool_result = tool(**tool_params)
                    
                # 记录工具执行结果
                if isinstance(tool_result, str):
                    result_str = tool_result
                else:
                    try:
                        result_str = json.dumps(tool_result, ensure_ascii=False, indent=2)
                    except:
                        result_str = str(tool_result)
                        
                # 更新步骤记录
                step_record["status"] = "completed"
                step_record["result"] = result_str
                
                # 构建工具执行结果提示
                prompt = f"工具 {tool_name} 执行结果:\n{result_str}\n\n请根据以上结果，执行步骤: {description}"
                
            except Exception as e:
                # 记录错误
                error_message = f"工具 {tool_name} 执行失败: {str(e)}"
                step_record["status"] = "failed"
                step_record["error"] = error_message
                
                # 请求智能体提供备选方案
                fallback_prompt = f"{error_message}\n请提供一个备选方案来执行步骤: {description}"
                fallback_response = await self.chat(fallback_prompt)
                
                # 更新步骤记录
                step_record["result"] = fallback_response
                
                # 构建提示
                prompt = f"{error_message}\n备选方案: {fallback_response}\n\n请继续执行步骤: {description}"
        else:
            # 如果没有工具或不需要使用工具，直接让智能体基于描述执行任务
            direct_prompt = f"请直接执行以下步骤（无需使用工具）：\n{description}"
            result = await self.chat(direct_prompt)
            
            # 更新步骤记录
            step_record["status"] = "completed"
            step_record["result"] = result
        
        # 如果工具存在但执行失败且没有设置结果，让智能体处理
        if tool_name and step_record["status"] != "completed":
            recovery_prompt = f"步骤 '{description}' 的工具执行有问题。请不使用工具，直接分析并完成这个步骤。"
            result = await self.chat(recovery_prompt)
            step_record["status"] = "recovered"
            step_record["result"] = result
        
        # 记录执行历史
        execution_record = {
            'step': description,
            'tool': tool_name,
            'result': result
        }
        self.execution_history.append(execution_record)
        
        return execution_record
    
    async def execute_plan(self, plan: Dict[str, Any], task: str = None) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        """执行完整计划
        
        Args:
            plan: 计划信息，包含多个步骤
            task: 原始任务描述，可选
            
        Returns:
            Tuple[str, List[Dict[str, Any]], Dict[str, Any]]: (执行结果, 执行历史, 元数据)
        """
        # 获取计划步骤
        steps = plan.get('steps', [])
        if not steps:
            error_message = "计划没有包含执行步骤"
            self.chat_history.append({"role": "system", "content": error_message})
            return error_message, self.chat_history, {"error": error_message, "task_completed": False}
            
        # 保存计划分析和预期结果
        plan_analysis = plan.get('analysis', '')
        expected_result = plan.get('expected_result', '')
        # 初始化执行历史和结果列表
        self.execution_history = []
        all_results = []
        total_token_count = 0
        execution_status = "completed"
        
        # 如果有原始任务描述，记录到聊天历史
        if task:
            self.chat_history.append({"role": "user", "content": f"请执行以下任务：{task}"})
            
        # 如果有计划分析，记录到聊天历史
        if plan_analysis:
            self.chat_history.append({"role": "assistant", "content": f"任务分析：{plan_analysis}"})
        
        # 实时记录执行进度
        progress_message = f"开始执行计划，共{len(steps)}个步骤"
        self.chat_history.append({"role": "system", "content": progress_message})
        
        # 执行每一个步骤
        for i, step in enumerate(steps):
            try:
                # 记录当前步骤
                step_message = f"正在执行步骤 {i+1}/{len(steps)}: {step.get('description', '')}"
                self.chat_history.append({"role": "system", "content": step_message})
                
                # 执行步骤
                step_result = await self.execute_step(step)
                self.execution_history.append(step_result)
                
                # 将步骤结果添加到聊天历史
                result_brief = step_result.get('result', '')
                if isinstance(result_brief, str) and len(result_brief) > 200:
                    result_brief = result_brief[:200] + "..."
                    
                self.chat_history.append({"role": "assistant", "content": f"步骤 {i+1} 结果: {result_brief}"})
                
                # 收集所有结果
                all_results.append(step_result.get('result', ''))
                
            except Exception as e:
                error_message = f"执行步骤 {i+1} 时出错: {str(e)}"
                self.chat_history.append({"role": "system", "content": error_message})
                execution_status = "failed"
                break
        
        # 生成最终结果摘要
        summary_prompt = "请根据以下信息生成结果摘要:\n"
        summary_prompt += f"\n原始任务: {task or '(未提供)'}\n"
        summary_prompt += f"\n计划分析: {plan_analysis or '(未提供)'}\n"
        summary_prompt += "\n执行结果:\n"
        
        for i, result in enumerate(all_results):
            result_text = result
            if isinstance(result_text, str) and len(result_text) > 300:
                result_text = result_text[:300] + "..."
            summary_prompt += f"\n步骤 {i+1}: {result_text}"
            
        summary_prompt += f"\n\n预期结果: {expected_result or '(未提供)'}\n"
        summary_prompt += "\n请提供一个全面的结果摘要，包括主要发现和结论。"
        
        # 获取摘要
        summary = await self.chat(summary_prompt)
        
        # 构造元数据
        metadata = {
            "token_usage": self.token_usage,
            "execution_status": execution_status,
            "steps_total": len(steps),
            "steps_completed": len(self.execution_history),
            "plan": plan
        }
        
        return summary, self.chat_history, metadata
        
    async def run_task(self, task: str, plan: Dict[str, Any] = None, tools: List[Any] = None, **kwargs) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        """执行任务
        
        Args:
            task: 任务描述
            plan: 任务执行计划，如果为None，则直接执行任务
            tools: 可用工具列表
            **kwargs: 额外参数
            
        Returns:
            Tuple[str, List[Dict[str, Any]], Dict[str, Any]]: (结果, 交互历史, 元数据)
        """
        # 添加工具
        if tools:
            self.add_tools(tools)
            
        # 检查是否有计划
        if plan:
            # 执行预定义计划
            result, history, metadata = await self.execute_plan(plan, task)
            return result, history, metadata
        
        # 如果需要执行一个单一步骤
        if kwargs.get("single_step", False):
            step = {
                "description": task,
                "tool": kwargs.get("tool"),
                "parameters": kwargs.get("parameters", {})
            }
            step_result = await self.execute_step(step)
            return step_result.get("result", ""), self.chat_history, {
                "step_result": step_result,
                "token_usage": self.token_usage
            }
            
        # 如果没有计划，直接执行任务
        return await super().run_task(task, tools, **kwargs)
