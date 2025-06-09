"""
安全组件抽象基类
提供威胁检测、安全事件管理和风险评估功能
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Union
from enum import Enum
import logging
import asyncio
from datetime import datetime, timedelta
import json
import hashlib

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """安全级别枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(Enum):
    """威胁类型枚举"""
    UNKNOWN = "unknown"
    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    DOS = "dos"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_LEAK = "data_leak"
    MALICIOUS_CONTENT = "malicious_content"


class SecurityEvent:
    """安全事件数据类"""
    
    def __init__(self, event_type: ThreatType, level: SecurityLevel, 
                 source_ip: str = "", user_id: str = "", 
                 description: str = "", metadata: Optional[Dict[str, Any]] = None):
        self.event_id = self._generate_event_id()
        self.event_type = event_type
        self.level = level
        self.source_ip = source_ip
        self.user_id = user_id
        self.description = description
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
        self.resolved = False
        self.resolved_at = None
        
    def _generate_event_id(self) -> str:
        """生成事件ID"""
        import uuid
        return str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "level": self.level.value,
            "source_ip": self.source_ip,
            "user_id": self.user_id,
            "description": self.description,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }
    
    def resolve(self, resolution_note: str = "") -> None:
        """标记事件为已解决"""
        self.resolved = True
        self.resolved_at = datetime.now()
        if resolution_note:
            self.metadata["resolution_note"] = resolution_note


