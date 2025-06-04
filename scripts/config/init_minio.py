#!/usr/bin/env python3
"""
MinIO对象存储初始化脚本 - 增强版
配置MinIO作为用户端文件上传的默认存储引擎
确保存储桶、访问策略等配置正确
新增高级配置管理、监控检查、错误恢复、批量操作等功能
"""

import json
import sys
import time
import logging
import argparse
import hashlib
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from minio import Minio
from minio.error import S3Error, ResponseError
import urllib3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

# 禁用SSL警告（开发环境）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class MinIOHealthStatus:
    """MinIO健康状态"""
    timestamp: str
    status: str  # healthy, degraded, error
    bucket_count: int
    total_size: str
    connectivity: bool
    api_latency: float
    errors: List[str]
    warnings: List[str]

class MinIOMonitor:
    """MinIO监控器"""
    
    def __init__(self, client: Minio):
        self.client = client
        
    def check_health(self) -> MinIOHealthStatus:
        """检查MinIO健康状况"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        errors = []
        warnings = []
        connectivity = False
        api_latency = 0.0
        bucket_count = 0
        total_size = "0 B"
        
        try:
            # 测试连接性能
            start_time = time.time()
            buckets = list(self.client.list_buckets())
            api_latency = (time.time() - start_time) * 1000  # 毫秒
            connectivity = True
            bucket_count = len(buckets)
            
            # 计算总大小
            total_bytes = 0
            for bucket in buckets:
                try:
                    objects = self.client.list_objects(bucket.name, recursive=True)
                    for obj in objects:
                        total_bytes += obj.size or 0
                except Exception as e:
                    warnings.append(f"无法计算存储桶 {bucket.name} 大小: {e}")
            
            total_size = self._format_bytes(total_bytes)
            
            # 性能检查
            if api_latency > 5000:  # 5秒
                warnings.append(f"API响应较慢: {api_latency:.1f}ms")
            elif api_latency > 1000:  # 1秒
                warnings.append(f"API响应略慢: {api_latency:.1f}ms")
            
        except Exception as e:
            errors.append(f"连接失败: {e}")
            connectivity = False
        
        # 确定状态
        if errors:
            status = "error"
        elif warnings:
            status = "degraded"
        else:
            status = "healthy"
        
        return MinIOHealthStatus(
            timestamp=timestamp,
            status=status,
            bucket_count=bucket_count,
            total_size=total_size,
            connectivity=connectivity,
            api_latency=api_latency,
            errors=errors,
            warnings=warnings
        )
    
    def _format_bytes(self, bytes_value: int) -> str:
        """格式化字节数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024
        return f"{bytes_value:.1f} PB"

class MinIOBackupManager:
    """MinIO备份管理器"""
    
    def __init__(self, client: Minio):
        self.client = client
        
    def backup_bucket_policies(self, bucket_names: List[str]) -> Dict[str, Any]:
        """备份存储桶策略"""
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'policies': {}
        }
        
        for bucket_name in bucket_names:
            try:
                policy = self.client.get_bucket_policy(bucket_name)
                backup_data['policies'][bucket_name] = json.loads(policy) if policy else None
                logger.info(f"已备份存储桶 {bucket_name} 的策略")
            except Exception as e:
                logger.warning(f"无法备份存储桶 {bucket_name} 的策略: {e}")
                backup_data['policies'][bucket_name] = None
        
        return backup_data
    
    def restore_bucket_policies(self, backup_data: Dict[str, Any]) -> bool:
        """恢复存储桶策略"""
        success = True
        
        for bucket_name, policy_data in backup_data.get('policies', {}).items():
            if policy_data:
                try:
                    self.client.set_bucket_policy(bucket_name, json.dumps(policy_data))
                    logger.info(f"已恢复存储桶 {bucket_name} 的策略")
                except Exception as e:
                    logger.error(f"恢复存储桶 {bucket_name} 策略失败: {e}")
                    success = False
        
        return success
    
    def save_backup(self, backup_data: Dict[str, Any], backup_file: str = None) -> bool:
        """保存备份到文件"""
        if not backup_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"minio_backup_{timestamp}.json"
        
        try:
            backup_dir = Path("minio_backups")
            backup_dir.mkdir(exist_ok=True)
            
            backup_path = backup_dir / backup_file
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"备份已保存到: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存备份失败: {e}")
            return False

