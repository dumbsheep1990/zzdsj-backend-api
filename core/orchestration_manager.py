"""
智能体编排管理器核心模块

整合编排解析器、服务层和执行引擎，提供统一的编排管理接口
"""

from typing import Dict, Any, List, Optional, AsyncIterator
import logging
from sqlalchemy.orm import Session
import asyncio

from app.models.agent_orchestration import AgentOrchestration
from app.schemas.orchestration import (
    OrchestrationCreate, OrchestrationUpdate, OrchestrationExecutionRequest,
    OrchestrationDataSchema
)
from app.services.agents.orchestration_service import OrchestrationService
from app.services.agents.orchestration_parser import AgentOrchestrationParser
from app.services.agents.modular_executor import ModularAgentExecutor

logger = logging.getLogger(__name__)


class OrchestrationManager:
    """智能体编排管理器"""
    
    def __init__(self, db: Session):
        """
        初始化编排管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.service = OrchestrationService(db)
        self.parser = AgentOrchestrationParser()
        self.executor = ModularAgentExecutor()
    
    # ============ 编排配置管理 ============
    
    async def create_orchestration(
        self, 
        orchestration_data: OrchestrationCreate,
        user_id: str
    ) -> AgentOrchestration:
        """
        创建编排配置
        
        Args:
            orchestration_data: 编排配置数据
            user_id: 用户ID
            
        Returns:
            创建的编排配置
        """
        logger.info(f"创建编排配置: {orchestration_data.name}")
        return await self.service.create_orchestration(orchestration_data, user_id)
    
    async def get_orchestration(self, orchestration_id: int) -> Optional[AgentOrchestration]:
        """获取编排配置"""
        return await self.service.get_orchestration_by_id(orchestration_id)
    
    async def update_orchestration(
        self,
        orchestration_id: int,
        orchestration_update: OrchestrationUpdate,
        user_id: str
    ) -> Optional[AgentOrchestration]:
        """更新编排配置"""
        logger.info(f"更新编排配置: {orchestration_id}")
        return await self.service.update_orchestration(orchestration_id, orchestration_update, user_id)
    
    async def delete_orchestration(self, orchestration_id: int) -> bool:
        """删除编排配置"""
        logger.info(f"删除编排配置: {orchestration_id}")
        return await self.service.delete_orchestration(orchestration_id)
    
    async def list_orchestrations_by_assistant(
        self, 
        assistant_id: int, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[AgentOrchestration]:
        """获取助手的编排配置列表"""
        return await self.service.get_orchestrations_by_assistant(
            assistant_id, skip, limit, is_active
        )
    
    # ============ 编排配置验证 ============
    
    async def validate_orchestration_config(
        self, 
        orchestration_data: OrchestrationDataSchema
    ) -> Dict[str, Any]:
        """
        验证编排配置
        
        Args:
            orchestration_data: 编排配置数据
            
        Returns:
            验证结果
        """
        validation_errors = self.parser.validate_orchestration_config(orchestration_data)
        
        # 生成警告和建议
        warnings = []
        suggestions = []
        
        # 检查模块配置的合理性
        for module_key, module_config in orchestration_data.modules.items():
            if not module_config.tools and not module_config.knowledgeBases:
                warnings.append(f"模块 {module_key} 未配置工具或知识库")
            
            if module_config.executionStrategy == "parallel" and len(module_config.tools) < 2:
                suggestions.append(f"模块 {module_key} 配置为并行执行但只有少量工具，建议调整策略")
        
        return {
            "is_valid": len(validation_errors) == 0,
            "validation_errors": validation_errors,
            "warnings": warnings,
            "suggestions": suggestions
        }
    
    async def validate_orchestration_by_id(self, orchestration_id: int) -> Dict[str, Any]:
        """根据ID验证编排配置"""
        return await self.service.validate_orchestration(orchestration_id)
    
    # ============ 编排解析 ============
    
    async def parse_orchestration_config(
        self,
        orchestration_data: OrchestrationDataSchema,
        orchestration_name: str = "unnamed_workflow",
        orchestration_description: str = ""
    ) -> Dict[str, Any]:
        """
        解析编排配置为可执行工作流
        
        Args:
            orchestration_data: 编排配置数据
            orchestration_name: 工作流名称
            orchestration_description: 工作流描述
            
        Returns:
            解析结果和执行计划
        """
        try:
            workflow = self.parser.parse_frontend_orchestration(
                orchestration_data,
                orchestration_name,
                orchestration_description
            )
            
            execution_summary = self.parser.get_execution_summary(workflow)
            
            return {
                "success": True,
                "workflow": workflow,
                "execution_summary": execution_summary,
                "message": f"成功解析编排配置，包含 {len(workflow.steps)} 个执行步骤"
            }
            
        except Exception as e:
            logger.error(f"解析编排配置失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"编排配置解析失败: {str(e)}"
            }
    
    # ============ 编排执行 ============
    
    async def execute_orchestration_by_id(
        self,
        orchestration_id: int,
        input_data: Dict[str, Any],
        user_id: str,
        session_id: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        根据编排ID执行编排
        
        Args:
            orchestration_id: 编排ID
            input_data: 输入数据
            user_id: 用户ID
            session_id: 会话ID（可选）
            
        Yields:
            执行进度和结果
        """
        logger.info(f"用户 {user_id} 执行编排: {orchestration_id}")
        
        # 获取编排配置
        orchestration = await self.get_orchestration(orchestration_id)
        if not orchestration:
            yield {
                "event": "execution_failed",
                "error": "编排配置不存在",
                "orchestration_id": orchestration_id
            }
            return
        
        if not orchestration.is_active:
            yield {
                "event": "execution_failed",
                "error": "编排配置已禁用",
                "orchestration_id": orchestration_id
            }
            return
        
        # 解析编排配置
        try:
            orchestration_data = OrchestrationDataSchema(**orchestration.orchestration_config)
            workflow = self.parser.parse_frontend_orchestration(
                orchestration_data,
                orchestration.name,
                orchestration.description or ""
            )
        except Exception as e:
            logger.error(f"解析编排配置失败: {str(e)}")
            yield {
                "event": "execution_failed",
                "error": f"配置解析失败: {str(e)}",
                "orchestration_id": orchestration_id
            }
            return
        
        # 执行工作流
        async for event in self.executor.execute_workflow(workflow, input_data, session_id):
            # 添加编排相关信息
            event["orchestration_id"] = orchestration_id
            event["orchestration_name"] = orchestration.name
            event["user_id"] = user_id
            yield event
    
    async def execute_orchestration_request(
        self,
        execution_request: OrchestrationExecutionRequest,
        user_id: str
    ) -> Dict[str, Any]:
        """
        执行编排请求（兼容现有接口）
        
        Args:
            execution_request: 执行请求
            user_id: 用户ID
            
        Returns:
            执行结果
        """
        return await self.service.execute_orchestration(execution_request, user_id)
    
    async def cancel_execution(self, session_id: str) -> bool:
        """取消编排执行"""
        logger.info(f"取消编排执行: {session_id}")
        return await self.executor.cancel_execution(session_id)
    
    async def get_execution_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取执行状态"""
        # 首先检查活跃执行
        executor_status = self.executor.get_execution_status(session_id)
        if executor_status:
            return executor_status
        
        # 检查数据库中的执行记录
        return await self.service.get_execution_status(session_id)
    
    # ============ 统计和监控 ============
    
    async def get_orchestration_stats(
        self, 
        assistant_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取编排统计信息"""
        from datetime import datetime
        
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        return await self.service.get_orchestration_stats(assistant_id, start_dt, end_dt)
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        stats = await self.get_orchestration_stats()
        
        # 获取当前活跃执行数
        active_executions = len(self.executor.active_executions)
        
        return {
            "current_load": {
                "active_executions": active_executions,
                "max_concurrent_executions": 100,  # 可配置
                "load_percentage": min(active_executions / 100 * 100, 100)
            },
            "resource_usage": {
                "memory_usage": "正常",  # 可以集成实际监控
                "cpu_usage": "正常",
                "database_connections": "正常"
            },
            "performance": {
                "avg_execution_time_ms": stats.get("avg_duration_ms", 0),
                "success_rate": stats.get("success_rate", 0),
                "total_executions_today": stats.get("total_executions", 0)
            },
            "error_rates": {
                "parsing_errors": 0,  # 可以添加实际统计
                "execution_errors": stats.get("failed_executions", 0),
                "timeout_errors": 0
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """系统健康检查"""
        try:
            # 检查数据库连接
            db_healthy = True
            try:
                self.db.execute("SELECT 1")
            except Exception:
                db_healthy = False
            
            # 检查各组件状态
            components = {
                "orchestration_parser": {"status": "healthy"},
                "orchestration_service": {"status": "healthy"},
                "modular_executor": {"status": "healthy"},
                "database": {"status": "healthy" if db_healthy else "unhealthy"}
            }
            
            # 计算整体状态
            overall_status = "healthy"
            if not db_healthy:
                overall_status = "unhealthy"
            
            return {
                "status": overall_status,
                "timestamp": logger.handlers[0].formatter.formatTime(logger.handlers[0].formatter) if logger.handlers else "unknown",
                "components": components,
                "dependencies": {
                    "database": "healthy" if db_healthy else "unhealthy",
                    "cache": "healthy",  # 可以添加实际检查
                    "external_apis": "healthy"
                },
                "message": "编排系统运行正常" if overall_status == "healthy" else "编排系统存在问题"
            }
            
        except Exception as e:
            logger.error(f"健康检查失败: {str(e)}")
            return {
                "status": "unhealthy",
                "timestamp": "unknown",
                "error": str(e)
            }
    
    # ============ 工具方法 ============
    
    async def get_workflow_preview(
        self, 
        orchestration_data: OrchestrationDataSchema
    ) -> Dict[str, Any]:
        """
        获取工作流预览
        
        Args:
            orchestration_data: 编排配置数据
            
        Returns:
            工作流预览信息
        """
        try:
            workflow = self.parser.parse_frontend_orchestration(
                orchestration_data,
                "preview_workflow",
                "工作流预览"
            )
            
            preview_data = {
                "workflow_id": workflow.workflow_id,
                "name": workflow.name,
                "execution_mode": workflow.execution_mode,
                "steps": [],
                "execution_flow": [],
                "estimated_duration": 0
            }
            
            # 构建步骤预览
            for step in workflow.steps:
                step_preview = {
                    "step_id": step.step_id,
                    "module_name": step.module_name,
                    "module_type": step.module_type,
                    "order": step.order,
                    "tools": step.tools,
                    "knowledge_bases": step.knowledge_bases,
                    "execution_strategy": step.execution_strategy.value,
                    "dependencies": step.dependencies,
                    "estimated_time_ms": self._estimate_step_time(step)
                }
                preview_data["steps"].append(step_preview)
                preview_data["estimated_duration"] += step_preview["estimated_time_ms"]
            
            # 构建执行流程图
            preview_data["execution_flow"] = self._build_execution_flow(workflow.steps)
            
            return {
                "success": True,
                "preview": preview_data,
                "validation": await self.validate_orchestration_config(orchestration_data)
            }
            
        except Exception as e:
            logger.error(f"生成工作流预览失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "preview": None
            }
    
    def _estimate_step_time(self, step) -> int:
        """估算步骤执行时间（毫秒）"""
        base_time = 500  # 基础时间500ms
        
        # 根据工具数量调整
        tool_time = len(step.tools) * 200
        
        # 根据知识库数量调整
        kb_time = len(step.knowledge_bases) * 300
        
        # 根据执行策略调整
        strategy_multiplier = 1.0
        if step.execution_strategy.value == "parallel":
            strategy_multiplier = 0.7  # 并行执行更快
        elif step.execution_strategy.value == "conditional":
            strategy_multiplier = 1.2  # 条件执行稍慢
        
        return int((base_time + tool_time + kb_time) * strategy_multiplier)
    
    def _build_execution_flow(self, steps) -> List[Dict[str, Any]]:
        """构建执行流程图数据"""
        flow_nodes = []
        
        for step in steps:
            node = {
                "id": step.step_id,
                "label": step.module_name,
                "type": step.module_type,
                "order": step.order,
                "dependencies": step.dependencies,
                "execution_strategy": step.execution_strategy.value
            }
            flow_nodes.append(node)
        
        return flow_nodes 