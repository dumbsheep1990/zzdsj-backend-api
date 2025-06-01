"""
指标收集框架
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import time
import threading
from collections import defaultdict, deque


class MetricType(str, Enum):
    """指标类型"""
    COUNTER = "counter"      # 计数器 - 只能增加
    GAUGE = "gauge"          # 仪表 - 可以任意增减  
    HISTOGRAM = "histogram"  # 直方图 - 分布统计
    SUMMARY = "summary"      # 摘要 - 分位数统计


@dataclass
class Metric:
    """
    指标数据结构
    """
    name: str
    value: Union[int, float]
    metric_type: MetricType
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "timestamp": self.timestamp,
            "labels": self.labels,
            "description": self.description
        }


class MetricsCollector:
    """
    指标收集器
    提供线程安全的指标收集和存储功能
    """
    
    def __init__(self, max_metrics: int = 10000):
        """
        初始化指标收集器
        
        参数:
            max_metrics: 最大存储指标数量
        """
        self.max_metrics = max_metrics
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_metrics))
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def record_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None, description: str = "") -> None:
        """
        记录计数器指标
        
        参数:
            name: 指标名称
            value: 增量值（默认1.0）
            labels: 标签
            description: 描述
        """
        with self._lock:
            metric_key = self._make_key(name, labels)
            self._counters[metric_key] += value
            
            metric = Metric(
                name=name,
                value=self._counters[metric_key], 
                metric_type=MetricType.COUNTER,
                labels=labels or {},
                description=description
            )
            
            self._metrics[metric_key].append(metric)
    
    def record_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None, description: str = "") -> None:
        """
        记录仪表指标
        
        参数:
            name: 指标名称
            value: 当前值
            labels: 标签
            description: 描述
        """
        with self._lock:
            metric_key = self._make_key(name, labels)
            self._gauges[metric_key] = value
            
            metric = Metric(
                name=name,
                value=value,
                metric_type=MetricType.GAUGE,
                labels=labels or {},
                description=description
            )
            
            self._metrics[metric_key].append(metric)
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None, description: str = "") -> None:
        """
        记录直方图指标
        
        参数:
            name: 指标名称
            value: 观测值
            labels: 标签
            description: 描述
        """
        with self._lock:
            metric_key = self._make_key(name, labels)
            self._histograms[metric_key].append(value)
            
            # 保持直方图大小在合理范围内
            if len(self._histograms[metric_key]) > 1000:
                self._histograms[metric_key] = self._histograms[metric_key][-1000:]
            
            metric = Metric(
                name=name,
                value=value,
                metric_type=MetricType.HISTOGRAM,
                labels=labels or {},
                description=description
            )
            
            self._metrics[metric_key].append(metric)
    
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """获取计数器当前值"""
        metric_key = self._make_key(name, labels)
        return self._counters.get(metric_key, 0.0)
    
    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """获取仪表当前值"""
        metric_key = self._make_key(name, labels)
        return self._gauges.get(metric_key)
    
    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """获取直方图统计信息"""
        metric_key = self._make_key(name, labels)
        values = self._histograms.get(metric_key, [])
        
        if not values:
            return {}
        
        sorted_values = sorted(values)
        count = len(sorted_values)
        
        return {
            "count": count,
            "sum": sum(sorted_values),
            "min": min(sorted_values),
            "max": max(sorted_values),
            "mean": sum(sorted_values) / count,
            "p50": sorted_values[int(count * 0.5)],
            "p90": sorted_values[int(count * 0.9)],
            "p95": sorted_values[int(count * 0.95)],
            "p99": sorted_values[int(count * 0.99)]
        }
    
    def get_all_metrics(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有指标"""
        with self._lock:
            result = {}
            for key, metrics_deque in self._metrics.items():
                result[key] = [metric.to_dict() for metric in metrics_deque]
            return result
    
    def get_latest_metrics(self) -> Dict[str, Dict[str, Any]]:
        """获取最新的指标值"""
        with self._lock:
            result = {}
            for key, metrics_deque in self._metrics.items():
                if metrics_deque:
                    result[key] = metrics_deque[-1].to_dict()
            return result
    
    def clear_metrics(self, name_pattern: Optional[str] = None) -> None:
        """
        清除指标数据
        
        参数:
            name_pattern: 指标名称模式，如果为None则清除所有指标
        """
        with self._lock:
            if name_pattern is None:
                self._metrics.clear()
                self._counters.clear()
                self._gauges.clear()
                self._histograms.clear()
            else:
                keys_to_remove = [key for key in self._metrics.keys() if name_pattern in key]
                for key in keys_to_remove:
                    del self._metrics[key]
                    self._counters.pop(key, None)
                    self._gauges.pop(key, None)
                    self._histograms.pop(key, None)
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """生成指标键"""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要信息"""
        with self._lock:
            return {
                "total_metrics": len(self._metrics),
                "counters": len(self._counters),
                "gauges": len(self._gauges),
                "histograms": len(self._histograms),
                "memory_usage": {
                    "metrics_count": sum(len(deque) for deque in self._metrics.values()),
                    "max_metrics": self.max_metrics
                }
            } 