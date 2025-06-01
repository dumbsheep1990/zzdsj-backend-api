"""
智能体链服务模块
管理智能体执行链和状态相关的业务逻辑
已重构为使用核心业务逻辑层，遵循分层架构原则
"""

from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from app.utils.core.database import get_db

# 导入核心业务逻辑层
from core.agents import ChainManager

from app.services.resource_permission_service import ResourcePermissionService
from app.repositories.agent_run_repository import AgentRunRepository

class AgentChainService:
    """智能体链服务类 - 已重构为使用核心业务逻辑层"""
    
    def __init__(self, 
                 db: Session = Depends(get_db),
                 permission_service: ResourcePermissionService = Depends()):
        """初始化智能体链服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
        """
        self.db = db
        self.permission_service = permission_service
        
        # 使用核心业务逻辑层
        self.chain_manager = ChainManager(db)
    
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
        try:
            # 检查智能体定义权限
            has_permission = await self.permission_service.check_permission(
                "agent_definition", agent_definition_id, user_id, "use"
            ) or await self._check_admin_permission(user_id)
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="没有权限使用此智能体定义"
                )
            
            # 使用核心层创建链
            result = await self.chain_manager.create_chain(
                agent_definition_id, inputs, user_id
            )
            
            if not result["success"]:
                if result.get("error_code") == "AGENT_NOT_FOUND":
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="智能体定义不存在"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=result["error"]
                    )
            
            # 返回兼容格式
            return result["data"]
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建智能体链失败: {str(e)}"
            )
    
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
        try:
            # 使用核心层获取链状态
            result = await self.chain_manager.get_chain_state(chain_id)
            
            if not result["success"]:
                if result.get("error_code") == "CHAIN_NOT_FOUND":
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="智能体链不存在"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=result["error"]
                    )
            
            chain_state = result["data"]
            
            # 检查权限（检查智能体定义权限）
            has_permission = await self.permission_service.check_permission(
                "agent_definition", chain_state["agent_definition_id"], user_id, "read"
            ) or await self._check_admin_permission(user_id)
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="没有权限访问此智能体链"
                )
            
            return chain_state
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取链状态失败: {str(e)}"
            )
    
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
        try:
            # 先获取链状态以检查权限
            chain_state = await self.get_chain_state(chain_id, user_id)
            
            # 检查编辑权限
            has_permission = await self.permission_service.check_permission(
                "agent_definition", chain_state["agent_definition_id"], user_id, "edit"
            ) or await self._check_admin_permission(user_id)
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="没有权限更新此智能体链"
                )
            
            # 使用核心层更新链步骤
            result = await self.chain_manager.update_chain_step(chain_id, step_data)
            
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["error"]
                )
            
            return result["data"]
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新链步骤失败: {str(e)}"
            )
    
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
        try:
            # 先获取链状态以检查权限
            chain_state = await self.get_chain_state(chain_id, user_id)
            
            # 检查工具使用权限
            has_tool_permission = await self.permission_service.check_permission(
                "tool", tool_id, user_id, "use"
            ) or await self._check_admin_permission(user_id)
            
            if not has_tool_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="没有权限使用此工具"
                )
            
            # 这里需要集成工具执行逻辑
            # 由于我们要避免直接依赖其他服务，这里先返回模拟结果
            # 实际实现中应该通过核心层来协调工具执行
            
            execution_id = str(uuid.uuid4())
            tool_execution_result = {
                "execution_id": execution_id,
                "tool_id": tool_id,
                "status": "completed",
                "input_params": input_params,
                "output_result": {"message": "工具执行成功（模拟结果）"},
                "execution_time": 100
            }
            
            # 添加工具执行记录到链
            add_result = await self.chain_manager.add_tool_execution(
                chain_id, tool_execution_result
            )
            
            if not add_result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=add_result["error"]
                )
            
            return {
                "execution_id": execution_id,
                "status": "success",
                "result": tool_execution_result["output_result"],
                "execution_time": tool_execution_result["execution_time"]
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"在链中执行工具失败: {str(e)}"
            )
    
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
        try:
            # 先获取链状态以检查权限
            chain_state = await self.get_chain_state(chain_id, user_id)
            
            # 检查编辑权限
            has_permission = await self.permission_service.check_permission(
                "agent_definition", chain_state["agent_definition_id"], user_id, "edit"
            ) or await self._check_admin_permission(user_id)
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="没有权限完成此智能体链"
                )
            
            # 使用核心层完成链
            result = await self.chain_manager.complete_chain(chain_id, outputs)
            
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["error"]
                )
            
            return result["data"]
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"完成链执行失败: {str(e)}"
            )
    
    async def fail_chain(self, 
                        chain_id: str, 
                        error_message: str,
                        user_id: str,
                        error_details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """标记智能体链为失败状态
        
        Args:
            chain_id: 链ID
            error_message: 错误消息
            user_id: 用户ID
            error_details: 错误详情
            
        Returns:
            Dict[str, Any]: 失败后的链状态
            
        Raises:
            HTTPException: 如果链不存在或没有权限
        """
        try:
            # 先获取链状态以检查权限
            chain_state = await self.get_chain_state(chain_id, user_id)
            
            # 检查编辑权限
            has_permission = await self.permission_service.check_permission(
                "agent_definition", chain_state["agent_definition_id"], user_id, "edit"
            ) or await self._check_admin_permission(user_id)
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="没有权限标记此智能体链为失败"
                )
            
            # 使用核心层标记链失败
            result = await self.chain_manager.fail_chain(
                chain_id, error_message, error_details
            )
            
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["error"]
                )
            
            return result["data"]
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"标记链失败状态失败: {str(e)}"
            )
    
    async def list_active_chains(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的活跃智能体链列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Dict[str, Any]]: 活跃链状态列表
        """
        try:
            # 使用核心层获取活跃链列表
            result = await self.chain_manager.list_active_chains(user_id)
            
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["error"]
                )
            
            active_chains = result["data"]["chains"]
            
            # 过滤用户有权限的链
            filtered_chains = []
            for chain in active_chains:
                try:
                    has_permission = await self.permission_service.check_permission(
                        "agent_definition", chain["agent_definition_id"], user_id, "read"
                    ) or await self._check_admin_permission(user_id)
                    
                    if has_permission:
                        filtered_chains.append(chain)
                except:
                    # 忽略权限检查失败的链
                    continue
            
            return filtered_chains
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取活跃链列表失败: {str(e)}"
            )
    
    async def cleanup_completed_chains(self, user_id: str, max_age_hours: int = 24) -> Dict[str, Any]:
        """清理已完成的链状态
        
        Args:
            user_id: 用户ID
            max_age_hours: 最大保留时间（小时）
            
        Returns:
            Dict[str, Any]: 清理结果
            
        Raises:
            HTTPException: 如果没有权限
        """
        try:
            # 检查管理员权限
            is_admin = await self._check_admin_permission(user_id)
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="只有管理员可以清理链状态"
                )
            
            # 使用核心层清理已完成的链
            result = await self.chain_manager.cleanup_completed_chains(max_age_hours)
            
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["error"]
                )
            
            return result["data"]
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"清理已完成链失败: {str(e)}"
            )
    
    # 私有辅助方法
    
    async def _check_admin_permission(self, user_id: str) -> bool:
        """检查用户是否为管理员
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否为管理员
        """
        try:
            # 这里应该实现实际的管理员权限检查逻辑
            # 暂时返回False，实际应该检查用户角色
            return False
        except Exception:
            return False
