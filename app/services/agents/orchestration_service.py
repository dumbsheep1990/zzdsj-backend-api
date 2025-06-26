from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import asyncio

from app.models.agent_orchestration import AgentOrchestration, OrchestrationExecutionLog
from app.models.assistant import Assistant
from app.schemas.orchestration import (
    OrchestrationCreate, OrchestrationUpdate, 
    OrchestrationExecutionRequest, OrchestrationDataSchema
)
from app.services.agents.orchestration_parser import AgentOrchestrationParser
from app.utils.core.database import get_db

logger = logging.getLogger(__name__)


class OrchestrationService:
    """编排服务层"""
    
    def __init__(self, db: Session):
        self.db = db
        self.parser = AgentOrchestrationParser()
    
    async def create_orchestration(
        self, 
        orchestration_data: OrchestrationCreate,
        user_id: str
    ) -> AgentOrchestration:
        """
        创建编排配置
        
        Args:
            orchestration_data: 编排创建数据
            user_id: 用户ID
            
        Returns:
            AgentOrchestration: 创建的编排配置
            
        Raises:
            ValueError: 配置验证失败
            Exception: 数据库操作失败
        """
        logger.info(f"用户 {user_id} 创建编排配置: {orchestration_data.name}")
        
        # 验证助手是否存在
        assistant = self.db.query(Assistant).filter(
            Assistant.id == orchestration_data.assistant_id
        ).first()
        
        if not assistant:
            raise ValueError(f"助手不存在: {orchestration_data.assistant_id}")
        
        # 验证配置
        validation_errors = self.parser.validate_orchestration_config(
            orchestration_data.orchestration_config
        )
        if validation_errors:
            raise ValueError(f"配置验证失败: {'; '.join(validation_errors)}")
        
        # 解析为执行计划
        try:
            workflow = self.parser.parse_frontend_orchestration(
                orchestration_data.orchestration_config,
                orchestration_data.name,
                orchestration_data.description or ""
            )
            
            execution_plan = {
                "workflow_id": workflow.workflow_id,
                "steps": [
                    {
                        "step_id": step.step_id,
                        "module_type": step.module_type,
                        "module_name": step.module_name,
                        "tools": step.tools,
                        "knowledge_bases": step.knowledge_bases,
                        "execution_strategy": step.execution_strategy.value,
                        "order": step.order,
                        "enabled": step.enabled,
                        "dependencies": step.dependencies,
                        "conditions": step.conditions,
                        "parallel_groups": step.parallel_groups,
                        "config": step.config
                    }
                    for step in workflow.steps
                ],
                "global_config": workflow.global_config,
                "execution_mode": workflow.execution_mode
            }
        except Exception as e:
            logger.error(f"解析编排配置失败: {str(e)}")
            raise ValueError(f"配置解析失败: {str(e)}")
        
        # 创建数据库记录
        db_orchestration = AgentOrchestration(
            assistant_id=orchestration_data.assistant_id,
            name=orchestration_data.name,
            description=orchestration_data.description,
            orchestration_config=orchestration_data.orchestration_config.dict(),
            execution_plan=execution_plan
        )
        
        try:
            self.db.add(db_orchestration)
            self.db.commit()
            self.db.refresh(db_orchestration)
            
            logger.info(f"编排配置创建成功: ID={db_orchestration.id}, 名称={db_orchestration.name}")
            return db_orchestration
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存编排配置失败: {str(e)}")
            raise Exception(f"保存编排配置失败: {str(e)}")
    
    async def get_orchestration_by_id(self, orchestration_id: int) -> Optional[AgentOrchestration]:
        """根据ID获取编排配置"""
        return self.db.query(AgentOrchestration).filter(
            AgentOrchestration.id == orchestration_id
        ).first()
    
    async def get_orchestrations_by_assistant(
        self, 
        assistant_id: int, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[AgentOrchestration]:
        """获取助手的所有编排配置"""
        query = self.db.query(AgentOrchestration).filter(
            AgentOrchestration.assistant_id == assistant_id
        )
        
        if is_active is not None:
            query = query.filter(AgentOrchestration.is_active == is_active)
        
        return query.offset(skip).limit(limit).all()
    
    async def update_orchestration(
        self,
        orchestration_id: int,
        orchestration_update: OrchestrationUpdate,
        user_id: str
    ) -> Optional[AgentOrchestration]:
        """
        更新编排配置
        
        Args:
            orchestration_id: 编排ID
            orchestration_update: 更新数据
            user_id: 用户ID
            
        Returns:
            更新后的编排配置
        """
        logger.info(f"用户 {user_id} 更新编排配置: {orchestration_id}")
        
        db_orchestration = await self.get_orchestration_by_id(orchestration_id)
        if not db_orchestration:
            return None
        
        # 更新字段
        update_data = orchestration_update.dict(exclude_unset=True)
        
        # 如果更新了编排配置，重新解析执行计划
        if "orchestration_config" in update_data:
            validation_errors = self.parser.validate_orchestration_config(
                orchestration_update.orchestration_config
            )
            if validation_errors:
                raise ValueError(f"配置验证失败: {'; '.join(validation_errors)}")
            
            try:
                workflow = self.parser.parse_frontend_orchestration(
                    orchestration_update.orchestration_config,
                    update_data.get("name", db_orchestration.name),
                    update_data.get("description", db_orchestration.description or "")
                )
                
                update_data["execution_plan"] = {
                    "workflow_id": workflow.workflow_id,
                    "steps": [
                        {
                            "step_id": step.step_id,
                            "module_type": step.module_type,
                            "module_name": step.module_name,
                            "tools": step.tools,
                            "knowledge_bases": step.knowledge_bases,
                            "execution_strategy": step.execution_strategy.value,
                            "order": step.order,
                            "enabled": step.enabled,
                            "dependencies": step.dependencies,
                            "conditions": step.conditions,
                            "parallel_groups": step.parallel_groups,
                            "config": step.config
                        }
                        for step in workflow.steps
                    ],
                    "global_config": workflow.global_config,
                    "execution_mode": workflow.execution_mode
                }
                
                # 增加版本号
                update_data["version"] = db_orchestration.version + 1
                
            except Exception as e:
                logger.error(f"重新解析编排配置失败: {str(e)}")
                raise ValueError(f"配置解析失败: {str(e)}")
        
        # 应用更新
        for field, value in update_data.items():
            setattr(db_orchestration, field, value)
        
        try:
            self.db.commit()
            self.db.refresh(db_orchestration)
            
            logger.info(f"编排配置更新成功: ID={orchestration_id}")
            return db_orchestration
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新编排配置失败: {str(e)}")
            raise Exception(f"更新编排配置失败: {str(e)}")
    
    async def delete_orchestration(self, orchestration_id: int) -> bool:
        """删除编排配置"""
        logger.info(f"删除编排配置: {orchestration_id}")
        
        db_orchestration = await self.get_orchestration_by_id(orchestration_id)
        if not db_orchestration:
            return False
        
        try:
            self.db.delete(db_orchestration)
            self.db.commit()
            
            logger.info(f"编排配置删除成功: ID={orchestration_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除编排配置失败: {str(e)}")
            raise Exception(f"删除编排配置失败: {str(e)}")
    
    async def validate_orchestration(self, orchestration_id: int) -> Dict[str, Any]:
        """验证编排配置"""
        db_orchestration = await self.get_orchestration_by_id(orchestration_id)
        if not db_orchestration:
            raise ValueError("编排配置不存在")
        
        try:
            orchestration_data = OrchestrationDataSchema(**db_orchestration.orchestration_config)
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
            
        except Exception as e:
            logger.error(f"验证编排配置失败: {str(e)}")
            return {
                "is_valid": False,
                "validation_errors": [f"验证过程中发生错误: {str(e)}"],
                "warnings": [],
                "suggestions": []
            }
    
    async def execute_orchestration(
        self,
        execution_request: OrchestrationExecutionRequest,
        user_id: str
    ) -> Dict[str, Any]:
        """
        执行编排（目前是模拟实现）
        
        Args:
            execution_request: 执行请求
            user_id: 用户ID
            
        Returns:
            执行结果
        """
        logger.info(f"用户 {user_id} 执行编排: {execution_request.orchestration_id}")
        
        # 获取编排配置
        orchestration = await self.get_orchestration_by_id(execution_request.orchestration_id)
        if not orchestration:
            raise ValueError("编排配置不存在")
        
        if not orchestration.is_active:
            raise ValueError("编排配置已禁用")
        
        # 生成会话ID
        session_id = execution_request.session_id or str(uuid.uuid4())
        
        # 创建执行日志
        execution_log = OrchestrationExecutionLog(
            orchestration_id=orchestration.id,
            session_id=session_id,
            input_data=execution_request.input_data,
            status="running"
        )
        
        self.db.add(execution_log)
        self.db.commit()
        
        try:
            # 解析执行计划
            orchestration_data = OrchestrationDataSchema(**orchestration.orchestration_config)
            workflow = self.parser.parse_frontend_orchestration(
                orchestration_data,
                orchestration.name,
                orchestration.description or ""
            )
            
            # 模拟执行过程
            execution_trace = []
            start_time = datetime.now()
            
            for step_data in orchestration.execution_plan["steps"]:
                step_start = datetime.now()
                
                # 模拟步骤执行
                await asyncio.sleep(0.1)  # 模拟执行时间
                
                step_duration = int((datetime.now() - step_start).total_seconds() * 1000)
                
                execution_trace.append({
                    "step_id": step_data["step_id"],
                    "module_name": step_data["module_name"],
                    "status": "success",
                    "duration_ms": step_duration,
                    "timestamp": datetime.now().isoformat(),
                    "details": {
                        "tools_executed": step_data["tools"],
                        "kb_queries": step_data["knowledge_bases"],
                        "execution_strategy": step_data["execution_strategy"]
                    }
                })
            
            # 模拟最终输出
            output_data = {
                "final_answer": f"基于编排 '{orchestration.name}' 的执行结果",
                "confidence": 0.95,
                "execution_summary": {
                    "total_steps": len(orchestration.execution_plan["steps"]),
                    "execution_mode": workflow.execution_mode,
                    "processed_modules": [step["module_type"] for step in orchestration.execution_plan["steps"]]
                }
            }
            
            total_duration = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 更新执行日志
            execution_log.status = "completed"
            execution_log.end_time = datetime.now()
            execution_log.duration_ms = total_duration
            execution_log.output_data = output_data
            execution_log.execution_trace = execution_trace
            
            self.db.commit()
            
            logger.info(f"编排执行完成: 会话={session_id}, 耗时={total_duration}ms")
            
            return {
                "session_id": session_id,
                "status": "completed",
                "output_data": output_data,
                "execution_trace": execution_trace,
                "duration_ms": total_duration,
                "metadata": {
                    "orchestration_name": orchestration.name,
                    "execution_mode": workflow.execution_mode,
                    "step_count": len(execution_trace)
                }
            }
            
        except Exception as e:
            logger.error(f"编排执行失败: {str(e)}")
            
            # 更新执行日志为失败状态
            execution_log.status = "failed"
            execution_log.end_time = datetime.now()
            execution_log.error_message = str(e)
            execution_log.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            self.db.commit()
            
            return {
                "session_id": session_id,
                "status": "failed",
                "error_message": str(e),
                "execution_trace": execution_trace,
                "duration_ms": execution_log.duration_ms
            }
    
    async def get_execution_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取执行状态"""
        execution_log = self.db.query(OrchestrationExecutionLog).filter(
            OrchestrationExecutionLog.session_id == session_id
        ).first()
        
        if not execution_log:
            return None
        
        # 计算进度信息
        progress = None
        if execution_log.execution_trace:
            total_steps = len(execution_log.execution_trace)
            completed_steps = len([
                step for step in execution_log.execution_trace 
                if step.get("status") in ["success", "failed"]
            ])
            
            progress = {
                "total_steps": total_steps,
                "completed_steps": completed_steps,
                "current_step": execution_log.execution_trace[-1].get("step_id") if execution_log.execution_trace else None
            }
        
        # 计算运行时间
        elapsed_ms = None
        if execution_log.start_time:
            end_time = execution_log.end_time or datetime.now()
            elapsed_ms = int((end_time - execution_log.start_time).total_seconds() * 1000)
        
        return {
            "session_id": execution_log.session_id,
            "orchestration_id": execution_log.orchestration_id,
            "status": execution_log.status,
            "progress": progress,
            "start_time": execution_log.start_time.isoformat() if execution_log.start_time else None,
            "end_time": execution_log.end_time.isoformat() if execution_log.end_time else None,
            "elapsed_ms": elapsed_ms,
            "execution_trace": execution_log.execution_trace or [],
            "output_data": execution_log.output_data,
            "error_message": execution_log.error_message
        }
    
    async def get_orchestration_stats(
        self, 
        assistant_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取编排统计信息"""
        
        # 基础查询
        orchestration_query = self.db.query(AgentOrchestration)
        execution_query = self.db.query(OrchestrationExecutionLog)
        
        if assistant_id:
            orchestration_query = orchestration_query.filter(
                AgentOrchestration.assistant_id == assistant_id
            )
            execution_query = execution_query.join(AgentOrchestration).filter(
                AgentOrchestration.assistant_id == assistant_id
            )
        
        if start_date:
            execution_query = execution_query.filter(
                OrchestrationExecutionLog.start_time >= start_date
            )
        
        if end_date:
            execution_query = execution_query.filter(
                OrchestrationExecutionLog.start_time <= end_date
            )
        
        # 统计数据
        total_orchestrations = orchestration_query.count()
        active_orchestrations = orchestration_query.filter(
            AgentOrchestration.is_active == True
        ).count()
        
        total_executions = execution_query.count()
        successful_executions = execution_query.filter(
            OrchestrationExecutionLog.status == "completed"
        ).count()
        failed_executions = execution_query.filter(
            OrchestrationExecutionLog.status == "failed"
        ).count()
        
        success_rate = successful_executions / total_executions if total_executions > 0 else 0
        
        # 平均执行时间
        avg_duration_ms = 0
        if successful_executions > 0:
            durations = execution_query.filter(
                OrchestrationExecutionLog.status == "completed",
                OrchestrationExecutionLog.duration_ms.isnot(None)
            ).all()
            
            if durations:
                avg_duration_ms = sum(log.duration_ms for log in durations) / len(durations)
        
        return {
            "total_orchestrations": total_orchestrations,
            "active_orchestrations": active_orchestrations,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": round(success_rate, 3),
            "avg_duration_ms": round(avg_duration_ms, 2)
        } 