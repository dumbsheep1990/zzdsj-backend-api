from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import asyncio

from app.frameworks.owl.agents.base import BaseAgent
from app.utils.logger import get_logger

logger = get_logger(__name__)

class OwlWorkflow:
    """OWL工作流协作模式，实现多阶段任务处理"""
    
    def __init__(self, name: str, description: str = ""):
        """初始化工作流
        
        Args:
            name: 工作流名称
            description: 工作流描述
        """
        self.name = name
        self.description = description
        self.stages = []
        self.current_stage = 0
        self.results = {}
        self.errors = []
        self.status = "created"  # created, running, completed, failed
        self.start_time = None
        self.end_time = None
        
    def add_stage(self, 
                 name: str, 
                 agent: BaseAgent, 
                 prompt_template: str, 
                 tools: Optional[List[Any]] = None,
                 condition: Optional[Callable[[Dict[str, Any]], bool]] = None) -> None:
        """添加工作流阶段
        
        Args:
            name: 阶段名称
            agent: 处理该阶段的智能体
            prompt_template: 提示模板，用{prev_result}表示上一阶段结果，可使用{result.stage_name}引用特定阶段结果
            tools: 该阶段可用的工具列表
            condition: 执行条件，接收之前的结果作为参数，返回布尔值决定是否执行该阶段
        """
        self.stages.append({
            "name": name,
            "agent": agent,
            "prompt_template": prompt_template,
            "tools": tools or [],
            "condition": condition,
            "status": "pending",  # pending, running, completed, skipped, failed
            "result": None,
            "start_time": None,
            "end_time": None,
            "error": None
        })
        
    def _format_prompt(self, stage: Dict[str, Any]) -> str:
        """根据模板和已有结果格式化提示
        
        Args:
            stage: 阶段信息
            
        Returns:
            str: 格式化后的提示
        """
        prompt = stage["prompt_template"]
        
        # 替换上一阶段结果
        if self.current_stage > 0:
            prev_result = self.results.get(self.stages[self.current_stage - 1]["name"], "")
            prompt = prompt.replace("{prev_result}", prev_result)
            
        # 替换指定阶段结果
        import re
        result_refs = re.findall(r'\{result\.([^\}]+)\}', prompt)
        for ref in result_refs:
            if ref in self.results:
                prompt = prompt.replace(f"{{result.{ref}}}", self.results[ref])
            else:
                prompt = prompt.replace(f"{{result.{ref}}}", "")
                
        return prompt
        
    async def execute_stage(self, stage_index: int) -> Dict[str, Any]:
        """执行指定阶段
        
        Args:
            stage_index: 阶段索引
            
        Returns:
            Dict[str, Any]: 阶段执行结果
        """
        if stage_index < 0 or stage_index >= len(self.stages):
            raise ValueError(f"阶段索引{stage_index}超出范围")
            
        stage = self.stages[stage_index]
        
        # 检查执行条件
        if stage["condition"] is not None:
            should_execute = stage["condition"](self.results)
            if not should_execute:
                stage["status"] = "skipped"
                logger.info(f"阶段 '{stage['name']}' 被跳过，条件未满足")
                return {"status": "skipped", "result": None}
        
        # 更新阶段状态
        stage["status"] = "running"
        stage["start_time"] = asyncio.get_event_loop().time()
        
        try:
            # 格式化提示
            prompt = self._format_prompt(stage)
            
            # 执行阶段
            agent = stage["agent"]
            tools = stage["tools"]
            
            logger.info(f"开始执行阶段 '{stage['name']}'")
            result = await agent.run_task(prompt, tools)
            
            # 更新结果
            self.results[stage["name"]] = result
            
            # 更新阶段状态
            stage["status"] = "completed"
            stage["result"] = result
            stage["end_time"] = asyncio.get_event_loop().time()
            
            logger.info(f"阶段 '{stage['name']}' 执行完成")
            
            return {
                "status": "completed",
                "result": result,
                "execution_time": stage["end_time"] - stage["start_time"]
            }
            
        except Exception as e:
            logger.error(f"执行阶段 '{stage['name']}' 时出错: {str(e)}", exc_info=True)
            
            # 更新阶段状态
            stage["status"] = "failed"
            stage["error"] = str(e)
            stage["end_time"] = asyncio.get_event_loop().time()
            
            self.errors.append({
                "stage": stage["name"],
                "error": str(e),
                "stage_index": stage_index
            })
            
            return {
                "status": "failed",
                "error": str(e),
                "execution_time": stage["end_time"] - stage["start_time"]
            }
            
    async def run(self, max_retries: int = 0) -> Dict[str, Any]:
        """运行完整工作流
        
        Args:
            max_retries: 失败时最大重试次数
            
        Returns:
            Dict[str, Any]: 执行结果，包含每个阶段的结果
        """
        self.status = "running"
        self.start_time = asyncio.get_event_loop().time()
        
        logger.info(f"开始运行工作流 '{self.name}'")
        
        for i in range(len(self.stages)):
            self.current_stage = i
            stage = self.stages[i]
            
            retry_count = 0
            stage_result = None
            
            # 执行阶段，如果失败则重试
            while retry_count <= max_retries:
                stage_result = await self.execute_stage(i)
                
                if stage_result["status"] == "failed":
                    if retry_count < max_retries:
                        logger.info(f"阶段 '{stage['name']}' 执行失败，准备重试 ({retry_count + 1}/{max_retries})")
                        retry_count += 1
                    else:
                        logger.error(f"阶段 '{stage['name']}' 执行失败，已达到最大重试次数")
                        self.status = "failed"
                        self.end_time = asyncio.get_event_loop().time()
                        return self._get_workflow_result()
                else:
                    break
                    
        # 工作流完成
        self.status = "completed"
        self.end_time = asyncio.get_event_loop().time()
        
        logger.info(f"工作流 '{self.name}' 执行完成")
        
        return self._get_workflow_result()
    
    def _get_workflow_result(self) -> Dict[str, Any]:
        """获取工作流执行结果
        
        Returns:
            Dict[str, Any]: 工作流执行结果
        """
        # 计算执行时间
        execution_time = 0
        if self.start_time and self.end_time:
            execution_time = self.end_time - self.start_time
            
        # 收集所有阶段结果
        stage_results = {}
        for stage in self.stages:
            stage_results[stage["name"]] = {
                "status": stage["status"],
                "result": stage["result"],
                "error": stage["error"]
            }
            
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "execution_time": execution_time,
            "results": self.results,
            "stage_results": stage_results,
            "errors": self.errors
        }
        
    def get_status(self) -> Dict[str, Any]:
        """获取工作流当前状态
        
        Returns:
            Dict[str, Any]: 工作流状态信息
        """
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "current_stage": self.current_stage if self.current_stage < len(self.stages) else None,
            "current_stage_name": self.stages[self.current_stage]["name"] if self.current_stage < len(self.stages) else None,
            "total_stages": len(self.stages),
            "completed_stages": sum(1 for stage in self.stages if stage["status"] == "completed"),
            "failed_stages": sum(1 for stage in self.stages if stage["status"] == "failed"),
            "skipped_stages": sum(1 for stage in self.stages if stage["status"] == "skipped")
        }

