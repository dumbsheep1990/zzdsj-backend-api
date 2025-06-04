#!/usr/bin/env python3
"""
系统健康检查仪表板
提供实时系统监控、可视化图表、告警通知等功能
"""

import psycopg2
import psycopg2.extras
import time
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import threading
import signal
import argparse
from collections import defaultdict, deque
import subprocess
import platform

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent.parent))

# 远程数据库连接配置
REMOTE_DB_CONFIG = {
    'host': '167.71.85.231',
    'port': 5432,
    'user': 'zzdsj',
    'password': 'zzdsj123',
    'database': 'zzdsj'
}

@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]
    process_count: int
    uptime: str

@dataclass
class DatabaseMetrics:
    """数据库指标"""
    timestamp: str
    connection_count: int
    active_queries: int
    cache_hit_ratio: float
    database_size: str
    slow_queries: int
    transactions_per_second: float
    lock_count: int

@dataclass
class ServiceStatus:
    """服务状态"""
    name: str
    status: str  # running, stopped, error
    port: int
    uptime: Optional[str]
    memory_usage: Optional[float]
    cpu_usage: Optional[float]

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.running = False
        self.metrics_history = deque(maxlen=100)  # 保留最近100条记录
        self.alerts = []
        
    def get_system_metrics(self) -> SystemMetrics:
        """获取系统指标"""
        try:
            # CPU使用率
            if platform.system() == "Linux":
                cpu_usage = self._get_linux_cpu_usage()
            elif platform.system() == "Darwin":  # macOS
                cpu_usage = self._get_macos_cpu_usage()
            else:
                cpu_usage = 0.0
            
            # 内存使用率
            memory_usage = self._get_memory_usage()
            
            # 磁盘使用率
            disk_usage = self._get_disk_usage()
            
            # 网络IO
            network_io = self._get_network_io()
            
            # 进程数
            process_count = self._get_process_count()
            
            # 系统运行时间
            uptime = self._get_system_uptime()
            
            return SystemMetrics(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_io=network_io,
                process_count=process_count,
                uptime=uptime
            )
            
        except Exception as e:
            print(f"❌ 获取系统指标失败: {e}")
            return SystemMetrics(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                network_io={},
                process_count=0,
                uptime="unknown"
            )
    
    def _get_linux_cpu_usage(self) -> float:
        """获取Linux CPU使用率"""
        try:
            with open('/proc/stat', 'r') as f:
                line = f.readline()
            cpu_times = [int(x) for x in line.split()[1:]]
            idle_time = cpu_times[3]
            total_time = sum(cpu_times)
            
            # 简单计算，实际应该计算两次差值
            usage = 100.0 * (total_time - idle_time) / total_time
            return min(100.0, max(0.0, usage))
        except:
            return 0.0
    
    def _get_macos_cpu_usage(self) -> float:
        """获取macOS CPU使用率"""
        try:
            result = subprocess.run(['top', '-l', '1', '-n', '0'], 
                                  capture_output=True, text=True, timeout=5)
            lines = result.stdout.split('\n')
            for line in lines:
                if 'CPU usage:' in line:
                    # 解析CPU使用率
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'user' in part and i > 0:
                            user_cpu = float(parts[i-1].rstrip('%'))
                            break
                    for i, part in enumerate(parts):
                        if 'sys' in part and i > 0:
                            sys_cpu = float(parts[i-1].rstrip('%'))
                            break
                    return user_cpu + sys_cpu
        except:
            pass
        return 0.0
    
    def _get_memory_usage(self) -> float:
        """获取内存使用率"""
        try:
            if platform.system() == "Linux":
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                lines = meminfo.split('\n')
                mem_total = mem_free = mem_available = 0
                
                for line in lines:
                    if line.startswith('MemTotal:'):
                        mem_total = int(line.split()[1]) * 1024
                    elif line.startswith('MemFree:'):
                        mem_free = int(line.split()[1]) * 1024
                    elif line.startswith('MemAvailable:'):
                        mem_available = int(line.split()[1]) * 1024
                
                if mem_total > 0:
                    used = mem_total - (mem_available or mem_free)
                    return (used / mem_total) * 100.0
                    
            elif platform.system() == "Darwin":
                result = subprocess.run(['vm_stat'], capture_output=True, text=True, timeout=5)
                lines = result.stdout.split('\n')
                page_size = 4096  # 默认页面大小
                
                free_pages = wired_pages = active_pages = inactive_pages = 0
                for line in lines:
                    if 'page size of' in line:
                        page_size = int(line.split()[-2])
                    elif 'Pages free:' in line:
                        free_pages = int(line.split()[-1].rstrip('.'))
                    elif 'Pages wired down:' in line:
                        wired_pages = int(line.split()[-1].rstrip('.'))
                    elif 'Pages active:' in line:
                        active_pages = int(line.split()[-1].rstrip('.'))
                    elif 'Pages inactive:' in line:
                        inactive_pages = int(line.split()[-1].rstrip('.'))
                
                total_pages = free_pages + wired_pages + active_pages + inactive_pages
                if total_pages > 0:
                    used_pages = wired_pages + active_pages + inactive_pages
                    return (used_pages / total_pages) * 100.0
        except:
            pass
        return 0.0
    
    def _get_disk_usage(self) -> float:
        """获取磁盘使用率"""
        try:
            if platform.system() in ["Linux", "Darwin"]:
                result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True, timeout=5)
                lines = result.stdout.split('\n')
                if len(lines) >= 2:
                    fields = lines[1].split()
                    if len(fields) >= 5:
                        usage_str = fields[4].rstrip('%')
                        return float(usage_str)
        except:
            pass
        return 0.0
    
    def _get_network_io(self) -> Dict[str, float]:
        """获取网络IO统计"""
        try:
            if platform.system() == "Linux":
                with open('/proc/net/dev', 'r') as f:
                    lines = f.readlines()
                
                total_rx = total_tx = 0
                for line in lines[2:]:  # 跳过头部
                    fields = line.split()
                    if len(fields) >= 10:
                        total_rx += int(fields[1])  # 接收字节
                        total_tx += int(fields[9])  # 发送字节
                
                return {
                    'rx_mb': round(total_rx / (1024 * 1024), 2),
                    'tx_mb': round(total_tx / (1024 * 1024), 2)
                }
        except:
            pass
        return {'rx_mb': 0.0, 'tx_mb': 0.0}
    
    def _get_process_count(self) -> int:
        """获取进程数"""
        try:
            if platform.system() == "Linux":
                result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
                return len(result.stdout.split('\n')) - 1  # 减去表头
            elif platform.system() == "Darwin":
                result = subprocess.run(['ps', 'ax'], capture_output=True, text=True, timeout=5)
                return len(result.stdout.split('\n')) - 1
        except:
            pass
        return 0
    
    def _get_system_uptime(self) -> str:
        """获取系统运行时间"""
        try:
            if platform.system() == "Linux":
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.readline().split()[0])
            elif platform.system() == "Darwin":
                result = subprocess.run(['uptime'], capture_output=True, text=True, timeout=5)
                # 解析uptime输出
                output = result.stdout.strip()
                if 'up' in output:
                    return output.split('up ')[1].split(',')[0].strip()
                return "unknown"
            
            # 转换为可读格式
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
                
        except:
            return "unknown"

