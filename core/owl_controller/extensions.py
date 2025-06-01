from typing import Any, Dict, List, Optional, Tuple, Union
import logging
from sqlalchemy.orm import Session

from core.owl_controller import OwlController
from core.agent_builder import AgentBuilder
from core.nl_config_parser import NLConfigParser
from core.tool_orchestrator import ToolOrchestrator

from app.repositories.agent_definition_repository import AgentDefinitionRepository
from app.repositories.agent_template_repository import AgentTemplateRepository
from app.repositories.tool_repository import ToolRepository
from app.repositories.agent_run_repository import AgentRunRepository

from app.utils.core.database import get_db

logger = logging.getLogger(__name__)

class OwlControllerExtensions:
    """OWL控制器扩展，提供对智能体自定义系统的支持"""
    
    def __init__(self, controller: Optional[OwlController] = None):
        """初始化OWL控制器扩展
        
        Args:
            controller: 现有的OWL控制器实例，如果不提供则创建新实例
        """
        self.controller = controller or OwlController()
        self.agent_builder = AgentBuilder()
        self.nl_config_parser = NLConfigParser()
        self.tool_orchestrator = ToolOrchestrator()
        
        # 初始化仓库
        self.agent_definition_repo = AgentDefinitionRepository()
        self.agent_template_repo = AgentTemplateRepository()
        self.tool_repo = ToolRepository()
        self.agent_run_repo = AgentRunRepository()
    
    async def initialize(self) -> None:
        """初始化控制器扩展"""
        await self.controller.initialize()
        await self.nl_config_parser.initialize()
    
    #---------------------------
    # 智能体定义管理
    #---------------------------
    
    async def get_agent_definitions(
        self, db: Session, skip: int = 0, limit: int = 100, 
        creator_id: Optional[int] = None, is_public: Optional[bool] = None,
        is_system: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """获取智能体定义列表
        
        Args:
            db: 数据库会话
            skip: 跳过数量
            limit: 限制数量
            creator_id: 创建者ID筛选
            is_public: 是否公开筛选
            is_system: 是否系统筛选
            
        Returns:
            List[Dict[str, Any]]: 智能体定义列表
        """
        definitions = await self.agent_definition_repo.get_all(
            db, skip=skip, limit=limit,
            creator_id=creator_id, is_public=is_public, is_system=is_system
        )
        
        return [definition.to_dict() for definition in definitions]
    
    async def get_agent_definition(self, definition_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """获取特定智能体定义
        
        Args:
            definition_id: 智能体定义ID
            db: 数据库会话
            
        Returns:
            Optional[Dict[str, Any]]: 智能体定义，不存在则返回None
        """
        definition = await self.agent_definition_repo.get_by_id(definition_id, db)
        if not definition:
            return None
        
        return definition.to_dict()
    
    async def create_agent_definition(self, data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """创建智能体定义
        
        Args:
            data: 创建数据
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 创建的智能体定义
        """
        definition = await self.agent_definition_repo.create(data, db)
        return definition.to_dict()
    
    async def update_agent_definition(
        self, definition_id: int, data: Dict[str, Any], db: Session
    ) -> Optional[Dict[str, Any]]:
        """更新智能体定义
        
        Args:
            definition_id: 智能体定义ID
            data: 更新数据
            db: 数据库会话
            
        Returns:
            Optional[Dict[str, Any]]: 更新后的智能体定义，不存在则返回None
        """
        definition = await self.agent_definition_repo.update(definition_id, data, db)
        if not definition:
            return None
        
        return definition.to_dict()
    
    async def delete_agent_definition(self, definition_id: int, db: Session) -> bool:
        """删除智能体定义
        
        Args:
            definition_id: 智能体定义ID
            db: 数据库会话
            
        Returns:
            bool: 是否成功删除
        """
        return await self.agent_definition_repo.delete(definition_id, db)
    
    #---------------------------
    # 智能体模板管理
    #---------------------------
    
    async def get_agent_templates(
        self, db: Session, skip: int = 0, limit: int = 100, 
        creator_id: Optional[int] = None, is_system: Optional[bool] = None,
        category: Optional[str] = None, base_agent_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取智能体模板列表
        
        Args:
            db: 数据库会话
            skip: 跳过数量
            limit: 限制数量
            creator_id: 创建者ID筛选
            is_system: 是否系统模板筛选
            category: 分类筛选
            base_agent_type: 基础智能体类型筛选
            
        Returns:
            List[Dict[str, Any]]: 智能体模板列表
        """
        templates = await self.agent_template_repo.get_all(
            db, skip=skip, limit=limit,
            creator_id=creator_id, is_system=is_system,
            category=category, base_agent_type=base_agent_type
        )
        
        return [template.to_dict() for template in templates]
    
    async def get_agent_template(self, template_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """获取特定智能体模板
        
        Args:
            template_id: 模板ID
            db: 数据库会话
            
        Returns:
            Optional[Dict[str, Any]]: 智能体模板，不存在则返回None
        """
        template = await self.agent_template_repo.get_by_id(template_id, db)
        if not template:
            return None
        
        return template.to_dict()
    
    async def create_agent_template(self, data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """创建智能体模板
        
        Args:
            data: 创建数据
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 创建的智能体模板
        """
        template = await self.agent_template_repo.create(data, db)
        return template.to_dict()
    
    async def update_agent_template(
        self, template_id: int, data: Dict[str, Any], db: Session
    ) -> Optional[Dict[str, Any]]:
        """更新智能体模板
        
        Args:
            template_id: 模板ID
            data: 更新数据
            db: 数据库会话
            
        Returns:
            Optional[Dict[str, Any]]: 更新后的智能体模板，不存在则返回None
        """
        template = await self.agent_template_repo.update(template_id, data, db)
        if not template:
            return None
        
        return template.to_dict()
    
    async def delete_agent_template(self, template_id: int, db: Session) -> bool:
        """删除智能体模板
        
        Args:
            template_id: 模板ID
            db: 数据库会话
            
        Returns:
            bool: 是否成功删除
        """
        return await self.agent_template_repo.delete(template_id, db)
    
    async def instantiate_template(
        self, template_id: int, data: Dict[str, Any], db: Session
    ) -> Optional[Dict[str, Any]]:
        """基于模板实例化智能体定义
        
        Args:
            template_id: 模板ID
            data: 实例化数据
            db: 数据库会话
            
        Returns:
            Optional[Dict[str, Any]]: 创建的智能体定义ID和名称，失败则返回None
        """
        # 获取模板
        template = await self.agent_template_repo.get_by_id(template_id, db)
        if not template:
            return None
            
        # 准备智能体定义数据
        definition_data = {
            "name": data["name"],
            "description": data.get("description") or template.description,
            "base_agent_type": template.base_agent_type,
            "is_public": data.get("is_public", False),
            "creator_id": data["creator_id"],
            "configuration": template.configuration,
            "system_prompt": template.system_prompt_template
        }
        
        # 应用参数替换（如果有）
        if "parameters" in data and template.system_prompt_template:
            for key, value in data["parameters"].items():
                placeholder = f"{{{key}}}"
                if placeholder in definition_data["system_prompt"]:
                    definition_data["system_prompt"] = definition_data["system_prompt"].replace(
                        placeholder, str(value)
                    )
        
        # 如果模板有推荐工具，添加工具配置
        if template.recommended_tools:
            definition_data["tools"] = template.recommended_tools
        
        # 如果模板有示例工作流，添加工作流定义
        if template.example_workflow:
            definition_data["workflow_definition"] = template.example_workflow
        
        # 创建智能体定义
        definition = await self.agent_definition_repo.create(definition_data, db)
        
        return {
            "definition_id": definition.id,
            "name": definition.name
        }
    
    #---------------------------
    # 工具管理
    #---------------------------
    
    async def get_tools(
        self, db: Session, skip: int = 0, limit: int = 100, 
        creator_id: Optional[int] = None, is_system: Optional[bool] = None,
        category: Optional[str] = None, tool_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取工具列表
        
        Args:
            db: 数据库会话
            skip: 跳过数量
            limit: 限制数量
            creator_id: 创建者ID筛选
            is_system: 是否系统工具筛选
            category: 分类筛选
            tool_type: 工具类型筛选
            
        Returns:
            List[Dict[str, Any]]: 工具列表
        """
        tools = await self.tool_repo.get_all(
            db, skip=skip, limit=limit,
            creator_id=creator_id, is_system=is_system,
            category=category, tool_type=tool_type
        )
        
        return [tool.to_dict() for tool in tools]
    
    async def get_tool(self, tool_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """获取特定工具
        
        Args:
            tool_id: 工具ID
            db: 数据库会话
            
        Returns:
            Optional[Dict[str, Any]]: 工具，不存在则返回None
        """
        tool = await self.tool_repo.get_by_id(tool_id, db)
        if not tool:
            return None
        
        return tool.to_dict()
    
    async def create_tool(self, data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """创建工具
        
        Args:
            data: 创建数据
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 创建的工具
        """
        tool = await self.tool_repo.create(data, db)
        return tool.to_dict()
    
    async def update_tool(
        self, tool_id: int, data: Dict[str, Any], db: Session
    ) -> Optional[Dict[str, Any]]:
        """更新工具
        
        Args:
            tool_id: 工具ID
            data: 更新数据
            db: 数据库会话
            
        Returns:
            Optional[Dict[str, Any]]: 更新后的工具，不存在则返回None
        """
        tool = await self.tool_repo.update(tool_id, data, db)
        if not tool:
            return None
        
        return tool.to_dict()
    
    async def delete_tool(self, tool_id: int, db: Session) -> bool:
        """删除工具
        
        Args:
            tool_id: 工具ID
            db: 数据库会话
            
        Returns:
            bool: 是否成功删除
        """
        return await self.tool_repo.delete(tool_id, db)
    
    #---------------------------
    # 智能体运行管理
    #---------------------------
    
    async def run_agent_task(
        self, definition_id: int, task: str, user_id: int, 
        parameters: Optional[Dict[str, Any]] = None, db: Session = None
    ) -> Dict[str, Any]:
        """运行智能体任务
        
        Args:
            definition_id: 智能体定义ID
            task: 任务内容
            user_id: 用户ID
            parameters: 任务参数
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 运行ID和初始状态
        """
        if db is None:
            db = next(get_db())
            
        # 创建运行记录
        run_data = {
            "agent_definition_id": definition_id,
            "user_id": user_id,
            "task": task,
            "status": "pending",
            "metadata": {"parameters": parameters} if parameters else {}
        }
        
        run = await self.agent_run_repo.create(run_data, db)
        
        return {
            "run_id": run.id,
            "status": "pending",
            "metadata": {"message": "任务已提交，正在处理中"}
        }
    
    async def get_agent_runs(
        self, user_id: int, db: Session, skip: int = 0, limit: int = 100, 
        agent_definition_id: Optional[int] = None, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取智能体运行记录列表
        
        Args:
            user_id: 用户ID
            db: 数据库会话
            skip: 跳过数量
            limit: 限制数量
            agent_definition_id: 智能体定义ID筛选
            status: 状态筛选
            
        Returns:
            List[Dict[str, Any]]: 运行记录列表
        """
        runs = await self.agent_run_repo.get_all(
            db, skip=skip, limit=limit,
            user_id=user_id,
            agent_definition_id=agent_definition_id,
            status=status
        )
        
        return [
            {
                "run_id": run.id,
                "result": run.result,
                "status": run.status,
                "metadata": {
                    "start_time": run.start_time,
                    "end_time": run.end_time,
                    "duration": run.duration,
                    "agent_definition_id": run.agent_definition_id,
                    "task": run.task,
                    **run.metadata if run.metadata else {}
                }
            }
            for run in runs
        ]
    
    async def get_agent_run(self, run_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """获取特定智能体运行记录
        
        Args:
            run_id: 运行记录ID
            db: 数据库会话
            
        Returns:
            Optional[Dict[str, Any]]: 运行记录，不存在则返回None
        """
        run = await self.agent_run_repo.get_by_id(run_id, db)
        if not run:
            return None
        
        return {
            "run_id": run.id,
            "result": run.result,
            "status": run.status,
            "metadata": {
                "start_time": run.start_time,
                "end_time": run.end_time,
                "duration": run.duration,
                "agent_definition_id": run.agent_definition_id,
                "task": run.task,
                "tool_calls": run.tool_calls,
                "error": run.error,
                **run.metadata if run.metadata else {}
            }
        }
    
    async def get_agent_run_logs(self, run_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """获取智能体运行日志
        
        Args:
            run_id: 运行记录ID
            db: 数据库会话
            
        Returns:
            Optional[Dict[str, Any]]: 运行日志，不存在则返回None
        """
        run = await self.agent_run_repo.get_by_id(run_id, db)
        if not run:
            return None
        
        return {
            "task": run.task,
            "status": run.status,
            "tool_calls": run.tool_calls or [],
            "start_time": run.start_time,
            "end_time": run.end_time,
            "duration": run.duration,
            "error": run.error
        }
        
    #---------------------------
    # 自然语言配置相关功能
    #---------------------------
    
    async def parse_natural_language_config(self, description: str) -> Dict[str, Any]:
        """将自然语言描述解析为结构化的智能体配置
        
        Args:
            description: 智能体需求描述
            
        Returns:
            Dict[str, Any]: 解析后的配置
        """
        return await self.nl_config_parser.parse_description(description)
    
    async def suggest_improvements(self, current_config: Dict[str, Any]) -> Dict[str, Any]:
        """基于当前配置提供优化建议
        
        Args:
            current_config: 当前配置
            
        Returns:
            Dict[str, Any]: 优化建议
        """
        return await self.nl_config_parser.suggest_improvements(current_config)
    
    #---------------------------
    # 工具链编排相关功能
    #---------------------------
    
    async def validate_tool_chain(self, config: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """验证工具链配置
        
        Args:
            config: 工具链配置
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        # 验证工具配置
        issues = []
        
        # 检查工具是否存在
        if "tools" in config:
            for i, tool_config in enumerate(config["tools"]):
                if "id" not in tool_config:
                    issues.append({
                        "type": "missing_id",
                        "message": f"工具配置 #{i+1} 缺少ID",
                        "position": i
                    })
                    continue
                    
                tool_id = tool_config["id"]
                tool = await self.tool_repo.get_by_id(tool_id, db)
                if not tool:
                    issues.append({
                        "type": "tool_not_found",
                        "message": f"找不到ID为 {tool_id} 的工具",
                        "position": i
                    })
                
                # 验证工具参数（如果有）
                if "parameters" in tool_config and tool and tool.parameter_schema:
                    # 这里可以根据参数模式验证参数
                    # 简化实现，只检查必填字段
                    if "required" in tool.parameter_schema:
                        for field in tool.parameter_schema["required"]:
                            if field not in tool_config["parameters"]:
                                issues.append({
                                    "type": "missing_parameter",
                                    "message": f"工具 {tool.name} 缺少必填参数 {field}",
                                    "position": i,
                                    "field": field
                                })
        else:
            issues.append({
                "type": "missing_tools",
                "message": "配置缺少工具列表"
            })
        
        # 检查工具顺序
        if "tools" in config:
            tools_with_order = [(i, tool.get("order", i)) for i, tool in enumerate(config["tools"])]
            seen_orders = {}
            for i, order in tools_with_order:
                if order in seen_orders:
                    issues.append({
                        "type": "duplicate_order",
                        "message": f"重复的工具顺序 {order}",
                        "positions": [seen_orders[order], i]
                    })
                seen_orders[order] = i
                
        # 验证条件表达式
        if "tools" in config:
            for i, tool_config in enumerate(config["tools"]):
                if "condition" in tool_config and tool_config["condition"]:
                    try:
                        # 使用安全的eval环境测试条件
                        test_context = {"task": "测试任务", "result": "测试结果"}
                        self.tool_orchestrator._evaluate_condition(tool_config["condition"], test_context)
                    except Exception as e:
                        issues.append({
                            "type": "invalid_condition",
                            "message": f"无效的条件表达式: {str(e)}",
                            "position": i,
                            "condition": tool_config["condition"]
                        })
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues if issues else None
        }
