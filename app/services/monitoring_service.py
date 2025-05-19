"""
监控服务模块
处理系统监控和性能跟踪相关的业务逻辑
"""

from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import psutil

from app.utils.database import get_db
from app.models.monitoring import SystemMetric, ServiceStatus, RequestLog, ErrorLog
from app.repositories.monitoring_repository import (
    SystemMetricRepository, 
    ServiceStatusRepository,
    RequestLogRepository,
    ErrorLogRepository
)
from app.services.resource_permission_service import ResourcePermissionService

class MonitoringService:
    """监控服务类"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 permission_service: ResourcePermissionService = Depends()):
        """初始化监控服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
        """
        self.db = db
        self.metric_repository = SystemMetricRepository()
        self.status_repository = ServiceStatusRepository()
        self.request_repository = RequestLogRepository()
        self.error_repository = ErrorLogRepository()
        self.permission_service = permission_service
    
    # ==================== 系统指标管理 ====================
    
    async def record_system_metrics(self) -> SystemMetric:
        """记录系统指标
        
        Returns:
            SystemMetric: 创建的系统指标记录
        """
        # 收集系统指标
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 创建指标数据
        metric_data = {
            "timestamp": datetime.utcnow(),
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "memory_available": memory.available,
            "disk_usage": disk.percent,
            "disk_available": disk.free,
            "network_metrics": self._get_network_metrics()
        }
        
        # 记录指标
        return await self.metric_repository.create(metric_data, self.db)
    
    async def get_system_metrics(self, start_time: datetime, end_time: datetime, user_id: str) -> List[SystemMetric]:
        """获取系统指标
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            user_id: 用户ID
            
        Returns:
            List[SystemMetric]: 系统指标列表
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 检查权限
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以查看系统指标"
            )
        
        # 获取指标
        return await self.metric_repository.get_in_time_range(start_time, end_time, self.db)
    
    async def get_latest_system_metrics(self, user_id: str) -> SystemMetric:
        """获取最新系统指标
        
        Args:
            user_id: 用户ID
            
        Returns:
            SystemMetric: 最新系统指标
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 检查权限
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以查看系统指标"
            )
        
        # 获取最新指标
        return await self.metric_repository.get_latest(self.db)
    
    # ==================== 服务状态管理 ====================
    
    async def update_service_status(self, service_name: str, status: str, details: Dict[str, Any] = None) -> ServiceStatus:
        """更新服务状态
        
        Args:
            service_name: 服务名称
            status: 状态 ('up', 'down', 'degraded')
            details: 状态详情
            
        Returns:
            ServiceStatus: 更新后的服务状态
        """
        # 获取现有状态
        current_status = await self.status_repository.get_by_name(service_name, self.db)
        
        # 准备状态数据
        status_data = {
            "service_name": service_name,
            "status": status,
            "details": details or {},
            "last_updated": datetime.utcnow()
        }
        
        # 更新或创建状态
        if current_status:
            return await self.status_repository.update(current_status.id, status_data, self.db)
        else:
            return await self.status_repository.create(status_data, self.db)
    
    async def get_service_status(self, service_name: str, user_id: str) -> ServiceStatus:
        """获取服务状态
        
        Args:
            service_name: 服务名称
            user_id: 用户ID
            
        Returns:
            ServiceStatus: 服务状态
            
        Raises:
            HTTPException: 如果服务不存在或没有权限
        """
        # 获取服务状态
        status = await self.status_repository.get_by_name(service_name, self.db)
        if not status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"服务 '{service_name}' 状态不存在"
            )
        
        return status
    
    async def get_all_service_statuses(self, user_id: str) -> List[ServiceStatus]:
        """获取所有服务状态
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[ServiceStatus]: 服务状态列表
        """
        # 获取所有服务状态
        return await self.status_repository.list_all(self.db)
    
    # ==================== 请求日志管理 ====================
    
    async def log_request(self, 
                       endpoint: str, 
                       method: str, 
                       user_id: Optional[str], 
                       response_time: float,
                       status_code: int,
                       request_data: Dict[str, Any] = None,
                       response_data: Dict[str, Any] = None) -> RequestLog:
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
            RequestLog: 创建的请求日志
        """
        # 创建日志数据
        log_data = {
            "timestamp": datetime.utcnow(),
            "endpoint": endpoint,
            "method": method,
            "user_id": user_id,
            "response_time": response_time,
            "status_code": status_code,
            "request_data": request_data,
            "response_data": response_data
        }
        
        # 记录请求
        return await self.request_repository.create(log_data, self.db)
    
    async def get_request_logs(self, 
                            start_time: datetime, 
                            end_time: datetime, 
                            endpoint: Optional[str] = None,
                            user_id: Optional[str] = None,
                            status_code: Optional[int] = None,
                            admin_id: str = None,
                            skip: int = 0, 
                            limit: int = 100) -> List[RequestLog]:
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
            List[RequestLog]: 请求日志列表
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 检查权限
        is_admin = await self._check_admin_permission(admin_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以查看请求日志"
            )
        
        # 获取日志
        return await self.request_repository.get_filtered_logs(
            start_time, end_time, endpoint, user_id, status_code, skip, limit, self.db
        )
    
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
        # 检查权限
        is_admin = await self._check_admin_permission(admin_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以查看请求统计分析"
            )
        
        # 获取时间范围内的所有请求
        logs = await self.request_repository.get_in_time_range(start_time, end_time, self.db)
        
        # 计算统计数据
        total_requests = len(logs)
        
        # 按端点分组
        endpoints = {}
        for log in logs:
            endpoint = log.endpoint
            if endpoint not in endpoints:
                endpoints[endpoint] = {
                    "count": 0,
                    "success_count": 0,
                    "avg_response_time": 0,
                    "total_response_time": 0
                }
            
            endpoints[endpoint]["count"] += 1
            if 200 <= log.status_code < 300:
                endpoints[endpoint]["success_count"] += 1
            endpoints[endpoint]["total_response_time"] += log.response_time
        
        # 计算平均响应时间
        for endpoint, data in endpoints.items():
            if data["count"] > 0:
                data["avg_response_time"] = data["total_response_time"] / data["count"]
            del data["total_response_time"]
        
        # 计算成功率
        success_rate = 0
        if total_requests > 0:
            success_count = sum(data["success_count"] for data in endpoints.values())
            success_rate = (success_count / total_requests) * 100
        
        # 返回统计数据
        return {
            "total_requests": total_requests,
            "success_rate": success_rate,
            "endpoint_stats": endpoints,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }
    
    # ==================== 错误日志管理 ====================
    
    async def log_error(self, 
                     error_type: str, 
                     error_message: str, 
                     source: str,
                     user_id: Optional[str] = None,
                     details: Dict[str, Any] = None) -> ErrorLog:
        """记录错误
        
        Args:
            error_type: 错误类型
            error_message: 错误消息
            source: 错误来源
            user_id: 相关的用户ID（可选）
            details: 错误详情（可选）
            
        Returns:
            ErrorLog: 创建的错误日志
        """
        # 创建日志数据
        log_data = {
            "timestamp": datetime.utcnow(),
            "error_type": error_type,
            "error_message": error_message,
            "source": source,
            "user_id": user_id,
            "details": details or {}
        }
        
        # 记录错误
        return await self.error_repository.create(log_data, self.db)
    
    async def get_error_logs(self, 
                          start_time: datetime, 
                          end_time: datetime, 
                          error_type: Optional[str] = None,
                          source: Optional[str] = None,
                          user_id: Optional[str] = None,
                          admin_id: str = None,
                          skip: int = 0, 
                          limit: int = 100) -> List[ErrorLog]:
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
            List[ErrorLog]: 错误日志列表
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 检查权限
        is_admin = await self._check_admin_permission(admin_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以查看错误日志"
            )
        
        # 获取日志
        return await self.error_repository.get_filtered_logs(
            start_time, end_time, error_type, source, user_id, skip, limit, self.db
        )
    
    # ==================== 辅助方法 ====================
    
    def _get_network_metrics(self) -> Dict[str, Any]:
        """获取网络指标
        
        Returns:
            Dict[str, Any]: 网络指标
        """
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        }
    
    async def _check_admin_permission(self, user_id: str) -> bool:
        """检查用户是否为管理员
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否为管理员
        """
        if not user_id:
            return False
            
        from app.services.user_service import UserService
        user_service = UserService(self.db)
        user = await user_service.get_by_id(user_id)
        return user and user.role == "admin"