class WorkflowManager:
    """工作流管理器，负责工作流的创建、运行和状态管理"""
    
    def __init__(self):
        """初始化工作流管理器"""
        self.workflows = {}  # name -> workflow实例
        self.templates = {}  # name -> workflow模板
        self.running_workflows = {}  # id -> workflow实例
        
    def create_workflow_from_template(self, template_name: str, variables: Dict[str, Any] = None) -> OwlWorkflow:
        """从模板创建工作流
        
        Args:
            template_name: 模板名称
            variables: 模板变量
            
        Returns:
            OwlWorkflow: 创建的工作流实例
        """
        if template_name not in self.templates:
            raise ValueError(f"未找到名为 '{template_name}' 的工作流模板")
            
        template = self.templates[template_name]
        variables = variables or {}
        
        # 创建工作流
        workflow = OwlWorkflow(
            name=template.get("name", ""),
            description=template.get("description", "")
        )
        
        # 添加阶段
        for stage in template.get("stages", []):
            # 替换变量
            prompt_template = stage.get("prompt_template", "")
            for var_name, var_value in variables.items():
                prompt_template = prompt_template.replace(f"{{{var_name}}}", str(var_value))
                
            workflow.add_stage(
                name=stage.get("name", ""),
                agent=stage.get("agent"),
                prompt_template=prompt_template,
                tools=stage.get("tools"),
                condition=stage.get("condition")
            )
            
        return workflow
        
    def register_template(self, name: str, template: Dict[str, Any]) -> None:
        """注册工作流模板
        
        Args:
            name: 模板名称
            template: 模板定义
        """
        self.templates[name] = template
        logger.info(f"注册工作流模板 '{name}'")
        
    def get_template(self, name: str) -> Dict[str, Any]:
        """获取工作流模板
        
        Args:
            name: 模板名称
            
        Returns:
            Dict[str, Any]: 模板定义
        """
        if name not in self.templates:
            raise ValueError(f"未找到名为 '{name}' 的工作流模板")
            
        return self.templates[name]
        
    def get_templates(self) -> List[Dict[str, Any]]:
        """获取所有工作流模板
        
        Returns:
            List[Dict[str, Any]]: 模板列表
        """
        return [
            {
                "name": name,
                "description": template.get("description", ""),
                "stages_count": len(template.get("stages", []))
            }
            for name, template in self.templates.items()
        ]
        
    def register_workflow(self, workflow: OwlWorkflow) -> None:
        """注册工作流
        
        Args:
            workflow: 工作流实例
        """
        self.workflows[workflow.name] = workflow
        logger.info(f"注册工作流 '{workflow.name}'")
        
    def get_workflow(self, name: str) -> OwlWorkflow:
        """获取工作流
        
        Args:
            name: 工作流名称
            
        Returns:
            OwlWorkflow: 工作流实例
        """
        if name not in self.workflows:
            raise ValueError(f"未找到名为 '{name}' 的工作流")
            
        return self.workflows[name]
        
    def get_workflows(self) -> List[Dict[str, Any]]:
        """获取所有工作流
        
        Returns:
            List[Dict[str, Any]]: 工作流列表
        """
        return [
            {
                "name": workflow.name,
                "description": workflow.description,
                "status": workflow.status,
                "total_stages": len(workflow.stages),
                "completed_stages": sum(1 for stage in workflow.stages if stage["status"] == "completed")
            }
            for workflow in self.workflows.values()
        ]
        
    async def run_workflow(self, workflow_name: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """运行工作流
        
        Args:
            workflow_name: 工作流名称或模板名称
            variables: 工作流变量
            
        Returns:
            Dict[str, Any]: 运行结果
        """
        # 优先查找已注册工作流
        if workflow_name in self.workflows:
            workflow = self.workflows[workflow_name]
        # 否则尝试从模板创建
        elif workflow_name in self.templates:
            workflow = self.create_workflow_from_template(workflow_name, variables)
            self.register_workflow(workflow)
        else:
            raise ValueError(f"未找到名为 '{workflow_name}' 的工作流或模板")
            
        # 运行工作流
        result = await workflow.run()
        return result
