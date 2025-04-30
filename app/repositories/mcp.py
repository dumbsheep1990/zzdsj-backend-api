"""
MCP服务数据仓库模块
提供MCP服务、工具和调用历史等数据的CRUD操作
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func, and_, or_
from datetime import datetime
import json

from app.models.mcp import MCPServiceConfig, MCPTool, MCPToolExecution, AgentConfig, AgentTool


class MCPServiceRepository:
    """MCP服务配置仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self, skip: int = 0, limit: int = 100) -> Tuple[List[MCPServiceConfig], int]:
        """
        获取所有MCP服务配置
        
        参数:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        返回:
            MCP服务配置列表和总记录数的元组
        """
        query = self.db.query(MCPServiceConfig)
        total = query.count()
        items = query.order_by(desc(MCPServiceConfig.updated_at)).offset(skip).limit(limit).all()
        return items, total
    
    def get_by_id(self, service_id: int) -> Optional[MCPServiceConfig]:
        """
        根据ID获取MCP服务配置
        
        参数:
            service_id: 服务ID
            
        返回:
            MCP服务配置，如果不存在则返回None
        """
        return self.db.query(MCPServiceConfig).filter(MCPServiceConfig.id == service_id).first()
    
    def get_by_deployment_id(self, deployment_id: str) -> Optional[MCPServiceConfig]:
        """
        根据部署ID获取MCP服务配置
        
        参数:
            deployment_id: 部署ID
            
        返回:
            MCP服务配置，如果不存在则返回None
        """
        return self.db.query(MCPServiceConfig).filter(MCPServiceConfig.deployment_id == deployment_id).first()
    
    def create(self, data: Dict[str, Any]) -> MCPServiceConfig:
        """
        创建MCP服务配置
        
        参数:
            data: 服务配置数据
            
        返回:
            创建的MCP服务配置
        """
        service = MCPServiceConfig(**data)
        self.db.add(service)
        self.db.commit()
        self.db.refresh(service)
        return service
    
    def update(self, service_id: int, data: Dict[str, Any]) -> Optional[MCPServiceConfig]:
        """
        更新MCP服务配置
        
        参数:
            service_id: 服务ID
            data: 更新的数据
            
        返回:
            更新后的MCP服务配置，如果不存在则返回None
        """
        service = self.get_by_id(service_id)
        if service:
            for key, value in data.items():
                setattr(service, key, value)
            self.db.commit()
            self.db.refresh(service)
        return service
    
    def delete(self, service_id: int) -> bool:
        """
        删除MCP服务配置
        
        参数:
            service_id: 服务ID
            
        返回:
            是否成功删除
        """
        service = self.get_by_id(service_id)
        if service:
            self.db.delete(service)
            self.db.commit()
            return True
        return False
    
    def update_status(self, deployment_id: str, status: str) -> bool:
        """
        更新MCP服务状态
        
        参数:
            deployment_id: 部署ID
            status: 新状态
            
        返回:
            是否成功更新
        """
        service = self.get_by_deployment_id(deployment_id)
        if service:
            service.status = status
            # 更新状态相关时间戳
            if status == "running":
                service.last_started_at = datetime.utcnow()
            elif status == "stopped":
                service.last_stopped_at = datetime.utcnow()
            self.db.commit()
            return True
        return False


