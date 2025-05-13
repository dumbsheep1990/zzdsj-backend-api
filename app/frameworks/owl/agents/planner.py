from typing import Any, Dict, List, Optional

from app.frameworks.owl.agents.base import BaseAgent

class PlannerAgent(BaseAgent):
    """规划智能体，负责任务分解和策略制定"""
    
    def __init__(self, model_config: Dict[str, Any]):
        """初始化规划智能体
        
        Args:
            model_config: 模型配置
        """
        system_message = (
            "你是一个专业的任务规划专家，擅长将复杂任务分解为可执行的子任务。\n"
            "你需要理解用户的需求，并制定清晰的执行计划。\n"
            "每个计划应当包含明确的步骤，以及每个步骤可能需要使用的工具。\n"
            "请保持计划的简洁性和可执行性，避免过度复杂化。\n"
            "按照以下格式输出你的计划：\n\n"
            "## 任务分析\n[分析用户需求和任务目标]\n\n"
            "## 执行计划\n1. [步骤1描述] - 使用工具: [工具名称]\n"
            "2. [步骤2描述] - 使用工具: [工具名称]\n"
            "...\n\n"
            "## 预期结果\n[描述执行计划后的预期结果]"
        )
        
        super().__init__(model_config, system_message)
        
    async def create_plan(self, task: str) -> Dict[str, Any]:
        """创建任务执行计划
        
        Args:
            task: 任务描述
            
        Returns:
            Dict[str, Any]: 包含任务分析、执行步骤和预期结果的计划
        """
        plan_prompt = f"请为以下任务制定详细的执行计划：\n\n{task}\n\n请确保计划包含必要的工具使用说明。"
        
        # 获取规划结果
        plan_text = await self.chat(plan_prompt)
        
        # 解析计划文本
        plan = self._parse_plan(plan_text)
        
        return plan
    
    def _parse_plan(self, plan_text: str) -> Dict[str, Any]:
        """解析计划文本，提取结构化信息
        
        Args:
            plan_text: 计划文本
            
        Returns:
            Dict[str, Any]: 结构化的计划
        """
        sections = {}
        current_section = None
        steps = []
        
        # 简单的文本解析
        for line in plan_text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('## 任务分析'):
                current_section = 'analysis'
                sections[current_section] = []
            elif line.startswith('## 执行计划'):
                current_section = 'steps'
                sections[current_section] = []
            elif line.startswith('## 预期结果'):
                current_section = 'expected_results'
                sections[current_section] = []
            elif current_section:
                if current_section == 'steps' and line[0].isdigit() and '. ' in line:
                    # 解析步骤
                    step_text = line.split('. ', 1)[1]
                    tool = None
                    
                    # 尝试提取工具信息
                    if ' - 使用工具: ' in step_text:
                        step_parts = step_text.split(' - 使用工具: ')
                        step_text = step_parts[0]
                        tool = step_parts[1]
                    
                    steps.append({
                        'description': step_text,
                        'tool': tool
                    })
                else:
                    sections[current_section].append(line)
        
        # 整合解析结果
        plan = {
            'analysis': '\n'.join(sections.get('analysis', [])),
            'steps': steps,
            'expected_results': '\n'.join(sections.get('expected_results', []))
        }
        
        return plan
