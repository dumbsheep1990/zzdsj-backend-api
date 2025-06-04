#!/usr/bin/env python3
"""
所有服务初始化脚本 - 主控制器
统一管理数据库、MinIO、Elasticsearch等所有服务的初始化
提供完整的系统部署和健康检查功能
"""

import asyncio
import json
import sys
import time
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import concurrent.futures

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ServiceStatus:
    """服务状态"""
    name: str
    status: str  # success, failed, skipped, running
    duration: float
    error_message: Optional[str] = None
    details: Optional[Dict] = None

@dataclass
class InitializationReport:
    """初始化报告"""
    timestamp: str
    total_duration: float
    services: List[ServiceStatus]
    overall_status: str  # success, partial, failed
    summary: Dict[str, int]

class ServiceInitializer:
    """服务初始化器基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.status = "pending"
        
    def check_prerequisites(self) -> bool:
        """检查前置条件"""
        return True
    
    def initialize(self) -> ServiceStatus:
        """执行初始化"""
        start_time = time.time()
        
        try:
            if not self.check_prerequisites():
                return ServiceStatus(
                    name=self.name,
                    status="failed",
                    duration=time.time() - start_time,
                    error_message="前置条件检查失败"
                )
            
            success = self._do_initialize()
            duration = time.time() - start_time
            
            return ServiceStatus(
                name=self.name,
                status="success" if success else "failed",
                duration=duration,
                error_message=None if success else "初始化失败"
            )
            
        except Exception as e:
            return ServiceStatus(
                name=self.name,
                status="failed",
                duration=time.time() - start_time,
                error_message=str(e)
            )
    
    def _do_initialize(self) -> bool:
        """子类需要实现的具体初始化逻辑"""
        raise NotImplementedError

class DatabaseInitializer(ServiceInitializer):
    """数据库初始化器"""
    
    def __init__(self, config: Dict):
        super().__init__("PostgreSQL Database")
        self.config = config
    
    def check_prerequisites(self) -> bool:
        """检查数据库连接"""
        try:
            import psycopg2
            conn = psycopg2.connect(**self.config)
            conn.close()
            return True
        except Exception as e:
            logger.error(f"数据库连接检查失败: {e}")
            return False
    
    def _do_initialize(self) -> bool:
        """执行数据库初始化"""
        try:
            # 运行数据库测试脚本
            script_path = Path(__file__).parent.parent / "database" / "test_remote_postgres.py"
            
            cmd = [
                sys.executable, str(script_path),
                "--mode", "init",
                "--host", self.config.get('host', 'localhost'),
                "--port", str(self.config.get('port', 5432)),
                "--user", self.config.get('user', 'postgres'),
                "--password", self.config.get('password', ''),
                "--database", self.config.get('database', 'postgres')
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info("数据库初始化成功")
                return True
            else:
                logger.error(f"数据库初始化失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"数据库初始化异常: {e}")
            return False

class MinIOInitializer(ServiceInitializer):
    """MinIO初始化器"""
    
    def __init__(self, config: Dict):
        super().__init__("MinIO Object Storage")
        self.config = config
    
    def check_prerequisites(self) -> bool:
        """检查MinIO连接"""
        try:
            from minio import Minio
            client = Minio(
                endpoint=self.config.get('endpoint', 'localhost:9000'),
                access_key=self.config.get('access_key', 'minioadmin'),
                secret_key=self.config.get('secret_key', 'minioadmin'),
                secure=self.config.get('secure', False)
            )
            list(client.list_buckets())
            return True
        except Exception as e:
            logger.error(f"MinIO连接检查失败: {e}")
            return False
    
    def _do_initialize(self) -> bool:
        """执行MinIO初始化"""
        try:
            script_path = Path(__file__).parent / "init_minio.py"
            
            cmd = [
                sys.executable, str(script_path),
                "--mode", "init",
                "--endpoint", self.config.get('endpoint', 'localhost:9000'),
                "--access-key", self.config.get('access_key', 'minioadmin'),
                "--secret-key", self.config.get('secret_key', 'minioadmin')
            ]
            
            if self.config.get('secure', False):
                cmd.append("--secure")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            
            if result.returncode == 0:
                logger.info("MinIO初始化成功")
                return True
            else:
                logger.error(f"MinIO初始化失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"MinIO初始化异常: {e}")
            return False

class ElasticsearchInitializer(ServiceInitializer):
    """Elasticsearch初始化器"""
    
    def __init__(self, config: Dict):
        super().__init__("Elasticsearch Search Engine")
        self.config = config
    
    def check_prerequisites(self) -> bool:
        """检查Elasticsearch连接"""
        try:
            from elasticsearch import Elasticsearch
            
            es_kwargs = {}
            if self.config.get('username') and self.config.get('password'):
                es_kwargs["basic_auth"] = (self.config['username'], self.config['password'])
            
            client = Elasticsearch(self.config.get('url', 'http://localhost:9200'), **es_kwargs)
            client.cluster.health()
            return True
        except Exception as e:
            logger.error(f"Elasticsearch连接检查失败: {e}")
            return False
    
    def _do_initialize(self) -> bool:
        """执行Elasticsearch初始化"""
        try:
            script_path = Path(__file__).parent / "init_elasticsearch_enhanced.py"
            
            cmd = [
                sys.executable, str(script_path),
                "--mode", "init",
                "--es-url", self.config.get('url', 'http://localhost:9200'),
                "--timeout", "60"
            ]
            
            if self.config.get('username'):
                cmd.extend(["--username", self.config['username']])
            if self.config.get('password'):
                cmd.extend(["--password", self.config['password']])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            
            if result.returncode == 0:
                logger.info("Elasticsearch初始化成功")
                return True
            else:
                logger.error(f"Elasticsearch初始化失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Elasticsearch初始化异常: {e}")
            return False

class RedisInitializer(ServiceInitializer):
    """Redis初始化器"""
    
    def __init__(self, config: Dict):
        super().__init__("Redis Cache")
        self.config = config
    
    def check_prerequisites(self) -> bool:
        """检查Redis连接"""
        try:
            import redis
            r = redis.Redis(
                host=self.config.get('host', 'localhost'),
                port=self.config.get('port', 6379),
                password=self.config.get('password'),
                db=self.config.get('db', 0)
            )
            r.ping()
            return True
        except Exception as e:
            logger.error(f"Redis连接检查失败: {e}")
            return False
    
    def _do_initialize(self) -> bool:
        """执行Redis初始化"""
        try:
            import redis
            r = redis.Redis(
                host=self.config.get('host', 'localhost'),
                port=self.config.get('port', 6379),
                password=self.config.get('password'),
                db=self.config.get('db', 0)
            )
            
            # 设置一些基础配置
            r.set("system:init:timestamp", datetime.now().isoformat())
            r.set("system:init:status", "completed")
            
            logger.info("Redis初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"Redis初始化异常: {e}")
            return False

class SystemHealthChecker:
    """系统健康检查器"""
    
    def __init__(self):
        pass
    
    def run_health_check(self) -> Dict[str, Any]:
        """运行系统健康检查"""
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'services': {},
            'overall_status': 'unknown'
        }
        
        # 运行系统仪表板健康检查
        try:
            script_path = Path(__file__).parent.parent / "monitoring" / "system_dashboard.py"
            
            cmd = [sys.executable, str(script_path), "--once"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            health_report['system_dashboard'] = {
                'status': 'success' if result.returncode == 0 else 'failed',
                'output': result.stdout[:500] if result.stdout else None
            }
            
        except Exception as e:
            health_report['system_dashboard'] = {
                'status': 'error',
                'error': str(e)
            }
        
        return health_report

class MasterInitializer:
    """主初始化器"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = self._load_config(config_file)
        self.services = []
        self.health_checker = SystemHealthChecker()
        
    def _load_config(self, config_file: Optional[str]) -> Dict:
        """加载配置文件"""
        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    if config_file.endswith('.json'):
                        return json.load(f)
                    elif config_file.endswith('.yaml') or config_file.endswith('.yml'):
                        import yaml
                        return yaml.safe_load(f)
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}")
        
        # 返回默认配置
        return {
            'database': {
                'host': '167.71.85.231',
                'port': 5432,
                'user': 'zzdsj',
                'password': 'zzdsj123',
                'database': 'zzdsj'
            },
            'minio': {
                'endpoint': 'localhost:9000',
                'access_key': 'minioadmin',
                'secret_key': 'minioadmin',
                'secure': False
            },
            'elasticsearch': {
                'url': 'http://localhost:9200',
                'username': None,
                'password': None
            },
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'password': None,
                'db': 0
            }
        }
    
    def _create_initializers(self, services: List[str]) -> List[ServiceInitializer]:
        """创建服务初始化器"""
        initializers = []
        
        service_map = {
            'database': DatabaseInitializer,
            'minio': MinIOInitializer,
            'elasticsearch': ElasticsearchInitializer,
            'redis': RedisInitializer
        }
        
        for service_name in services:
            if service_name in service_map and service_name in self.config:
                initializer_class = service_map[service_name]
                initializer = initializer_class(self.config[service_name])
                initializers.append(initializer)
                logger.info(f"已创建 {service_name} 初始化器")
            else:
                logger.warning(f"未知服务或缺少配置: {service_name}")
        
        return initializers
    
    def initialize_services(self, services: List[str], parallel: bool = False) -> InitializationReport:
        """初始化服务"""
        start_time = time.time()
        
        logger.info(f"开始初始化服务: {', '.join(services)}")
        logger.info(f"并行模式: {'启用' if parallel else '禁用'}")
        
        initializers = self._create_initializers(services)
        service_statuses = []
        
        if parallel and len(initializers) > 1:
            # 并行初始化
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(initializers)) as executor:
                future_to_service = {
                    executor.submit(initializer.initialize): initializer.name 
                    for initializer in initializers
                }
                
                for future in concurrent.futures.as_completed(future_to_service):
                    service_name = future_to_service[future]
                    try:
                        status = future.result()
                        service_statuses.append(status)
                        
                        if status.status == "success":
                            logger.info(f"✅ {service_name} 初始化成功 ({status.duration:.1f}s)")
                        else:
                            logger.error(f"❌ {service_name} 初始化失败: {status.error_message}")
                            
                    except Exception as e:
                        logger.error(f"❌ {service_name} 初始化异常: {e}")
                        service_statuses.append(ServiceStatus(
                            name=service_name,
                            status="failed",
                            duration=0,
                            error_message=str(e)
                        ))
        else:
            # 串行初始化
            for initializer in initializers:
                logger.info(f"正在初始化 {initializer.name}...")
                status = initializer.initialize()
                service_statuses.append(status)
                
                if status.status == "success":
                    logger.info(f"✅ {initializer.name} 初始化成功 ({status.duration:.1f}s)")
                else:
                    logger.error(f"❌ {initializer.name} 初始化失败: {status.error_message}")
        
        # 生成报告
        total_duration = time.time() - start_time
        
        success_count = sum(1 for s in service_statuses if s.status == "success")
        failed_count = sum(1 for s in service_statuses if s.status == "failed")
        
        if failed_count == 0:
            overall_status = "success"
        elif success_count > 0:
            overall_status = "partial"
        else:
            overall_status = "failed"
        
        report = InitializationReport(
            timestamp=datetime.now().isoformat(),
            total_duration=total_duration,
            services=service_statuses,
            overall_status=overall_status,
            summary={
                'total': len(service_statuses),
                'success': success_count,
                'failed': failed_count,
                'skipped': len(service_statuses) - success_count - failed_count
            }
        )
        
        logger.info(f"初始化完成 - 总耗时: {total_duration:.1f}s")
        logger.info(f"结果: {success_count}成功, {failed_count}失败")
        
        return report
    
    def save_report(self, report: InitializationReport) -> bool:
        """保存初始化报告"""
        try:
            report_dir = Path("init_reports")
            report_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = report_dir / f"init_report_{timestamp}.json"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(report), f, indent=2, ensure_ascii=False)
            
            logger.info(f"初始化报告已保存到: {report_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
            return False
    
    def print_summary(self, report: InitializationReport):
        """打印初始化摘要"""
        print(f"\n{'='*60}")
        print("🚀 ZZDSJ 系统初始化报告")
        print(f"{'='*60}")
        print(f"时间: {report.timestamp}")
        print(f"总耗时: {report.total_duration:.1f} 秒")
        print(f"整体状态: {report.overall_status.upper()}")
        print(f"服务统计: {report.summary['success']}成功 / {report.summary['failed']}失败 / {report.summary['total']}总计")
        
        print(f"\n📋 服务详情:")
        for service in report.services:
            status_icon = "✅" if service.status == "success" else "❌" if service.status == "failed" else "⏸️"
            print(f"  {status_icon} {service.name:25} | {service.duration:6.1f}s | {service.status.upper()}")
            if service.error_message:
                print(f"     错误: {service.error_message}")
        
        if report.overall_status == "success":
            print(f"\n🎉 所有服务初始化成功!")
            print("💡 系统已准备就绪，可以开始使用")
        elif report.overall_status == "partial":
            print(f"\n⚠️ 部分服务初始化成功")
            print("💡 请检查失败的服务并重新初始化")
        else:
            print(f"\n❌ 初始化失败")
            print("💡 请检查错误信息并修复问题后重试")
        
        print(f"{'='*60}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="ZZDSJ 系统服务初始化脚本")
    parser.add_argument('--services', nargs='+', 
                       choices=['database', 'minio', 'elasticsearch', 'redis', 'all'],
                       default=['all'],
                       help='要初始化的服务列表')
    parser.add_argument('--config-file',
                       help='配置文件路径 (JSON/YAML)')
    parser.add_argument('--parallel', action='store_true',
                       help='并行初始化服务')
    parser.add_argument('--health-check', action='store_true',
                       help='初始化后运行健康检查')
    parser.add_argument('--save-report', action='store_true',
                       help='保存初始化报告')
    
    args = parser.parse_args()
    
    try:
        # 处理服务列表
        if 'all' in args.services:
            services = ['database', 'minio', 'elasticsearch', 'redis']
        else:
            services = args.services
        
        # 创建主初始化器
        master_init = MasterInitializer(args.config_file)
        
        # 执行初始化
        report = master_init.initialize_services(services, args.parallel)
        
        # 打印摘要
        master_init.print_summary(report)
        
        # 保存报告
        if args.save_report:
            master_init.save_report(report)
        
        # 运行健康检查
        if args.health_check and report.overall_status in ['success', 'partial']:
            logger.info("运行系统健康检查...")
            health_report = master_init.health_checker.run_health_check()
            logger.info("健康检查完成")
        
        # 返回状态码
        if report.overall_status == "success":
            return 0
        elif report.overall_status == "partial":
            return 1
        else:
            return 2
            
    except Exception as e:
        logger.error(f"初始化过程异常: {e}")
        return 3

if __name__ == "__main__":
    sys.exit(main()) 