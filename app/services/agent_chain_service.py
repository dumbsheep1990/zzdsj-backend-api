"""
智能体链服务模块
管理智能体执行链和状态相关的业务逻辑
"""

from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from app.utils.database import get_db
from app.models.agent_run import AgentRun
from app.services.agent_service import AgentService
from app.services.tool_execution_service import ToolExecutionService
from app.services.resource_permission_service import ResourcePermissionService

class AgentChainService:
    """智能体链服务类"""
    
    def __init__(self, 
                 db: Session = Depends(get_db),
                 agent_service: AgentService = Depends(),
                 tool_execution_service: ToolExecutionService = Depends(),
                 permission_service: ResourcePermissionService = Depends()):
        """初始化智能体链服务
        
        Args:
            db: 数据库会话
            agent_service: 智能体服务
            tool_execution_service: 工具执行服务
            permission_service: 资源权限服务
        """
        self.db = db
        self.agent_service = agent_service
        self.tool_execution_service = tool_execution_service
        self.permission_service = permission_service
        # 内存中的链状态映射
        self.chain_states = {}
    
    async def create_chain(self, 
                        agent_definition_id: str, 
                        inputs: Dict[str, Any],
                        user_id: str) -> Dict[str, Any]:
        """创建并启动智能体执行链
        
        Args:
            agent_definition_id: 智能体定义ID
            inputs: 输入参数
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 包含链ID和状态信息的字典
            
        Raises:
            HTTPException: 如果没有权限或智能体定义不存在
        """
        # 检查智能体定义
        agent_definition = await self.agent_service.get_agent_definition(agent_definition_id, user_id)
        if not agent_definition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="智能体定义不存在"
            )
        
        # 生成链ID
        chain_id = str(uuid.uuid4())
        
        # 创建智能体运行记录
        run_data = {
            "agent_definition_id": agent_definition_id,
            "chain_id": chain_id,
            "inputs": inputs,
            "status": "running"
        }
        agent_run = await self.agent_service.create_agent_run(run_data, user_id)
        
        # 初始化链状态
        self.chain_states[chain_id] = {
            "agent_run_id": agent_run.id,
            "status": "running",
            "steps": [],
            "current_step": 0,
            "inputs": inputs,
            "outputs": {},
            "errors": [],
            "tools_used": []
        }
        
        # 启动链（实际执行逻辑应在异步任务中完成）
        # 这里简化为返回初始状态
        return {
            "chain_id": chain_id,
            "agent_run_id": agent_run.id,
            "status": "running",
            "message": "智能体链已启动"
        }
    
    async def get_chain_state(self, chain_id: str, user_id: str) -> Dict[str, Any]:
        """获取智能体链状态
        
        Args:
            chain_id: 链ID
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 链状态信息
            
        Raises:
            HTTPException: 如果链不存在或没有权限
        """
        # 检查链是否存在
        if chain_id not in self.chain_states:
            # 尝试从数据库加载
            agent_run = await self._get_agent_run_by_chain_id(chain_id, user_id)
            if not agent_run:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="智能体链不存在"
                )
            
            # 重建链状态
            self.chain_states[chain_id] = {
                "agent_run_id": agent_run.id,
                "status": agent_run.status,
                "steps": agent_run.steps if hasattr(agent_run, 'steps') and agent_run.steps else [],
                "current_step": len(agent_run.steps) if hasattr(agent_run, 'steps') and agent_run.steps else 0,
                "inputs": agent_run.inputs,
                "outputs": agent_run.result if agent_run.result else {},
                "errors": agent_run.errors if hasattr(agent_run, 'errors') and agent_run.errors else [],
                "tools_used": []  # 需要从工具执行记录中加载
            }
            
            # 加载工具执行记录
            if agent_run.id:
                tool_executions = await self.tool_execution_service.list_executions_by_agent_run(agent_run.id, user_id)
                self.chain_states[chain_id]["tools_used"] = [
                    {
                        "tool_id": execution.tool_id,
                        "execution_id": execution.id,
                        "status": execution.status,
                        "input_params": execution.input_params,
                        "output_result": execution.output_result
                    }
                    for execution in tool_executions
                ]
        
        return self.chain_states[chain_id]
    
    async def update_chain_step(self, 
                             chain_id: str, 
                             step_data: Dict[str, Any],
                             user_id: str) -> Dict[str, Any]:
        """更新智能体链步骤
        
        Args:
            chain_id: 链ID
            step_data: 步骤数据
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 更新后的链状态
            
        Raises:
            HTTPException: 如果链不存在或没有权限
        """
        # 获取链状态
        chain_state = await self.get_chain_state(chain_id, user_id)
        
        # 添加步骤
        chain_state["steps"].append(step_data)
        chain_state["current_step"] += 1
        
        # 更新链状态
        self.chain_states[chain_id] = chain_state
        
        # 更新数据库中的智能体运行记录
        await self.agent_service.update_agent_run_status(
            chain_state["agent_run_id"],
            chain_state["status"],
            {"steps": chain_state["steps"]},
            user_id
        )
        
        return chain_state
    
    async def execute_tool_in_chain(self, 
                                 chain_id: str, 
                                 tool_id: str,
                                 input_params: Dict[str, Any],
                                 user_id: str) -> Dict[str, Any]:
        """在智能体链中执行工具
        
        Args:
            chain_id: 链ID
            tool_id: 工具ID
            input_params: 输入参数
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 工具执行结果
            
        Raises:
            HTTPException: 如果链不存在、工具不存在或没有权限
        """
        # 获取链状态
        chain_state = await self.get_chain_state(chain_id, user_id)
        
        # 执行工具
        result = await self.tool_execution_service.execute_tool(
            tool_id, 
            input_params, 
            user_id, 
            chain_state["agent_run_id"]
        )
        
        # 更新链状态
        tool_usage = {
            "tool_id": tool_id,
            "execution_id": result.get("execution_id"),
            "status": result.get("status"),
            "input_params": input_params,
            "output_result": result.get("result")
        }
        chain_state["tools_used"].append(tool_usage)
        self.chain_states[chain_id] = chain_state
        
        return result
    
    async def complete_chain(self, 
                          chain_id: str, 
                          outputs: Dict[str, Any],
                          user_id: str) -> Dict[str, Any]:
        """完成智能体链
        
        Args:
            chain_id: 链ID
            outputs: 输出结果
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 完成后的链状态
            
        Raises:
            HTTPException: 如果链不存在或没有权限
        """
        # 获取链状态
        chain_state = await self.get_chain_state(chain_id, user_id)
        
        # 更新状态为完成
        chain_state["status"] = "completed"
        chain_state["outputs"] = outputs
        self.chain_states[chain_id] = chain_state
        
        # 更新数据库中的智能体运行记录
        await self.agent_service.update_agent_run_status(
            chain_state["agent_run_id"],
            "completed",
            outputs,
            user_id
        )
        
        return chain_state
    
    async def fail_chain(self, 
                      chain_id: str, 
                      error: str,
                      user_id: str) -> Dict[str, Any]:
        """标记智能体链失败
        
        Args:
            chain_id: 链ID
            error: 错误信息
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 更新后的链状态
            
        Raises:
            HTTPException: 如果链不存在或没有权限
        """
        # 获取链状态
        chain_state = await self.get_chain_state(chain_id, user_id)
        
        # 更新状态为失败
        chain_state["status"] = "failed"
        chain_state["errors"].append(error)
        self.chain_states[chain_id] = chain_state
        
        # 更新数据库中的智能体运行记录
        await self.agent_service.update_agent_run_status(
            chain_state["agent_run_id"],
            "failed",
            {"errors": chain_state["errors"]},
            user_id
        )
        
        return chain_state
    
    async def list_active_chains(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的活跃智能体链列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Dict[str, Any]]: 活跃链状态列表
        """
        # 加载用户的所有运行中的智能体运行记录
        agent_runs = await self.agent_service.list_agent_runs_by_user(user_id)
        active_runs = [run for run in agent_runs if run.status == "running"]
        
        # 返回链状态
        active_chains = []
        for run in active_runs:
            if run.chain_id and run.chain_id in self.chain_states:
                active_chains.append(self.chain_states[run.chain_id])
            else:
                # 重建链状态
                chain_state = {
                    "chain_id": run.chain_id,
                    "agent_run_id": run.id,
                    "status": run.status,
                    "steps": run.steps if hasattr(run, 'steps') and run.steps else [],
                    "current_step": len(run.steps) if hasattr(run, 'steps') and run.steps else 0,
                    "inputs": run.inputs,
                    "outputs": run.result if run.result else {},
                    "errors": run.errors if hasattr(run, 'errors') and run.errors else [],
                    "tools_used": []  # 需要从工具执行记录中加载
                }
                
                # 缓存链状态
                if run.chain_id:
                    self.chain_states[run.chain_id] = chain_state
                
                active_chains.append(chain_state)
        
        return active_chains
    
    async def _get_agent_run_by_chain_id(self, chain_id: str, user_id: str) -> Optional[AgentRun]:
        """通过链ID获取智能体运行记录
        
        Args:
            chain_id: 链ID
            user_id: 用户ID
            
        Returns:
            Optional[AgentRun]: 获取的智能体运行实例或None
        """
        # 这里应该实现通过链ID查询智能体运行记录的逻辑
        # 由于Repository中可能没有直接通过chain_id查询的方法
        # 先获取所有记录，再进行过滤
        all_runs = await self.agent_service.list_agent_runs_by_user(user_id)
        for run in all_runs:
            if hasattr(run, 'chain_id') and run.chain_id == chain_id:
                return run
        
        # 管理员可以查看所有链
        if await self._check_admin_permission(user_id):
            # 实现管理员查询所有运行记录的逻辑
            # ...
            pass
        
        return None
    
    async def _check_admin_permission(self, user_id: str) -> bool:
        """检查用户是否为管理员
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否为管理员
        """
        from app.services.user_service import UserService
        user_service = UserService(self.db)
        user = await user_service.get_by_id(user_id)
        return user and user.role == "admin"
