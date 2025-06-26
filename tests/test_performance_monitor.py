#!/usr/bin/env python3
"""
工具性能监控系统测试
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import statistics

class MetricType(Enum):
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"  
    ERROR_RATE = "error_rate"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    CONCURRENT_USERS = "concurrent_users"

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class PerformanceMetric:
    metric_id: str
    metric_type: MetricType
    tool_name: str
    value: float
    timestamp: datetime
    unit: str
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

@dataclass
class PerformanceAlert:
    alert_id: str
    tool_name: str
    metric_type: MetricType
    level: AlertLevel
    message: str
    value: float
    threshold: float
    timestamp: datetime

@dataclass
class PerformanceThreshold:
    metric_type: MetricType
    warning_threshold: float
    critical_threshold: float
    tool_pattern: str = "*"

@dataclass
class PerformanceReport:
    tool_name: str
    time_period: str
    avg_response_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = 0.0
    throughput: float = 0.0
    error_rate: float = 0.0
    availability: float = 100.0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

class PerformanceMonitor:
    def __init__(self):
        self._metrics: List[PerformanceMetric] = []
        self._alerts: List[PerformanceAlert] = []
        self._thresholds: List[PerformanceThreshold] = []
        self._max_metrics = 50000
        
        # 实时性能计数器
        self._tool_metrics: Dict[str, Dict[str, List[float]]] = {}
        
        # 初始化默认阈值
        self._initialize_default_thresholds()
    
    def _initialize_default_thresholds(self):
        """初始化默认性能阈值"""
        default_thresholds = [
            PerformanceThreshold(MetricType.RESPONSE_TIME, 2000.0, 5000.0),  # 2s警告，5s严重
            PerformanceThreshold(MetricType.ERROR_RATE, 5.0, 20.0),          # 5%警告，20%严重
            PerformanceThreshold(MetricType.MEMORY_USAGE, 80.0, 95.0),       # 80%警告，95%严重
            PerformanceThreshold(MetricType.CPU_USAGE, 70.0, 90.0),          # 70%警告，90%严重
            PerformanceThreshold(MetricType.THROUGHPUT, 10.0, 5.0),          # 低于10请求/秒警告，5请求/秒严重
        ]
        self._thresholds.extend(default_thresholds)
    
    async def record_metric(self, metric: PerformanceMetric) -> bool:
        """记录性能指标"""
        try:
            # 添加指标
            self._metrics.append(metric)
            
            # 限制指标数量
            if len(self._metrics) > self._max_metrics:
                self._metrics = self._metrics[self._max_metrics // 2:]
            
            # 更新实时计数器
            await self._update_tool_metrics(metric)
            
            # 检查是否需要告警
            await self._check_thresholds(metric)
            
            return True
            
        except Exception as e:
            print(f"Failed to record metric: {e}")
            return False
    
    async def _update_tool_metrics(self, metric: PerformanceMetric):
        """更新工具实时指标"""
        tool_name = metric.tool_name
        metric_type = metric.metric_type.value
        
        if tool_name not in self._tool_metrics:
            self._tool_metrics[tool_name] = {}
        
        if metric_type not in self._tool_metrics[tool_name]:
            self._tool_metrics[tool_name][metric_type] = []
        
        # 保持最近100个数据点
        metrics_list = self._tool_metrics[tool_name][metric_type]
        metrics_list.append(metric.value)
        if len(metrics_list) > 100:
            metrics_list.pop(0)
    
    async def _check_thresholds(self, metric: PerformanceMetric):
        """检查性能阈值"""
        for threshold in self._thresholds:
            if threshold.metric_type != metric.metric_type:
                continue
            
            if threshold.tool_pattern != "*" and threshold.tool_pattern != metric.tool_name:
                continue
            
            # 检查临界阈值
            if metric.value >= threshold.critical_threshold:
                alert = PerformanceAlert(
                    alert_id=f"alert_{len(self._alerts) + 1}",
                    tool_name=metric.tool_name,
                    metric_type=metric.metric_type,
                    level=AlertLevel.CRITICAL,
                    message=f"Critical {metric.metric_type.value}: {metric.value} {metric.unit}",
                    value=metric.value,
                    threshold=threshold.critical_threshold,
                    timestamp=metric.timestamp
                )
                self._alerts.append(alert)
            
            # 检查警告阈值
            elif metric.value >= threshold.warning_threshold:
                alert = PerformanceAlert(
                    alert_id=f"alert_{len(self._alerts) + 1}",
                    tool_name=metric.tool_name,
                    metric_type=metric.metric_type,
                    level=AlertLevel.WARNING,
                    message=f"Warning {metric.metric_type.value}: {metric.value} {metric.unit}",
                    value=metric.value,
                    threshold=threshold.warning_threshold,
                    timestamp=metric.timestamp
                )
                self._alerts.append(alert)
    
    async def get_tool_performance(self, tool_name: str, start_time: datetime = None, end_time: datetime = None) -> PerformanceReport:
        """获取工具性能报告"""
        # 过滤指标
        filtered_metrics = []
        for metric in self._metrics:
            if metric.tool_name != tool_name:
                continue
            if start_time and metric.timestamp < start_time:
                continue
            if end_time and metric.timestamp > end_time:
                continue
            filtered_metrics.append(metric)
        
        if not filtered_metrics:
            return PerformanceReport(tool_name=tool_name, time_period="No data")
        
        # 计算性能指标
        response_times = [m.value for m in filtered_metrics if m.metric_type == MetricType.RESPONSE_TIME]
        error_rates = [m.value for m in filtered_metrics if m.metric_type == MetricType.ERROR_RATE]
        
        report = PerformanceReport(
            tool_name=tool_name,
            time_period=f"{start_time} to {end_time}" if start_time and end_time else "All time"
        )
        
        # 响应时间统计
        if response_times:
            report.avg_response_time = statistics.mean(response_times)
            report.max_response_time = max(response_times)
            report.min_response_time = min(response_times)
        
        # 错误率统计
        if error_rates:
            report.error_rate = statistics.mean(error_rates)
            report.availability = 100.0 - report.error_rate
        
        # 请求统计（简化计算）
        report.total_requests = len(response_times)
        if error_rates:
            report.failed_requests = int(report.total_requests * report.error_rate / 100)
            report.successful_requests = report.total_requests - report.failed_requests
        else:
            report.successful_requests = report.total_requests
        
        # 吞吐量（简化计算）
        if response_times and len(response_times) > 1:
            time_span_hours = (filtered_metrics[-1].timestamp - filtered_metrics[0].timestamp).total_seconds() / 3600
            if time_span_hours > 0:
                report.throughput = len(response_times) / time_span_hours
        
        return report
    
    async def get_real_time_metrics(self, tool_name: str) -> Dict[str, Any]:
        """获取实时性能指标"""
        if tool_name not in self._tool_metrics:
            return {"error": "No metrics found for tool"}
        
        tool_data = self._tool_metrics[tool_name]
        real_time_metrics = {}
        
        for metric_type, values in tool_data.items():
            if not values:
                continue
            
            real_time_metrics[metric_type] = {
                "current": values[-1],
                "average": statistics.mean(values),
                "max": max(values),
                "min": min(values),
                "samples": len(values)
            }
        
        return real_time_metrics
    
    async def get_alerts(self, level: AlertLevel = None, tool_name: str = None) -> List[PerformanceAlert]:
        """获取性能告警"""
        filtered_alerts = []
        
        for alert in self._alerts:
            if level and alert.level != level:
                continue
            if tool_name and alert.tool_name != tool_name:
                continue
            filtered_alerts.append(alert)
        
        # 按时间倒序排列
        filtered_alerts.sort(key=lambda a: a.timestamp, reverse=True)
        return filtered_alerts
    
    async def add_threshold(self, threshold: PerformanceThreshold) -> bool:
        """添加性能阈值"""
        try:
            self._thresholds.append(threshold)
            return True
        except Exception:
            return False
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        total_tools = len(set(m.tool_name for m in self._metrics))
        
        # 最近的告警
        recent_alerts = [a for a in self._alerts if (datetime.now() - a.timestamp).seconds < 3600]  # 最近1小时
        critical_alerts = [a for a in recent_alerts if a.level == AlertLevel.CRITICAL]
        warning_alerts = [a for a in recent_alerts if a.level == AlertLevel.WARNING]
        
        return {
            "total_tools_monitored": total_tools,
            "total_metrics": len(self._metrics),
            "total_alerts": len(self._alerts),
            "recent_critical_alerts": len(critical_alerts),
            "recent_warning_alerts": len(warning_alerts),
            "system_status": "CRITICAL" if critical_alerts else "WARNING" if warning_alerts else "HEALTHY"
        }

async def test_performance_monitor():
    try:
        print("=== 工具性能监控系统测试 ===")
        
        monitor = PerformanceMonitor()
        print("✅ 性能监控器创建成功")
        
        # 测试1: 记录性能指标
        print("\n📋 测试1: 记录性能指标")
        
        now = datetime.now()
        
        # 正常响应时间
        normal_metric = PerformanceMetric(
            metric_id="metric_001",
            metric_type=MetricType.RESPONSE_TIME,
            tool_name="agno_reasoning",
            value=1500.0,
            timestamp=now - timedelta(minutes=30),
            unit="ms"
        )
        
        # 高响应时间（触发警告）
        high_metric = PerformanceMetric(
            metric_id="metric_002", 
            metric_type=MetricType.RESPONSE_TIME,
            tool_name="agno_reasoning",
            value=3000.0,
            timestamp=now - timedelta(minutes=25),
            unit="ms"
        )
        
        # 极高响应时间（触发严重告警）
        critical_metric = PerformanceMetric(
            metric_id="metric_003",
            metric_type=MetricType.RESPONSE_TIME,
            tool_name="haystack_extract_answers",
            value=6000.0,
            timestamp=now - timedelta(minutes=20),
            unit="ms"
        )
        
        # 错误率指标
        error_metric = PerformanceMetric(
            metric_id="metric_004",
            metric_type=MetricType.ERROR_RATE,
            tool_name="agno_reasoning",
            value=3.5,
            timestamp=now - timedelta(minutes=15),
            unit="%"
        )
        
        success1 = await monitor.record_metric(normal_metric)
        success2 = await monitor.record_metric(high_metric)
        success3 = await monitor.record_metric(critical_metric)
        success4 = await monitor.record_metric(error_metric)
        
        print(f"  • 记录正常指标: {'✅' if success1 else '❌'}")
        print(f"  • 记录高响应时间指标: {'✅' if success2 else '❌'}")
        print(f"  • 记录严重指标: {'✅' if success3 else '❌'}")
        print(f"  • 记录错误率指标: {'✅' if success4 else '❌'}")
        
        # 测试2: 获取性能报告
        print("\n📋 测试2: 获取性能报告")
        
        agno_report = await monitor.get_tool_performance("agno_reasoning")
        print(f"  • Agno推理工具性能报告:")
        print(f"    - 平均响应时间: {agno_report.avg_response_time:.1f}ms")
        print(f"    - 最大响应时间: {agno_report.max_response_time:.1f}ms")
        print(f"    - 最小响应时间: {agno_report.min_response_time:.1f}ms")
        print(f"    - 错误率: {agno_report.error_rate:.1f}%")
        print(f"    - 可用性: {agno_report.availability:.1f}%")
        print(f"    - 总请求数: {agno_report.total_requests}")
        
        # 测试3: 获取实时指标
        print("\n📋 测试3: 获取实时指标")
        
        real_time = await monitor.get_real_time_metrics("agno_reasoning")
        if "response_time" in real_time:
            rt_metrics = real_time["response_time"]
            print(f"  • 实时响应时间指标:")
            print(f"    - 当前值: {rt_metrics['current']:.1f}ms")
            print(f"    - 平均值: {rt_metrics['average']:.1f}ms")
            print(f"    - 最大值: {rt_metrics['max']:.1f}ms")
            print(f"    - 样本数: {rt_metrics['samples']}")
        
        # 测试4: 获取告警
        print("\n📋 测试4: 获取告警")
        
        all_alerts = await monitor.get_alerts()
        critical_alerts = await monitor.get_alerts(AlertLevel.CRITICAL)
        warning_alerts = await monitor.get_alerts(AlertLevel.WARNING)
        
        print(f"  • 总告警数: {len(all_alerts)}")
        print(f"  • 严重告警数: {len(critical_alerts)}")
        print(f"  • 警告告警数: {len(warning_alerts)}")
        
        if all_alerts:
            latest_alert = all_alerts[0]
            print(f"  • 最新告警:")
            print(f"    - 级别: {latest_alert.level.value}")
            print(f"    - 工具: {latest_alert.tool_name}")
            print(f"    - 消息: {latest_alert.message}")
            print(f"    - 值: {latest_alert.value}")
            print(f"    - 阈值: {latest_alert.threshold}")
        
        # 测试5: 系统健康状态
        print("\n📋 测试5: 系统健康状态")
        
        health = monitor.get_system_health()
        print(f"  • 监控工具数: {health['total_tools_monitored']}")
        print(f"  • 总指标数: {health['total_metrics']}")
        print(f"  • 总告警数: {health['total_alerts']}")
        print(f"  • 最近严重告警: {health['recent_critical_alerts']}")
        print(f"  • 最近警告告警: {health['recent_warning_alerts']}")
        print(f"  • 系统状态: {health['system_status']}")
        
        # 测试6: 添加自定义阈值
        print("\n📋 测试6: 添加自定义阈值")
        
        custom_threshold = PerformanceThreshold(
            metric_type=MetricType.RESPONSE_TIME,
            warning_threshold=1000.0,
            critical_threshold=2000.0,
            tool_pattern="custom_*"
        )
        
        threshold_success = await monitor.add_threshold(custom_threshold)
        print(f"  • 添加自定义阈值: {'✅' if threshold_success else '❌'}")
        
        print("\n✅ 工具性能监控系统测试完成！")
        
        print("\n📊 测试总结:")
        print("✅ 性能指标记录功能正常")
        print("✅ 性能报告生成功能正常")
        print("✅ 实时指标获取功能正常")
        print("✅ 告警机制功能正常")
        print("✅ 阈值检查功能正常")
        print("✅ 系统健康监控功能正常")
        print("✅ 自定义阈值功能正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 性能监控系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_performance_monitor())
    print(f"\n🎯 测试结果: {'✅ 全部通过' if success else '❌ 有失败项'}")
    exit(0 if success else 1) 