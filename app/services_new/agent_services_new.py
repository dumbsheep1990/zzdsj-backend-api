"""
智能体服务层：处理智能体相关的业务逻辑
"""

from typing import Any, Dict, List, Optional, Tuple
import logging
from sqlalchemy.orm import Session

from app.core.agent_manager import AgentManager
from app.core.exceptions import NotFoundError, ValidationError
from app.models.tools import Tool, AgentTool

logger = logging.getLogger(__name__)


class AgentService:
    """智能体服务类"""

    def __init__(self, db: Session):
        self.db = db
        self.agent_manager = AgentManager()

    async def process_task(
            self,
            task: str,
            framework: Optional[str] = None,
            tool_ids: Optional[List[str]] = None,
            parameters: Optional[Dict[str, Any]] = None,
            user_id: Optional[int] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """处理智能体任务"""
        try:
            # 加载工具
            tools = []
            if tool_ids:
                tools = await self._load_tools(tool_ids, user_id)

            # 处理任务
            result, metadata = await self.agent_manager.process_task(
                task=task,
                use_framework=framework,
                tools=tools,
                parameters=parameters
            )

            # 记录任务历史
            await self._record_task_history(
                user_id=user_id,
                task=task,
                framework=framework,
                result=result,
                metadata=metadata
            )

            return result, metadata

        except Exception as e:
            logger.error(f"处理任务失败: {str(e)}", exc_info=True)
            raise ValidationError(f"任务处理失败: {str(e)}")

    async def _load_tools(self, tool_ids: List[str], user_id: Optional[int] = None) -> List[Any]:
        """加载指定的工具"""
        tools = []

        for tool_id in tool_ids:
            # 从数据库加载工具配置
            tool = self.db.query(Tool).filter(
                Tool.id == tool_id,
                Tool.is_active == True
            ).first()

            if not tool:
                logger.warning(f"工具未找到: {tool_id}")
                continue

            # 检查权限
            if user_id and tool.requires_permission:
                if not await self._check_tool_permission(tool_id, user_id):
                    logger.warning(f"用户 {user_id} 无权使用工具 {tool_id}")
                    continue

            # 实例化工具
            tool_instance = await self._instantiate_tool(tool)
            if tool_instance:
                tools.append(tool_instance)

        return tools

    async def _check_tool_permission(self, tool_id: str, user_id: int) -> bool:
        """检查用户是否有权限使用工具"""
        # TODO: 实现权限检查逻辑
        return True

    async def _instantiate_tool(self, tool: Tool) -> Optional[Any]:
        """实例化工具"""
        try:
            # 根据工具类型实例化
            if tool.type == "mcp":
                from app.frameworks.integration.mcp_integration import MCPIntegrationService
                mcp_service = MCPIntegrationService()
                return mcp_service.get_tool_by_name(tool.name)

            elif tool.type == "function":
                # TODO: 实现函数工具加载
                pass

            elif tool.type == "query_engine":
                # TODO: 实现查询引擎工具加载
                pass

            return None

        except Exception as e:
            logger.error(f"实例化工具失败 {tool.name}: {str(e)}")
            return None

    async def _record_task_history(
            self,
            user_id: Optional[int],
            task: str,
            framework: Optional[str],
            result: str,
            metadata: Dict[str, Any]
    ):
        """记录任务历史"""
        try:
            # TODO: 实现任务历史记录
            pass
        except Exception as e:
            logger.error(f"记录任务历史失败: {str(e)}")

    def list_available_frameworks(self) -> List[Dict[str, Any]]:
        """获取可用的智能体框架列表"""
        return self.agent_manager.list_available_frameworks()

    def list_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用的智能体工具列表"""
        # 从数据库获取工具列表
        tools = self.db.query(Tool).filter(Tool.is_active == True).all()

        tool_list = []
        for tool in tools:
            tool_list.append({
                "id": tool.id,
                "name": tool.name,
                "type": tool.type,
                "description": tool.description,
                "category": tool.category,
                "requires_permission": tool.requires_permission,
                "config": tool.config
            })

        # 添加内置工具
        builtin_tools = self.agent_manager.list_available_tools()
        tool_list.extend(builtin_tools)

        return tool_list

    async def configure_agent_tools(
            self,
            agent_id: int,
            tool_configs: List[Dict[str, Any]],
            user_id: int
    ) -> List[Dict[str, Any]]:
        """配置智能体工具"""
        # 验证智能体权限
        from app.services.assistant_service import AssistantService
        assistant_service = AssistantService(self.db)
        assistant = await assistant_service.get_assistant_by_id(agent_id, user_id)

        if not assistant:
            raise NotFoundError("助手不存在")

        if assistant.owner_id != user_id:
            raise PermissionError("只有所有者可以配置助手工具")

        # 清除现有配置
        self.db.query(AgentTool).filter(AgentTool.agent_id == agent_id).delete()

        # 添加新配置
        configured_tools = []
        for config in tool_configs:
            agent_tool = AgentTool(
                agent_id=agent_id,
                tool_id=config.get("tool_id"),
                tool_type=config["tool_type"],
                tool_name=config["tool_name"],
                enabled=config.get("enabled", True),
                settings=config.get("settings", {})
            )
            self.db.add(agent_tool)

            configured_tools.append({
                "tool_type": agent_tool.tool_type,
                "tool_name": agent_tool.tool_name,
                "enabled": agent_tool.enabled,
                "settings": agent_tool.settings
            })

        try:
            self.db.commit()
            logger.info(f"配置智能体 {agent_id} 的工具成功")
            return configured_tools

        except Exception as e:
            self.db.rollback()
            logger.error(f"配置智能体工具失败: {str(e)}")
            raise ValidationError(f"配置工具失败: {str(e)}")

    async def get_agent_tools(self, agent_id: int) -> List[Dict[str, Any]]:
        """获取智能体工具配置"""
        agent_tools = self.db.query(AgentTool).filter(
            AgentTool.agent_id == agent_id
        ).all()

        tools = []
        for agent_tool in agent_tools:
            tools.append({
                "tool_id": agent_tool.tool_id,
                "tool_type": agent_tool.tool_type,
                "tool_name": agent_tool.tool_name,
                "enabled": agent_tool.enabled,
                "settings": agent_tool.settings
            })

        return tools