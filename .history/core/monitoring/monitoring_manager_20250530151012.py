"""
监控管理器
提供系统监控的核心业务逻辑
"""

import logging
import psutil
import time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.monitoring import SystemMetrics, ServiceHealth, AlertRule, AlertLog
from app.repositories.monitoring_repository import MonitoringRepository
from .metrics_collector import MetricsCollector
from .alert_manager import AlertManager

logger = logging.getLogger(__name__)


class MonitoringManager:
    """监控管理器 - Core层业务逻辑"""
    
    def __init__(self, db: Session):
        """初始化监控管理器"""
        self.db = db
        self.repository = MonitoringRepository(db)
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager(db)
    
    # ============ 系统指标监控 ============
    
    async def collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统指标 - 业务逻辑层"""
        try:
            # 收集系统指标
            metrics_data = self.metrics_collector.collect_system_metrics()
            
            # 保存到数据库
            metrics = await self.repository.save_system_metrics(metrics_data)
            
            # 检查告警规则
            await self._check_alert_rules(metrics_data)
            
            return {
                "success": True,
                "data": {
                    "metrics_id": metrics.id,
                    "timestamp": metrics.timestamp.isoformat(),
                    "cpu_usage": metrics_data["cpu_usage"],
                    "memory_usage": metrics_data["memory_usage"],
                    "disk_usage": metrics_data["disk_usage"],
                    "network_io": metrics_data["network_io"]
                }
            }
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {str(e)}")
            return {
                "success": False,
                "error": f"收集系统指标失败: {str(e)}",
                "error_code": "COLLECT_METRICS_FAILED"
            }
    
    async def get_system_metrics_history(self, hours: int = 24, 
                                       interval_minutes: int = 5) -> Dict[str, Any]:
        """获取系统指标历史 - 业务逻辑层"""
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            
            metrics_list = await self.repository.get_metrics_history(
                start_time=start_time,
                interval_minutes=interval_minutes
            )
            
            # 处理数据格式
            formatted_metrics = []
            for metrics in metrics_list:
                formatted_metrics.append({
                    "timestamp": metrics.timestamp.isoformat(),
                    "cpu_usage": metrics.cpu_usage,
                    "memory_usage": metrics.memory_usage,
                    "disk_usage": metrics.disk_usage,
                    "network_io_read": metrics.network_io_read,
                    "network_io_write": metrics.network_io_write,
                    "active_connections": metrics.active_connections,
                    "response_time": metrics.response_time
                })
            
            return {
                "success": True,
                "data": {
                    "metrics": formatted_metrics,
                    "period": {
                        "start": start_time.isoformat(),
                        "end": datetime.now().isoformat(),
                        "hours": hours,
                        "interval_minutes": interval_minutes
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"获取系统指标历史失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取系统指标历史失败: {str(e)}",
                "error_code": "GET_HISTORY_FAILED"
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态概览 - 业务逻辑层"""
        try:
            # 获取最新指标
            latest_metrics = await self.repository.get_latest_metrics()
            
            # 获取服务健康状态
            service_health = await self.get_services_health()
            
            # 获取活跃告警
            active_alerts = await self.alert_manager.get_active_alerts()
            
            # 计算系统健康评分
            health_score = self._calculate_health_score(latest_metrics, service_health["data"])
            
            return {
                "success": True,
                "data": {
                    "health_score": health_score,
                    "status": self._get_status_level(health_score),
                    "latest_metrics": {
                        "timestamp": latest_metrics.timestamp.isoformat() if latest_metrics else None,
                        "cpu_usage": latest_metrics.cpu_usage if latest_metrics else None,
                        "memory_usage": latest_metrics.memory_usage if latest_metrics else None,
                        "disk_usage": latest_metrics.disk_usage if latest_metrics else None,
                        "response_time": latest_metrics.response_time if latest_metrics else None
                    },
                    "services": service_health["data"] if service_health["success"] else [],
                    "active_alerts": active_alerts["data"] if active_alerts["success"] else [],
                    "last_updated": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取系统状态失败: {str(e)}",
                "error_code": "GET_STATUS_FAILED"
            }
    
    # ============ 服务健康监控 ============
    
    async def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """检查服务健康状态 - 业务逻辑层"""
        try:
            # 执行健康检查
            health_data = await self.metrics_collector.check_service_health(service_name)
            
            # 保存健康状态
            health_record = await self.repository.save_service_health(service_name, health_data)
            
            # 检查服务告警
            await self._check_service_alerts(service_name, health_data)
            
            return {
                "success": True,
                "data": {
                    "service_name": service_name,
                    "status": health_data["status"],
                    "response_time": health_data["response_time"],
                    "error_message": health_data.get("error_message"),
                    "checked_at": health_record.checked_at.isoformat(),
                    "details": health_data.get("details", {})
                }
            }
            
        except Exception as e:
            logger.error(f"检查服务健康状态失败: {str(e)}")
            return {
                "success": False,
                "error": f"检查服务健康状态失败: {str(e)}",
                "error_code": "CHECK_HEALTH_FAILED"
            }
    
    async def get_services_health(self) -> Dict[str, Any]:
        """获取所有服务健康状态 - 业务逻辑层"""
        try:
            services_health = await self.repository.get_services_health()
            
            formatted_health = []
            for health in services_health:
                formatted_health.append({
                    "service_name": health.service_name,
                    "status": health.status,
                    "response_time": health.response_time,
                    "error_message": health.error_message,
                    "checked_at": health.checked_at.isoformat(),
                    "uptime_percentage": await self._calculate_uptime(health.service_name)
                })
            
            return {
                "success": True,
                "data": formatted_health
            }
            
        except Exception as e:
            logger.error(f"获取服务健康状态失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取服务健康状态失败: {str(e)}",
                "error_code": "GET_SERVICES_HEALTH_FAILED"
            }
    
    # ============ 性能分析 ============
    
    async def analyze_performance_trends(self, days: int = 7) -> Dict[str, Any]:
        """分析性能趋势 - 业务逻辑层"""
        try:
            start_time = datetime.now() - timedelta(days=days)
            
            # 获取历史数据
            metrics_data = await self.repository.get_metrics_for_analysis(start_time)
            
            # 分析趋势
            trends = self._analyze_trends(metrics_data)
            
            # 生成建议
            recommendations = self._generate_recommendations(trends)
            
            return {
                "success": True,
                "data": {
                    "analysis_period": {
                        "start": start_time.isoformat(),
                        "end": datetime.now().isoformat(),
                        "days": days
                    },
                    "trends": trends,
                    "recommendations": recommendations,
                    "summary": {
                        "avg_cpu_usage": trends["cpu"]["average"],
                        "avg_memory_usage": trends["memory"]["average"],
                        "avg_response_time": trends["response_time"]["average"],
                        "peak_usage_time": trends["peak_time"]
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"分析性能趋势失败: {str(e)}")
            return {
                "success": False,
                "error": f"分析性能趋势失败: {str(e)}",
                "error_code": "ANALYZE_TRENDS_FAILED"
            }
    
    async def get_resource_usage_report(self, period: str = "daily") -> Dict[str, Any]:
        """获取资源使用报告 - 业务逻辑层"""
        try:
            # 根据周期确定时间范围
            if period == "daily":
                start_time = datetime.now() - timedelta(days=1)
                interval_minutes = 10
            elif period == "weekly":
                start_time = datetime.now() - timedelta(weeks=1)
                interval_minutes = 60
            elif period == "monthly":
                start_time = datetime.now() - timedelta(days=30)
                interval_minutes = 240
            else:
                raise ValueError(f"不支持的周期: {period}")
            
            # 获取数据
            metrics_data = await self.repository.get_aggregated_metrics(
                start_time=start_time,
                interval_minutes=interval_minutes
            )
            
            # 生成报告
            report = self._generate_usage_report(metrics_data, period)
            
            return {
                "success": True,
                "data": report
            }
            
        except Exception as e:
            logger.error(f"获取资源使用报告失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取资源使用报告失败: {str(e)}",
                "error_code": "GET_REPORT_FAILED"
            }
    
    # ============ 私有辅助方法 ============
    
    async def _check_alert_rules(self, metrics_data: Dict[str, Any]) -> None:
        """检查告警规则"""
        try:
            alert_rules = await self.repository.get_active_alert_rules()
            
            for rule in alert_rules:
                if self._should_trigger_alert(rule, metrics_data):
                    await self.alert_manager.trigger_alert(rule, metrics_data)
                    
        except Exception as e:
            logger.error(f"检查告警规则失败: {str(e)}")
    
    async def _check_service_alerts(self, service_name: str, health_data: Dict[str, Any]) -> None:
        """检查服务告警"""
        try:
            if health_data["status"] != "healthy":
                await self.alert_manager.trigger_service_alert(service_name, health_data)
                
        except Exception as e:
            logger.error(f"检查服务告警失败: {str(e)}")
    
    def _should_trigger_alert(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> bool:
        """判断是否应该触发告警"""
        try:
            metric_value = metrics_data.get(rule.metric_name)
            if metric_value is None:
                return False
            
            if rule.condition == "greater_than":
                return metric_value > rule.threshold
            elif rule.condition == "less_than":
                return metric_value < rule.threshold
            elif rule.condition == "equals":
                return metric_value == rule.threshold
            
            return False
            
        except Exception:
            return False
    
    def _calculate_health_score(self, latest_metrics: Optional[SystemMetrics], 
                              services_health: List[Dict[str, Any]]) -> float:
        """计算系统健康评分"""
        try:
            score = 100.0
            
            # 基于系统指标扣分
            if latest_metrics:
                if latest_metrics.cpu_usage > 80:
                    score -= 20
                elif latest_metrics.cpu_usage > 60:
                    score -= 10
                
                if latest_metrics.memory_usage > 85:
                    score -= 20
                elif latest_metrics.memory_usage > 70:
                    score -= 10
                
                if latest_metrics.disk_usage > 90:
                    score -= 15
                elif latest_metrics.disk_usage > 80:
                    score -= 5
            
            # 基于服务健康状态扣分
            unhealthy_services = sum(1 for service in services_health if service["status"] != "healthy")
            if unhealthy_services > 0:
                score -= unhealthy_services * 15
            
            return max(0.0, min(100.0, score))
            
        except Exception:
            return 50.0  # 默认中等健康评分
    
    def _get_status_level(self, health_score: float) -> str:
        """根据健康评分获取状态级别"""
        if health_score >= 90:
            return "excellent"
        elif health_score >= 75:
            return "good"
        elif health_score >= 60:
            return "warning"
        elif health_score >= 40:
            return "critical"
        else:
            return "emergency"
    
    async def _calculate_uptime(self, service_name: str) -> float:
        """计算服务可用性百分比"""
        try:
            # 获取最近24小时的健康检查记录
            start_time = datetime.now() - timedelta(hours=24)
            health_records = await self.repository.get_service_health_history(
                service_name, start_time
            )
            
            if not health_records:
                return 0.0
            
            healthy_count = sum(1 for record in health_records if record.status == "healthy")
            return (healthy_count / len(health_records)) * 100
            
        except Exception:
            return 0.0
    
    def _analyze_trends(self, metrics_data: List[SystemMetrics]) -> Dict[str, Any]:
        """分析性能趋势"""
        if not metrics_data:
            return {}
        
        cpu_values = [m.cpu_usage for m in metrics_data]
        memory_values = [m.memory_usage for m in metrics_data]
        response_times = [m.response_time for m in metrics_data if m.response_time]
        
        return {
            "cpu": {
                "average": sum(cpu_values) / len(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values),
                "trend": "increasing" if cpu_values[-1] > cpu_values[0] else "decreasing"
            },
            "memory": {
                "average": sum(memory_values) / len(memory_values),
                "max": max(memory_values),
                "min": min(memory_values),
                "trend": "increasing" if memory_values[-1] > memory_values[0] else "decreasing"
            },
            "response_time": {
                "average": sum(response_times) / len(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "min": min(response_times) if response_times else 0
            },
            "peak_time": self._find_peak_usage_time(metrics_data)
        }
    
    def _find_peak_usage_time(self, metrics_data: List[SystemMetrics]) -> str:
        """找出峰值使用时间"""
        if not metrics_data:
            return "unknown"
        
        max_usage = 0
        peak_time = None
        
        for metrics in metrics_data:
            total_usage = metrics.cpu_usage + metrics.memory_usage
            if total_usage > max_usage:
                max_usage = total_usage
                peak_time = metrics.timestamp
        
        return peak_time.strftime("%H:%M") if peak_time else "unknown"
    
    def _generate_recommendations(self, trends: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        if trends.get("cpu", {}).get("average", 0) > 70:
            recommendations.append("CPU使用率较高，建议优化计算密集型任务或增加计算资源")
        
        if trends.get("memory", {}).get("average", 0) > 80:
            recommendations.append("内存使用率较高，建议检查内存泄漏或增加内存容量")
        
        if trends.get("response_time", {}).get("average", 0) > 1000:
            recommendations.append("响应时间较长，建议优化数据库查询或增加缓存")
        
        if not recommendations:
            recommendations.append("系统运行状态良好，继续保持当前配置")
        
        return recommendations
    
    def _generate_usage_report(self, metrics_data: List[SystemMetrics], period: str) -> Dict[str, Any]:
        """生成使用报告"""
        if not metrics_data:
            return {"error": "没有可用数据"}
        
        cpu_values = [m.cpu_usage for m in metrics_data]
        memory_values = [m.memory_usage for m in metrics_data]
        disk_values = [m.disk_usage for m in metrics_data]
        
        return {
            "period": period,
            "data_points": len(metrics_data),
            "cpu_usage": {
                "average": sum(cpu_values) / len(cpu_values),
                "peak": max(cpu_values),
                "minimum": min(cpu_values)
            },
            "memory_usage": {
                "average": sum(memory_values) / len(memory_values),
                "peak": max(memory_values),
                "minimum": min(memory_values)
            },
            "disk_usage": {
                "average": sum(disk_values) / len(disk_values),
                "peak": max(disk_values),
                "minimum": min(disk_values)
            },
            "generated_at": datetime.now().isoformat()
        } 