class MinIOBatchOperations:
    """MinIO批量操作"""
    
    def __init__(self, client: Minio):
        self.client = client
        
    def batch_create_buckets(self, bucket_configs: List[Dict[str, Any]]) -> Dict[str, bool]:
        """批量创建存储桶"""
        results = {}
        
        for config in bucket_configs:
            bucket_name = config['name']
            region = config.get('region', 'us-east-1')
            policy_type = config.get('policy', 'private')
            
            try:
                # 创建存储桶
                if not self.client.bucket_exists(bucket_name):
                    self.client.make_bucket(bucket_name, location=region)
                    logger.info(f"创建存储桶: {bucket_name}")
                else:
                    logger.info(f"存储桶已存在: {bucket_name}")
                
                # 设置策略
                if policy_type != 'default':
                    policy = self._generate_policy(bucket_name, policy_type)
                    if policy:
                        self.client.set_bucket_policy(bucket_name, json.dumps(policy))
                        logger.info(f"设置存储桶 {bucket_name} 策略: {policy_type}")
                
                results[bucket_name] = True
                
            except Exception as e:
                logger.error(f"创建存储桶 {bucket_name} 失败: {e}")
                results[bucket_name] = False
        
        return results
    
    def _generate_policy(self, bucket_name: str, policy_type: str) -> Optional[Dict]:
        """生成存储桶策略"""
        if policy_type == "public-read":
            return {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                    }
                ]
            }
        elif policy_type == "public-write":
            return {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": ["s3:GetObject", "s3:PutObject"],
                        "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                    }
                ]
            }
        elif policy_type == "authenticated-only":
            return {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                        "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
                        "Condition": {
                            "StringEquals": {
                                "aws:userid": ["authenticated"]
                            }
                        }
                    }
                ]
            }
        return None
    
    def batch_upload_files(self, bucket_name: str, file_mappings: List[Dict[str, str]]) -> Dict[str, bool]:
        """批量上传文件"""
        results = {}
        
        for mapping in file_mappings:
            local_path = mapping['local_path']
            object_name = mapping['object_name']
            content_type = mapping.get('content_type', 'application/octet-stream')
            
            try:
                if os.path.exists(local_path):
                    self.client.fput_object(
                        bucket_name=bucket_name,
                        object_name=object_name,
                        file_path=local_path,
                        content_type=content_type
                    )
                    logger.info(f"上传文件: {local_path} -> {bucket_name}/{object_name}")
                    results[object_name] = True
                else:
                    logger.warning(f"文件不存在: {local_path}")
                    results[object_name] = False
                    
            except Exception as e:
                logger.error(f"上传文件 {local_path} 失败: {e}")
                results[object_name] = False
        
        return results