class DatabaseMonitor:
    """数据库监控器"""
    
    def __init__(self, config: Dict):
        self.config = config
        
    def get_database_metrics(self) -> Optional[DatabaseMetrics]:
        """获取数据库指标"""
        try:
            conn = psycopg2.connect(**self.config)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 连接数
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
            connection_count = cursor.fetchone()[0]
            
            # 活跃查询数
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active' AND datname = current_database()")
            active_queries = cursor.fetchone()[0]
            
            # 缓存命中率
            cursor.execute("""
                SELECT ROUND(100.0 * sum(blks_hit) / NULLIF(sum(blks_hit) + sum(blks_read), 0), 2)
                FROM pg_stat_database WHERE datname = current_database()
            """)
            cache_hit_ratio = cursor.fetchone()[0] or 0.0
            
            # 数据库大小
            cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
            database_size = cursor.fetchone()[0]
            
            # 慢查询数（运行超过5秒的查询）
            cursor.execute("""
                SELECT count(*) FROM pg_stat_activity 
                WHERE state = 'active' AND datname = current_database()
                AND now() - query_start > interval '5 seconds'
            """)
            slow_queries = cursor.fetchone()[0]
            
            # 事务数（简单估算TPS）
            cursor.execute("""
                SELECT xact_commit + xact_rollback as total_xacts
                FROM pg_stat_database WHERE datname = current_database()
            """)
            total_xacts = cursor.fetchone()[0] or 0
            
            # 锁数量
            cursor.execute("SELECT count(*) FROM pg_locks")
            lock_count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return DatabaseMetrics(
                timestamp=timestamp,
                connection_count=connection_count,
                active_queries=active_queries,
                cache_hit_ratio=cache_hit_ratio,
                database_size=database_size,
                slow_queries=slow_queries,
                transactions_per_second=0.0,  # 需要计算差值
                lock_count=lock_count
            )
            
        except Exception as e:
            print(f"❌ 获取数据库指标失败: {e}")
            return None

