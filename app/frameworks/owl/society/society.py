"""
Society framework for OWL
"""

from typing import Any, Dict, List, Optional, Tuple, Union, Callable
import json
import asyncio
import uuid
from abc import ABC, abstractmethod

from app.frameworks.owl.agents.base import BaseAgent
from app.frameworks.owl.agents.planner import PlannerAgent
from app.frameworks.owl.agents.executor import ExecutorAgent
from app.utils.common.logger import get_logger
from .expert_team import ExpertTeam

logger = get_logger(__name__)

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
        self.id = str(uuid.uuid4())  # 唯一ID
        self.agents = {}  # 智能体名称到实例的映射
        self.workflow = {}  # 工作流定义
        self.roles = {}  # 角色定义
        self.collaboration_mode = "default"  # 协作模式：default, expert_team, debate, workflow
        self.chat_history = []  # 交互历史
        self.metadata = {}  # 元数据
        
    def add_agent(self, name: str, agent: BaseAgent, role_description: Optional[str] = None, expertise: Optional[str] = None) -> None:
        """添加智能体到社会
        
        Args:
            name: 智能体名称
            agent: 智能体实例
            role_description: 角色描述
            expertise: 专长领域
        """
        self.agents[name] = {
            "instance": agent,
            "role": role_description or f"{name}智能体",
            "expertise": expertise,
            "contributions": [],
            "added_at": asyncio.get_event_loop().time()
        }
        
    def set_workflow(self, workflow_definition: Dict[str, Any]) -> None:
        """设置工作流定义
        
        Args:
            workflow_definition: 工作流定义
        """
        self.workflow = workflow_definition
        
    async def define_role(self, role_name: str, description: str, required_skills: List[str] = None, tools_access: List[str] = None) -> None:
        """定义角色
        
        Args:
            role_name: 角色名称
            description: 角色描述
            required_skills: 所需技能
            tools_access: 可访问的工具
        """
        self.roles[role_name] = {
            "description": description,
            "required_skills": required_skills or [],
            "tools_access": tools_access or [],
            "agents": []  # 分配到该角色的智能体列表
        }
        
    def assign_role(self, agent_name: str, role_name: str) -> None:
        """将智能体分配到角色
        
        Args:
            agent_name: 智能体名称
            role_name: 角色名称
        """
        if agent_name not in self.agents:
            raise ValueError(f"智能体'{agent_name}'不存在")
            
        if role_name not in self.roles:
            raise ValueError(f"角色'{role_name}'不存在")
            
        # 将智能体添加到角色
        self.roles[role_name]["agents"].append(agent_name)
        
        # 更新智能体角色信息
        self.agents[agent_name]["role"] = role_name
        
    def set_collaboration_mode(self, mode: str) -> None:
        """设置协作模式
        
        Args:
            mode: 协作模式，可选值: default, expert_team, debate, workflow
        """
        valid_modes = ["default", "expert_team", "debate", "workflow"]
        if mode not in valid_modes:
            raise ValueError(f"无效的协作模式: {mode}，有效值为: {', '.join(valid_modes)}")
            
        self.collaboration_mode = mode
        
    async def run_task(self, task: str, tools: Optional[List[Any]] = None, **kwargs) -> Tuple[str, List[Dict[str, str]], Dict[str, Any]]:
        """处理任务，利用社会中的多个智能体协作
        
        Args:
            task: 任务描述
            tools: 可用工具列表
            **kwargs: 额外参数，如:
                - max_rounds: 最大交互轮数
                - parallel: 是否并行执行
                - force_mode: 强制使用指定协作模式
            
        Returns:
            Tuple[str, List[Dict[str, str]], Dict[str, Any]]: (结果, 交互历史, 元数据)
        """
        if not self.agents:
            raise ValueError("社会中没有智能体")
            
        # 获取强制模式
        force_mode = kwargs.get("force_mode")
        mode = force_mode or self.collaboration_mode
            
        # 根据模式选择协作方式
        if mode == "workflow" and self.workflow:
            # 使用预定义工作流处理任务
            return await self._run_with_workflow(task, tools, **kwargs)
        elif mode == "expert_team":
            # 使用专家团队模式
            return await self._run_with_expert_team(task, tools, **kwargs)
        elif mode == "debate":
            # 使用辩论模式
            return await self._run_with_debate(task, tools, **kwargs)
        else:
            # 使用默认的规划-执行工作流
            return await self._run_with_planner_executor(task, tools, **kwargs)
    
    async def _run_with_planner_executor(self, task: str, tools: Optional[List[Any]] = None, **kwargs) -> Tuple[str, List[Dict[str, str]], Dict[str, Any]]:
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
    
    async def _run_with_workflow(self, task: str, tools: Optional[List[Any]] = None, **kwargs) -> Tuple[str, List[Dict[str, str]], Dict[str, Any]]:
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
        
    async def _run_with_expert_team(self, task: str, tools: Optional[List[Any]] = None, **kwargs) -> Tuple[str, List[Dict[str, str]], Dict[str, Any]]:
        """使用专家团队模式处理任务
        
        Args:
            task: 任务描述
            tools: 可用工具列表
            **kwargs: 额外参数，包括:
                - parallel: 是否并行获取专家意见，默认True
                
        Returns:
            Tuple[str, List[Dict[str, str]], Dict[str, Any]]: (结果, 交互历史, 元数据)
        """
        # 检查是否有足够的智能体
        if len(self.agents) < 2:
            logger.warning("专家团队模式需要至少两个智能体，将回退到默认模式")
            return await self._run_with_planner_executor(task, tools, **kwargs)
        
        # 获取是否并行执行
        parallel = kwargs.get("parallel", True)
        
        # 准备专家
        experts = []
        for name, agent_info in self.agents.items():
            if isinstance(agent_info["instance"], PlannerAgent) or isinstance(agent_info["instance"], ExecutorAgent):
                continue  # 跳过规划者和执行者
            experts.append((name, agent_info))
        
        # 如果没有足够的专家，添加默认专家
        if len(experts) < 2:
            from app.config import settings
            for i in range(2 - len(experts)):
                expert_name = f"expert_{i+1}"
                expert = BaseAgent(settings.owl.default_model)
                expertise = f"领域{i+1}专家"
                self.add_agent(expert_name, expert, expertise=expertise)
                experts.append((expert_name, self.agents[expert_name]))
        
        # 创建主持人（如果没有）
        moderator = None
        for name, agent_info in self.agents.items():
            if agent_info.get("role") == "moderator":
                moderator = agent_info["instance"]
                break
                
        if not moderator:
            from app.config import settings
            moderator_name = "moderator"
            moderator = BaseAgent(settings.owl.default_model)
            moderator.set_system_message("你是一位公正的主持人，负责综合各位专家的意见，形成最终解决方案。")
            self.add_agent(moderator_name, moderator, role_description="moderator")
            moderator = self.agents[moderator_name]["instance"]
        
        # 为每个专家设置背景
        for name, agent_info in experts:
            expert = agent_info["instance"]
            expertise = agent_info.get("expertise", "通用领域")
            if tools:
                expert.add_tools(tools)
            # 设置系统提示
            expert.set_system_message(f"你是{name}，专长领域是{expertise}。你的任务是提供专业意见解决问题。")
        
        # 获取每个专家的意见
        opinions = []
        chat_histories = []
        total_tokens = 0
        
        try:
            if parallel:
                # 并行获取所有专家意见
                tasks = []
                for name, agent_info in experts:
                    expert = agent_info["instance"]
                    tasks.append(expert.run_task(task, tools=tools))
                    
                # 等待所有任务完成
                results = await asyncio.gather(*tasks)
                
                # 处理结果
                for i, (name, _) in enumerate(experts):
                    opinion, chat_history, metadata = results[i]
                    opinions.append({
                        "expert": name,
                        "opinion": opinion,
                        "metadata": metadata
                    })
                    chat_histories.extend(chat_history)
                    total_tokens += metadata.get("token_count", 0)
            else:
                # 顺序获取专家意见
                for name, agent_info in experts:
                    expert = agent_info["instance"]
                    opinion, chat_history, metadata = await expert.run_task(task, tools=tools)
                    
                    opinions.append({
                        "expert": name,
                        "opinion": opinion,
                        "metadata": metadata
                    })
                    
                    chat_histories.extend(chat_history)
                    total_tokens += metadata.get("token_count", 0)
            
            # 让主持人综合意见
            synthesis_input = f"任务: {task}\n\n各位专家意见:\n"
            
            for opinion_data in opinions:
                name = opinion_data["expert"]
                expert_opinion = opinion_data["opinion"]
                expertise = self.agents[name].get("expertise", "通用领域") if name in self.agents else "未知"
                
                synthesis_input += f"\n专家: {name} (专长: {expertise})\n"
                synthesis_input += f"意见: {expert_opinion}\n"
                synthesis_input += "-" * 40 + "\n"
                
            synthesis_input += "\n请综合以上专家意见，给出最终解决方案。"
            
            # 获取主持人的综合意见
            final_result, moderator_chat_history, moderator_metadata = await moderator.run_task(synthesis_input)
            
            # 更新聊天历史和token计数
            chat_histories.extend(moderator_chat_history)
            total_tokens += moderator_metadata.get("token_count", 0)
            
            # 构建元数据
            metadata = {
                "token_count": total_tokens,
                "opinions": opinions,
                "expert_count": len(experts),
                "execution_mode": "parallel" if parallel else "sequential"
            }
            
            return final_result, chat_histories, metadata
            
        except Exception as e:
            logger.error(f"专家团队模式执行出错: {str(e)}", exc_info=True)
            # 回退到默认模式
            logger.info("回退到默认的规划-执行模式")
            return await self._run_with_planner_executor(task, tools, **kwargs)
    
    async def _run_with_debate(self, task: str, tools: Optional[List[Any]] = None, **kwargs) -> Tuple[str, List[Dict[str, str]], Dict[str, Any]]:
        """使用辩论模式处理任务
        
        Args:
            task: 任务描述
            tools: 可用工具列表
            **kwargs: 额外参数，包括:
                - rounds: 辩论轮数，默认3
                
        Returns:
            Tuple[str, List[Dict[str, str]], Dict[str, Any]]: (结果, 交互历史, 元数据)
        """
        # 检查是否有足够的智能体
        if len(self.agents) < 2:
            logger.warning("辩论模式需要至少两个智能体，将回退到默认模式")
            return await self._run_with_planner_executor(task, tools, **kwargs)
        
        # 获取辩论轮数
        rounds = kwargs.get("rounds", 3)
        
        # 准备辩手
        debaters = []
        for name, agent_info in self.agents.items():
            if isinstance(agent_info["instance"], PlannerAgent) or isinstance(agent_info["instance"], ExecutorAgent):
                continue  # 跳过规划者和执行者
            if agent_info.get("role") == "moderator":
                continue  # 跳过主持人
            debaters.append((name, agent_info))
        
        # 如果没有足够的辩手，添加默认辩手
        if len(debaters) < 2:
            from app.config import settings
            perspectives = ["正方", "反方"]
            for i in range(2 - len(debaters)):
                debater_name = f"debater_{i+1}"
                debater = BaseAgent(settings.owl.default_model)
                self.add_agent(debater_name, debater, role_description=perspectives[i])
                debaters.append((debater_name, self.agents[debater_name]))
        
        # 创建主持人（如果没有）
        moderator = None
        for name, agent_info in self.agents.items():
            if agent_info.get("role") == "moderator":
                moderator = agent_info["instance"]
                break
                
        if not moderator:
            from app.config import settings
            moderator_name = "moderator"
            moderator = BaseAgent(settings.owl.default_model)
            moderator.set_system_message("你是一位公正的主持人，负责引导辩论并总结辩论结果。")
            self.add_agent(moderator_name, moderator, role_description="moderator")
            moderator = self.agents[moderator_name]["instance"]
        
        # 为每个辩手设置背景
        for i, (name, agent_info) in enumerate(debaters):
            debater = agent_info["instance"]
            perspective = agent_info.get("role") or f"辩手{i+1}"
            if tools:
                debater.add_tools(tools)
            # 设置系统提示
            debater.set_system_message(f"你是{name}，在辩论中的角色是{perspective}。你的任务是提出观点并回应其他辩手的观点。")
        
        try:
            # 辩论历史
            debate_history = []
            chat_histories = []
            total_tokens = 0
            
            # 当前讨论内容
            current_topic = task
            
            # 多轮辩论
            for round_num in range(rounds):
                logger.info(f"开始第{round_num + 1}轮辩论")
                round_opinions = []
                
                # 收集本轮所有辩手意见
                for name, agent_info in debaters:
                    debater = agent_info["instance"]
                    
                    # 构建输入，包含上一轮辩论历史
                    input_text = f"任务: {task}\n\n"
                    
                    # 添加之前的辩论记录
                    if debate_history:
                        input_text += "以下是之前的辩论记录:\n\n"
                        for prev_round in debate_history:
                            for opinion in prev_round:
                                debater_name = opinion["debater"]
                                debater_opinion = opinion["opinion"]
                                input_text += f"{debater_name}: {debater_opinion}\n\n"
                    
                    # 当前讨论要求
                    input_text += f"当前讨论主题: {current_topic}\n"
                    input_text += f"请你作为{name}提供你的观点。"
                    
                    # 获取辩手意见
                    opinion, chat_history, metadata = await debater.run_task(input_text)
                    
                    round_opinions.append({
                        "debater": name,
                        "opinion": opinion,
                        "metadata": metadata
                    })
                    
                    chat_histories.extend(chat_history)
                    total_tokens += metadata.get("token_count", 0)
                    
                # 记录本轮辩论
                debate_history.append(round_opinions)
                
                # 让主持人总结本轮讨论并制定下一轮主题
                if round_num < rounds - 1:  # 不是最后一轮
                    summary_input = f"任务: {task}\n\n第{round_num + 1}轮辩论总结:\n\n"
                    
                    for opinion in round_opinions:
                        debater_name = opinion["debater"]
                        debater_opinion = opinion["opinion"]
                        summary_input += f"{debater_name}: {debater_opinion}\n\n"
                        
                    summary_input += "请总结本轮讨论，并提出下一轮需要讨论的问题或争议点。"
                    
                    summary, moderator_chat_history, moderator_metadata = await moderator.run_task(summary_input)
                    chat_histories.extend(moderator_chat_history)
                    total_tokens += moderator_metadata.get("token_count", 0)
                    
                    # 提取下一轮主题
                    current_topic = summary.split("下一轮讨论:")[-1].strip() if "下一轮讨论:" in summary else summary
            
            # 让主持人给出最终结论
            final_input = f"任务: {task}\n\n完整辩论记录:\n\n"
            
            for round_num, round_opinions in enumerate(debate_history):
                final_input += f"--- 第{round_num + 1}轮辩论 ---\n\n"
                
                for opinion in round_opinions:
                    debater_name = opinion["debater"]
                    debater_opinion = opinion["opinion"]
                    final_input += f"{debater_name}: {debater_opinion}\n\n"
                    
            final_input += "请综合以上辩论，给出最终解决方案。"
            
            # 获取主持人的最终意见
            final_result, final_chat_history, final_metadata = await moderator.run_task(final_input)
            
            # 更新聊天历史和token计数
            chat_histories.extend(final_chat_history)
            total_tokens += final_metadata.get("token_count", 0)
            
            # 构建元数据
            metadata = {
                "token_count": total_tokens,
                "rounds": rounds,
                "debate_history": debate_history,
                "debater_count": len(debaters)
            }
            
            return final_result, chat_histories, metadata
                
        except Exception as e:
            logger.error(f"辩论模式执行出错: {str(e)}", exc_info=True)
            # 回退到默认模式
            logger.info("回退到默认的规划-执行模式")
            return await self._run_with_planner_executor(task, tools, **kwargs)
