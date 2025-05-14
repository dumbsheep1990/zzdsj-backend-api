from typing import Any, Dict, List, Optional, Tuple, Union
import asyncio

from app.frameworks.owl.agents.base import BaseAgent
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ExpertTeam:
    """专家团队协作模式，实现多专家角色协作"""
    
    def __init__(self, name: str, description: str = ""):
        """初始化专家团队
        
        Args:
            name: 团队名称
            description: 团队描述
        """
        self.name = name
        self.description = description
        self.experts = {}  # 专家名称到实例的映射
        self.moderator = None  # 主持人智能体，负责协调
        self.chat_history = []  # 交互历史
        
    def add_expert(self, name: str, agent: BaseAgent, expertise: str) -> None:
        """添加专家到团队
        
        Args:
            name: 专家名称
            agent: 专家智能体实例
            expertise: 专长领域
        """
        self.experts[name] = {
            "instance": agent,
            "expertise": expertise,
            "contributions": []  # 该专家的贡献记录
        }
        
    def set_moderator(self, agent: BaseAgent) -> None:
        """设置主持人智能体
        
        Args:
            agent: 主持人智能体实例
        """
        self.moderator = agent
        
    async def _prepare_experts(self, task: str, tools: Optional[List[Any]] = None) -> None:
        """准备专家智能体，设置工具和任务背景
        
        Args:
            task: 任务描述
            tools: 可用工具列表
        """
        for expert_name, expert_info in self.experts.items():
            expert = expert_info["instance"]
            
            # 设置工具
            if tools:
                expert.add_tools(tools)
                
            # 设置专家背景
            expertise = expert_info["expertise"]
            background = f"你是{expert_name}，专长领域是{expertise}。你的任务是：{task}"
            expert.set_system_message(background)
            
    async def _get_expert_opinion(self, expert_name: str, input_text: str) -> Dict[str, Any]:
        """获取专家意见
        
        Args:
            expert_name: 专家名称
            input_text: 输入文本
            
        Returns:
            Dict[str, Any]: 专家意见和元数据
        """
        if expert_name not in self.experts:
            raise ValueError(f"专家'{expert_name}'不存在")
            
        expert_info = self.experts[expert_name]
        expert = expert_info["instance"]
        
        # 获取专家意见
        try:
            opinion, chat_history, metadata = await expert.run_task(input_text)
            
            # 记录贡献
            contribution = {
                "input": input_text,
                "opinion": opinion,
                "timestamp": asyncio.get_event_loop().time()
            }
            expert_info["contributions"].append(contribution)
            
            # 更新聊天历史
            self.chat_history.extend(chat_history)
            
            return {
                "expert": expert_name,
                "opinion": opinion,
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"获取专家'{expert_name}'意见时出错: {str(e)}", exc_info=True)
            return {
                "expert": expert_name,
                "error": str(e),
                "opinion": f"无法获取专家意见：{str(e)}"
            }
            
    async def _synthesize_opinions(self, opinions: List[Dict[str, Any]], task: str) -> str:
        """合成专家意见
        
        Args:
            opinions: 专家意见列表
            task: 原始任务
            
        Returns:
            str: 合成的意见
        """
        if not self.moderator:
            # 创建默认主持人
            from app.config import settings
            from app.frameworks.owl.agents.base import BaseAgent
            
            self.moderator = BaseAgent(settings.owl.default_model)
            self.moderator.set_system_message("你是一位公正的主持人，负责综合各位专家的意见，形成最终解决方案。")
            
        # 构建输入
        input_text = f"原始任务: {task}\n\n专家意见:\n"
        for opinion in opinions:
            expert_name = opinion["expert"]
            expert_opinion = opinion.get("opinion", "未提供意见")
            expert_expertise = self.experts[expert_name]["expertise"] if expert_name in self.experts else "未知"
            
            input_text += f"\n专家: {expert_name} (专长: {expert_expertise})\n"
            input_text += f"意见: {expert_opinion}\n"
            input_text += "-" * 40 + "\n"
            
        input_text += "\n请综合以上专家意见，给出最终解决方案。"
        
        # 获取主持人的综合意见
        synthesis, chat_history, metadata = await self.moderator.run_task(input_text)
        
        # 更新聊天历史
        self.chat_history.extend(chat_history)
        
        return synthesis
    
    async def collaborate(self, task: str, tools: Optional[List[Any]] = None, parallel: bool = True) -> Tuple[str, List[Dict[str, str]], Dict[str, Any]]:
        """让专家团队协作解决任务
        
        Args:
            task: 任务描述
            tools: 可用工具列表
            parallel: 是否并行获取专家意见
            
        Returns:
            Tuple[str, List[Dict[str, str]], Dict[str, Any]]: (结果, 交互历史, 元数据)
        """
        if not self.experts:
            raise ValueError("专家团队中没有专家")
            
        # 准备专家
        await self._prepare_experts(task, tools)
        
        # 获取专家意见
        opinions = []
        
        if parallel:
            # 并行获取所有专家意见
            tasks = []
            for expert_name in self.experts.keys():
                tasks.append(self._get_expert_opinion(expert_name, task))
                
            # 等待所有任务完成
            opinions = await asyncio.gather(*tasks)
        else:
            # 顺序获取专家意见
            for expert_name in self.experts.keys():
                opinion = await self._get_expert_opinion(expert_name, task)
                opinions.append(opinion)
                
        # 合成意见
        final_result = await self._synthesize_opinions(opinions, task)
        
        # 构建元数据
        metadata = {
            "opinions": opinions,
            "expert_count": len(self.experts),
            "execution_mode": "parallel" if parallel else "sequential"
        }
        
        return final_result, self.chat_history, metadata
        
    async def debate(self, task: str, rounds: int = 3, tools: Optional[List[Any]] = None) -> Tuple[str, List[Dict[str, str]], Dict[str, Any]]:
        """让专家团队进行辩论，多轮讨论解决问题
        
        Args:
            task: 任务描述
            rounds: 辩论轮数
            tools: 可用工具列表
            
        Returns:
            Tuple[str, List[Dict[str, str]], Dict[str, Any]]: (结果, 交互历史, 元数据)
        """
        if not self.experts:
            raise ValueError("专家团队中没有专家")
            
        if len(self.experts) < 2:
            raise ValueError("辩论至少需要两位专家")
            
        # 准备专家
        await self._prepare_experts(task, tools)
        
        # 辩论历史
        debate_history = []
        
        # 当前讨论内容
        current_topic = task
        
        # 多轮辩论
        for round_num in range(rounds):
            logger.info(f"开始第{round_num + 1}轮辩论")
            round_opinions = []
            
            # 收集本轮所有专家意见
            for expert_name, expert_info in self.experts.items():
                # 构建输入，包含上一轮辩论历史
                input_text = f"任务: {task}\n\n"
                
                # 添加之前的辩论记录
                if debate_history:
                    input_text += "以下是之前的辩论记录:\n\n"
                    for prev_round in debate_history:
                        for opinion in prev_round:
                            expert = opinion["expert"]
                            text = opinion["opinion"]
                            input_text += f"{expert}: {text}\n"
                    input_text += "\n"
                
                # 当前讨论要求
                input_text += f"当前讨论主题: {current_topic}\n"
                input_text += f"请你作为{expert_name}（{expert_info['expertise']}专家）提供你的观点。"
                
                # 获取专家意见
                opinion = await self._get_expert_opinion(expert_name, input_text)
                round_opinions.append(opinion)
                
            # 记录本轮辩论
            debate_history.append(round_opinions)
            
            # 让主持人总结本轮讨论并制定下一轮主题
            if round_num < rounds - 1:  # 不是最后一轮
                summary_input = f"任务: {task}\n\n第{round_num + 1}轮辩论总结:\n\n"
                
                for opinion in round_opinions:
                    expert_name = opinion["expert"]
                    expert_opinion = opinion.get("opinion", "未提供意见")
                    summary_input += f"{expert_name}: {expert_opinion}\n\n"
                    
                summary_input += "请总结本轮讨论，并提出下一轮需要讨论的问题或争议点。"
                
                if self.moderator:
                    summary, chat_history, _ = await self.moderator.run_task(summary_input)
                    self.chat_history.extend(chat_history)
                    
                    # 提取下一轮主题
                    current_topic = summary.split("下一轮讨论:")[-1].strip() if "下一轮讨论:" in summary else summary
                else:
                    # 没有主持人，使用上一轮的争议点作为下一轮主题
                    current_topic = f"请继续讨论任务'{task}'的解决方案"
                    
        # 让主持人给出最终结论
        final_input = f"任务: {task}\n\n完整辩论记录:\n\n"
        
        for round_num, round_opinions in enumerate(debate_history):
            final_input += f"--- 第{round_num + 1}轮辩论 ---\n\n"
            
            for opinion in round_opinions:
                expert_name = opinion["expert"]
                expert_opinion = opinion.get("opinion", "未提供意见")
                final_input += f"{expert_name}: {expert_opinion}\n\n"
                
        final_input += "请综合以上辩论，给出最终解决方案。"
        
        # 获取主持人的最终意见
        if not self.moderator:
            # 创建默认主持人
            from app.config import settings
            from app.frameworks.owl.agents.base import BaseAgent
            
            self.moderator = BaseAgent(settings.owl.default_model)
            self.moderator.set_system_message("你是一位公正的主持人，负责综合各位专家的辩论，形成最终解决方案。")
            
        final_result, chat_history, synthesis_metadata = await self.moderator.run_task(final_input)
        self.chat_history.extend(chat_history)
        
        # 构建元数据
        metadata = {
            "rounds": rounds,
            "debate_history": debate_history,
            "expert_count": len(self.experts),
            "token_count": synthesis_metadata.get("token_count", 0)
        }
        
        return final_result, self.chat_history, metadata
