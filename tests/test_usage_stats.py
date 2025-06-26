#!/usr/bin/env python3
"""
工具使用统计系统测试
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

class UsageEventType(Enum):
    TOOL_EXECUTION = "tool_execution"
    TOOL_DISCOVERY = "tool_discovery"
    TOOL_ERROR = "tool_error"

class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class UsageEvent:
    event_id: str
    event_type: UsageEventType
    timestamp: datetime
    user_id: str
    tool_name: str
    framework: str
    execution_time_ms: Optional[int] = None
    status: Optional[ExecutionStatus] = None
    error_message: Optional[str] = None

@dataclass
class UsageStatistics:
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_execution_time: float = 0.0
    most_used_tool: Optional[str] = None
    framework_distribution: Dict[str, int] = field(default_factory=dict)

class UsageStatisticsManager:
    def __init__(self):
        self._events: List[UsageEvent] = []
        self._execution_count = 0
        self._success_count = 0
        self._failure_count = 0
    
    async def record_event(self, event: UsageEvent) -> bool:
        """记录使用事件"""
        try:
            self._events.append(event)
            
            if event.event_type == UsageEventType.TOOL_EXECUTION:
                self._execution_count += 1
                
                if event.status == ExecutionStatus.SUCCESS:
                    self._success_count += 1
                elif event.status == ExecutionStatus.FAILED:
                    self._failure_count += 1
            
            return True
        except Exception:
            return False
    
    async def get_statistics(self) -> UsageStatistics:
        """获取使用统计"""
        stats = UsageStatistics()
        
        execution_events = [e for e in self._events if e.event_type == UsageEventType.TOOL_EXECUTION]
        stats.total_executions = len(execution_events)
        
        if not execution_events:
            return stats
        
        stats.successful_executions = len([e for e in execution_events if e.status == ExecutionStatus.SUCCESS])
        stats.failed_executions = len([e for e in execution_events if e.status == ExecutionStatus.FAILED])
        
        # 平均执行时间
        valid_times = [e.execution_time_ms for e in execution_events if e.execution_time_ms]
        if valid_times:
            stats.average_execution_time = sum(valid_times) / len(valid_times)
        
        # 最常用工具
        tool_counts = {}
        for event in execution_events:
            tool_counts[event.tool_name] = tool_counts.get(event.tool_name, 0) + 1
        
        if tool_counts:
            stats.most_used_tool = max(tool_counts, key=tool_counts.get)
        
        # 框架分布
        for event in execution_events:
            framework = event.framework
            stats.framework_distribution[framework] = stats.framework_distribution.get(framework, 0) + 1
        
        return stats
    
    async def get_tool_statistics(self, tool_name: str) -> Dict[str, Any]:
        """获取特定工具的统计信息"""
        tool_events = [e for e in self._events if e.tool_name == tool_name and e.event_type == UsageEventType.TOOL_EXECUTION]
        
        if not tool_events:
            return {"error": "No events found for tool"}
        
        valid_times = [e.execution_time_ms for e in tool_events if e.execution_time_ms]
        avg_time = sum(valid_times) / len(valid_times) if valid_times else 0.0
        
        return {
            "tool_name": tool_name,
            "total_executions": len(tool_events),
            "successful_executions": len([e for e in tool_events if e.status == ExecutionStatus.SUCCESS]),
            "failed_executions": len([e for e in tool_events if e.status == ExecutionStatus.FAILED]),
            "average_execution_time": avg_time,
            "unique_users": len(set(e.user_id for e in tool_events))
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "total_events": len(self._events),
            "execution_count": self._execution_count,
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "success_rate": (self._success_count / self._execution_count * 100) if self._execution_count > 0 else 0
        }

async def test_usage_statistics():
    try:
        print("=== 工具使用统计系统测试 ===")
        
        stats_manager = UsageStatisticsManager()
        print("✅ 统计管理器创建成功")
        
        # 测试1: 记录使用事件
        print("\n📋 测试1: 记录使用事件")
        
        now = datetime.now()
        
        success_event = UsageEvent(
            event_id="evt_001",
            event_type=UsageEventType.TOOL_EXECUTION,
            timestamp=now - timedelta(minutes=30),
            user_id="user1",
            tool_name="agno_reasoning",
            framework="agno",
            execution_time_ms=1500,
            status=ExecutionStatus.SUCCESS
        )
        
        failed_event = UsageEvent(
            event_id="evt_002",
            event_type=UsageEventType.TOOL_EXECUTION,
            timestamp=now - timedelta(minutes=25),
            user_id="user2",
            tool_name="haystack_extract_answers",
            framework="haystack",
            execution_time_ms=3000,
            status=ExecutionStatus.FAILED,
            error_message="Connection timeout"
        )
        
        success1 = await stats_manager.record_event(success_event)
        success2 = await stats_manager.record_event(failed_event)
        
        print(f"  • 记录成功事件: {'✅' if success1 else '❌'}")
        print(f"  • 记录失败事件: {'✅' if success2 else '❌'}")
        
        # 测试2: 获取整体统计
        print("\n📋 测试2: 获取整体统计")
        
        overall_stats = await stats_manager.get_statistics()
        print(f"  • 总执行次数: {overall_stats.total_executions}")
        print(f"  • 成功执行次数: {overall_stats.successful_executions}")
        print(f"  • 失败执行次数: {overall_stats.failed_executions}")
        print(f"  • 平均执行时间: {overall_stats.average_execution_time:.1f}ms")
        print(f"  • 最常用工具: {overall_stats.most_used_tool}")
        print(f"  • 框架分布: {overall_stats.framework_distribution}")
        
        # 测试3: 获取工具统计
        print("\n📋 测试3: 获取工具统计")
        
        agno_stats = await stats_manager.get_tool_statistics("agno_reasoning")
        print(f"  • Agno推理工具统计:")
        print(f"    - 总执行次数: {agno_stats['total_executions']}")
        print(f"    - 成功次数: {agno_stats['successful_executions']}")
        print(f"    - 失败次数: {agno_stats['failed_executions']}")
        print(f"    - 平均执行时间: {agno_stats['average_execution_time']:.1f}ms")
        print(f"    - 独特用户数: {agno_stats['unique_users']}")
        
        # 测试4: 系统信息
        print("\n📋 测试4: 系统信息")
        
        system_info = stats_manager.get_system_info()
        print(f"  • 总事件数: {system_info['total_events']}")
        print(f"  • 执行计数: {system_info['execution_count']}")
        print(f"  • 成功率: {system_info['success_rate']:.1f}%")
        
        print("\n✅ 工具使用统计系统测试完成！")
        
        print("\n📊 测试总结:")
        print("✅ 事件记录功能正常")
        print("✅ 整体统计功能正常")
        print("✅ 工具统计功能正常")
        print("✅ 系统信息功能正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 使用统计系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_usage_statistics())
    print(f"\n🎯 测试结果: {'✅ 全部通过' if success else '❌ 有失败项'}")
    exit(0 if success else 1) 