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
        
        # 构建执行提示
        prompt = f"执行步骤: {description}"
        if tool_name:
            prompt += f"\n使用工具: {tool_name}"
            
        # 如果有指定工具且工具可用，尝试使用工具执行
        result = None
        if tool_name and tool_name in self.tool_map:
            try:
                tool = self.tool_map[tool_name]
                # 生成工具使用提示
                tool_prompt = f"请详细说明如何使用{tool_name}工具执行以下任务：\n{description}"
                tool_guidance = await self.chat(tool_prompt)
                
                # 实际执行工具（框架搭建阶段为模拟执行）
                # result = await tool(description)
                result = f"使用{tool_name}工具模拟执行结果: 已完成'{description}'"
            except Exception as e:
                result = f"工具执行失败: {str(e)}"
        
        # 如果没有工具或工具执行失败，使用智能体直接回答
        if not result:
            result = await self.chat(prompt)
            
        # 记录执行历史
        execution_record = {
            'step': description,
            'tool': tool_name,
            'result': result
        }
        self.execution_history.append(execution_record)
        
        return execution_record
    
    async def execute_plan(self, plan: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        """执行完整计划
        
        Args:
            plan: 任务执行计划，包含步骤列表
            
        Returns:
            Tuple[str, List[Dict[str, Any]]]: (执行摘要, 执行历史)
        """
        steps = plan.get('steps', [])
        self.execution_history = []
        
        for step in steps:
            await self.execute_step(step)
            
        # 生成执行摘要
        summary_prompt = (
            "请根据以下执行历史，生成简洁的执行摘要:\n\n" + 
            "\n".join([f"步骤: {record['step']}\n结果: {record['result']}" 
                      for record in self.execution_history])
        )
        
        summary = await self.chat(summary_prompt)
        
        return summary, self.execution_history
    
    async def run_task(self, task: str, plan: Dict[str, Any] = None, tools: List[Any] = None, **kwargs) -> Tuple[str, List[Dict[str, str]], Dict[str, Any]]:
        """执行任务
        
        Args:
            task: 任务描述
            plan: 预定义的执行计划，如果为None，则直接执行任务
            tools: 可用工具列表
            
        Returns:
            Tuple[str, List[Dict[str, str]], Dict[str, Any]]: (结果, 交互历史, 元数据)
        """
        if tools:
            self.add_tools(tools)
            
        if plan:
            # 执行预定义计划
            summary, execution_history = await self.execute_plan(plan)
            
            # 构建聊天历史
            chat_history = [
                {"role": "user", "content": task},
                {"role": "assistant", "content": summary}
            ]
            
            # 计算token消耗（简化实现）
            token_count = len(task.split()) + len(summary.split())
            
            return summary, chat_history, {"token_count": token_count, "execution_history": execution_history}
        else:
            # 直接执行任务
            response = await self.chat(task)
            
            chat_history = [
                {"role": "user", "content": task},
                {"role": "assistant", "content": response}
            ]
            
            token_count = len(task.split()) + len(response.split())
            
            return response, chat_history, {"token_count": token_count}
