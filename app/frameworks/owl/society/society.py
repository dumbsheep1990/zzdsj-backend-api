from typing import Any, Dict, List, Optional, Tuple, Union
import json

from app.frameworks.owl.agents.base import BaseAgent
from app.frameworks.owl.agents.planner import PlannerAgent
from app.frameworks.owl.agents.executor import ExecutorAgent

class Society:
    """智能体社会，管理多智能体协作"""
    
    def __init__(self, name: str, description: str = ""):
        """初始化社会
        
        Args:
            name: 社会名称
            description: 描述
        """
        self.name = name
        self.description = description
        self.agents = {}  # 智能体名称到实例的映射
        self.workflow = {}  # 工作流定义
        
    def add_agent(self, name: str, agent: BaseAgent, role_description: Optional[str] = None) -> None:
        """添加智能体到社会
        
        Args:
            name: 智能体名称
            agent: 智能体实例
            role_description: 角色描述
        """
        self.agents[name] = {
            "instance": agent,
            "role": role_description or f"{name}智能体"
        }
        
    def set_workflow(self, workflow_definition: Dict[str, Any]) -> None:
        """设置工作流定义
        
        Args:
            workflow_definition: 工作流定义
        """
        self.workflow = workflow_definition
        
    async def run_task(self, task: str, tools: Optional[List[Any]] = None) -> Tuple[str, List[Dict[str, str]], Dict[str, Any]]:
        """处理任务，利用社会中的多个智能体协作
        
        Args:
            task: 任务描述
            tools: 可用工具列表
            
        Returns:
            Tuple[str, List[Dict[str, str]], Dict[str, Any]]: (结果, 交互历史, 元数据)
        """
        if not self.agents:
            raise ValueError("社会中没有智能体")
            
        if self.workflow:
            # 使用预定义工作流处理任务
            return await self._run_with_workflow(task, tools)
        else:
            # 使用默认的规划-执行工作流
            return await self._run_with_planner_executor(task, tools)
    
    async def _run_with_planner_executor(self, task: str, tools: Optional[List[Any]] = None) -> Tuple[str, List[Dict[str, str]], Dict[str, Any]]:
        """使用规划-执行模式处理任务
        
        Args:
            task: 任务描述
            tools: 可用工具列表
            
        Returns:
            Tuple[str, List[Dict[str, str]], Dict[str, Any]]: (结果, 交互历史, 元数据)
        """
        # 检查是否有规划者和执行者
        planner = None
        executor = None
        
        # 从已有智能体中查找规划者和执行者
        for name, agent_info in self.agents.items():
            agent = agent_info["instance"]
            if isinstance(agent, PlannerAgent):
                planner = agent
            elif isinstance(agent, ExecutorAgent):
                executor = agent
                
        # 如果没有找到合适的智能体，则创建
        if not planner:
            from app.config import settings
            planner = PlannerAgent(settings.owl.planner_model)
            self.add_agent("planner", planner, "任务规划专家")
            
        if not executor:
            from app.config import settings
            executor = ExecutorAgent(settings.owl.executor_model)
            self.add_agent("executor", executor, "任务执行专家")
            
        # 添加工具
        if tools:
            planner.add_tools(tools)
            executor.add_tools(tools)
            
        # 1. 规划阶段
        plan = await planner.create_plan(task)
        
        # 2. 执行阶段
        result, chat_history, metadata = await executor.run_task(task, plan=plan)
        
        # 添加规划信息到元数据
        metadata["plan"] = plan
        
        return result, chat_history, metadata
    
    async def _run_with_workflow(self, task: str, tools: Optional[List[Any]] = None) -> Tuple[str, List[Dict[str, str]], Dict[str, Any]]:
        """使用预定义工作流处理任务
        
        Args:
            task: 任务描述
            tools: 可用工具列表
            
        Returns:
            Tuple[str, List[Dict[str, str]], Dict[str, Any]]: (结果, 交互历史, 元数据)
        """
        # 获取工作流步骤
        steps = self.workflow.get("steps", [])
        if not steps:
            raise ValueError("工作流没有定义步骤")
            
        # 工作流执行历史
        execution_history = []
        final_result = None
        combined_chat_history = []
        total_tokens = 0
        
        # 上下文，用于在步骤之间传递信息
        context = {"task": task, "tools": tools}
        
        # 执行每个步骤
        for i, step in enumerate(steps):
            step_name = step.get("name", f"步骤{i+1}")
            agent_name = step.get("agent")
            input_template = step.get("input", "{task}")
            
            if not agent_name or agent_name not in self.agents:
                raise ValueError(f"步骤 '{step_name}' 指定的智能体 '{agent_name}' 不存在")
                
            # 获取智能体
            agent_info = self.agents[agent_name]
            agent = agent_info["instance"]
            
            # 构建输入
            input_text = input_template.format(**context)
            
            # 执行智能体任务
            step_result, step_chat_history, step_metadata = await agent.run_task(input_text, tools=tools)
            
            # 更新上下文
            context[f"result_{i}"] = step_result
            context["last_result"] = step_result
            
            # 记录执行历史
            execution_record = {
                "step": step_name,
                "agent": agent_name,
                "input": input_text,
                "result": step_result,
                "metadata": step_metadata
            }
            execution_history.append(execution_record)
            
            # 更新聊天历史和token计数
            combined_chat_history.extend(step_chat_history)
            total_tokens += step_metadata.get("token_count", 0)
            
            # 如果是最后一步，保存结果
            if i == len(steps) - 1:
                final_result = step_result
                
        # 如果没有得到最终结果，则使用最后一步的结果
        if final_result is None and execution_history:
            final_result = execution_history[-1]["result"]
            
        # 如果仍然没有结果，返回错误
        if final_result is None:
            final_result = "工作流执行失败，没有产生结果"
            
        # 构建元数据
        metadata = {
            "token_count": total_tokens,
            "execution_history": execution_history,
            "workflow": self.workflow
        }
        
        return final_result, combined_chat_history, metadata
