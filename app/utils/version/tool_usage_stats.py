"""
工具使用统计管理器
收集、存储和分析工具使用数据，为推荐系统提供数据支持
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter

# 集成现有组件
from app.utils.core.cache.cache_manager import CacheManager
from app.utils.core.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

@dataclass
class ToolUsageEvent:
    """工具使用事件"""
    event_id: str
    user_id: str
    tool_id: str
    tool_name: str
    action: str  # "start", "success", "failure", "error"
    timestamp: datetime
    duration: Optional[float] = None  # 执行时间（秒）
    input_size: Optional[int] = None  # 输入数据大小
    output_size: Optional[int] = None  # 输出数据大小
    error_message: Optional[str] = None
    context: Dict[str, Any] = None  # 执行上下文
    metadata: Dict[str, Any] = None  # 额外元数据
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ToolStatistics:
    """工具统计信息"""
    tool_id: str
    tool_name: str
    total_usage_count: int
    success_count: int
    failure_count: int
    error_count: int
    success_rate: float
    avg_execution_time: float
    total_execution_time: float
    last_used: Optional[datetime]
    first_used: Optional[datetime]
    active_users: int
    peak_usage_hour: int  # 使用高峰时段
    performance_trend: str  # "improving", "stable", "declining"

@dataclass 
class UserToolUsage:
    """用户工具使用情况"""
    user_id: str
    tool_usage_stats: Dict[str, ToolStatistics]
    total_sessions: int
    avg_session_duration: float
    favorite_tools: List[str]
    recently_used_tools: List[str]
    skill_level: str  # "beginner", "intermediate", "advanced"
    usage_patterns: Dict[str, Any]

class ToolUsageStatsManager:
    """工具使用统计管理器"""
    
    def __init__(self, cache_manager: CacheManager, db_manager: DatabaseManager):
        self.cache_manager = cache_manager
        self.db_manager = db_manager
        
        # 缓存配置
        self.stats_cache_ttl = 3600  # 1小时
        self.event_buffer_size = 100  # 事件缓冲区大小
        self.flush_interval = 300    # 5分钟刷新一次
        
        # 内存缓冲区
        self.event_buffer: List[ToolUsageEvent] = []
        self.stats_cache: Dict[str, Any] = {}
        
        # 初始化定时任务
        self._flush_task = None
        
    async def initialize(self):
        """初始化统计管理器"""
        try:
            # 创建数据库表
            await self._create_tables()
            
            # 启动定时刷新任务
            self._flush_task = asyncio.create_task(self._periodic_flush())
            
            logger.info("工具使用统计管理器初始化完成")
            
        except Exception as e:
            logger.error(f"统计管理器初始化失败: {str(e)}", exc_info=True)
            raise
    
    async def record_tool_usage(
        self,
        user_id: str,
        tool_id: str,
        tool_name: str,
        action: str,
        duration: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        记录工具使用事件
        
        Args:
            user_id: 用户ID
            tool_id: 工具ID
            tool_name: 工具名称
            action: 操作类型
            duration: 执行时间
            success: 是否成功
            error_message: 错误信息
            context: 执行上下文
        """
        try:
            event = ToolUsageEvent(
                event_id=f"{user_id}_{tool_id}_{datetime.now().timestamp()}",
                user_id=user_id,
                tool_id=tool_id,
                tool_name=tool_name,
                action=action,
                timestamp=datetime.now(),
                duration=duration,
                error_message=error_message if not success else None,
                context=context or {}
            )
            
            # 添加到缓冲区
            self.event_buffer.append(event)
            
            # 如果缓冲区满了，立即刷新
            if len(self.event_buffer) >= self.event_buffer_size:
                await self._flush_events()
            
            # 更新实时统计缓存
            await self._update_real_time_stats(event)
            
        except Exception as e:
            logger.error(f"记录工具使用失败: {str(e)}", exc_info=True)
    
    async def get_tool_stats(
        self,
        tool_id: str,
        user_id: Optional[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """
        获取工具统计信息
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID（可选，用于获取用户特定统计）
            time_range: 时间范围（可选）
            
        Returns:
            Dict: 统计信息
        """
        try:
            # 构建缓存键
            cache_key = f"tool_stats:{tool_id}"
            if user_id:
                cache_key += f":user:{user_id}"
            if time_range:
                cache_key += f":range:{time_range[0].timestamp()}_{time_range[1].timestamp()}"
            
            # 尝试从缓存获取
            cached_stats = await self.cache_manager.get(cache_key)
            if cached_stats:
                return json.loads(cached_stats)
            
            # 从数据库计算统计信息
            stats = await self._calculate_tool_stats(tool_id, user_id, time_range)
            
            # 缓存结果
            await self.cache_manager.set(
                cache_key, 
                json.dumps(stats, default=str), 
                self.stats_cache_ttl
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"获取工具统计失败: {str(e)}", exc_info=True)
            return self._get_default_stats()
    
    async def get_user_usage_pattern(
        self,
        user_id: str,
        days: int = 30
    ) -> UserToolUsage:
        """
        获取用户工具使用模式
        
        Args:
            user_id: 用户ID
            days: 分析天数
            
        Returns:
            UserToolUsage: 用户使用模式
        """
        try:
            cache_key = f"user_pattern:{user_id}:{days}"
            
            # 尝试从缓存获取
            cached_pattern = await self.cache_manager.get(cache_key)
            if cached_pattern:
                return UserToolUsage(**json.loads(cached_pattern))
            
            # 计算用户使用模式
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            # 获取用户事件
            events = await self._get_user_events(user_id, start_time, end_time)
            
            # 分析使用模式
            pattern = await self._analyze_user_pattern(user_id, events)
            
            # 缓存结果
            await self.cache_manager.set(
                cache_key,
                json.dumps(asdict(pattern), default=str),
                self.stats_cache_ttl
            )
            
            return pattern
            
        except Exception as e:
            logger.error(f"获取用户使用模式失败: {str(e)}", exc_info=True)
            return self._get_default_user_pattern(user_id)
    
    async def get_performance_stats(self, tool_id: str) -> Dict[str, Any]:
        """
        获取工具性能统计
        
        Args:
            tool_id: 工具ID
            
        Returns:
            Dict: 性能统计
        """
        try:
            cache_key = f"performance_stats:{tool_id}"
            
            # 尝试从缓存获取
            cached_stats = await self.cache_manager.get(cache_key)
            if cached_stats:
                return json.loads(cached_stats)
            
            # 计算性能统计
            stats = await self._calculate_performance_stats(tool_id)
            
            # 缓存结果
            await self.cache_manager.set(
                cache_key,
                json.dumps(stats, default=str),
                self.stats_cache_ttl
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"获取性能统计失败: {str(e)}", exc_info=True)
            return {
                "avg_response_time": 30.0,
                "error_rate": 0.1,
                "resource_usage": "medium"
            }
    
    async def get_trending_tools(
        self,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取趋势工具
        
        Args:
            days: 分析天数
            limit: 返回数量限制
            
        Returns:
            List[Dict]: 趋势工具列表
        """
        try:
            cache_key = f"trending_tools:{days}:{limit}"
            
            # 尝试从缓存获取
            cached_trends = await self.cache_manager.get(cache_key)
            if cached_trends:
                return json.loads(cached_trends)
            
            # 计算趋势
            trends = await self._calculate_trending_tools(days, limit)
            
            # 缓存结果
            await self.cache_manager.set(
                cache_key,
                json.dumps(trends, default=str),
                self.stats_cache_ttl
            )
            
            return trends
            
        except Exception as e:
            logger.error(f"获取趋势工具失败: {str(e)}", exc_info=True)
            return []
    
    # ========== 私有方法 ==========
    
    async def _create_tables(self):
        """创建数据库表"""
        create_events_table = """
        CREATE TABLE IF NOT EXISTS tool_usage_events (
            event_id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            tool_id VARCHAR(255) NOT NULL,
            tool_name VARCHAR(255) NOT NULL,
            action VARCHAR(50) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            duration FLOAT,
            input_size INTEGER,
            output_size INTEGER,
            error_message TEXT,
            context JSON,
            metadata JSON,
            INDEX idx_user_tool_time (user_id, tool_id, timestamp),
            INDEX idx_tool_time (tool_id, timestamp),
            INDEX idx_user_time (user_id, timestamp)
        )
        """
        
        create_stats_table = """
        CREATE TABLE IF NOT EXISTS tool_usage_stats (
            id SERIAL PRIMARY KEY,
            tool_id VARCHAR(255) NOT NULL,
            user_id VARCHAR(255),
            date DATE NOT NULL,
            usage_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            total_duration FLOAT DEFAULT 0,
            avg_duration FLOAT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_tool_user_date (tool_id, user_id, date),
            INDEX idx_tool_date (tool_id, date),
            INDEX idx_user_date (user_id, date)
        )
        """
        
        try:
            async with self.db_manager.get_connection() as conn:
                await conn.execute(create_events_table)
                await conn.execute(create_stats_table)
                await conn.commit()
                
        except Exception as e:
            logger.error(f"创建统计表失败: {str(e)}")
            raise
    
    async def _periodic_flush(self):
        """定期刷新事件缓冲区"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_events()
            except Exception as e:
                logger.error(f"定期刷新失败: {str(e)}")
    
    async def _flush_events(self):
        """刷新事件缓冲区到数据库"""
        if not self.event_buffer:
            return
        
        try:
            events_to_flush = self.event_buffer.copy()
            self.event_buffer.clear()
            
            # 批量插入数据库
            await self._batch_insert_events(events_to_flush)
            
            # 更新聚合统计
            await self._update_aggregated_stats(events_to_flush)
            
            logger.debug(f"成功刷新 {len(events_to_flush)} 个使用事件")
            
        except Exception as e:
            logger.error(f"刷新事件失败: {str(e)}")
            # 重新添加到缓冲区
            self.event_buffer.extend(events_to_flush)
    
    async def _batch_insert_events(self, events: List[ToolUsageEvent]):
        """批量插入事件"""
        if not events:
            return
        
        insert_sql = """
        INSERT INTO tool_usage_events 
        (event_id, user_id, tool_id, tool_name, action, timestamp, 
         duration, input_size, output_size, error_message, context, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = []
        for event in events:
            values.append((
                event.event_id,
                event.user_id,
                event.tool_id,
                event.tool_name,
                event.action,
                event.timestamp,
                event.duration,
                event.input_size,
                event.output_size,
                event.error_message,
                json.dumps(event.context) if event.context else None,
                json.dumps(event.metadata) if event.metadata else None
            ))
        
        try:
            async with self.db_manager.get_connection() as conn:
                await conn.executemany(insert_sql, values)
                await conn.commit()
                
        except Exception as e:
            logger.error(f"批量插入事件失败: {str(e)}")
            raise
    
    async def _update_aggregated_stats(self, events: List[ToolUsageEvent]):
        """更新聚合统计"""
        # 按日期、工具、用户分组统计
        daily_stats = defaultdict(lambda: {
            'usage_count': 0,
            'success_count': 0,
            'failure_count': 0,
            'total_duration': 0.0
        })
        
        for event in events:
            date_key = event.timestamp.date()
            key = (event.tool_id, event.user_id, date_key)
            
            daily_stats[key]['usage_count'] += 1
            if event.action == 'success':
                daily_stats[key]['success_count'] += 1
            elif event.action in ['failure', 'error']:
                daily_stats[key]['failure_count'] += 1
            
            if event.duration:
                daily_stats[key]['total_duration'] += event.duration
        
        # 更新数据库统计
        await self._upsert_daily_stats(daily_stats)
    
    async def _upsert_daily_stats(self, daily_stats: Dict[Tuple, Dict]):
        """更新日统计数据"""
        upsert_sql = """
        INSERT INTO tool_usage_stats 
        (tool_id, user_id, date, usage_count, success_count, failure_count, total_duration, avg_duration)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        usage_count = usage_count + VALUES(usage_count),
        success_count = success_count + VALUES(success_count),
        failure_count = failure_count + VALUES(failure_count),
        total_duration = total_duration + VALUES(total_duration),
        avg_duration = IF(usage_count + VALUES(usage_count) > 0, 
                         (total_duration + VALUES(total_duration)) / (usage_count + VALUES(usage_count)), 
                         0),
        updated_at = CURRENT_TIMESTAMP
        """
        
        values = []
        for (tool_id, user_id, date), stats in daily_stats.items():
            avg_duration = stats['total_duration'] / stats['usage_count'] if stats['usage_count'] > 0 else 0
            values.append((
                tool_id, user_id, date,
                stats['usage_count'],
                stats['success_count'],
                stats['failure_count'],
                stats['total_duration'],
                avg_duration
            ))
        
        try:
            async with self.db_manager.get_connection() as conn:
                await conn.executemany(upsert_sql, values)
                await conn.commit()
                
        except Exception as e:
            logger.error(f"更新日统计失败: {str(e)}")
    
    async def _update_real_time_stats(self, event: ToolUsageEvent):
        """更新实时统计缓存"""
        cache_key = f"realtime_stats:{event.tool_id}"
        
        try:
            # 获取当前统计
            current_stats = await self.cache_manager.get(cache_key)
            if current_stats:
                stats = json.loads(current_stats)
            else:
                stats = {
                    'usage_count': 0,
                    'success_count': 0,
                    'failure_count': 0,
                    'total_duration': 0.0,
                    'avg_duration': 0.0
                }
            
            # 更新统计
            stats['usage_count'] += 1
            if event.action == 'success':
                stats['success_count'] += 1
            elif event.action in ['failure', 'error']:
                stats['failure_count'] += 1
            
            if event.duration:
                stats['total_duration'] += event.duration
                stats['avg_duration'] = stats['total_duration'] / stats['usage_count']
            
            # 更新缓存
            await self.cache_manager.set(
                cache_key,
                json.dumps(stats),
                300  # 5分钟过期
            )
            
        except Exception as e:
            logger.warning(f"更新实时统计失败: {str(e)}")
    
    async def _calculate_tool_stats(
        self,
        tool_id: str,
        user_id: Optional[str],
        time_range: Optional[Tuple[datetime, datetime]]
    ) -> Dict[str, Any]:
        """计算工具统计信息"""
        # 构建查询条件
        where_conditions = ["tool_id = %s"]
        params = [tool_id]
        
        if user_id:
            where_conditions.append("user_id = %s")
            params.append(user_id)
        
        if time_range:
            where_conditions.append("date BETWEEN %s AND %s")
            params.extend([time_range[0].date(), time_range[1].date()])
        
        where_clause = " AND ".join(where_conditions)
        
        # 查询统计数据
        query = f"""
        SELECT 
            SUM(usage_count) as total_usage,
            SUM(success_count) as total_success,
            SUM(failure_count) as total_failure,
            AVG(avg_duration) as avg_duration,
            SUM(total_duration) as total_duration,
            COUNT(DISTINCT user_id) as unique_users,
            MAX(date) as last_used_date,
            MIN(date) as first_used_date
        FROM tool_usage_stats 
        WHERE {where_clause}
        """
        
        try:
            async with self.db_manager.get_connection() as conn:
                result = await conn.fetchone(query, params)
                
                if result and result['total_usage']:
                    total_usage = result['total_usage'] or 0
                    total_success = result['total_success'] or 0
                    total_failure = result['total_failure'] or 0
                    
                    return {
                        'success_rate': total_success / total_usage if total_usage > 0 else 0.0,
                        'avg_execution_time': result['avg_duration'] or 0.0,
                        'usage_count': total_usage,
                        'total_execution_time': result['total_duration'] or 0.0,
                        'unique_users': result['unique_users'] or 0,
                        'last_used': result['last_used_date'],
                        'first_used': result['first_used_date'],
                        'failure_rate': total_failure / total_usage if total_usage > 0 else 0.0
                    }
                else:
                    return self._get_default_stats()
                    
        except Exception as e:
            logger.error(f"计算工具统计失败: {str(e)}")
            return self._get_default_stats()
    
    def _get_default_stats(self) -> Dict[str, Any]:
        """获取默认统计信息"""
        return {
            'success_rate': 0.5,
            'avg_execution_time': 30.0,
            'usage_count': 0,
            'total_execution_time': 0.0,
            'unique_users': 0,
            'last_used': None,
            'first_used': None,
            'failure_rate': 0.1
        }
    
    async def _get_user_events(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[ToolUsageEvent]:
        """获取用户事件"""
        query = """
        SELECT * FROM tool_usage_events 
        WHERE user_id = %s AND timestamp BETWEEN %s AND %s
        ORDER BY timestamp DESC
        """
        
        try:
            async with self.db_manager.get_connection() as conn:
                results = await conn.fetchall(query, [user_id, start_time, end_time])
                
                events = []
                for row in results:
                    event = ToolUsageEvent(
                        event_id=row['event_id'],
                        user_id=row['user_id'],
                        tool_id=row['tool_id'],
                        tool_name=row['tool_name'],
                        action=row['action'],
                        timestamp=row['timestamp'],
                        duration=row['duration'],
                        input_size=row['input_size'],
                        output_size=row['output_size'],
                        error_message=row['error_message'],
                        context=json.loads(row['context']) if row['context'] else {},
                        metadata=json.loads(row['metadata']) if row['metadata'] else {}
                    )
                    events.append(event)
                
                return events
                
        except Exception as e:
            logger.error(f"获取用户事件失败: {str(e)}")
            return []
    
    async def _analyze_user_pattern(
        self,
        user_id: str,
        events: List[ToolUsageEvent]
    ) -> UserToolUsage:
        """分析用户使用模式"""
        if not events:
            return self._get_default_user_pattern(user_id)
        
        # 分析工具使用情况
        tool_stats = defaultdict(lambda: {
            'usage_count': 0,
            'success_count': 0,
            'failure_count': 0,
            'total_duration': 0.0
        })
        
        tool_usage_times = defaultdict(list)
        
        for event in events:
            tool_id = event.tool_id
            tool_stats[tool_id]['usage_count'] += 1
            
            if event.action == 'success':
                tool_stats[tool_id]['success_count'] += 1
            elif event.action in ['failure', 'error']:
                tool_stats[tool_id]['failure_count'] += 1
            
            if event.duration:
                tool_stats[tool_id]['total_duration'] += event.duration
            
            tool_usage_times[tool_id].append(event.timestamp)
        
        # 构建工具统计
        tool_usage_stats = {}
        for tool_id, stats in tool_stats.items():
            usage_count = stats['usage_count']
            success_rate = stats['success_count'] / usage_count if usage_count > 0 else 0.0
            avg_duration = stats['total_duration'] / usage_count if usage_count > 0 else 0.0
            
            tool_usage_stats[tool_id] = ToolStatistics(
                tool_id=tool_id,
                tool_name=next((e.tool_name for e in events if e.tool_id == tool_id), tool_id),
                total_usage_count=usage_count,
                success_count=stats['success_count'],
                failure_count=stats['failure_count'],
                error_count=0,  # 简化处理
                success_rate=success_rate,
                avg_execution_time=avg_duration,
                total_execution_time=stats['total_duration'],
                last_used=max(tool_usage_times[tool_id]) if tool_usage_times[tool_id] else None,
                first_used=min(tool_usage_times[tool_id]) if tool_usage_times[tool_id] else None,
                active_users=1,
                peak_usage_hour=12,  # 简化处理
                performance_trend="stable"
            )
        
        # 确定技能水平
        total_usage = sum(stats['usage_count'] for stats in tool_stats.values())
        unique_tools = len(tool_stats)
        
        if total_usage < 10 or unique_tools < 3:
            skill_level = "beginner"
        elif total_usage < 50 or unique_tools < 8:
            skill_level = "intermediate"
        else:
            skill_level = "advanced"
        
        # 最喜爱的工具
        favorite_tools = sorted(
            tool_stats.keys(),
            key=lambda t: tool_stats[t]['usage_count'],
            reverse=True
        )[:5]
        
        # 最近使用的工具
        recent_events = sorted(events, key=lambda e: e.timestamp, reverse=True)[:10]
        recently_used_tools = list(dict.fromkeys([e.tool_id for e in recent_events]))[:5]
        
        return UserToolUsage(
            user_id=user_id,
            tool_usage_stats=tool_usage_stats,
            total_sessions=len(set(e.timestamp.date() for e in events)),
            avg_session_duration=sum(e.duration for e in events if e.duration) / len(events),
            favorite_tools=favorite_tools,
            recently_used_tools=recently_used_tools,
            skill_level=skill_level,
            usage_patterns={
                'peak_hours': [9, 10, 14, 15],  # 简化处理
                'preferred_complexity': 'medium',
                'success_rate_trend': 'improving'
            }
        )
    
    def _get_default_user_pattern(self, user_id: str) -> UserToolUsage:
        """获取默认用户模式"""
        return UserToolUsage(
            user_id=user_id,
            tool_usage_stats={},
            total_sessions=0,
            avg_session_duration=0.0,
            favorite_tools=[],
            recently_used_tools=[],
            skill_level="beginner",
            usage_patterns={}
        )
    
    async def _calculate_performance_stats(self, tool_id: str) -> Dict[str, Any]:
        """计算性能统计"""
        # 简化实现，实际应该查询详细的性能数据
        stats = await self.get_tool_stats(tool_id)
        
        return {
            "avg_response_time": stats.get('avg_execution_time', 30.0),
            "error_rate": stats.get('failure_rate', 0.1),
            "resource_usage": "medium",  # 简化处理
            "throughput": stats.get('usage_count', 0) / 24,  # 每小时平均使用次数
            "availability": 0.99,  # 简化处理
            "recent_performance": stats.get('success_rate', 0.5)
        }
    
    async def _calculate_trending_tools(self, days: int, limit: int) -> List[Dict[str, Any]]:
        """计算趋势工具"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        query = """
        SELECT 
            tool_id,
            SUM(usage_count) as total_usage,
            AVG(usage_count) as avg_daily_usage,
            SUM(success_count) / SUM(usage_count) as success_rate,
            COUNT(DISTINCT user_id) as unique_users
        FROM tool_usage_stats 
        WHERE date BETWEEN %s AND %s
        GROUP BY tool_id
        HAVING total_usage > 0
        ORDER BY total_usage DESC, success_rate DESC
        LIMIT %s
        """
        
        try:
            async with self.db_manager.get_connection() as conn:
                results = await conn.fetchall(query, [start_date, end_date, limit])
                
                trends = []
                for row in results:
                    trends.append({
                        'tool_id': row['tool_id'],
                        'total_usage': row['total_usage'],
                        'avg_daily_usage': float(row['avg_daily_usage']),
                        'success_rate': float(row['success_rate']),
                        'unique_users': row['unique_users'],
                        'trend_score': row['total_usage'] * row['success_rate']  # 简单的趋势评分
                    })
                
                return trends
                
        except Exception as e:
            logger.error(f"计算趋势工具失败: {str(e)}")
            return []


# 工厂函数
def get_tool_usage_stats_manager(
    cache_manager: CacheManager,
    db_manager: DatabaseManager
) -> ToolUsageStatsManager:
    """获取工具使用统计管理器实例"""
    return ToolUsageStatsManager(cache_manager, db_manager) 