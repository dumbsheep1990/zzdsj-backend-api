"""
ZZDSJ高级团队协作管理器

基于Agno框架实现的智能团队协作系统，支持：
- 多专家代理协作
- 动态任务分配
- 智能决策流程
- 实时协作监控

遵循Agno官方最新语法和最佳实践
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import json

try:
    from agno.agent import Agent
    from agno.team import Team
    from agno.models.openai import OpenAIChat
    from agno.models.anthropic import Claude
    from agno.models.google import Gemini
    from agno.tools.duckduckgo import DuckDuckGoTools
    from agno.tools.reasoning import ReasoningTools
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False
    # 创建虚拟类以支持类型提示
    class Agent:
        pass
    
    class Team:
        pass

logger = logging.getLogger(__name__)


class TeamMode(Enum):
    """团队协作模式"""
    COORDINATE = "coordinate"  # 协调模式：有统一协调者
    DEBATE = "debate"          # 辩论模式：多观点讨论
    CONSENSUS = "consensus"    # 共识模式：协商达成一致
    PIPELINE = "pipeline"      # 流水线模式：顺序处理


class AgentRole(Enum):
    """代理角色类型"""
    COORDINATOR = "coordinator"        # 协调者
    RESEARCHER = "researcher"          # 研究专家
    ANALYZER = "analyzer"             # 分析专家
    WRITER = "writer"                 # 写作专家
    REVIEWER = "reviewer"             # 评审专家
    EXECUTOR = "executor"             # 执行专家
    KNOWLEDGE_EXPERT = "knowledge_expert"  # 知识专家
    TECHNICAL_EXPERT = "technical_expert"  # 技术专家


@dataclass
class AgentSpec:
    """代理规格定义"""
    name: str
    role: AgentRole
    description: str
    instructions: List[str]
    tools: List[str]
    model_config: Dict[str, Any]
    capabilities: List[str]
    performance_metrics: Dict[str, float] = None


@dataclass
class TeamSpec:
    """团队规格定义"""
    name: str
    description: str
    mode: TeamMode
    agents: List[AgentSpec]
    success_criteria: str
    coordination_strategy: str
    max_iterations: int = 10
    timeout_seconds: int = 300


@dataclass
class CollaborationResult:
    """协作结果"""
    success: bool
    result: Any
    timestamp: str
    duration_seconds: float
    iterations_used: int
    agent_contributions: Dict[str, Any]
    performance_metrics: Dict[str, float]
    issues: List[str] = None


class ZZDSJTeamCoordinator:
    """ZZDSJ团队协作管理器"""
    
    def __init__(self):
        """初始化团队协作管理器"""
        self.teams: Dict[str, Team] = {}
        self.agent_registry: Dict[str, Agent] = {}
        self.team_specs: Dict[str, TeamSpec] = {}
        
        # 导入模型配置适配器
        from .model_config_adapter import get_model_adapter
        self.model_adapter = get_model_adapter()
        
        # 预定义专家团队模板
        self.predefined_teams = self._initialize_predefined_teams()
        
        # 性能监控
        self.performance_history: List[CollaborationResult] = []
        
        logger.info("ZZDSJ团队协作管理器已初始化")

    def _initialize_predefined_teams(self) -> Dict[str, TeamSpec]:
        """初始化预定义团队模板"""
        return {
            "research_team": TeamSpec(
                name="ZZDSJ研究团队",
                description="专门进行深度研究和信息收集的专家团队",
                mode=TeamMode.COORDINATE,
                agents=[
                    AgentSpec(
                        name="ResearchCoordinator",
                        role=AgentRole.COORDINATOR,
                        description="研究项目协调者，负责任务分配和结果整合",
                        instructions=[
                            "分析研究任务并分配给合适的专家",
                            "监控研究进度并确保质量",
                            "整合各专家的研究结果",
                            "确保研究的全面性和准确性"
                        ],
                        tools=["reasoning", "task_planning"],
                        model_config={"provider": "openai", "model": "gpt-4o"},
                        capabilities=["task_decomposition", "result_synthesis", "quality_control"]
                    ),
                    AgentSpec(
                        name="WebResearcher",
                        role=AgentRole.RESEARCHER,
                        description="网络信息研究专家",
                        instructions=[
                            "使用搜索工具查找最新信息",
                            "评估信息来源的可靠性",
                            "提供详细的搜索结果摘要",
                            "包含完整的引用和链接"
                        ],
                        tools=["duckduckgo_search", "web_crawler"],
                        model_config={"provider": "openai", "model": "gpt-4o"},
                        capabilities=["web_search", "source_verification", "information_extraction"]
                    ),
                    AgentSpec(
                        name="DataAnalyzer",
                        role=AgentRole.ANALYZER,
                        description="数据分析和洞察专家",
                        instructions=[
                            "分析收集到的数据和信息",
                            "识别模式和趋势",
                            "提供深度洞察和建议",
                            "使用推理工具验证结论"
                        ],
                        tools=["reasoning", "data_analysis"],
                        model_config={"provider": "anthropic", "model": "claude-3-5-sonnet-20241022"},
                        capabilities=["pattern_recognition", "statistical_analysis", "insight_generation"]
                    ),
                    AgentSpec(
                        name="KnowledgeExpert",
                        role=AgentRole.KNOWLEDGE_EXPERT,
                        description="领域知识专家",
                        instructions=[
                            "提供专业领域知识",
                            "验证信息的准确性",
                            "补充背景知识和上下文",
                            "确保信息的专业性"
                        ],
                        tools=["knowledge_base", "reasoning"],
                        model_config={"provider": "openai", "model": "gpt-4o"},
                        capabilities=["domain_expertise", "fact_verification", "context_provision"]
                    )
                ],
                success_criteria="提供全面、准确、有洞察力的研究报告",
                coordination_strategy="coordinator_delegation",
                max_iterations=8,
                timeout_seconds=300
            ),
            
            "content_creation_team": TeamSpec(
                name="ZZDSJ内容创作团队",
                description="专门进行内容创作和编辑的专家团队",
                mode=TeamMode.PIPELINE,
                agents=[
                    AgentSpec(
                        name="ContentPlanner",
                        role=AgentRole.COORDINATOR,
                        description="内容策划专家",
                        instructions=[
                            "分析内容需求并制定创作计划",
                            "确定内容结构和要点",
                            "协调团队成员的工作",
                            "确保内容质量和一致性"
                        ],
                        tools=["reasoning", "content_planning"],
                        model_config={"provider": "openai", "model": "gpt-4o"},
                        capabilities=["content_strategy", "structure_design", "team_coordination"]
                    ),
                    AgentSpec(
                        name="ContentWriter",
                        role=AgentRole.WRITER,
                        description="专业内容写作专家",
                        instructions=[
                            "根据计划创作高质量内容",
                            "确保内容的可读性和吸引力",
                            "遵循品牌语调和风格指南",
                            "使用适当的格式和结构"
                        ],
                        tools=["writing", "style_guide"],
                        model_config={"provider": "anthropic", "model": "claude-3-5-sonnet-20241022"},
                        capabilities=["creative_writing", "technical_writing", "style_adaptation"]
                    ),
                    AgentSpec(
                        name="ContentReviewer",
                        role=AgentRole.REVIEWER,
                        description="内容质量评审专家",
                        instructions=[
                            "全面评审内容质量",
                            "检查语法、拼写和格式",
                            "确保信息准确性",
                            "提供改进建议"
                        ],
                        tools=["reasoning", "quality_check"],
                        model_config={"provider": "openai", "model": "gpt-4o"},
                        capabilities=["quality_assurance", "error_detection", "improvement_suggestions"]
                    )
                ],
                success_criteria="创作出高质量、符合要求的内容作品",
                coordination_strategy="sequential_pipeline",
                max_iterations=5,
                timeout_seconds=240
            ),
            
            "problem_solving_team": TeamSpec(
                name="ZZDSJ问题解决团队",
                description="专门解决复杂问题的多角度专家团队",
                mode=TeamMode.DEBATE,
                agents=[
                    AgentSpec(
                        name="ProblemAnalyzer",
                        role=AgentRole.ANALYZER,
                        description="问题分析专家",
                        instructions=[
                            "深度分析问题的各个方面",
                            "识别根本原因和影响因素",
                            "提供问题分解和框架",
                            "确保分析的全面性"
                        ],
                        tools=["reasoning", "problem_analysis"],
                        model_config={"provider": "openai", "model": "gpt-4o"},
                        capabilities=["root_cause_analysis", "systems_thinking", "problem_decomposition"]
                    ),
                    AgentSpec(
                        name="SolutionArchitect",
                        role=AgentRole.TECHNICAL_EXPERT,
                        description="解决方案架构师",
                        instructions=[
                            "设计创新的解决方案",
                            "考虑技术可行性和实现路径",
                            "评估方案的优缺点",
                            "提供详细的实施计划"
                        ],
                        tools=["reasoning", "solution_design"],
                        model_config={"provider": "anthropic", "model": "claude-3-5-sonnet-20241022"},
                        capabilities=["solution_architecture", "feasibility_analysis", "implementation_planning"]
                    ),
                    AgentSpec(
                        name="CriticalThinker",
                        role=AgentRole.REVIEWER,
                        description="批判性思维专家",
                        instructions=[
                            "从不同角度质疑和评估解决方案",
                            "识别潜在的风险和问题",
                            "提供建设性的批评和改进意见",
                            "确保方案的稳健性"
                        ],
                        tools=["reasoning", "critical_analysis"],
                        model_config={"provider": "openai", "model": "gpt-4o"},
                        capabilities=["critical_thinking", "risk_assessment", "devil_advocate"]
                    )
                ],
                success_criteria="找到可行、有效、经过充分论证的解决方案",
                coordination_strategy="debate_consensus",
                max_iterations=12,
                timeout_seconds=400
            )
        }

    async def create_agent_from_spec(self, spec: AgentSpec) -> Optional[Agent]:
        """根据规格创建代理"""
        if not AGNO_AVAILABLE:
            logger.error("Agno框架未安装")
            return None
        
        try:
            # 使用模型配置适配器创建模型
            model_provider = spec.model_config.get("provider", "openai")
            model_name = spec.model_config.get("model")
            
            if model_name:
                # 如果指定了具体模型，尝试使用该模型
                model = await self.model_adapter.create_agno_model(model_id=model_name)
            else:
                # 否则根据提供商类型创建模型
                model = await self.model_adapter.create_agno_model(provider_type=model_provider)
            
            # 如果模型创建失败，使用默认模型
            if not model:
                logger.warning(f"无法创建指定模型 {model_name or model_provider}，使用默认模型")
                model = await self.model_adapter.create_agno_model()
            
            # 如果仍然失败，使用硬编码的回退模型
            if not model:
                logger.warning("模型适配器失败，使用硬编码回退模型")
                model = OpenAIChat(id="gpt-4o")
            
            # 根据工具配置创建工具列表
            tools = []
            for tool_name in spec.tools:
                if tool_name == "duckduckgo_search":
                    tools.append(DuckDuckGoTools())
                elif tool_name == "reasoning":
                    tools.append(ReasoningTools())
                # 可以继续添加更多工具
            
            # 创建代理
            agent = Agent(
                name=spec.name,
                model=model,
                tools=tools,
                description=spec.description,
                instructions=spec.instructions,
                markdown=True,
                show_tool_calls=True,
                add_history_to_messages=True,
                add_datetime_to_instructions=True
            )
            
            logger.info(f"已创建代理: {spec.name} ({spec.role.value})")
            return agent
            
        except Exception as e:
            logger.error(f"创建代理失败 {spec.name}: {e}")
            return None

    async def create_team_from_spec(self, team_spec: TeamSpec) -> Optional[Team]:
        """根据规格创建团队"""
        if not AGNO_AVAILABLE:
            logger.error("Agno框架未安装")
            return None
        
        try:
            # 创建团队成员
            members = []
            for agent_spec in team_spec.agents:
                agent = await self.create_agent_from_spec(agent_spec)
                if agent:
                    members.append(agent)
                    # 注册到代理注册表
                    self.agent_registry[f"{team_spec.name}_{agent_spec.name}"] = agent
            
            if not members:
                logger.error(f"团队 {team_spec.name} 没有可用成员")
                return None
            
            # 选择协调模型（通常使用更强的模型作为协调者）
            coordinator_model = await self.model_adapter.create_agno_model(provider_type="openai")
            if not coordinator_model:
                coordinator_model = OpenAIChat(id="gpt-4o")
            
            # 创建团队 - 使用正确的Agno Team语法
            team = Team(
                name=team_spec.name,
                mode=team_spec.mode.value,
                model=coordinator_model,
                members=members,
                description=team_spec.description,
                success_criteria=team_spec.success_criteria,
                instructions=[
                    f"您正在协调一个{team_spec.description}",
                    f"团队目标: {team_spec.success_criteria}",
                    f"协调策略: {team_spec.coordination_strategy}",
                    "请根据任务需求合理分配工作给团队成员",
                    "确保团队协作高效有序",
                    "最终提供高质量的综合结果"
                ],
                markdown=True,
                show_tool_calls=False,
                show_members_responses=False,
                enable_agentic_context=True,
                share_member_interactions=True,
                enable_team_history=True
            )
            
            # 存储团队
            self.teams[team_spec.name] = team
            self.team_specs[team_spec.name] = team_spec
            
            logger.info(f"已创建团队: {team_spec.name}，成员数量: {len(members)}")
            return team
            
        except Exception as e:
            logger.error(f"创建团队失败 {team_spec.name}: {e}")
            return None

    async def create_predefined_team(self, team_name: str) -> Optional[Team]:
        """创建预定义团队"""
        if team_name not in self.predefined_teams:
            logger.error(f"未找到预定义团队: {team_name}")
            return None
        
        team_spec = self.predefined_teams[team_name]
        return await self.create_team_from_spec(team_spec)

    async def run_team_collaboration(self, 
                                   team_name: str, 
                                   task: str,
                                   additional_context: Optional[Dict] = None) -> CollaborationResult:
        """运行团队协作"""
        start_time = datetime.now()
        
        try:
            # 获取团队
            team = self.teams.get(team_name)
            if not team:
                # 尝试创建预定义团队
                team = await self.create_predefined_team(team_name)
                if not team:
                    return CollaborationResult(
                        success=False,
                        result=None,
                        timestamp=start_time.isoformat(),
                        duration_seconds=0,
                        iterations_used=0,
                        agent_contributions={},
                        performance_metrics={},
                        issues=[f"无法找到或创建团队: {team_name}"]
                    )
            
            # 准备任务上下文
            full_task = task
            if additional_context:
                context_str = "\n".join([f"{k}: {v}" for k, v in additional_context.items()])
                full_task = f"{task}\n\n附加上下文:\n{context_str}"
            
            # 运行团队协作
            response = team.run(full_task)
            
            # 计算执行时间
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 创建协作结果
            result = CollaborationResult(
                success=True,
                result=response.content if hasattr(response, 'content') else str(response),
                timestamp=start_time.isoformat(),
                duration_seconds=duration,
                iterations_used=1,  # Agno Team API 不直接暴露迭代次数
                agent_contributions={},  # 可以通过team历史获取
                performance_metrics={
                    "response_time": duration,
                    "team_size": len(team.members),
                    "success_rate": 1.0
                }
            )
            
            # 记录到性能历史
            self.performance_history.append(result)
            
            logger.info(f"团队协作完成: {team_name}, 耗时: {duration:.2f}秒")
            return result
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            error_result = CollaborationResult(
                success=False,
                result=None,
                timestamp=start_time.isoformat(),
                duration_seconds=duration,
                iterations_used=0,
                agent_contributions={},
                performance_metrics={},
                issues=[str(e)]
            )
            
            self.performance_history.append(error_result)
            logger.error(f"团队协作失败 {team_name}: {e}")
            return error_result

    def get_team_status(self, team_name: str) -> Optional[Dict[str, Any]]:
        """获取团队状态"""
        team = self.teams.get(team_name)
        team_spec = self.team_specs.get(team_name)
        
        if not team or not team_spec:
            return None
        
        return {
            "name": team_name,
            "description": team_spec.description,
            "mode": team_spec.mode.value,
            "member_count": len(team.members),
            "members": [
                {
                    "name": agent.name,
                    "description": getattr(agent, 'description', ''),
                    "tools": len(getattr(agent, 'tools', []))
                }
                for agent in team.members
            ],
            "success_criteria": team_spec.success_criteria,
            "max_iterations": team_spec.max_iterations,
            "timeout_seconds": team_spec.timeout_seconds
        }

    def list_available_teams(self) -> List[str]:
        """列出所有可用团队"""
        return list(self.predefined_teams.keys()) + list(self.teams.keys())

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        if not self.performance_history:
            return {
                "total_collaborations": 0,
                "success_rate": 0.0,
                "average_duration": 0.0,
                "total_duration": 0.0
            }
        
        successful = [r for r in self.performance_history if r.success]
        total = len(self.performance_history)
        
        return {
            "total_collaborations": total,
            "successful_collaborations": len(successful),
            "success_rate": len(successful) / total if total > 0 else 0.0,
            "average_duration": sum(r.duration_seconds for r in self.performance_history) / total,
            "total_duration": sum(r.duration_seconds for r in self.performance_history),
            "latest_collaboration": self.performance_history[-1].timestamp if self.performance_history else None
        }

    async def optimize_team_performance(self, team_name: str) -> Dict[str, Any]:
        """优化团队性能"""
        # 分析历史性能数据
        team_results = [r for r in self.performance_history if team_name in str(r)]
        
        if not team_results:
            return {"message": "没有足够的历史数据进行优化"}
        
        # 计算性能指标
        avg_duration = sum(r.duration_seconds for r in team_results) / len(team_results)
        success_rate = sum(1 for r in team_results if r.success) / len(team_results)
        
        # 生成优化建议
        recommendations = []
        
        if avg_duration > 180:  # 超过3分钟
            recommendations.append("考虑减少团队成员数量或优化任务分配策略")
        
        if success_rate < 0.8:  # 成功率低于80%
            recommendations.append("考虑调整团队成员配置或增强错误处理")
        
        return {
            "team_name": team_name,
            "current_performance": {
                "average_duration": avg_duration,
                "success_rate": success_rate,
                "total_collaborations": len(team_results)
            },
            "recommendations": recommendations,
            "optimization_timestamp": datetime.now().isoformat()
        }


# 全局团队协调器实例
_team_coordinator = None

def get_team_coordinator() -> ZZDSJTeamCoordinator:
    """获取全局团队协调器实例"""
    global _team_coordinator
    if _team_coordinator is None:
        _team_coordinator = ZZDSJTeamCoordinator()
    return _team_coordinator


# 便捷函数
async def create_research_team() -> Optional[Team]:
    """创建研究团队"""
    coordinator = get_team_coordinator()
    return await coordinator.create_predefined_team("research_team")


async def create_content_team() -> Optional[Team]:
    """创建内容创作团队"""
    coordinator = get_team_coordinator()
    return await coordinator.create_predefined_team("content_creation_team")


async def create_problem_solving_team() -> Optional[Team]:
    """创建问题解决团队"""
    coordinator = get_team_coordinator()
    return await coordinator.create_predefined_team("problem_solving_team")


async def run_research_collaboration(task: str, context: Optional[Dict] = None) -> CollaborationResult:
    """运行研究协作"""
    coordinator = get_team_coordinator()
    return await coordinator.run_team_collaboration("research_team", task, context)


async def run_content_collaboration(task: str, context: Optional[Dict] = None) -> CollaborationResult:
    """运行内容创作协作"""
    coordinator = get_team_coordinator()
    return await coordinator.run_team_collaboration("content_creation_team", task, context)


async def run_problem_solving_collaboration(task: str, context: Optional[Dict] = None) -> CollaborationResult:
    """运行问题解决协作"""
    coordinator = get_team_coordinator()
    return await coordinator.run_team_collaboration("problem_solving_team", task, context)


# 示例使用
async def example_team_collaboration():
    """团队协作示例"""
    try:
        # 获取团队协调器
        coordinator = get_team_coordinator()
        
        # 创建研究团队
        research_team = await coordinator.create_predefined_team("research_team")
        if research_team:
            print("✅ 研究团队创建成功")
            
            # 运行研究任务
            task = "研究当前AI代理框架的发展趋势和技术特点"
            result = await coordinator.run_team_collaboration("research_team", task)
            
            if result.success:
                print(f"✅ 研究协作成功，耗时: {result.duration_seconds:.2f}秒")
                print(f"📊 结果: {result.result[:200]}...")
            else:
                print(f"❌ 研究协作失败: {result.issues}")
        
        # 获取性能指标
        metrics = coordinator.get_performance_metrics()
        print(f"📈 总协作次数: {metrics['total_collaborations']}")
        print(f"📈 成功率: {metrics['success_rate']:.2%}")
        print(f"📈 平均耗时: {metrics['average_duration']:.2f}秒")
        
    except Exception as e:
        logger.error(f"团队协作示例失败: {e}")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_team_collaboration()) 