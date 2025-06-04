#!/usr/bin/env python3
"""
数据库进度监控系统 - 增强版
提供全面的数据库状态监控、性能分析、告警和报告功能
"""

import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import time
import sys
import json
import os
from pathlib import Path
import argparse
from typing import Dict, List, Optional, Tuple
import threading
import signal
from dataclasses import dataclass, asdict
from enum import Enum

# 远程数据库连接配置
REMOTE_DB_CONFIG = {
    'host': '167.71.85.231',
    'port': 5432,
    'user': 'zzdsj',
    'password': 'zzdsj123',
    'database': 'zzdsj'
}

class AlertLevel(Enum):
    """告警级别"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class DatabaseMetrics:
    """数据库指标数据类"""
    timestamp: str
    table_count: int
    total_records: int
    database_size: str
    connection_count: int
    active_queries: int
    slow_queries: int
    cache_hit_ratio: float
    disk_usage: Dict[str, float]
    memory_usage: float
    cpu_usage: float
    status: str

@dataclass
class TableInfo:
    """表信息数据类"""
    name: str
    row_count: int
    size: str
    indexes: int
    last_vacuum: Optional[str]
    last_analyze: Optional[str]

class DatabaseMonitor:
    """数据库监控器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or REMOTE_DB_CONFIG
        self.monitoring = False
        self.metrics_history = []
        self.alerts = []
        self.last_check_time = None
        
    def get_connection(self) -> Optional[psycopg2.extensions.connection]:
        """获取数据库连接"""
        try:
            conn = psycopg2.connect(**self.config)
            return conn
        except Exception as e:
            self._add_alert(AlertLevel.ERROR, f"数据库连接失败: {e}")
            return None
    
    def _add_alert(self, level: AlertLevel, message: str):
        """添加告警"""
        alert = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'level': level.value,
            'message': message
        }
        self.alerts.append(alert)
        print(f"🚨 [{level.value}] {message}")
    
    def check_database_health(self) -> Optional[DatabaseMetrics]:
        """检查数据库健康状况"""
        conn = self.get_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 1. 基础表统计
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)
            table_count = cursor.fetchone()[0]
            
            # 2. 总记录数
            cursor.execute("""
                SELECT schemaname, tablename FROM pg_tables 
                WHERE schemaname = 'public';
            """)
            tables = cursor.fetchall()
            
            total_records = 0
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table['tablename']};")
                    count = cursor.fetchone()[0]
                    total_records += count
                except:
                    pass
            
            # 3. 数据库大小
            cursor.execute("""
                SELECT pg_size_pretty(pg_database_size(current_database()));
            """)
            database_size = cursor.fetchone()[0]
            
            # 4. 连接数统计
            cursor.execute("""
                SELECT COUNT(*) FROM pg_stat_activity 
                WHERE datname = current_database();
            """)
            connection_count = cursor.fetchone()[0]
            
            # 5. 活跃查询数
            cursor.execute("""
                SELECT COUNT(*) FROM pg_stat_activity 
                WHERE state = 'active' AND datname = current_database();
            """)
            active_queries = cursor.fetchone()[0]
            
            # 6. 慢查询数 (超过1秒)
            cursor.execute("""
                SELECT COUNT(*) FROM pg_stat_activity 
                WHERE state = 'active' 
                AND datname = current_database()
                AND now() - query_start > interval '1 second';
            """)
            slow_queries = cursor.fetchone()[0]
            
            # 7. 缓存命中率
            cursor.execute("""
                SELECT 
                    ROUND(
                        100.0 * (sum(blks_hit) / NULLIF(sum(blks_hit) + sum(blks_read), 0)), 2
                    ) as cache_hit_ratio
                FROM pg_stat_database 
                WHERE datname = current_database();
            """)
            cache_hit_ratio = cursor.fetchone()[0] or 0.0
            
            # 8. 磁盘使用情况
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size_pretty,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10;
            """)
            disk_stats = cursor.fetchall()
            disk_usage = {
                row['tablename']: round(row['size_bytes'] / (1024*1024), 2)  # MB
                for row in disk_stats
            }
            
            # 9. 内存使用 (估算)
            cursor.execute("SELECT setting FROM pg_settings WHERE name = 'shared_buffers';")
            shared_buffers = cursor.fetchone()[0]
            memory_usage = self._parse_memory_setting(shared_buffers)
            
            # 10. CPU使用 (通过活跃连接估算)
            cpu_usage = min(100.0, (active_queries / max(connection_count, 1)) * 100)
            
            # 创建指标对象
            metrics = DatabaseMetrics(
                timestamp=timestamp,
                table_count=table_count,
                total_records=total_records,
                database_size=database_size,
                connection_count=connection_count,
                active_queries=active_queries,
                slow_queries=slow_queries,
                cache_hit_ratio=cache_hit_ratio,
                disk_usage=disk_usage,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                status="healthy"
            )
            
            # 健康状况评估
            self._evaluate_health(metrics)
            
            cursor.close()
            conn.close()
            
            return metrics
            
        except Exception as e:
            self._add_alert(AlertLevel.ERROR, f"健康检查失败: {e}")
            return None
    
    def _parse_memory_setting(self, setting: str) -> float:
        """解析PostgreSQL内存设置"""
        try:
            if 'MB' in setting:
                return float(setting.replace('MB', ''))
            elif 'GB' in setting:
                return float(setting.replace('GB', '')) * 1024
            elif 'kB' in setting:
                return float(setting.replace('kB', '')) / 1024
            else:
                # 默认单位是8kB块
                return float(setting) * 8 / 1024
        except:
            return 0.0
    
    def _evaluate_health(self, metrics: DatabaseMetrics):
        """评估数据库健康状况"""
        # 检查慢查询
        if metrics.slow_queries > 5:
            self._add_alert(AlertLevel.WARNING, f"检测到 {metrics.slow_queries} 个慢查询")
        
        # 检查缓存命中率
        if metrics.cache_hit_ratio < 80:
            self._add_alert(AlertLevel.WARNING, f"缓存命中率过低: {metrics.cache_hit_ratio}%")
        
        # 检查连接数
        if metrics.connection_count > 100:
            self._add_alert(AlertLevel.WARNING, f"连接数过多: {metrics.connection_count}")
        
        # 检查活跃查询
        if metrics.active_queries > 20:
            self._add_alert(AlertLevel.ERROR, f"活跃查询数过多: {metrics.active_queries}")
    
    def get_table_details(self) -> List[TableInfo]:
        """获取详细的表信息"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            # 获取表的详细信息
            cursor.execute("""
                SELECT 
                    t.tablename,
                    t.schemaname,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    (SELECT COUNT(*) FROM information_schema.table_constraints 
                     WHERE table_name = t.tablename AND constraint_type = 'PRIMARY KEY') as pk_count,
                    s.n_tup_ins as inserts,
                    s.n_tup_upd as updates,
                    s.n_tup_del as deletes,
                    s.last_vacuum,
                    s.last_autovacuum,
                    s.last_analyze,
                    s.last_autoanalyze
                FROM pg_tables t
                LEFT JOIN pg_stat_user_tables s ON s.relname = t.tablename
                WHERE t.schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
            """)
            
            tables_data = cursor.fetchall()
            table_infos = []
            
            for row in tables_data:
                # 获取行数
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {row['tablename']};")
                    row_count = cursor.fetchone()[0]
                except:
                    row_count = 0
                
                # 获取索引数
                cursor.execute("""
                    SELECT COUNT(*) FROM pg_indexes 
                    WHERE tablename = %s AND schemaname = 'public';
                """, (row['tablename'],))
                index_count = cursor.fetchone()[0]
                
                table_info = TableInfo(
                    name=row['tablename'],
                    row_count=row_count,
                    size=row['size'],
                    indexes=index_count,
                    last_vacuum=str(row['last_vacuum']) if row['last_vacuum'] else None,
                    last_analyze=str(row['last_analyze']) if row['last_analyze'] else None
                )
                table_infos.append(table_info)
            
            cursor.close()
            conn.close()
            
            return table_infos
            
        except Exception as e:
            self._add_alert(AlertLevel.ERROR, f"获取表详情失败: {e}")
            return []
    
    def generate_report(self, metrics: DatabaseMetrics, tables: List[TableInfo]) -> str:
        """生成监控报告"""
        report = f"""
{'='*80}
📊 数据库监控报告 - {metrics.timestamp}
{'='*80}

🏥 健康状况总览:
  状态: {metrics.status.upper()}
  数据库大小: {metrics.database_size}
  缓存命中率: {metrics.cache_hit_ratio}%
  
📈 性能指标:
  连接数: {metrics.connection_count}
  活跃查询: {metrics.active_queries}
  慢查询: {metrics.slow_queries}
  内存使用: {metrics.memory_usage:.1f} MB
  CPU使用率: {metrics.cpu_usage:.1f}%

📋 数据统计:
  表数量: {metrics.table_count}
  总记录数: {metrics.total_records:,}

📊 表空间使用 (Top 5):"""
        
        # 表空间使用排序
        sorted_tables = sorted(tables, key=lambda x: x.row_count, reverse=True)[:5]
        for i, table in enumerate(sorted_tables, 1):
            report += f"\n  {i:2}. {table.name:25} | {table.row_count:>10,} 行 | {table.size:>10} | {table.indexes} 索引"
        
        if self.alerts:
            report += f"\n\n🚨 告警信息 ({len(self.alerts)} 条):"
            for alert in self.alerts[-5:]:  # 显示最近5条告警
                report += f"\n  [{alert['level']:8}] {alert['timestamp']} - {alert['message']}"
        
        report += f"\n\n{'='*80}\n"
        return report
    
    def save_metrics(self, metrics: DatabaseMetrics):
        """保存监控指标到文件"""
        metrics_dir = Path("monitoring_data")
        metrics_dir.mkdir(exist_ok=True)
        
        # 保存到JSON文件
        metrics_file = metrics_dir / f"db_metrics_{datetime.now().strftime('%Y%m%d')}.json"
        
        metrics_data = asdict(metrics)
        
        # 读取现有数据
        if metrics_file.exists():
            with open(metrics_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = []
        
        # 添加新数据
        existing_data.append(metrics_data)
        
        # 保存数据
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
    
    def start_monitoring(self, interval: int = 60):
        """开始持续监控"""
        print(f"🔄 开始数据库监控，检查间隔: {interval} 秒")
        print("按 Ctrl+C 停止监控\n")
        
        self.monitoring = True
        
        def signal_handler(signum, frame):
            print("\n🛑 收到停止信号，正在停止监控...")
            self.monitoring = False
        
        signal.signal(signal.SIGINT, signal_handler)
        
        while self.monitoring:
            try:
                # 执行健康检查
                metrics = self.check_database_health()
                if metrics:
                    tables = self.get_table_details()
                    
                    # 生成并显示报告
                    report = self.generate_report(metrics, tables)
                    print(report)
                    
                    # 保存指标
                    self.save_metrics(metrics)
                    self.metrics_history.append(metrics)
                    
                    # 保留最近100条记录
                    if len(self.metrics_history) > 100:
                        self.metrics_history = self.metrics_history[-100:]
                
                # 等待下次检查
                if self.monitoring:
                    time.sleep(interval)
                    
            except Exception as e:
                self._add_alert(AlertLevel.ERROR, f"监控异常: {e}")
                time.sleep(5)  # 出错后短暂等待
        
        print("📴 监控已停止")

def quick_check():
    """快速检查数据库状态"""
    monitor = DatabaseMonitor()
    
    print("🔍 正在执行快速数据库检查...")
    metrics = monitor.check_database_health()
    
    if metrics:
        tables = monitor.get_table_details()
        report = monitor.generate_report(metrics, tables)
        print(report)
        return True
    else:
        print("❌ 快速检查失败")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据库监控系统")
    parser.add_argument('--mode', choices=['quick', 'monitor'], default='quick',
                       help='运行模式: quick(快速检查) 或 monitor(持续监控)')
    parser.add_argument('--interval', type=int, default=60,
                       help='监控间隔(秒)，默认60秒')
    
    args = parser.parse_args()
    
    if args.mode == 'quick':
        quick_check()
    elif args.mode == 'monitor':
        monitor = DatabaseMonitor()
        monitor.start_monitoring(args.interval)

if __name__ == "__main__":
    main() 