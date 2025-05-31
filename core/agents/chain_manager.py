"""
智能体链管理器
处理智能体执行链的核心业务逻辑
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import uuid
import json
from datetime import datetime

from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.conversation_chain_repository import ConversationChainRepository
from .agent_manager import AgentManager


class ChainManager:
    """智能体链管理器"""
    
    def __init__(self, db: Session):
        """初始化链管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.agent_run_repository = AgentRunRepository()
        self.agent_manager = AgentManager(db)
        
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
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证智能体定义是否存在
            agent_result = await self.agent_manager.get_agent_definition(agent_definition_id)
            if not agent_result["success"]:
                return {
                    "success": False,
                    "error": "智能体定义不存在",
                    "error_code": "AGENT_NOT_FOUND"
                }
            
            # 生成链ID
            chain_id = str(uuid.uuid4())
            
            # 创建智能体运行记录
            run_data = {
                "agent_definition_id": agent_definition_id,
                "chain_id": chain_id,
                "inputs": inputs,
                "status": "running",
                "user_id": user_id,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            agent_run = await self.agent_run_repository.create(run_data, self.db)
            
            # 初始化链状态
            self.chain_states[chain_id] = {
                "chain_id": chain_id,
                "agent_run_id": agent_run.id,
                "agent_definition_id": agent_definition_id,
                "status": "running",
                "steps": [],
                "current_step": 0,
                "inputs": inputs,
                "outputs": {},
                "errors": [],
                "tools_used": [],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            return {
                "success": True,
                "data": {
                    "chain_id": chain_id,
                    "agent_run_id": agent_run.id,
                    "status": "running",
                    "message": "智能体链已启动"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"创建智能体链失败: {str(e)}",
                "error_code": "CHAIN_CREATION_FAILED"
            }
    
    async def get_chain_state(self, chain_id: str) -> Dict[str, Any]:
        """获取智能体链状态
        
        Args:
            chain_id: 链ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查内存中是否存在链状态
            if chain_id in self.chain_states:
                return {
                    "success": True,
                    "data": self.chain_states[chain_id]
                }
            
            # 尝试从数据库加载
            agent_run = await self._get_agent_run_by_chain_id(chain_id)
            if not agent_run:
                return {
                    "success": False,
                    "error": "智能体链不存在",
                    "error_code": "CHAIN_NOT_FOUND"
                }
            
            # 重建链状态
            chain_state = {
                "chain_id": chain_id,
                "agent_run_id": agent_run.id,
                "agent_definition_id": agent_run.agent_definition_id,
                "status": agent_run.status,
                "steps": self._parse_steps(agent_run.steps) if hasattr(agent_run, 'steps') and agent_run.steps else [],
                "current_step": 0,
                "inputs": agent_run.inputs,
                "outputs": agent_run.result if agent_run.result else {},
                "errors": self._parse_errors(agent_run.errors) if hasattr(agent_run, 'errors') and agent_run.errors else [],
                "tools_used": [],
                "created_at": agent_run.created_at,
                "updated_at": agent_run.updated_at
            }
            
            # 计算当前步骤
            chain_state["current_step"] = len(chain_state["steps"])
            
            # 缓存链状态
            self.chain_states[chain_id] = chain_state
            
            return {
                "success": True,
                "data": chain_state
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取链状态失败: {str(e)}",
                "error_code": "GET_CHAIN_STATE_FAILED"
            }
    
    async def update_chain_step(self, 
                               chain_id: str, 
                               step_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新智能体链步骤
        
        Args:
            chain_id: 链ID
            step_data: 步骤数据
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 获取链状态
            state_result = await self.get_chain_state(chain_id)
            if not state_result["success"]:
                return state_result
            
            chain_state = state_result["data"]
            
            # 添加步骤
            step_with_metadata = {
                **step_data,
                "step_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "position": chain_state["current_step"]
            }
            
            chain_state["steps"].append(step_with_metadata)
            chain_state["current_step"] += 1
            chain_state["updated_at"] = datetime.now()
            
            # 更新内存状态
            self.chain_states[chain_id] = chain_state
            
            # 更新数据库中的智能体运行记录
            await self._update_agent_run_steps(
                chain_state["agent_run_id"],
                chain_state["steps"]
            )
            
            return {
                "success": True,
                "data": chain_state
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"更新链步骤失败: {str(e)}",
                "error_code": "UPDATE_CHAIN_STEP_FAILED"
            }
    
    async def add_tool_execution(self, 
                                chain_id: str, 
                                tool_execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加工具执行记录到链
        
        Args:
            chain_id: 链ID
            tool_execution_data: 工具执行数据
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 获取链状态
            state_result = await self.get_chain_state(chain_id)
            if not state_result["success"]:
                return state_result
            
            chain_state = state_result["data"]
            
            # 添加工具执行记录
            tool_usage = {
                **tool_execution_data,
                "timestamp": datetime.now().isoformat(),
                "chain_step": chain_state["current_step"]
            }
            
            chain_state["tools_used"].append(tool_usage)
            chain_state["updated_at"] = datetime.now()
            
            # 更新内存状态
            self.chain_states[chain_id] = chain_state
            
            return {
                "success": True,
                "data": chain_state
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"添加工具执行记录失败: {str(e)}",
                "error_code": "ADD_TOOL_EXECUTION_FAILED"
            }
    
    async def complete_chain(self, 
                            chain_id: str, 
                            outputs: Dict[str, Any],
                            status: str = "completed") -> Dict[str, Any]:
        """完成智能体链
        
        Args:
            chain_id: 链ID
            outputs: 输出结果
            status: 最终状态
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 获取链状态
            state_result = await self.get_chain_state(chain_id)
            if not state_result["success"]:
                return state_result
            
            chain_state = state_result["data"]
            
            # 更新状态为完成
            chain_state["status"] = status
            chain_state["outputs"] = outputs
            chain_state["updated_at"] = datetime.now()
            
            # 更新内存状态
            self.chain_states[chain_id] = chain_state
            
            # 更新数据库中的智能体运行记录
            await self.agent_run_repository.update(
                chain_state["agent_run_id"],
                {
                    "status": status,
                    "result": outputs,
                    "updated_at": datetime.now()
                },
                self.db
            )
            
            return {
                "success": True,
                "data": chain_state
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"完成链执行失败: {str(e)}",
                "error_code": "COMPLETE_CHAIN_FAILED"
            }
    
    async def fail_chain(self, 
                        chain_id: str, 
                        error_message: str,
                        error_details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """标记智能体链为失败状态
        
        Args:
            chain_id: 链ID
            error_message: 错误消息
            error_details: 错误详情
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 获取链状态
            state_result = await self.get_chain_state(chain_id)
            if not state_result["success"]:
                return state_result
            
            chain_state = state_result["data"]
            
            # 添加错误信息
            error_record = {
                "message": error_message,
                "details": error_details or {},
                "timestamp": datetime.now().isoformat(),
                "step": chain_state["current_step"]
            }
            
            chain_state["errors"].append(error_record)
            chain_state["status"] = "failed"
            chain_state["updated_at"] = datetime.now()
            
            # 更新内存状态
            self.chain_states[chain_id] = chain_state
            
            # 更新数据库中的智能体运行记录
            await self.agent_run_repository.update(
                chain_state["agent_run_id"],
                {
                    "status": "failed",
                    "errors": chain_state["errors"],
                    "updated_at": datetime.now()
                },
                self.db
            )
            
            return {
                "success": True,
                "data": chain_state
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"标记链失败状态失败: {str(e)}",
                "error_code": "FAIL_CHAIN_FAILED"
            }
    
    async def list_active_chains(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取活跃的智能体链列表
        
        Args:
            user_id: 用户ID（可选，用于过滤）
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 从内存中获取活跃链
            active_chains = []
            for chain_id, chain_state in self.chain_states.items():
                if chain_state["status"] in ["running", "pending"]:
                    if user_id is None or self._chain_belongs_to_user(chain_state, user_id):
                        active_chains.append(chain_state)
            
            # 从数据库加载可能遗漏的活跃链
            db_active_runs = await self.agent_run_repository.list_by_status("running", self.db)
            
            for run in db_active_runs:
                if run.chain_id and run.chain_id not in self.chain_states:
                    # 重建链状态
                    chain_state = {
                        "chain_id": run.chain_id,
                        "agent_run_id": run.id,
                        "agent_definition_id": run.agent_definition_id,
                        "status": run.status,
                        "steps": self._parse_steps(run.steps) if hasattr(run, 'steps') and run.steps else [],
                        "current_step": 0,
                        "inputs": run.inputs,
                        "outputs": run.result if run.result else {},
                        "errors": self._parse_errors(run.errors) if hasattr(run, 'errors') and run.errors else [],
                        "tools_used": [],
                        "created_at": run.created_at,
                        "updated_at": run.updated_at
                    }
                    
                    chain_state["current_step"] = len(chain_state["steps"])
                    
                    # 缓存链状态
                    self.chain_states[run.chain_id] = chain_state
                    
                    if user_id is None or self._chain_belongs_to_user(chain_state, user_id):
                        active_chains.append(chain_state)
            
            return {
                "success": True,
                "data": {
                    "chains": active_chains,
                    "total": len(active_chains)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取活跃链列表失败: {str(e)}",
                "error_code": "LIST_ACTIVE_CHAINS_FAILED"
            }
    
    async def cleanup_completed_chains(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """清理已完成的链状态（从内存中移除）
        
        Args:
            max_age_hours: 最大保留时间（小时）
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            current_time = datetime.now()
            chains_to_remove = []
            
            for chain_id, chain_state in self.chain_states.items():
                if chain_state["status"] in ["completed", "failed", "cancelled"]:
                    # 检查是否超过最大保留时间
                    updated_at = chain_state.get("updated_at")
                    if isinstance(updated_at, str):
                        updated_at = datetime.fromisoformat(updated_at)
                    elif not isinstance(updated_at, datetime):
                        updated_at = datetime.now()
                    
                    age_hours = (current_time - updated_at).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        chains_to_remove.append(chain_id)
            
            # 移除过期的链状态
            for chain_id in chains_to_remove:
                del self.chain_states[chain_id]
            
            return {
                "success": True,
                "data": {
                    "removed_chains": len(chains_to_remove),
                    "remaining_chains": len(self.chain_states)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"清理已完成链失败: {str(e)}",
                "error_code": "CLEANUP_CHAINS_FAILED"
            }
    
    # 私有辅助方法
    
    async def _get_agent_run_by_chain_id(self, chain_id: str):
        """根据链ID获取智能体运行记录"""
        try:
            # 这里需要在repository中添加相应的方法
            # 暂时使用简单的查询逻辑
            runs = await self.agent_run_repository.list_all(0, 1000, self.db)
            for run in runs:
                if hasattr(run, 'chain_id') and run.chain_id == chain_id:
                    return run
            return None
        except Exception:
            return None
    
    async def _update_agent_run_steps(self, agent_run_id: str, steps: List[Dict[str, Any]]):
        """更新智能体运行记录的步骤"""
        try:
            await self.agent_run_repository.update(
                agent_run_id,
                {
                    "steps": steps,
                    "updated_at": datetime.now()
                },
                self.db
            )
        except Exception:
            pass  # 忽略更新失败
    
    def _parse_steps(self, steps_data: Any) -> List[Dict[str, Any]]:
        """解析步骤数据"""
        if isinstance(steps_data, list):
            return steps_data
        elif isinstance(steps_data, str):
            try:
                return json.loads(steps_data)
            except:
                return []
        else:
            return []
    
    def _parse_errors(self, errors_data: Any) -> List[Dict[str, Any]]:
        """解析错误数据"""
        if isinstance(errors_data, list):
            return errors_data
        elif isinstance(errors_data, str):
            try:
                return json.loads(errors_data)
            except:
                return []
        else:
            return []
    
    def _chain_belongs_to_user(self, chain_state: Dict[str, Any], user_id: str) -> bool:
        """检查链是否属于指定用户"""
        # 这里需要根据实际的用户关联逻辑来实现
        # 暂时返回True，实际应该检查agent_run的user_id
        return True 