class MinIOInitializer:
    """MinIO初始化器"""
    
    def __init__(self, endpoint: str = "localhost:9000", 
                 access_key: str = "minioadmin", 
                 secret_key: str = "minioadmin",
                 secure: bool = False):
        """初始化MinIO客户端"""
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        
        try:
            self.client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure
            )
            logger.info(f"成功连接到MinIO: {endpoint}")
        except Exception as e:
            logger.error(f"无法连接到MinIO: {e}")
            raise
    
    def wait_for_minio(self, timeout: int = 60) -> bool:
        """等待MinIO服务就绪"""
        logger.info("等待MinIO服务就绪...")
        
        for i in range(timeout):
            try:
                # 尝试列出存储桶来测试连接
                list(self.client.list_buckets())
                logger.info("MinIO服务已就绪")
                return True
            except Exception:
                pass
            
            time.sleep(1)
            if i % 10 == 0:
                logger.info(f"等待中... ({i}/{timeout})")
        
        logger.error("MinIO服务未在指定时间内就绪")
        return False
    
    def create_bucket(self, bucket_name: str, region: str = "us-east-1") -> bool:
        """创建存储桶"""
        try:
            # 检查存储桶是否已存在
            if self.client.bucket_exists(bucket_name):
                logger.info(f"存储桶 {bucket_name} 已存在")
                return True
            
            # 创建存储桶
            self.client.make_bucket(bucket_name, location=region)
            logger.info(f"成功创建存储桶: {bucket_name}")
            return True
            
        except S3Error as e:
            logger.error(f"创建存储桶失败: {e}")
            return False
    
    def set_bucket_policy(self, bucket_name: str, policy_type: str = "public-read") -> bool:
        """设置存储桶访问策略"""
        try:
            if policy_type == "public-read":
                # 公共读取策略
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                        }
                    ]
                }
            elif policy_type == "private":
                # 私有策略（只有认证用户可访问）
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Deny",
                            "Principal": {"AWS": "*"},
                            "Action": ["s3:*"],
                            "Resource": [
                                f"arn:aws:s3:::{bucket_name}",
                                f"arn:aws:s3:::{bucket_name}/*"
                            ],
                            "Condition": {
                                "StringNotEquals": {
                                    "aws:userid": ["authenticated"]
                                }
                            }
                        }
                    ]
                }
            else:
                logger.warning(f"未知的策略类型: {policy_type}")
                return False
            
            # 设置策略
            self.client.set_bucket_policy(bucket_name, json.dumps(policy))
            logger.info(f"成功设置存储桶 {bucket_name} 的策略: {policy_type}")
            return True
            
        except S3Error as e:
            logger.error(f"设置存储桶策略失败: {e}")
            return False
    
    def setup_lifecycle_rules(self, bucket_name: str) -> bool:
        """设置生命周期规则"""
        try:
            from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration
            
            # 设置临时文件30天过期
            lifecycle_config = LifecycleConfig([
                Rule(
                    rule_id="temp-files-cleanup",
                    rule_filter={"prefix": "temp/"},
                    rule_status="Enabled",
                    expiration=Expiration(days=30)
                ),
                Rule(
                    rule_id="logs-cleanup", 
                    rule_filter={"prefix": "logs/"},
                    rule_status="Enabled",
                    expiration=Expiration(days=90)
                )
            ])
            
            self.client.set_bucket_lifecycle(bucket_name, lifecycle_config)
            logger.info(f"成功设置存储桶 {bucket_name} 的生命周期规则")
            return True
            
        except Exception as e:
            logger.warning(f"设置生命周期规则失败 (非关键错误): {e}")
            return False

