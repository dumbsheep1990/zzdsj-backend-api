"""
OWL Controller - 智能控制器核心模块
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod

# 基础工具导入
from app.utils.core.database import get_db
from app.utils.core.config import get_config_manager
from app.utils.common.logger import get_logger

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from core.agent_manager import AgentManager
from app.frameworks.owl.utils.tool_chain_helper import ToolChainHelper
from app.frameworks.owl.toolkits.base import OwlToolkitManager
from app.frameworks.owl.agents.base import BaseAgent
from app.frameworks.owl.agents.planner import PlannerAgent
from app.frameworks.owl.agents.executor import ExecutorAgent
from app.frameworks.owl.society.workflow import WorkflowManager
from app.frameworks.owl.toolkit_integrator import OwlToolkitIntegrator
from app.frameworks.owl.utils.tool_factory import CustomTool
from app.services.owl_tool_service import OwlToolService
from app.startup.owl_toolkit_init import initialize_owl_toolkits
from app.config import settings

logger = get_logger(__name__)

class OwlController:
    """OWL框架控制器，为API层提供服务"""
    
    def __init__(self, db: Optional[Session] = None):
        """初始化OWL控制器
        
        Args:
            db: 数据库会话，用于初始化工具服务
        """
        self.agent_manager = AgentManager()
        self.toolkit_manager = None
        self.tool_chain_helper = None
        self.workflow_manager = None
        self.toolkit_integrator = None
        self.custom_agents = {}  # 用户创建的自定义智能体
        self.task_history = {}   # 任务历史记录
        self.custom_tools = {}   # 自定义工具
        self.initialized = False
        self.db = db
        
    async def initialize(self) -> None:
        """初始化控制器"""
        if self.initialized:
            return
            
        # 初始化智能体管理器
        await self.agent_manager.initialize()
        
        # 初始化工具包管理器
        self.toolkit_manager = OwlToolkitManager()
        await self.toolkit_manager.initialize(settings.owl.mcp_config_path)
        
        # 初始化工具链助手
        self.tool_chain_helper = ToolChainHelper(self.toolkit_manager)
        await self.tool_chain_helper.initialize()
        
        # 初始化工作流管理器
        self.workflow_manager = WorkflowManager()
        
        # 初始化工具包集成器
        if self.db:
            # 在有数据库会话的情况下初始化工具包集成器
            self.toolkit_integrator = await initialize_owl_toolkits(self.db)
        else:
            # 在没有数据库会话的情况下，只初始化基本组件
            logger.warning("未提供数据库会话，OWL工具包集成器将不会初始化")
            
        # 从数据库加载自定义智能体、自定义工具和任务历史
        # TODO: 实现数据库持久化
        
        self.initialized = True
        
    async def process_task(self, task: str, tools: Optional[List[str]] = None, 
                          user_id: Optional[str] = None,
                          model_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理用户任务
        
        Args:
            task: 任务描述
            tools: 工具ID列表
            user_id: 用户ID
            model_config: 用户指定的模型配置
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        if not self.initialized:
            await self.initialize()
            
        # 加载指定的工具
        selected_tools = []
        if tools:
            # 首先从内部工具中查找
            all_tools = await self.toolkit_manager.get_tools()
            tool_map = {tool.name: tool for tool in all_tools if hasattr(tool, 'name')}
            selected_tools = [tool_map[name] for name in tools if name in tool_map]
            
            # 然后查找Camel工具
            if self.toolkit_integrator and self.db:
                for tool_name in tools:
                    if tool_name not in tool_map:
                        try:
                            camel_tool = await self.toolkit_integrator.get_custom_tool(tool_name)
                            if camel_tool:
                                selected_tools.append(camel_tool)
                        except Exception as e:
                            logger.warning(f"加载Camel工具 {tool_name} 失败: {str(e)}")
        
        # 准备额外参数
        extra_params = {}
        if model_config:
            extra_params["agent_config"] = model_config
            
        # 处理任务
        answer, metadata = await self.agent_manager.process_task(
            task=task,
            use_framework="owl",
            tools=selected_tools,
            **extra_params
        )
        
        # 构造结果
        result = {
            "result": answer,
            "chat_history": metadata.get("chat_history", []),
            "metadata": {k: v for k, v in metadata.items() if k != "chat_history"}
        }
        
        return result
    
    async def create_workflow(self, name: str, description: str) -> Dict[str, Any]:
        """创建工作流
        
        Args:
            name: 工作流名称
            description: 工作流描述
            
        Returns:
            Dict[str, Any]: 创建结果
        """
        if not self.initialized:
            await self.initialize()
            
        # 创建工作流
        workflow_json = await self.tool_chain_helper.create_workflow_from_description(name, description)
        
        return {
            "name": name,
            "description": description,
            "workflow": json.loads(workflow_json)
        }
    
    async def execute_workflow(self, workflow_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行工作流
        
        Args:
            workflow_name: 工作流名称
            inputs: 输入参数
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        if not self.initialized:
            await self.initialize()
            
        # 执行工作流
        result = await self.tool_chain_helper.execute_workflow(workflow_name, inputs)
        
        return result
    
    async def get_available_tools(self) -> List[Dict[str, str]]:
        """获取所有可用工具
        
        Returns:
            List[Dict[str, str]]: 工具列表
        """
        if not self.initialized:
            await self.initialize()
            
        all_tools = []
        
        # 从工具链助手获取工具
        for name, tool_info in self.tool_chain_helper.available_tools.items():
            all_tools.append({
                "name": name,
                "description": tool_info["description"],
                "source": "internal"
            })
        
        # 从工具包集成器获取工具（如果已初始化）
        if self.toolkit_integrator and self.db:
            tool_service = OwlToolService(self.db)
            db_tools = await tool_service.list_enabled_tools()
            
            for tool in db_tools:
                all_tools.append({
                    "name": tool.name,
                    "description": tool.description or f"{tool.toolkit_name}.{tool.function_name}",
                    "source": "camel",
                    "toolkit": tool.toolkit_name
                })
        
        return all_tools
    
    async def get_available_workflows(self) -> List[Dict[str, Any]]:
        """获取所有可用工作流
        
        Returns:
            List[Dict[str, Any]]: 工作流列表
        """
        if not self.initialized:
            await self.initialize()
            
        all_workflows = []
        for name, workflow in self.tool_chain_helper.workflows.items():
            all_workflows.append({
                "name": name,
                "description": workflow.get("description", ""),
                "steps_count": len(workflow.get("steps", []))
            })
            
        return all_workflows
        
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行特定工具
        
        Args:
            tool_name: 工具名称
            parameters: 工具参数
            
        Returns:
            Dict[str, Any]: 执行结果
            
        Raises:
            ValueError: 如果工具不存在或执行失败
        """
        if not self.initialized:
            await self.initialize()
        
        # 首先检查内部工具
        if tool_name in self.tool_chain_helper.available_tools:
            tool_instance = self.tool_chain_helper.available_tools[tool_name]["instance"]
            try:
                result = await tool_instance(**parameters)
                return {
                    "status": "success",
                    "tool": tool_name,
                    "source": "internal",
                    "result": result
                }
            except Exception as e:
                logger.error(f"执行内部工具 {tool_name} 失败: {str(e)}")
                return {
                    "status": "error",
                    "tool": tool_name,
                    "source": "internal",
                    "error": str(e)
                }
        
        # 然后检查Camel工具
        if self.toolkit_integrator and self.db:
            try:
                result = await self.toolkit_integrator.execute_tool(tool_name, parameters)
                if isinstance(result, dict) and "error" in result:
                    return {
                        "status": "error",
                        "tool": tool_name,
                        "source": "camel",
                        "error": result["error"]
                    }
                return {
                    "status": "success",
                    "tool": tool_name,
                    "source": "camel",
                    "result": result
                }
            except ValueError as e:
                # 工具不存在或未启用
                pass
            except Exception as e:
                logger.error(f"执行Camel工具 {tool_name} 失败: {str(e)}")
                return {
                    "status": "error",
                    "tool": tool_name,
                    "source": "camel",
                    "error": str(e)
                }
        
        # 工具不存在
        raise ValueError(f"工具 '{tool_name}' 不存在或未启用")
    
    async def get_tool_metadata(self, tool_name: str) -> Dict[str, Any]:
        """获取工具元数据
        
        Args:
            tool_name: 工具名称
            
        Returns:
            Dict[str, Any]: 工具元数据
            
        Raises:
            ValueError: 如果工具不存在
        """
        if not self.initialized:
            await self.initialize()
        
        # 首先检查内部工具
        if tool_name in self.tool_chain_helper.available_tools:
            tool_info = self.tool_chain_helper.available_tools[tool_name]
            tool_instance = tool_info["instance"]
            
            metadata = {
                "name": tool_name,
                "description": tool_info["description"],
                "source": "internal"
            }
            
            # 获取更多元数据（如果可用）
            if hasattr(tool_instance, "to_dict"):
                metadata.update(tool_instance.to_dict())
            elif hasattr(tool_instance, "__dict__"):
                metadata["attributes"] = {
                    k: v for k, v in tool_instance.__dict__.items() 
                    if not k.startswith("_") and not callable(v)
                }
            
            return metadata
        
        # 然后检查Camel工具
        if self.toolkit_integrator and self.db:
            tool_service = OwlToolService(self.db)
            tool = await tool_service.get_tool_by_name(tool_name)
            
            if tool:
                return {
                    "name": tool.name,
                    "description": tool.description,
                    "source": "camel",
                    "toolkit": tool.toolkit_name,
                    "function_name": tool.function_name,
                    "parameters_schema": tool.parameters_schema,
                    "requires_api_key": tool.requires_api_key,
                    "is_enabled": tool.is_enabled,
                    "created_at": tool.created_at.isoformat() if hasattr(tool, "created_at") else None,
                    "updated_at": tool.updated_at.isoformat() if hasattr(tool, "updated_at") else None
                }
        
        # 工具不存在
        raise ValueError(f"工具 '{tool_name}' 不存在")
    
    # ============================== 智能体管理 ==============================
    
    async def create_agent(self, name: str, agent_type: str, description: Optional[str] = None,
                         model_config: Optional[Dict[str, Any]] = None, 
                         system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """创建自定义智能体
        
        Args:
            name: 智能体名称
            agent_type: 智能体类型，如planner或executor
            description: 智能体描述
            model_config: 模型配置
            system_prompt: 系统提示词
            
        Returns:
            Dict[str, Any]: 创建的智能体信息
        """
        if not self.initialized:
            await self.initialize()
            
        # 生成唯一ID
        agent_id = str(uuid.uuid4())
        
        # 获取模型配置
        config = settings.owl.get_model_config(agent_type, model_config)
        
        # 创建智能体实例
        if agent_type == "planner":
            agent_instance = PlannerAgent(config)
        elif agent_type == "executor":
            agent_instance = ExecutorAgent(config)
        else:
            agent_instance = BaseAgent(config)
            
        # 设置系统提示词
        if system_prompt:
            agent_instance.set_system_message(system_prompt)
            
        # 保存智能体信息
        created_at = datetime.datetime.now().isoformat()
        self.custom_agents[agent_id] = {
            "id": agent_id,
            "name": name,
            "type": agent_type,
            "description": description,
            "system_prompt": system_prompt,
            "model_config": config,
            "instance": agent_instance,
            "created_at": created_at
        }
        
        # 返回智能体信息（不包含实例）
        return {
            "id": agent_id,
            "name": name,
            "type": agent_type,
            "description": description,
            "created_at": created_at
        }
    
    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取智能体详情
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            Optional[Dict[str, Any]]: 智能体信息，如不存在则返回None
        """
        if not self.initialized:
            await self.initialize()
            
        if agent_id not in self.custom_agents:
            return None
            
        agent_info = self.custom_agents[agent_id]
        # 返回不包含实例的信息
        return {
            "id": agent_info["id"],
            "name": agent_info["name"],
            "type": agent_info["type"],
            "description": agent_info["description"],
            "created_at": agent_info["created_at"]
        }
    
    async def get_agents(self) -> List[Dict[str, Any]]:
        """获取所有智能体
        
        Returns:
            List[Dict[str, Any]]: 智能体列表
        """
        if not self.initialized:
            await self.initialize()
            
        return [
            {
                "id": agent_info["id"],
                "name": agent_info["name"],
                "type": agent_info["type"],
                "description": agent_info["description"],
                "created_at": agent_info["created_at"]
            }
            for agent_info in self.custom_agents.values()
        ]
    
    async def delete_agent(self, agent_id: str) -> bool:
        """删除智能体
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            bool: 是否成功删除
        """
        if not self.initialized:
            await self.initialize()
            
        if agent_id not in self.custom_agents:
            return False
            
        del self.custom_agents[agent_id]
        return True
    
    # ============================== 工作流模板管理 ==============================
    
    async def create_workflow_template(self, name: str, description: str, 
                                      template: Dict[str, Any], category: Optional[str] = None) -> Dict[str, Any]:
        """创建工作流模板
        
        Args:
            name: 模板名称
            description: 模板描述
            template: 工作流模板定义
            category: 模板分类
            
        Returns:
            Dict[str, Any]: 创建的模板信息
        """
        if not self.initialized:
            await self.initialize()
            
        # 生成唯一ID
        template_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()
        
        # 注册模板
        self.workflow_manager.register_template(name, {
            "id": template_id,
            "name": name,
            "description": description,
            "template": template,
            "category": category,
            "created_at": created_at
        })
        
        # 返回模板信息
        return {
            "id": template_id,
            "name": name,
            "description": description,
            "category": category,
            "created_at": created_at
        }
    
    async def get_workflow_templates(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取工作流模板
        
        Args:
            category: 模板分类
            
        Returns:
            List[Dict[str, Any]]: 模板列表
        """
        if not self.initialized:
            await self.initialize()
            
        templates = self.workflow_manager.get_templates()
        
        # 按分类过滤
        if category:
            templates = [t for t in templates if t.get("category") == category]
            
        return templates
    
    # ============================== 自定义工具管理 ==============================
    
    async def register_custom_tool(self, name: str, description: str, function_def: Dict[str, Any],
                                 api_endpoint: Optional[str] = None, is_async: bool = False) -> Dict[str, Any]:
        """注册自定义工具
        
        Args:
            name: 工具名称
            description: 工具描述
            function_def: 函数定义
            api_endpoint: API端点，如果是远程工具
            is_async: 是否为异步工具
            
        Returns:
            Dict[str, Any]: 注册的工具信息
        """
        if not self.initialized:
            await self.initialize()
            
        # 检查工具是否已存在
        if name in self.custom_tools or name in self.tool_chain_helper.available_tools:
            raise ValueError(f"工具名称'{name}'已存在")
            
        # 生成唯一ID和创建时间
        tool_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()
        
        # 创建工具
        from app.frameworks.owl.utils.tool_factory import create_custom_tool
        custom_tool = await create_custom_tool(
            name=name,
            description=description,
            function_def=function_def,
            api_endpoint=api_endpoint,
            is_async=is_async
        )
        
        # 保存工具信息
        self.custom_tools[tool_id] = {
            "id": tool_id,
            "name": name,
            "description": description,
            "function_def": function_def,
            "api_endpoint": api_endpoint,
            "is_async": is_async,
            "tool": custom_tool,
            "created_at": created_at
        }
        
        # 注册到工具链助手
        self.tool_chain_helper.register_tool(name, custom_tool, description)
        
        # 返回工具信息
        return {
            "id": tool_id,
            "name": name,
            "description": description,
            "created_at": created_at
        }
    
    # ============================== 任务历史管理 ==============================
    
    async def get_task_history(self, task_id: Optional[str] = None, user_id: Optional[str] = None,
                            limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """获取任务历史
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            limit: 返回记录数量限制
            offset: 分页偏移量
            
        Returns:
            Dict[str, Any]: 任务历史记录及分页信息
        """
        if not self.initialized:
            await self.initialize()
            
        # 过滤历史记录
        filtered_history = list(self.task_history.values())
        
        # 按任务ID过滤
        if task_id:
            filtered_history = [h for h in filtered_history if h["id"] == task_id]
            
        # 按用户ID过滤
        if user_id:
            filtered_history = [h for h in filtered_history if h.get("user_id") == user_id]
            
        # 统计总记录数
        total = len(filtered_history)
        
        # 排序并分页
        sorted_history = sorted(filtered_history, key=lambda x: x["created_at"], reverse=True)
        paginated_history = sorted_history[offset:offset + limit]
        
        # 返回结果
        return {
            "items": paginated_history,
            "total": total,
            "offset": offset,
            "limit": limit
        }
    
    async def get_task_details(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务详情
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[Dict[str, Any]]: 任务详情，如不存在则返回None
        """
        if not self.initialized:
            await self.initialize()
            
        if task_id not in self.task_history:
            return None
            
        return self.task_history[task_id]
    
    async def _record_task(self, task: str, result: str, user_id: Optional[str] = None,
                         tools_used: Optional[List[str]] = None) -> str:
        """记录任务执行历史
        
        Args:
            task: 任务描述
            result: 任务结果
            user_id: 用户ID
            tools_used: 使用的工具列表
            
        Returns:
            str: 任务ID
        """
        # 生成唯一ID
        task_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()
        
        # 保存任务历史
        self.task_history[task_id] = {
            "id": task_id,
            "task": task,
            "result": result,
            "user_id": user_id,
            "tools_used": tools_used or [],
            "created_at": created_at
        }
        
        return task_id
