"""
工具执行记录仓库模块
提供对工具执行记录的CRUD操作
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.tool_execution import ToolExecution
from app.repositories.base import BaseRepository

class ToolExecutionRepository(BaseRepository):
    """工具执行记录仓库类"""
    
    async def create(self, data: Dict[str, Any], db: Session) -> ToolExecution:
        """创建工具执行记录
        
        Args:
            data: 工具执行记录数据
            db: 数据库会话
            
        Returns:
            ToolExecution: 创建的工具执行记录实例
        """
        tool_execution = ToolExecution(**data)
        db.add(tool_execution)
        db.commit()
        db.refresh(tool_execution)
        return tool_execution
    
    async def get_by_id(self, execution_id: str, db: Session) -> Optional[ToolExecution]:
        """通过ID获取工具执行记录
        
        Args:
            execution_id: 工具执行记录ID
            db: 数据库会话
            
        Returns:
            Optional[ToolExecution]: 查找到的工具执行记录或None
        """
        return db.query(ToolExecution).filter(ToolExecution.id == execution_id).first()
    
    async def list_by_tool_id(self, tool_id: str, skip: int = 0, limit: int = 100, db: Session) -> List[ToolExecution]:
        """获取指定工具的执行记录列表
        
        Args:
            tool_id: 工具ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            db: 数据库会话
            
        Returns:
            List[ToolExecution]: 工具执行记录列表
        """
        return db.query(ToolExecution)\
            .filter(ToolExecution.tool_id == tool_id)\
            .order_by(desc(ToolExecution.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()
    
    async def list_by_agent_run_id(self, agent_run_id: str, db: Session) -> List[ToolExecution]:
        """获取指定智能体运行的工具执行记录列表
        
        Args:
            agent_run_id: 智能体运行ID
            db: 数据库会话
            
        Returns:
            List[ToolExecution]: 工具执行记录列表
        """
        return db.query(ToolExecution)\
            .filter(ToolExecution.agent_run_id == agent_run_id)\
            .order_by(ToolExecution.created_at)\
            .all()
    
    async def list_by_user_id(self, user_id: str, skip: int = 0, limit: int = 100, db: Session) -> List[ToolExecution]:
        """获取指定用户的工具执行记录列表
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            db: 数据库会话
            
        Returns:
            List[ToolExecution]: 工具执行记录列表
        """
        return db.query(ToolExecution)\
            .filter(ToolExecution.user_id == user_id)\
            .order_by(desc(ToolExecution.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()
    
    async def update(self, execution_id: str, data: Dict[str, Any], db: Session) -> Optional[ToolExecution]:
        """更新工具执行记录
        
        Args:
            execution_id: 工具执行记录ID
            data: 更新数据
            db: 数据库会话
            
        Returns:
            Optional[ToolExecution]: 更新后的工具执行记录或None
        """
        tool_execution = await self.get_by_id(execution_id, db)
        if not tool_execution:
            return None
        
        for key, value in data.items():
            setattr(tool_execution, key, value)
        
        db.commit()
        db.refresh(tool_execution)
        return tool_execution
    
    async def mark_complete(self, execution_id: str, output_result: Dict[str, Any], 
                         execution_time: int, db: Session) -> Optional[ToolExecution]:
        """标记工具执行完成
        
        Args:
            execution_id: 工具执行记录ID
            output_result: 输出结果
            execution_time: 执行时间(毫秒)
            db: 数据库会话
            
        Returns:
            Optional[ToolExecution]: 更新后的工具执行记录或None
        """
        tool_execution = await self.get_by_id(execution_id, db)
        if not tool_execution:
            return None
        
        tool_execution.output_result = output_result
        tool_execution.status = 'success'
        tool_execution.execution_time = execution_time
        tool_execution.completed_at = db.query(func.now()).scalar()
        
        db.commit()
        db.refresh(tool_execution)
        return tool_execution
    
    async def mark_failed(self, execution_id: str, error_message: str, 
                       execution_time: Optional[int] = None, db: Session = None) -> Optional[ToolExecution]:
        """标记工具执行失败
        
        Args:
            execution_id: 工具执行记录ID
            error_message: 错误信息
            execution_time: 执行时间(毫秒) (可选)
            db: 数据库会话
            
        Returns:
            Optional[ToolExecution]: 更新后的工具执行记录或None
        """
        tool_execution = await self.get_by_id(execution_id, db)
        if not tool_execution:
            return None
        
        tool_execution.error_message = error_message
        tool_execution.status = 'failed'
        if execution_time is not None:
            tool_execution.execution_time = execution_time
        tool_execution.completed_at = db.query(func.now()).scalar()
        
        db.commit()
        db.refresh(tool_execution)
        return tool_execution
    
    async def delete(self, execution_id: str, db: Session) -> bool:
        """删除工具执行记录
        
        Args:
            execution_id: 工具执行记录ID
            db: 数据库会话
            
        Returns:
            bool: 是否成功删除
        """
        tool_execution = await self.get_by_id(execution_id, db)
        if not tool_execution:
            return False
        
        db.delete(tool_execution)
        db.commit()
        return True