class MCPToolRepository:
    """MCP工具仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(
        self, 
        service_id: Optional[int] = None,
        category: Optional[str] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> Tuple[List[MCPTool], int]:
        """
        获取所有MCP工具
        
        参数:
            service_id: 按服务ID筛选（可选）
            category: 按类别筛选（可选）
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        返回:
            MCP工具列表和总记录数的元组
        """
        query = self.db.query(MCPTool)
        
        # 应用筛选条件
        if service_id is not None:
            query = query.filter(MCPTool.service_id == service_id)
        if category is not None:
            query = query.filter(MCPTool.category == category)
        
        total = query.count()
        items = query.order_by(MCPTool.tool_name).offset(skip).limit(limit).all()
        return items, total
    
    def get_by_id(self, tool_id: int) -> Optional[MCPTool]:
        """
        根据ID获取MCP工具
        
        参数:
            tool_id: 工具ID
            
        返回:
            MCP工具，如果不存在则返回None
        """
        return self.db.query(MCPTool).filter(MCPTool.id == tool_id).first()
    
    def get_by_name_and_service(self, service_id: int, tool_name: str) -> Optional[MCPTool]:
        """
        根据名称和服务ID获取MCP工具
        
        参数:
            service_id: 服务ID
            tool_name: 工具名称
            
        返回:
            MCP工具，如果不存在则返回None
        """
        return self.db.query(MCPTool).filter(
            MCPTool.service_id == service_id,
            MCPTool.tool_name == tool_name
        ).first()
    
    def create(self, data: Dict[str, Any]) -> MCPTool:
        """
        创建MCP工具
        
        参数:
            data: 工具数据
            
        返回:
            创建的MCP工具
        """
        tool = MCPTool(**data)
        self.db.add(tool)
        self.db.commit()
        self.db.refresh(tool)
        return tool
    
    def update(self, tool_id: int, data: Dict[str, Any]) -> Optional[MCPTool]:
        """
        更新MCP工具
        
        参数:
            tool_id: 工具ID
            data: 更新的数据
            
        返回:
            更新后的MCP工具，如果不存在则返回None
        """
        tool = self.get_by_id(tool_id)
        if tool:
            for key, value in data.items():
                setattr(tool, key, value)
            self.db.commit()
            self.db.refresh(tool)
        return tool
    
    def delete(self, tool_id: int) -> bool:
        """
        删除MCP工具
        
        参数:
            tool_id: 工具ID
            
        返回:
            是否成功删除
        """
        tool = self.get_by_id(tool_id)
        if tool:
            self.db.delete(tool)
            self.db.commit()
            return True
        return False
    
    def update_schema(self, tool_id: int, schema: Dict[str, Any]) -> bool:
        """
        更新MCP工具Schema
        
        参数:
            tool_id: 工具ID
            schema: 新Schema
            
        返回:
            是否成功更新
        """
        tool = self.get_by_id(tool_id)
        if tool:
            tool.schema = schema
            tool.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        return False
    
    def update_examples(self, tool_id: int, examples: List[Dict[str, Any]]) -> bool:
        """
        更新MCP工具示例
        
        参数:
            tool_id: 工具ID
            examples: 新示例列表
            
        返回:
            是否成功更新
        """
        tool = self.get_by_id(tool_id)
        if tool:
            tool.examples = examples
            tool.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        return False


class MCPToolExecutionRepository:
    """MCP工具调用历史仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(
        self, 
        tool_id: Optional[int] = None,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> Tuple[List[MCPToolExecution], int]:
        """
        获取工具调用历史
        
        参数:
            tool_id: 按工具ID筛选（可选）
            agent_id: 按代理ID筛选（可选）
            status: 按状态筛选（可选）
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        返回:
            工具调用历史列表和总记录数的元组
        """
        query = self.db.query(MCPToolExecution)
        
        # 应用筛选条件
        if tool_id is not None:
            query = query.filter(MCPToolExecution.tool_id == tool_id)
        if agent_id is not None:
            query = query.filter(MCPToolExecution.agent_id == agent_id)
        if status is not None:
            query = query.filter(MCPToolExecution.status == status)
        
        total = query.count()
        items = query.order_by(desc(MCPToolExecution.started_at)).offset(skip).limit(limit).all()
        return items, total
    
    def get_by_id(self, execution_id: int) -> Optional[MCPToolExecution]:
        """
        根据ID获取调用历史
        
        参数:
            execution_id: 调用历史ID
            
        返回:
            调用历史，如果不存在则返回None
        """
        return self.db.query(MCPToolExecution).filter(MCPToolExecution.id == execution_id).first()
    
    def get_by_execution_id(self, execution_id: str) -> Optional[MCPToolExecution]:
        """
        根据执行ID获取调用历史
        
        参数:
            execution_id: 执行ID
            
        返回:
            调用历史，如果不存在则返回None
        """
        return self.db.query(MCPToolExecution).filter(MCPToolExecution.execution_id == execution_id).first()
    
    def create(self, data: Dict[str, Any]) -> MCPToolExecution:
        """
        创建调用历史
        
        参数:
            data: 调用历史数据
            
        返回:
            创建的调用历史
        """
        execution = MCPToolExecution(**data)
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return execution
    
    def update_result(
        self, 
        execution_id: str, 
        result: Any, 
        status: str = "success"
    ) -> Optional[MCPToolExecution]:
        """
        更新调用结果
        
        参数:
            execution_id: 执行ID
            result: 执行结果
            status: 执行状态
            
        返回:
            更新后的调用历史，如果不存在则返回None
        """
        execution = self.get_by_execution_id(execution_id)
        if execution:
            execution.result = result
            execution.status = status
            execution.completed_at = datetime.utcnow()
            
            # 计算执行时间（毫秒）
            if execution.started_at:
                delta = execution.completed_at - execution.started_at
                execution.execution_time_ms = int(delta.total_seconds() * 1000)
            
            self.db.commit()
            self.db.refresh(execution)
        return execution
    
    def update_error(
        self, 
        execution_id: str, 
        error_message: str
    ) -> Optional[MCPToolExecution]:
        """
        更新调用错误
        
        参数:
            execution_id: 执行ID
            error_message: 错误信息
            
        返回:
            更新后的调用历史，如果不存在则返回None
        """
        execution = self.get_by_execution_id(execution_id)
        if execution:
            execution.error_message = error_message
            execution.status = "error"
            execution.completed_at = datetime.utcnow()
            
            # 计算执行时间（毫秒）
            if execution.started_at:
                delta = execution.completed_at - execution.started_at
                execution.execution_time_ms = int(delta.total_seconds() * 1000)
            
            self.db.commit()
            self.db.refresh(execution)
        return execution
    
    def get_execution_stats(
        self,
        tool_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取工具调用统计信息
        
        参数:
            tool_id: 按工具ID筛选（可选）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        返回:
            统计信息
        """
        query = self.db.query(MCPToolExecution)
        
        # 应用筛选条件
        if tool_id is not None:
            query = query.filter(MCPToolExecution.tool_id == tool_id)
        if start_date is not None:
            query = query.filter(MCPToolExecution.started_at >= start_date)
        if end_date is not None:
            query = query.filter(MCPToolExecution.started_at <= end_date)
        
        # 总调用次数
        total_count = query.count()
        
        # 成功调用次数
        success_count = query.filter(MCPToolExecution.status == "success").count()
        
        # 失败调用次数
        error_count = query.filter(MCPToolExecution.status == "error").count()
        
        # 平均执行时间
        avg_execution_time = self.db.query(func.avg(MCPToolExecution.execution_time_ms))\
            .filter(MCPToolExecution.execution_time_ms != None)\
            .scalar()
        
        return {
            "total_count": total_count,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": (success_count / total_count * 100) if total_count > 0 else 0,
            "avg_execution_time_ms": float(avg_execution_time) if avg_execution_time else 0
        }


class AgentConfigRepository:
    """Agent配置仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self, skip: int = 0, limit: int = 100) -> Tuple[List[AgentConfig], int]:
        """
        获取所有Agent配置
        
        参数:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        返回:
            Agent配置列表和总记录数的元组
        """
        query = self.db.query(AgentConfig)
        total = query.count()
        items = query.order_by(AgentConfig.name).offset(skip).limit(limit).all()
        return items, total
    
    def get_by_id(self, agent_id: int) -> Optional[AgentConfig]:
        """
        根据ID获取Agent配置
        
        参数:
            agent_id: 代理ID
            
        返回:
            Agent配置，如果不存在则返回None
        """
        return self.db.query(AgentConfig).filter(AgentConfig.id == agent_id).first()
    
    def get_by_agent_id(self, agent_id: str) -> Optional[AgentConfig]:
        """
        根据Agent UUID获取Agent配置
        
        参数:
            agent_id: 代理UUID
            
        返回:
            Agent配置，如果不存在则返回None
        """
        return self.db.query(AgentConfig).filter(AgentConfig.agent_id == agent_id).first()
    
    def create(self, data: Dict[str, Any]) -> AgentConfig:
        """
        创建Agent配置
        
        参数:
            data: Agent配置数据
            
        返回:
            创建的Agent配置
        """
        agent = AgentConfig(**data)
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        return agent
    
    def update(self, agent_id: int, data: Dict[str, Any]) -> Optional[AgentConfig]:
        """
        更新Agent配置
        
        参数:
            agent_id: 代理ID
            data: 更新的数据
            
        返回:
            更新后的Agent配置，如果不存在则返回None
        """
        agent = self.get_by_id(agent_id)
        if agent:
            for key, value in data.items():
                setattr(agent, key, value)
            self.db.commit()
            self.db.refresh(agent)
        return agent
    
    def delete(self, agent_id: int) -> bool:
        """
        删除Agent配置
        
        参数:
            agent_id: 代理ID
            
        返回:
            是否成功删除
        """
        agent = self.get_by_id(agent_id)
        if agent:
            self.db.delete(agent)
            self.db.commit()
            return True
        return False
    
    def get_with_tools(self, agent_id: int) -> Optional[Dict[str, Any]]:
        """
        获取Agent配置及其工具
        
        参数:
            agent_id: 代理ID
            
        返回:
            Agent配置及其工具，如果不存在则返回None
        """
        agent = self.get_by_id(agent_id)
        if agent:
            tools = self.db.query(AgentTool).filter(AgentTool.agent_id == agent.id).all()
            return {
                "id": agent.id,
                "agent_id": agent.agent_id,
                "name": agent.name,
                "description": agent.description,
                "agent_type": agent.agent_type,
                "model": agent.model,
                "settings": agent.settings,
                "is_enabled": agent.is_enabled,
                "created_at": agent.created_at,
                "updated_at": agent.updated_at,
                "tools": [
                    {
                        "id": tool.id,
                        "tool_type": tool.tool_type,
                        "tool_name": tool.tool_name,
                        "description": tool.description,
                        "is_enabled": tool.is_enabled,
                        "mcp_tool_id": tool.mcp_tool_id,
                        "settings": tool.settings
                    }
                    for tool in tools
                ]
            }
        return None


class AgentToolRepository:
    """Agent工具配置仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(
        self, 
        agent_id: Optional[int] = None,
        tool_type: Optional[str] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> Tuple[List[AgentTool], int]:
        """
        获取所有Agent工具配置
        
        参数:
            agent_id: 按代理ID筛选（可选）
            tool_type: 按工具类型筛选（可选）
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        返回:
            Agent工具配置列表和总记录数的元组
        """
        query = self.db.query(AgentTool)
        
        # 应用筛选条件
        if agent_id is not None:
            query = query.filter(AgentTool.agent_id == agent_id)
        if tool_type is not None:
            query = query.filter(AgentTool.tool_type == tool_type)
        
        total = query.count()
        items = query.order_by(AgentTool.tool_name).offset(skip).limit(limit).all()
        return items, total
    
    def get_by_id(self, tool_id: int) -> Optional[AgentTool]:
        """
        根据ID获取Agent工具配置
        
        参数:
            tool_id: 工具ID
            
        返回:
            Agent工具配置，如果不存在则返回None
        """
        return self.db.query(AgentTool).filter(AgentTool.id == tool_id).first()
    
    def get_by_name_and_agent(self, agent_id: int, tool_name: str) -> Optional[AgentTool]:
        """
        根据名称和代理ID获取Agent工具配置
        
        参数:
            agent_id: 代理ID
            tool_name: 工具名称
            
        返回:
            Agent工具配置，如果不存在则返回None
        """
        return self.db.query(AgentTool).filter(
            AgentTool.agent_id == agent_id,
            AgentTool.tool_name == tool_name
        ).first()
    
    def create(self, data: Dict[str, Any]) -> AgentTool:
        """
        创建Agent工具配置
        
        参数:
            data: 工具配置数据
            
        返回:
            创建的Agent工具配置
        """
        tool = AgentTool(**data)
        self.db.add(tool)
        self.db.commit()
        self.db.refresh(tool)
        return tool
    
    def update(self, tool_id: int, data: Dict[str, Any]) -> Optional[AgentTool]:
        """
        更新Agent工具配置
        
        参数:
            tool_id: 工具ID
            data: 更新的数据
            
        返回:
            更新后的Agent工具配置，如果不存在则返回None
        """
        tool = self.get_by_id(tool_id)
        if tool:
            for key, value in data.items():
                setattr(tool, key, value)
            self.db.commit()
            self.db.refresh(tool)
        return tool
    
    def delete(self, tool_id: int) -> bool:
        """
        删除Agent工具配置
        
        参数:
            tool_id: 工具ID
            
        返回:
            是否成功删除
        """
        tool = self.get_by_id(tool_id)
        if tool:
            self.db.delete(tool)
            self.db.commit()
            return True
        return False