class ServiceMonitor:
    """服务监控器"""
    
    def __init__(self):
        self.services = [
            {'name': 'PostgreSQL', 'port': 5432},
            {'name': 'Redis', 'port': 6379},
            {'name': 'MinIO', 'port': 9000},
            {'name': 'Elasticsearch', 'port': 9200},
            {'name': 'FastAPI', 'port': 8000},
        ]
    
    def check_service_status(self, host: str, port: int, timeout: int = 3) -> bool:
        """检查服务端口是否可达"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def get_service_statuses(self) -> List[ServiceStatus]:
        """获取所有服务状态"""
        statuses = []
        
        for service in self.services:
            name = service['name']
            port = service['port']
            
            # 检查本地服务
            is_running = self.check_service_status('localhost', port)
            
            # 对于数据库，也检查远程服务
            if name == 'PostgreSQL':
                remote_running = self.check_service_status(REMOTE_DB_CONFIG['host'], port)
                is_running = is_running or remote_running
            
            status = ServiceStatus(
                name=name,
                status='running' if is_running else 'stopped',
                port=port,
                uptime=None,
                memory_usage=None,
                cpu_usage=None
            )
            statuses.append(status)
        
        return statuses

class HealthDashboard:
    """健康检查仪表板"""
    
    def __init__(self):
        self.system_monitor = SystemMonitor()
        self.db_monitor = DatabaseMonitor(REMOTE_DB_CONFIG)
        self.service_monitor = ServiceMonitor()
        self.running = False
        
    def print_dashboard(self, system_metrics: SystemMetrics, 
                       db_metrics: Optional[DatabaseMetrics], 
                       service_statuses: List[ServiceStatus]):
        """打印仪表板"""
        os.system('clear' if os.name == 'posix' else 'cls')  # 清屏
        
        print("=" * 80)
        print("🖥️  ZZDSJ 系统健康检查仪表板")
        print("=" * 80)
        print(f"📅 更新时间: {system_metrics.timestamp}")
        print()
        
        # 系统指标
        print("🖥️  系统指标:")
        print(f"  CPU使用率:    {system_metrics.cpu_usage:6.1f}% {'🔴' if system_metrics.cpu_usage > 80 else '🟡' if system_metrics.cpu_usage > 60 else '🟢'}")
        print(f"  内存使用率:   {system_metrics.memory_usage:6.1f}% {'🔴' if system_metrics.memory_usage > 85 else '🟡' if system_metrics.memory_usage > 70 else '🟢'}")
        print(f"  磁盘使用率:   {system_metrics.disk_usage:6.1f}% {'🔴' if system_metrics.disk_usage > 90 else '🟡' if system_metrics.disk_usage > 80 else '🟢'}")
        print(f"  进程数:       {system_metrics.process_count:6d}")
        print(f"  系统运行时间: {system_metrics.uptime}")
        print(f"  网络IO:       RX {system_metrics.network_io.get('rx_mb', 0)} MB, TX {system_metrics.network_io.get('tx_mb', 0)} MB")
        print()
        
        # 数据库指标
        if db_metrics:
            print("🗄️  数据库指标:")
            print(f"  连接数:       {db_metrics.connection_count:6d} {'🔴' if db_metrics.connection_count > 100 else '🟡' if db_metrics.connection_count > 50 else '🟢'}")
            print(f"  活跃查询:     {db_metrics.active_queries:6d} {'🔴' if db_metrics.active_queries > 20 else '🟡' if db_metrics.active_queries > 10 else '🟢'}")
            print(f"  慢查询:       {db_metrics.slow_queries:6d} {'🔴' if db_metrics.slow_queries > 5 else '🟡' if db_metrics.slow_queries > 0 else '🟢'}")
            print(f"  缓存命中率:   {db_metrics.cache_hit_ratio:6.1f}% {'🔴' if db_metrics.cache_hit_ratio < 80 else '🟡' if db_metrics.cache_hit_ratio < 90 else '🟢'}")
            print(f"  数据库大小:   {db_metrics.database_size}")
            print(f"  锁数量:       {db_metrics.lock_count:6d}")
        else:
            print("🗄️  数据库指标: ❌ 无法连接")
        print()
        
        # 服务状态
        print("🔧 服务状态:")
        for service in service_statuses:
            status_icon = "🟢" if service.status == "running" else "🔴"
            print(f"  {service.name:12} ({service.port:4d}): {status_icon} {service.status.upper()}")
        print()
        
        # 总体健康评分
        health_score = self._calculate_health_score(system_metrics, db_metrics, service_statuses)
        score_icon = "🟢" if health_score >= 80 else "🟡" if health_score >= 60 else "🔴"
        print(f"💚 总体健康评分: {score_icon} {health_score}/100")
        print()
        print("按 Ctrl+C 停止监控")
        print("=" * 80)
    
    def _calculate_health_score(self, system_metrics: SystemMetrics, 
                               db_metrics: Optional[DatabaseMetrics], 
                               service_statuses: List[ServiceStatus]) -> int:
        """计算健康评分"""
        score = 100
        
        # 系统指标扣分
        if system_metrics.cpu_usage > 80:
            score -= 20
        elif system_metrics.cpu_usage > 60:
            score -= 10
            
        if system_metrics.memory_usage > 85:
            score -= 20
        elif system_metrics.memory_usage > 70:
            score -= 10
            
        if system_metrics.disk_usage > 90:
            score -= 25
        elif system_metrics.disk_usage > 80:
            score -= 15
        
        # 数据库指标扣分
        if db_metrics:
            if db_metrics.connection_count > 100:
                score -= 15
            elif db_metrics.connection_count > 50:
                score -= 8
                
            if db_metrics.slow_queries > 5:
                score -= 15
            elif db_metrics.slow_queries > 0:
                score -= 5
                
            if db_metrics.cache_hit_ratio < 80:
                score -= 15
            elif db_metrics.cache_hit_ratio < 90:
                score -= 8
        else:
            score -= 30  # 数据库不可用
        
        # 服务状态扣分
        running_services = sum(1 for s in service_statuses if s.status == "running")
        total_services = len(service_statuses)
        if running_services < total_services:
            score -= (total_services - running_services) * 10
        
        return max(0, score)
    
    def save_metrics(self, system_metrics: SystemMetrics, 
                    db_metrics: Optional[DatabaseMetrics], 
                    service_statuses: List[ServiceStatus]):
        """保存指标到文件"""
        metrics_dir = Path("dashboard_data")
        metrics_dir.mkdir(exist_ok=True)
        
        data = {
            'timestamp': system_metrics.timestamp,
            'system': asdict(system_metrics),
            'database': asdict(db_metrics) if db_metrics else None,
            'services': [asdict(s) for s in service_statuses]
        }
        
        # 保存到今日文件
        date_str = datetime.now().strftime('%Y%m%d')
        metrics_file = metrics_dir / f"dashboard_{date_str}.json"
        
        # 读取现有数据
        if metrics_file.exists():
            with open(metrics_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = []
        
        # 添加新数据
        existing_data.append(data)
        
        # 保留最近1000条记录
        if len(existing_data) > 1000:
            existing_data = existing_data[-1000:]
        
        # 保存数据
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
    
    def start_monitoring(self, interval: int = 5):
        """开始监控"""
        print("🚀 启动系统健康检查仪表板...")
        print(f"📊 监控间隔: {interval} 秒")
        print("🔄 按 Ctrl+C 停止监控\n")
        
        self.running = True
        
        def signal_handler(signum, frame):
            print("\n🛑 收到停止信号，正在停止监控...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        
        while self.running:
            try:
                # 收集指标
                system_metrics = self.system_monitor.get_system_metrics()
                db_metrics = self.db_monitor.get_database_metrics()
                service_statuses = self.service_monitor.get_service_statuses()
                
                # 显示仪表板
                self.print_dashboard(system_metrics, db_metrics, service_statuses)
                
                # 保存数据
                self.save_metrics(system_metrics, db_metrics, service_statuses)
                
                # 等待下次检查
                if self.running:
                    time.sleep(interval)
                    
            except Exception as e:
                print(f"❌ 监控异常: {e}")
                time.sleep(5)  # 出错后短暂等待
        
        print("📴 监控已停止")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="系统健康检查仪表板")
    parser.add_argument('--interval', type=int, default=5,
                       help='监控间隔(秒)，默认5秒')
    parser.add_argument('--once', action='store_true',
                       help='只运行一次，不持续监控')
    
    args = parser.parse_args()
    
    dashboard = HealthDashboard()
    
    if args.once:
        # 只运行一次
        system_metrics = dashboard.system_monitor.get_system_metrics()
        db_metrics = dashboard.db_monitor.get_database_metrics()
        service_statuses = dashboard.service_monitor.get_service_statuses()
        
        dashboard.print_dashboard(system_metrics, db_metrics, service_statuses)
        dashboard.save_metrics(system_metrics, db_metrics, service_statuses)
    else:
        # 持续监控
        dashboard.start_monitoring(args.interval)

if __name__ == "__main__":
    main() 