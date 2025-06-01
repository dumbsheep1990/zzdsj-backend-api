"""
监控服务模块
处理系统监控和性能跟踪相关的业务逻辑
重构版本：调用core层业务逻辑，符合分层架构原则
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

from app.utils.core.database import get_db
# 导入core层业务逻辑
from core.monitoring import MonitoringManager, MetricsCollector, AlertManager

# 导入模型类型（仅用于类型提示和API兼容性）
from app.models.monitoring import SystemMetric, ServiceStatus, RequestLog, ErrorLog

logger = logging.getLogger(__name__)


class MonitoringService:
    """监控服务类 - Services层，调用Core层业务逻辑"""
    
    def __init__(self, db: Session = Depends(get_db)):
        """初始化监控服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        # 使用core层的监控管理器
        self.monitoring_manager = MonitoringManager(db)
        self.metrics_collector = MetricsCollector(db)
        self.alert_manager = AlertManager(db)
    
    # ==================== 系统指标管理 ====================
    
    async def record_system_metrics(self) -> Dict[str, Any]:
        """记录系统指标
        
        Returns:
            Dict[str, Any]: 创建的系统指标记录信息
        """
        try:
            result = await self.metrics_collector.collect_system_metrics()
            if result["success"]:
                logger.info(f"系统指标记录成功: {result['data']['id']}")
                return result["data"]
            else:
                logger.error(f"系统指标记录失败: {result.get('error')}")
                return {}
        except Exception as e:
            logger.error(f"记录系统指标过程中出错: {str(e)}")
            return {}
    
    async def get_system_metrics(self, start_time: datetime, end_time: datetime, user_id: str) -> List[Dict[str, Any]]:
        """获取系统指标
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            user_id: 用户ID
            
        Returns:
            List[Dict[str, Any]]: 系统指标列表
            
        Raises:
            HTTPException: 如果没有权限
        """
        try:
            # 检查权限
            is_admin = await self._check_admin_permission(user_id)
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="只有管理员可以查看系统指标"
                )
            
            result = await self.monitoring_manager.get_system_metrics(start_time, end_time)
            if result["success"]:
                return result["data"]["metrics"]
            else:
                logger.error(f"获取系统指标失败: {result.get('error')}")
                return []
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取系统指标过程中出错: {str(e)}")
            return []
    
    async def get_latest_system_metrics(self, user_id: str) -> Dict[str, Any]:
        """获取最新系统指标
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 最新系统指标
            
        Raises:
            HTTPException: 如果没有权限
        """
        try:
            # 检查权限
            is_admin = await self._check_admin_permission(user_id)
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="只有管理员可以查看系统指标"
                )
            
            result = await self.monitoring_manager.get_latest_metrics()
            if result["success"]:
                return result["data"]
            else:
                logger.error(f"获取最新系统指标失败: {result.get('error')}")
                return {}
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取最新系统指标过程中出错: {str(e)}")
            return {}
    
    # ==================== 服务状态管理 ====================
    
    async def update_service_status(self, service_name: str, status: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """更新服务状态
        
        Args:
            service_name: 服务名称
            status: 状态 ('up', 'down', 'degraded')
            details: 状态详情
            
        Returns:
            Dict[str, Any]: 更新后的服务状态信息
        """
        try:
            result = await self.monitoring_manager.update_service_status(
                service_name=service_name,
                status=status,
                details=details or {}
            )
            
            if result["success"]:
                return result["data"]
            else:
                logger.error(f"更新服务状态失败: {result.get('error')}")
                return {}
                
        except Exception as e:
            logger.error(f"更新服务状态过程中出错: {str(e)}")
            return {}
    
    async def get_service_status(self, service_name: str, user_id: str) -> Dict[str, Any]:
        """获取服务状态
        
        Args:
            service_name: 服务名称
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 服务状态信息
            
        Raises:
            HTTPException: 如果服务不存在或没有权限
        """
        try:
            result = await self.monitoring_manager.get_service_status(service_name)
            if result["success"]:
                return result["data"]
            else:
                error_code = result.get("error_code", "UNKNOWN_ERROR")
                if error_code == "SERVICE_NOT_FOUND":
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"服务 '{service_name}' 状态不存在"
                    )
                else:
                    logger.error(f"获取服务状态失败: {result.get('error')}")
                    return {}
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取服务状态过程中出错: {str(e)}")
            return {}
    
    async def get_all_service_statuses(self, user_id: str) -> List[Dict[str, Any]]:
        """获取所有服务状态
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Dict[str, Any]]: 服务状态列表
        """
        try:
            result = await self.monitoring_manager.get_all_service_statuses()
            if result["success"]:
                return result["data"]["services"]
            else:
                logger.error(f"获取所有服务状态失败: {result.get('error')}")
                return []
                
        except Exception as e:
            logger.error(f"获取所有服务状态过程中出错: {str(e)}")
            return []
    
    # ==================== 请求日志管理 ====================
    
    async def log_request(self, 
                       endpoint: str, 
                       method: str, 
                       user_id: Optional[str], 
                       response_time: float,
                       status_code: int,
                       request_data: Dict[str, Any] = None,
                       response_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """记录API请求
        
        Args:
            endpoint: API端点
            method: HTTP方法
            user_id: 用户ID（可选）
            response_time: 响应时间（毫秒）
            status_code: HTTP状态码
            request_data: 请求数据（可选）
            response_data: 响应数据（可选）
            
        Returns:
            Dict[str, Any]: 创建的请求日志信息
        """
        try:
            result = await self.monitoring_manager.log_request(
                endpoint=endpoint,
                method=method,
                user_id=user_id,
                response_time=response_time,
                status_code=status_code,
                request_data=request_data,
                response_data=response_data
            )
            
            if result["success"]:
                return result["data"]
            else:
                logger.error(f"记录请求日志失败: {result.get('error')}")
                return {}
                
        except Exception as e:
            logger.error(f"记录请求日志过程中出错: {str(e)}")
            return {}
    
    async def get_request_logs(self, 
                            start_time: datetime, 
                            end_time: datetime, 
                            endpoint: Optional[str] = None,
                            user_id: Optional[str] = None,
                            status_code: Optional[int] = None,
                            admin_id: str = None,
                            skip: int = 0, 
                            limit: int = 100) -> List[Dict[str, Any]]:
        """获取请求日志
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            endpoint: 过滤的API端点（可选）
            user_id: 过滤的用户ID（可选）
            status_code: 过滤的状态码（可选）
            admin_id: 请求者的用户ID（需要管理员权限）
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[Dict[str, Any]]: 请求日志列表
            
        Raises:
            HTTPException: 如果没有权限
        """
        try:
            # 检查权限
            is_admin = await self._check_admin_permission(admin_id)
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="只有管理员可以查看请求日志"
                )
            
            # 构建过滤条件
            filters = {}
            if endpoint:
                filters["endpoint"] = endpoint
            if user_id:
                filters["user_id"] = user_id
            if status_code:
                filters["status_code"] = status_code
            
            result = await self.monitoring_manager.get_request_logs(
                start_time=start_time,
                end_time=end_time,
                filters=filters,
                skip=skip,
                limit=limit
            )
            
            if result["success"]:
                return result["data"]["logs"]
            else:
                logger.error(f"获取请求日志失败: {result.get('error')}")
                return []
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取请求日志过程中出错: {str(e)}")
            return []
    
    async def get_request_analytics(self, 
                                 start_time: datetime, 
                                 end_time: datetime,
                                 admin_id: str) -> Dict[str, Any]:
        """获取请求统计分析
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            admin_id: 请求者的用户ID（需要管理员权限）
            
        Returns:
            Dict[str, Any]: 请求统计分析
            
        Raises:
            HTTPException: 如果没有权限
        """
        try:
            # 检查权限
            is_admin = await self._check_admin_permission(admin_id)
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="只有管理员可以查看请求统计分析"
                )
            
            result = await self.monitoring_manager.get_request_analytics(start_time, end_time)
            
            if result["success"]:
                return result["data"]
            else:
                logger.error(f"获取请求统计分析失败: {result.get('error')}")
                return {}
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取请求统计分析过程中出错: {str(e)}")
            return {}
    
    # ==================== 错误日志管理 ====================
    
    async def log_error(self, 
                     error_type: str, 
                     error_message: str, 
                     source: str,
                     user_id: Optional[str] = None,
                     details: Dict[str, Any] = None) -> Dict[str, Any]:
        """记录错误
        
        Args:
            error_type: 错误类型
            error_message: 错误消息
            source: 错误来源
            user_id: 相关的用户ID（可选）
            details: 错误详情（可选）
            
        Returns:
            Dict[str, Any]: 创建的错误日志信息
        """
        try:
            result = await self.monitoring_manager.log_error(
                error_type=error_type,
                error_message=error_message,
                source=source,
                user_id=user_id,
                details=details or {}
            )
            
            if result["success"]:
                return result["data"]
            else:
                logger.error(f"记录错误日志失败: {result.get('error')}")
                return {}
                
        except Exception as e:
            logger.error(f"记录错误日志过程中出错: {str(e)}")
            return {}
    
    async def get_error_logs(self, 
                          start_time: datetime, 
                          end_time: datetime, 
                          error_type: Optional[str] = None,
                          source: Optional[str] = None,
                          user_id: Optional[str] = None,
                          admin_id: str = None,
                          skip: int = 0, 
                          limit: int = 100) -> List[Dict[str, Any]]:
        """获取错误日志
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            error_type: 过滤的错误类型（可选）
            source: 过滤的错误来源（可选）
            user_id: 过滤的用户ID（可选）
            admin_id: 请求者的用户ID（需要管理员权限）
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[Dict[str, Any]]: 错误日志列表
            
        Raises:
            HTTPException: 如果没有权限
        """
        try:
            # 检查权限
            is_admin = await self._check_admin_permission(admin_id)
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="只有管理员可以查看错误日志"
                )
            
            # 构建过滤条件
            filters = {}
            if error_type:
                filters["error_type"] = error_type
            if source:
                filters["source"] = source
            if user_id:
                filters["user_id"] = user_id
            
            result = await self.monitoring_manager.get_error_logs(
                start_time=start_time,
                end_time=end_time,
                filters=filters,
                skip=skip,
                limit=limit
            )
            
            if result["success"]:
                return result["data"]["logs"]
            else:
                logger.error(f"获取错误日志失败: {result.get('error')}")
                return []
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取错误日志过程中出错: {str(e)}")
            return []
    
    # ==================== 告警管理 ====================
    
    async def create_alert(self, alert_type: str, message: str, severity: str = "medium",
                          source: str = None, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建告警
        
        Args:
            alert_type: 告警类型
            message: 告警消息
            severity: 严重程度 ('low', 'medium', 'high', 'critical')
            source: 告警来源
            details: 告警详情
            
        Returns:
            Dict[str, Any]: 创建的告警信息
        """
        try:
            result = await self.alert_manager.create_alert(
                alert_type=alert_type,
                message=message,
                severity=severity,
                source=source,
                details=details or {}
            )
            
            if result["success"]:
                return result["data"]
            else:
                logger.error(f"创建告警失败: {result.get('error')}")
                return {}
                
        except Exception as e:
            logger.error(f"创建告警过程中出错: {str(e)}")
            return {}
    
    async def get_active_alerts(self, admin_id: str) -> List[Dict[str, Any]]:
        """获取活跃告警
        
        Args:
            admin_id: 请求者的用户ID（需要管理员权限）
            
        Returns:
            List[Dict[str, Any]]: 活跃告警列表
            
        Raises:
            HTTPException: 如果没有权限
        """
        try:
            # 检查权限
            is_admin = await self._check_admin_permission(admin_id)
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="只有管理员可以查看告警"
                )
            
            result = await self.alert_manager.get_active_alerts()
            
            if result["success"]:
                return result["data"]["alerts"]
            else:
                logger.error(f"获取活跃告警失败: {result.get('error')}")
                return []
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取活跃告警过程中出错: {str(e)}")
            return []
    
    async def resolve_alert(self, alert_id: str, admin_id: str) -> bool:
        """解决告警
        
        Args:
            alert_id: 告警ID
            admin_id: 操作者的用户ID（需要管理员权限）
            
        Returns:
            bool: 是否成功解决
            
        Raises:
            HTTPException: 如果没有权限
        """
        try:
            # 检查权限
            is_admin = await self._check_admin_permission(admin_id)
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="只有管理员可以解决告警"
                )
            
            result = await self.alert_manager.resolve_alert(alert_id, admin_id)
            return result["success"]
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"解决告警过程中出错: {str(e)}")
            return False
    
    # ==================== 辅助方法 ====================
    
    async def _check_admin_permission(self, user_id: str) -> bool:
        """检查用户是否为管理员
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否为管理员
        """
        if not user_id:
            return False
            
        try:
            # 使用core层的权限检查
            from core.auth import AuthService
            auth_service = AuthService(self.db)
            
            # 检查是否为管理员角色
            return await auth_service.check_permission(user_id, "admin_access")
            
        except Exception as e:
            logger.error(f"检查管理员权限失败: {str(e)}")
            return False
