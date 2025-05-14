from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from datetime import datetime
from app.models.agent_run import AgentRun

class AgentRunRepository:
    """智能体运行记录仓库"""
    
    async def create(self, data: Dict[str, Any], db: Session) -> AgentRun:
        """创建智能体运行记录
        
        Args:
            data: 创建数据
            db: 数据库会话
            
        Returns:
            AgentRun: 创建的智能体运行记录
        """
        run = AgentRun(**data)
        db.add(run)
        await db.commit()
        await db.refresh(run)
        return run
    
    async def get_by_id(self, run_id: int, db: Session) -> Optional[AgentRun]:
        """通过ID获取智能体运行记录
        
        Args:
            run_id: 运行记录ID
            db: 数据库会话
            
        Returns:
            Optional[AgentRun]: 智能体运行记录，不存在则返回None
        """
        query = select(AgentRun).where(AgentRun.id == run_id)
        result = await db.execute(query)
        return result.scalars().first()
    
    async def get_all(
        self, db: Session, skip: int = 0, limit: int = 100, 
        user_id: Optional[int] = None, agent_definition_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[AgentRun]:
        """获取所有智能体运行记录
        
        Args:
            db: 数据库会话
            skip: 跳过数量
            limit: 限制数量
            user_id: 用户ID筛选
            agent_definition_id: 智能体定义ID筛选
            status: 状态筛选
            
        Returns:
            List[AgentRun]: 智能体运行记录列表
        """
        query = select(AgentRun)
        
        # 应用筛选条件
        if user_id is not None:
            query = query.where(AgentRun.user_id == user_id)
        if agent_definition_id is not None:
            query = query.where(AgentRun.agent_definition_id == agent_definition_id)
        if status is not None:
            query = query.where(AgentRun.status == status)
            
        # 按创建时间降序排序
        query = query.order_by(AgentRun.created_at.desc())
            
        # 应用分页
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def update_status(
        self, run_id: int, status: str, 
        result: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> Optional[AgentRun]:
        """更新智能体运行状态
        
        Args:
            run_id: 运行记录ID
            status: 新状态
            result: 运行结果
            error: 错误信息
            metadata: 元数据
            db: 数据库会话
            
        Returns:
            Optional[AgentRun]: 更新后的智能体运行记录，不存在则返回None
        """
        run = await self.get_by_id(run_id, db)
        if not run:
            return None
            
        # 更新状态
        run.status = status
        
        # 更新结果（如果提供）
        if result is not None:
            run.result = result
            
        # 更新错误信息（如果提供）
        if error is not None:
            run.error = error
            
        # 更新元数据（如果提供）
        if metadata is not None:
            if run.metadata is None:
                run.metadata = metadata
            else:
                run.metadata.update(metadata)
                
        # 如果是完成状态，设置结束时间和持续时间
        if status in ["completed", "failed"]:
            now = datetime.now().isoformat()
            run.end_time = now
            
            # 计算持续时间
            if run.start_time:
                start_time = datetime.fromisoformat(run.start_time)
                end_time = datetime.fromisoformat(now)
                run.duration = (end_time - start_time).total_seconds()
        
        await db.commit()
        await db.refresh(run)
        return run
    
    async def add_tool_call(
        self, run_id: int, tool_call: Dict[str, Any], db: Session
    ) -> Optional[AgentRun]:
        """添加工具调用记录
        
        Args:
            run_id: 运行记录ID
            tool_call: 工具调用信息
            db: 数据库会话
            
        Returns:
            Optional[AgentRun]: 更新后的智能体运行记录，不存在则返回None
        """
        run = await self.get_by_id(run_id, db)
        if not run:
            return None
            
        # 初始化工具调用列表（如果不存在）
        if run.tool_calls is None:
            run.tool_calls = []
            
        # 添加调用记录
        run.tool_calls.append(tool_call)
        
        await db.commit()
        await db.refresh(run)
        return run
    
    async def delete(self, run_id: int, db: Session) -> bool:
        """删除智能体运行记录
        
        Args:
            run_id: 运行记录ID
            db: 数据库会话
            
        Returns:
            bool: 是否成功删除
        """
        run = await self.get_by_id(run_id, db)
        if not run:
            return False
            
        await db.delete(run)
        await db.commit()
        return True