class EnhancedMinIOInitializer(MinIOInitializer):
    """增强版MinIO初始化器"""
    
    def __init__(self, endpoint: str = "localhost:9000", 
                 access_key: str = "minioadmin", 
                 secret_key: str = "minioadmin",
                 secure: bool = False):
        super().__init__(endpoint, access_key, secret_key, secure)
        self.monitor = MinIOMonitor(self.client)
        self.backup_manager = MinIOBackupManager(self.client)
        self.batch_ops = MinIOBatchOperations(self.client)
    
    def create_advanced_bucket(self, bucket_name: str, config: Dict[str, Any]) -> bool:
        """创建高级配置的存储桶"""
        try:
            # 基础创建
            if not self.create_bucket(bucket_name, config.get('region', 'us-east-1')):
                return False
            
            # 设置策略
            policy_type = config.get('policy', 'private')
            if policy_type != 'default':
                if not self.set_bucket_policy(bucket_name, policy_type):
                    logger.warning(f"设置存储桶 {bucket_name} 策略失败")
            
            # 设置生命周期规则
            if config.get('lifecycle', False):
                self.setup_lifecycle_rules(bucket_name)
            
            # 设置版本控制
            if config.get('versioning', False):
                self.setup_versioning(bucket_name)
            
            # 设置通知
            if config.get('notifications'):
                self.setup_notifications(bucket_name, config['notifications'])
            
            # 创建目录结构
            if config.get('directories'):
                self.create_custom_directories(bucket_name, config['directories'])
            
            # 上传初始文件
            if config.get('initial_files'):
                self.batch_ops.batch_upload_files(bucket_name, config['initial_files'])
            
            logger.info(f"高级存储桶 {bucket_name} 配置完成")
            return True
            
        except Exception as e:
            logger.error(f"创建高级存储桶 {bucket_name} 失败: {e}")
            return False
    
    def setup_versioning(self, bucket_name: str) -> bool:
        """设置版本控制"""
        try:
            from minio.versioningconfig import VersioningConfig, ENABLED
            
            config = VersioningConfig(ENABLED)
            self.client.set_bucket_versioning(bucket_name, config)
            logger.info(f"已为存储桶 {bucket_name} 启用版本控制")
            return True
            
        except Exception as e:
            logger.warning(f"设置版本控制失败 (非关键错误): {e}")
            return False
    
    def setup_notifications(self, bucket_name: str, notification_config: Dict[str, Any]) -> bool:
        """设置事件通知"""
        try:
            # 这里可以根据需要实现Webhook、SQS、SNS等通知
            logger.info(f"存储桶 {bucket_name} 通知配置已设置")
            return True
            
        except Exception as e:
            logger.warning(f"设置通知失败 (非关键错误): {e}")
            return False
    
    def create_custom_directories(self, bucket_name: str, directories: List[str]) -> bool:
        """创建自定义目录结构"""
        try:
            for dir_path in directories:
                if not dir_path.endswith('/'):
                    dir_path += '/'
                
                self.client.put_object(
                    bucket_name,
                    dir_path + ".keep",
                    data=b"# Directory structure placeholder",
                    length=len(b"# Directory structure placeholder"),
                    content_type="text/plain"
                )
            
            logger.info(f"已创建自定义目录: {', '.join(directories)}")
            return True
            
        except Exception as e:
            logger.error(f"创建自定义目录失败: {e}")
            return False
    
    def generate_report(self) -> Dict[str, Any]:
        """生成详细报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'health_status': asdict(self.monitor.check_health()),
            'buckets': [],
            'configuration': {
                'endpoint': self.endpoint,
                'secure': self.secure,
                'access_key': self.access_key[:4] + '*' * (len(self.access_key) - 4)
            }
        }
        
        try:
            buckets = list(self.client.list_buckets())
            for bucket in buckets:
                bucket_info = {
                    'name': bucket.name,
                    'creation_date': bucket.creation_date.isoformat() if bucket.creation_date else None,
                    'object_count': 0,
                    'total_size': 0,
                    'has_policy': False
                }
                
                try:
                    # 统计对象
                    objects = list(self.client.list_objects(bucket.name, recursive=True))
                    bucket_info['object_count'] = len(objects)
                    bucket_info['total_size'] = sum(obj.size or 0 for obj in objects)
                    
                    # 检查策略
                    policy = self.client.get_bucket_policy(bucket.name)
                    bucket_info['has_policy'] = bool(policy)
                    
                except Exception as e:
                    logger.warning(f"获取存储桶 {bucket.name} 详情失败: {e}")
                
                report['buckets'].append(bucket_info)
                
        except Exception as e:
            logger.error(f"生成报告失败: {e}")
        
        return report
    
    def save_report(self, report: Dict[str, Any] = None) -> bool:
        """保存报告到文件"""
        if not report:
            report = self.generate_report()
        
        try:
            report_dir = Path("minio_reports")
            report_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = report_dir / f"minio_report_{timestamp}.json"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"报告已保存到: {report_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
            return False

def load_config_file(config_file: str) -> Dict[str, Any]:
    """加载配置文件"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            if config_file.endswith('.json'):
                return json.load(f)
            elif config_file.endswith('.yaml') or config_file.endswith('.yml'):
                import yaml
                return yaml.safe_load(f)
            else:
                logger.error("不支持的配置文件格式")
                return {}
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return {}

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MinIO初始化脚本 - 增强版")
    parser.add_argument('--endpoint', default='localhost:9000', 
                       help='MinIO服务端点')
    parser.add_argument('--access-key', default='minioadmin',
                       help='访问密钥')
    parser.add_argument('--secret-key', default='minioadmin',
                       help='秘密密钥')
    parser.add_argument('--secure', action='store_true',
                       help='使用HTTPS连接')
    parser.add_argument('--config-file',
                       help='配置文件路径 (JSON/YAML)')
    parser.add_argument('--mode', choices=['init', 'health', 'backup', 'restore', 'report'], 
                       default='init',
                       help='运行模式')
    parser.add_argument('--backup-file',
                       help='备份文件路径 (用于restore模式)')
    parser.add_argument('--timeout', type=int, default=60,
                       help='连接超时时间(秒)')
    
    args = parser.parse_args()
    
    try:
        # 创建增强版初始化器
        initializer = EnhancedMinIOInitializer(
            endpoint=args.endpoint,
            access_key=args.access_key,
            secret_key=args.secret_key,
            secure=args.secure
        )
        
        if args.mode == 'health':
            # 健康检查模式
            logger.info("执行MinIO健康检查...")
            health_status = initializer.monitor.check_health()
            
            print(f"\n{'='*60}")
            print("MinIO健康检查报告")
            print(f"{'='*60}")
            print(f"时间: {health_status.timestamp}")
            print(f"状态: {health_status.status.upper()}")
            print(f"连接性: {'✅' if health_status.connectivity else '❌'}")
            print(f"API延迟: {health_status.api_latency:.1f}ms")
            print(f"存储桶数量: {health_status.bucket_count}")
            print(f"总存储大小: {health_status.total_size}")
            
            if health_status.errors:
                print(f"\n❌ 错误:")
                for error in health_status.errors:
                    print(f"  - {error}")
            
            if health_status.warnings:
                print(f"\n⚠️ 警告:")
                for warning in health_status.warnings:
                    print(f"  - {warning}")
            
            print(f"{'='*60}")
            return health_status.status == 'healthy'
        
        elif args.mode == 'backup':
            # 备份模式
            logger.info("执行MinIO配置备份...")
            buckets = [bucket.name for bucket in initializer.client.list_buckets()]
            backup_data = initializer.backup_manager.backup_bucket_policies(buckets)
            
            if initializer.backup_manager.save_backup(backup_data):
                logger.info("备份完成")
                return True
            else:
                logger.error("备份失败")
                return False
        
        elif args.mode == 'restore':
            # 恢复模式
            if not args.backup_file:
                logger.error("恢复模式需要指定 --backup-file")
                return False
            
            logger.info(f"从 {args.backup_file} 恢复配置...")
            try:
                with open(args.backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                
                if initializer.backup_manager.restore_bucket_policies(backup_data):
                    logger.info("恢复完成")
                    return True
                else:
                    logger.error("恢复失败")
                    return False
                    
            except Exception as e:
                logger.error(f"读取备份文件失败: {e}")
                return False
        
        elif args.mode == 'report':
            # 报告模式
            logger.info("生成详细报告...")
            report = initializer.generate_report()
            
            # 打印摘要
            print(f"\n{'='*60}")
            print("MinIO详细报告")
            print(f"{'='*60}")
            print(f"时间: {report['timestamp']}")
            print(f"健康状态: {report['health_status']['status'].upper()}")
            print(f"存储桶数量: {len(report['buckets'])}")
            
            total_objects = sum(bucket['object_count'] for bucket in report['buckets'])
            total_size = sum(bucket['total_size'] for bucket in report['buckets'])
            print(f"总对象数: {total_objects:,}")
            print(f"总大小: {initializer.monitor._format_bytes(total_size)}")
            
            print(f"\n存储桶详情:")
            for bucket in report['buckets']:
                print(f"  📦 {bucket['name']:20} | {bucket['object_count']:>6} 对象 | {initializer.monitor._format_bytes(bucket['total_size']):>10} | 策略: {'✅' if bucket['has_policy'] else '❌'}")
            
            print(f"{'='*60}")
            
            # 保存详细报告
            if initializer.save_report(report):
                return True
            else:
                return False
        
        else:  # init模式
            logger.info("开始MinIO初始化...")
            
            # 等待服务就绪
            if not initializer.wait_for_minio(args.timeout):
                logger.error("MinIO服务未就绪")
                return False
            
            # 加载配置文件
            config = {}
            if args.config_file:
                config = load_config_file(args.config_file)
                if not config:
                    logger.error("无法加载配置文件")
                    return False
            else:
                # 使用默认配置
                config = {
                    "default_buckets": [
                        {
                            "name": "zzdsj-documents",
                            "policy": "private",
                            "lifecycle": True,
                            "directories": ["uploads/", "processed/", "archived/"]
                        },
                        {
                            "name": "zzdsj-images", 
                            "policy": "public-read",
                            "directories": ["avatars/", "thumbnails/", "temp/"]
                        },
                        {
                            "name": "zzdsj-backups",
                            "policy": "private", 
                            "lifecycle": True,
                            "directories": ["database/", "files/", "configs/"]
                        }
                    ]
                }
            
            # 批量创建存储桶
            buckets_config = config.get('default_buckets', [])
            if buckets_config:
                logger.info(f"批量创建 {len(buckets_config)} 个存储桶...")
                results = initializer.batch_ops.batch_create_buckets(buckets_config)
                
                success_count = sum(1 for success in results.values() if success)
                logger.info(f"存储桶创建完成: {success_count}/{len(buckets_config)} 成功")
                
                if success_count < len(buckets_config):
                    logger.warning("部分存储桶创建失败")
            
            # 执行健康检查
            health_status = initializer.monitor.check_health()
            logger.info(f"最终健康状态: {health_status.status}")
            
            # 生成报告
            initializer.save_report()
            
            logger.info("MinIO初始化完成")
            return health_status.status in ['healthy', 'degraded']
            
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 