class SecurityComponent(ABC):
    """
    安全组件抽象基类
    所有安全相关组件的基础类
    支持威胁检测、安全事件管理和风险评估
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化安全组件
        
        参数:
            config: 配置参数字典
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialized = False
        
        # 安全事件管理
        self._security_events: List[SecurityEvent] = []
        self._threat_patterns: Dict[str, Dict[str, Any]] = {}
        self._blocked_ips: Dict[str, Dict[str, Any]] = {}
        self._risk_scores: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        
        # 配置参数
        self.max_events_history = self.config.get("max_events_history", 10000)
        self.auto_block_threshold = self.config.get("auto_block_threshold", 10)
        self.block_duration_minutes = self.config.get("block_duration_minutes", 60)
        self.risk_threshold_high = self.config.get("risk_threshold_high", 0.8)
        self.risk_threshold_medium = self.config.get("risk_threshold_medium", 0.5)
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        初始化组件
        子类必须实现此方法
        """
        pass
    
    @abstractmethod
    async def check(self, *args, **kwargs) -> Any:
        """
        执行安全检查
        子类必须实现此方法
        """
        pass
    
    async def detect_threat(self, request_data: Dict[str, Any]) -> Optional[SecurityEvent]:
        """
        威胁检测
        
        Args:
            request_data: 请求数据
            
        Returns:
            Optional[SecurityEvent]: 检测到的安全事件，如果没有威胁则返回None
        """
        # 提取关键信息
        source_ip = request_data.get("source_ip", "")
        user_id = request_data.get("user_id", "")
        content = request_data.get("content", "")
        headers = request_data.get("headers", {})
        
        # 检查IP是否被阻止
        if await self._is_ip_blocked(source_ip):
            return SecurityEvent(
                event_type=ThreatType.UNAUTHORIZED_ACCESS,
                level=SecurityLevel.HIGH,
                source_ip=source_ip,
                user_id=user_id,
                description="访问被阻止的IP地址",
                metadata={"reason": "blocked_ip"}
            )
        
        # 暴力破解检测
        brute_force_event = await self._detect_brute_force(source_ip, user_id, request_data)
        if brute_force_event:
            return brute_force_event
        
        # SQL注入检测
        sql_injection_event = await self._detect_sql_injection(content)
        if sql_injection_event:
            sql_injection_event.source_ip = source_ip
            sql_injection_event.user_id = user_id
            return sql_injection_event
        
        # XSS检测
        xss_event = await self._detect_xss(content)
        if xss_event:
            xss_event.source_ip = source_ip
            xss_event.user_id = user_id
            return xss_event
        
        # 恶意内容检测
        malicious_event = await self._detect_malicious_content(content)
        if malicious_event:
            malicious_event.source_ip = source_ip
            malicious_event.user_id = user_id
            return malicious_event
        
        return None
    
    async def _detect_brute_force(self, source_ip: str, user_id: str, 
                                request_data: Dict[str, Any]) -> Optional[SecurityEvent]:
        """检测暴力破解攻击"""
        # 检查最近失败的登录尝试
        recent_failures = await self._count_recent_failures(source_ip, user_id)
        
        if recent_failures >= self.auto_block_threshold:
            # 自动阻止IP
            await self._block_ip(source_ip, f"暴力破解攻击 - {recent_failures}次失败尝试")
            
            return SecurityEvent(
                event_type=ThreatType.BRUTE_FORCE,
                level=SecurityLevel.CRITICAL,
                source_ip=source_ip,
                user_id=user_id,
                description=f"检测到暴力破解攻击，{recent_failures}次失败尝试",
                metadata={"failure_count": recent_failures, "auto_blocked": True}
            )
        
        return None
    
    async def _detect_sql_injection(self, content: str) -> Optional[SecurityEvent]:
        """检测SQL注入攻击"""
        if not content:
            return None
        
        # SQL注入模式
        sql_patterns = [
            r"union\s+select", r"1\s*=\s*1", r"'\s*or\s*'", r"--\s*",
            r"drop\s+table", r"insert\s+into", r"delete\s+from",
            r"xp_cmdshell", r"sp_executesql"
        ]
        
        import re
        content_lower = content.lower()
        
        for pattern in sql_patterns:
            if re.search(pattern, content_lower):
                return SecurityEvent(
                    event_type=ThreatType.SQL_INJECTION,
                    level=SecurityLevel.HIGH,
                    description=f"检测到SQL注入攻击模式: {pattern}",
                    metadata={"pattern": pattern, "content_sample": content[:200]}
                )
        
        return None
    
    async def _detect_xss(self, content: str) -> Optional[SecurityEvent]:
        """检测XSS攻击"""
        if not content:
            return None
        
        # XSS模式
        xss_patterns = [
            r"<script", r"javascript:", r"onload\s*=", r"onerror\s*=",
            r"onclick\s*=", r"onmouseover\s*=", r"eval\s*\(",
            r"document\.cookie", r"window\.location"
        ]
        
        import re
        content_lower = content.lower()
        
        for pattern in xss_patterns:
            if re.search(pattern, content_lower):
                return SecurityEvent(
                    event_type=ThreatType.XSS,
                    level=SecurityLevel.HIGH,
                    description=f"检测到XSS攻击模式: {pattern}",
                    metadata={"pattern": pattern, "content_sample": content[:200]}
                )
        
        return None
    
    async def _detect_malicious_content(self, content: str) -> Optional[SecurityEvent]:
        """检测恶意内容"""
        if not content:
            return None
        
        # 恶意关键词
        malicious_keywords = [
            "virus", "malware", "trojan", "backdoor", "phishing",
            "钓鱼", "病毒", "木马", "后门", "恶意软件"
        ]
        
        content_lower = content.lower()
        
        for keyword in malicious_keywords:
            if keyword in content_lower:
                return SecurityEvent(
                    event_type=ThreatType.MALICIOUS_CONTENT,
                    level=SecurityLevel.MEDIUM,
                    description=f"检测到恶意内容关键词: {keyword}",
                    metadata={"keyword": keyword, "content_sample": content[:200]}
                )
        
        return None
    
    async def _count_recent_failures(self, source_ip: str, user_id: str) -> int:
        """统计最近的失败尝试次数"""
        # 这里应该查询数据库或缓存中的失败记录
        # 暂时返回模拟数据
        return 0
    
    async def _is_ip_blocked(self, ip: str) -> bool:
        """检查IP是否被阻止"""
        async with self._lock:
            if ip in self._blocked_ips:
                block_info = self._blocked_ips[ip]
                block_until = block_info["blocked_until"]
                
                if datetime.now() < block_until:
                    return True
                else:
                    # 阻止时间已过，移除阻止
                    del self._blocked_ips[ip]
                    return False
            
            return False
    
    async def _block_ip(self, ip: str, reason: str) -> None:
        """阻止IP地址"""
        async with self._lock:
            block_until = datetime.now() + timedelta(minutes=self.block_duration_minutes)
            
            self._blocked_ips[ip] = {
                "reason": reason,
                "blocked_at": datetime.now(),
                "blocked_until": block_until
            }
            
            self.logger.warning(f"IP {ip} 已被阻止，原因: {reason}")
    
    async def record_security_event(self, event: SecurityEvent) -> None:
        """记录安全事件"""
        async with self._lock:
            self._security_events.append(event)
            
            # 限制历史记录数量
            if len(self._security_events) > self.max_events_history:
                self._security_events = self._security_events[-self.max_events_history:]
            
            # 更新风险评分
            await self._update_risk_score(event)
            
            self.logger.warning(f"记录安全事件: {event.event_type.value} - {event.description}")
    
    async def _update_risk_score(self, event: SecurityEvent) -> None:
        """更新风险评分"""
        key = f"{event.source_ip}:{event.user_id}" if event.user_id else event.source_ip
        
        # 根据事件级别调整风险评分
        risk_increment = {
            SecurityLevel.LOW: 0.1,
            SecurityLevel.MEDIUM: 0.2,
            SecurityLevel.HIGH: 0.4,
            SecurityLevel.CRITICAL: 0.8
        }
        
        current_score = self._risk_scores.get(key, 0.0)
        new_score = min(1.0, current_score + risk_increment[event.level])
        
        self._risk_scores[key] = new_score
        
        # 根据风险评分自动采取行动
        if new_score >= self.risk_threshold_high and event.source_ip:
            await self._block_ip(event.source_ip, f"高风险评分: {new_score}")
    
    async def get_security_events(self, limit: int = 100, 
                                level: Optional[SecurityLevel] = None,
                                resolved: Optional[bool] = None) -> List[SecurityEvent]:
        """获取安全事件列表"""
        async with self._lock:
            events = self._security_events.copy()
            
            # 过滤条件
            if level:
                events = [e for e in events if e.level == level]
            
            if resolved is not None:
                events = [e for e in events if e.resolved == resolved]
            
            # 按时间倒序排列
            events.sort(key=lambda x: x.timestamp, reverse=True)
            
            return events[:limit]
    
    async def get_risk_score(self, source_ip: str, user_id: str = "") -> float:
        """获取风险评分"""
        key = f"{source_ip}:{user_id}" if user_id else source_ip
        return self._risk_scores.get(key, 0.0)
    
    async def reset_risk_score(self, source_ip: str, user_id: str = "") -> None:
        """重置风险评分"""
        key = f"{source_ip}:{user_id}" if user_id else source_ip
        
        async with self._lock:
            if key in self._risk_scores:
                del self._risk_scores[key]
                self.logger.info(f"重置风险评分: {key}")
    
    async def unblock_ip(self, ip: str) -> bool:
        """解除IP阻止"""
        async with self._lock:
            if ip in self._blocked_ips:
                del self._blocked_ips[ip]
                self.logger.info(f"解除IP阻止: {ip}")
                return True
            return False
    
    async def get_blocked_ips(self) -> List[Dict[str, Any]]:
        """获取被阻止的IP列表"""
        async with self._lock:
            blocked_list = []
            
            for ip, info in self._blocked_ips.items():
                blocked_list.append({
                    "ip": ip,
                    "reason": info["reason"],
                    "blocked_at": info["blocked_at"].isoformat(),
                    "blocked_until": info["blocked_until"].isoformat(),
                    "remaining_minutes": max(0, (info["blocked_until"] - datetime.now()).total_seconds() / 60)
                })
            
            return blocked_list
    
    async def get_security_stats(self) -> Dict[str, Any]:
        """获取安全统计信息"""
        async with self._lock:
            # 按级别统计事件
            level_counts = {level.value: 0 for level in SecurityLevel}
            type_counts = {threat_type.value: 0 for threat_type in ThreatType}
            
            for event in self._security_events:
                level_counts[event.level.value] += 1
                type_counts[event.event_type.value] += 1
            
            # 统计最近24小时的事件
            recent_time = datetime.now() - timedelta(hours=24)
            recent_events = [e for e in self._security_events if e.timestamp > recent_time]
            
            return {
                "total_events": len(self._security_events),
                "recent_24h_events": len(recent_events),
                "unresolved_events": len([e for e in self._security_events if not e.resolved]),
                "blocked_ips_count": len(self._blocked_ips),
                "high_risk_entities": len([k for k, v in self._risk_scores.items() if v >= self.risk_threshold_high]),
                "events_by_level": level_counts,
                "events_by_type": type_counts
            }
    
    def is_initialized(self) -> bool:
        """
        检查组件是否已初始化
        
        返回:
            是否已初始化
        """
        return self._initialized
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        参数:
            key: 配置键
            default: 默认值
            
        返回:
            配置值
        """
        return self.config.get(key, default)
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """
        更新配置
        
        参数:
            config: 新配置参数
        """
        self.config.update(config)
        self.logger.info(f"配置已更新: {list(config.keys())}") 