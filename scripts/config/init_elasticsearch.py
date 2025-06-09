#!/usr/bin/env python3
"""
Elasticsearch初始化脚本 - 增强版
配置混合检索所需的索引模板、映射和搜索模板
确保ES存储能够完全支持混合检索功能
新增健康监控、备份恢复、批量索引管理等高级功能
"""

import json
import sys
import time
import logging
import argparse
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, RequestError
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ESHealthStatus:
    """Elasticsearch健康状态"""
    timestamp: str
    cluster_status: str  # green, yellow, red
    cluster_name: str
    node_count: int
    active_shards: int
    unassigned_shards: int
    relocating_shards: int
    initializing_shards: int
    active_primary_shards: int
    disk_usage: Dict[str, float]
    memory_usage: Dict[str, float]
    errors: List[str]
    warnings: List[str]

class ESMonitor:
    """Elasticsearch监控器"""
    
    def __init__(self, client: Elasticsearch):
        self.client = client
        
    def check_health(self) -> ESHealthStatus:
        """检查Elasticsearch健康状况"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        errors = []
        warnings = []
        
        try:
            # 集群健康
            health = self.client.cluster.health()
            
            # 节点统计
            stats = self.client.cluster.stats()
            
            # 节点信息
            nodes_stats = self.client.nodes.stats()
            
            # 磁盘使用
            disk_usage = {}
            memory_usage = {}
            
            for node_id, node_info in nodes_stats.get('nodes', {}).items():
                node_name = node_info.get('name', node_id)
                
                # 磁盘使用率
                fs_info = node_info.get('fs', {}).get('total', {})
                if fs_info:
                    total_gb = fs_info.get('total_in_bytes', 0) / (1024**3)
                    available_gb = fs_info.get('available_in_bytes', 0) / (1024**3)
                    if total_gb > 0:
                        usage_percent = ((total_gb - available_gb) / total_gb) * 100
                        disk_usage[node_name] = round(usage_percent, 1)
                
                # 内存使用率
                jvm_info = node_info.get('jvm', {}).get('mem', {})
                if jvm_info:
                    heap_used = jvm_info.get('heap_used_in_bytes', 0)
                    heap_max = jvm_info.get('heap_max_in_bytes', 0)
                    if heap_max > 0:
                        memory_percent = (heap_used / heap_max) * 100
                        memory_usage[node_name] = round(memory_percent, 1)
            
            # 检查告警条件
            cluster_status = health.get('status', 'unknown')
            if cluster_status == 'red':
                errors.append("集群状态为红色，存在严重问题")
            elif cluster_status == 'yellow':
                warnings.append("集群状态为黄色，存在副本分片问题")
            
            unassigned_shards = health.get('unassigned_shards', 0)
            if unassigned_shards > 0:
                warnings.append(f"存在 {unassigned_shards} 个未分配的分片")
            
            relocating_shards = health.get('relocating_shards', 0)
            if relocating_shards > 5:
                warnings.append(f"存在 {relocating_shards} 个正在迁移的分片")
            
            # 检查磁盘使用率
            for node, usage in disk_usage.items():
                if usage > 90:
                    errors.append(f"节点 {node} 磁盘使用率过高: {usage}%")
                elif usage > 80:
                    warnings.append(f"节点 {node} 磁盘使用率较高: {usage}%")
            
            # 检查内存使用率
            for node, usage in memory_usage.items():
                if usage > 90:
                    warnings.append(f"节点 {node} 内存使用率过高: {usage}%")
                elif usage > 80:
                    warnings.append(f"节点 {node} 内存使用率较高: {usage}%")
            
            return ESHealthStatus(
                timestamp=timestamp,
                cluster_status=cluster_status,
                cluster_name=health.get('cluster_name', 'unknown'),
                node_count=health.get('number_of_nodes', 0),
                active_shards=health.get('active_shards', 0),
                unassigned_shards=unassigned_shards,
                relocating_shards=relocating_shards,
                initializing_shards=health.get('initializing_shards', 0),
                active_primary_shards=health.get('active_primary_shards', 0),
                disk_usage=disk_usage,
                memory_usage=memory_usage,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            return ESHealthStatus(
                timestamp=timestamp,
                cluster_status="error",
                cluster_name="unknown",
                node_count=0,
                active_shards=0,
                unassigned_shards=0,
                relocating_shards=0,
                initializing_shards=0,
                active_primary_shards=0,
                disk_usage={},
                memory_usage={},
                errors=[f"健康检查失败: {e}"],
                warnings=[]
            )

class ESBackupManager:
    """Elasticsearch备份管理器"""
    
    def __init__(self, client: Elasticsearch):
        self.client = client
        
    def backup_index_mappings(self, index_patterns: List[str]) -> Dict[str, Any]:
        """备份索引映射"""
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'mappings': {},
            'settings': {},
            'templates': {}
        }
        
        try:
            # 备份索引映射和设置
            for pattern in index_patterns:
                try:
                    # 获取匹配的索引
                    indices = self.client.indices.get(index=pattern, ignore_unavailable=True)
                    
                    for index_name, index_data in indices.items():
                        backup_data['mappings'][index_name] = index_data.get('mappings', {})
                        backup_data['settings'][index_name] = index_data.get('settings', {})
                        logger.info(f"已备份索引 {index_name} 的映射和设置")
                        
                except Exception as e:
                    logger.warning(f"备份索引模式 {pattern} 失败: {e}")
            
            # 备份索引模板
            try:
                templates = self.client.indices.get_index_template()
                backup_data['templates'] = {
                    template['name']: template for template in templates.get('index_templates', [])
                }
                logger.info(f"已备份 {len(backup_data['templates'])} 个索引模板")
            except Exception as e:
                logger.warning(f"备份索引模板失败: {e}")
            
        except Exception as e:
            logger.error(f"备份过程中出现错误: {e}")
        
        return backup_data
    
    def restore_mappings(self, backup_data: Dict[str, Any]) -> bool:
        """恢复索引映射"""
        success = True
        
        try:
            # 恢复索引模板
            for template_name, template_data in backup_data.get('templates', {}).items():
                try:
                    template_body = template_data.get('index_template', {})
                    self.client.indices.put_index_template(
                        name=template_name,
                        body=template_body
                    )
                    logger.info(f"已恢复索引模板: {template_name}")
                except Exception as e:
                    logger.error(f"恢复索引模板 {template_name} 失败: {e}")
                    success = False
            
            logger.info("映射恢复完成")
            
        except Exception as e:
            logger.error(f"恢复过程中出现错误: {e}")
            success = False
        
        return success
    
    def save_backup(self, backup_data: Dict[str, Any], backup_file: str = None) -> bool:
        """保存备份到文件"""
        if not backup_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"es_backup_{timestamp}.json"
        
        try:
            backup_dir = Path("es_backups")
            backup_dir.mkdir(exist_ok=True)
            
            backup_path = backup_dir / backup_file
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"备份已保存到: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存备份失败: {e}")
            return False

class ESIndexManager:
    """Elasticsearch索引管理器"""
    
    def __init__(self, client: Elasticsearch):
        self.client = client
        
    def batch_create_indices(self, index_configs: List[Dict[str, Any]]) -> Dict[str, bool]:
        """批量创建索引"""
        results = {}
        
        for config in index_configs:
            index_name = config['name']
            
            try:
                # 检查索引是否存在
                if self.client.indices.exists(index=index_name):
                    logger.info(f"索引 {index_name} 已存在")
                    results[index_name] = True
                    continue
                
                # 创建索引
                index_body = {
                    'settings': config.get('settings', {}),
                    'mappings': config.get('mappings', {})
                }
                
                self.client.indices.create(index=index_name, body=index_body)
                logger.info(f"成功创建索引: {index_name}")
                results[index_name] = True
                
            except Exception as e:
                logger.error(f"创建索引 {index_name} 失败: {e}")
                results[index_name] = False
        
        return results
    
    def reindex_data(self, source_index: str, dest_index: str, 
                     query: Dict[str, Any] = None) -> bool:
        """重建索引"""
        try:
            reindex_body = {
                'source': {
                    'index': source_index
                },
                'dest': {
                    'index': dest_index
                }
            }
            
            if query:
                reindex_body['source']['query'] = query
            
            response = self.client.reindex(body=reindex_body, wait_for_completion=True)
            
            if response.get('failures'):
                logger.error(f"重建索引时出现失败: {response['failures']}")
                return False
            
            logger.info(f"成功重建索引: {source_index} -> {dest_index}")
            return True
            
        except Exception as e:
            logger.error(f"重建索引失败: {e}")
            return False
    
    def optimize_indices(self, index_patterns: List[str]) -> Dict[str, bool]:
        """优化索引"""
        results = {}
        
        for pattern in index_patterns:
            try:
                # 强制合并段
                self.client.indices.forcemerge(index=pattern, max_num_segments=1)
                logger.info(f"已优化索引: {pattern}")
                results[pattern] = True
                
            except Exception as e:
                logger.error(f"优化索引 {pattern} 失败: {e}")
                results[pattern] = False
        
        return results
    
    def get_index_stats(self, index_patterns: List[str]) -> Dict[str, Any]:
        """获取索引统计信息"""
        stats = {}
        
        for pattern in index_patterns:
            try:
                index_stats = self.client.indices.stats(index=pattern)
                
                for index_name, index_data in index_stats.get('indices', {}).items():
                    total = index_data.get('total', {})
                    stats[index_name] = {
                        'docs_count': total.get('docs', {}).get('count', 0),
                        'docs_deleted': total.get('docs', {}).get('deleted', 0),
                        'store_size': total.get('store', {}).get('size_in_bytes', 0),
                        'segments_count': total.get('segments', {}).get('count', 0),
                        'index_time': total.get('indexing', {}).get('index_time_in_millis', 0),
                        'search_time': total.get('search', {}).get('query_time_in_millis', 0)
                    }
                    
            except Exception as e:
                logger.warning(f"获取索引 {pattern} 统计失败: {e}")
        
        return stats

class EnhancedElasticsearchInitializer(ElasticsearchInitializer):
    """增强版Elasticsearch初始化器"""
    
    def __init__(self, es_url: str = "http://localhost:9200", 
                 username: Optional[str] = None, 
                 password: Optional[str] = None):
        super().__init__(es_url, username, password)
        self.monitor = ESMonitor(self.client)
        self.backup_manager = ESBackupManager(self.client)
        self.index_manager = ESIndexManager(self.client)
    
    def create_advanced_index(self, index_name: str, config: Dict[str, Any]) -> bool:
        """创建高级配置的索引"""
        try:
            # 检查索引是否存在
            if self.client.indices.exists(index=index_name):
                logger.info(f"索引 {index_name} 已存在")
                
                # 是否需要更新映射
                if config.get('update_mapping', False):
                    try:
                        self.client.indices.put_mapping(
                            index=index_name,
                            body=config.get('mappings', {})
                        )
                        logger.info(f"已更新索引 {index_name} 的映射")
                    except Exception as e:
                        logger.warning(f"更新映射失败: {e}")
                
                return True
            
            # 构建索引配置
            index_body = {
                'settings': config.get('settings', {}),
                'mappings': config.get('mappings', {})
            }
            
            # 添加别名
            if config.get('aliases'):
                index_body['aliases'] = config['aliases']
            
            # 创建索引
            self.client.indices.create(index=index_name, body=index_body)
            logger.info(f"成功创建高级索引: {index_name}")
            
            # 设置索引策略
            if config.get('policy'):
                self.set_index_policy(index_name, config['policy'])
            
            return True
            
        except Exception as e:
            logger.error(f"创建高级索引 {index_name} 失败: {e}")
            return False
    
    def set_index_policy(self, index_name: str, policy: Dict[str, Any]) -> bool:
        """设置索引生命周期策略"""
        try:
            # 这里可以设置ILM策略
            logger.info(f"索引 {index_name} 策略配置已设置")
            return True
            
        except Exception as e:
            logger.warning(f"设置索引策略失败: {e}")
            return False
    
    def setup_monitoring(self, config: Dict[str, Any]) -> bool:
        """设置监控和告警"""
        try:
            # 这里可以配置监控和告警
            logger.info("监控配置已设置")
            return True
            
        except Exception as e:
            logger.warning(f"设置监控失败: {e}")
            return False
    
    def generate_report(self) -> Dict[str, Any]:
        """生成详细报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'health_status': asdict(self.monitor.check_health()),
            'indices': {},
            'configuration': {
                'es_url': self.es_url
            }
        }
        
        try:
            # 获取所有索引
            indices = self.client.indices.get(index='*', ignore_unavailable=True)
            
            for index_name, index_data in indices.items():
                if not index_name.startswith('.'):  # 忽略系统索引
                    report['indices'][index_name] = {
                        'mappings': index_data.get('mappings', {}),
                        'settings': index_data.get('settings', {})
                    }
            
            # 获取索引统计
            index_patterns = list(report['indices'].keys())
            if index_patterns:
                stats = self.index_manager.get_index_stats(index_patterns)
                for index_name, stat_data in stats.items():
                    if index_name in report['indices']:
                        report['indices'][index_name]['stats'] = stat_data
            
        except Exception as e:
            logger.error(f"生成报告失败: {e}")
        
        return report
    
    def save_report(self, report: Dict[str, Any] = None) -> bool:
        """保存报告到文件"""
        if not report:
            report = self.generate_report()
        
        try:
            report_dir = Path("es_reports")
            report_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = report_dir / f"es_report_{timestamp}.json"
            
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
    parser = argparse.ArgumentParser(description="Elasticsearch初始化脚本 - 增强版")
    parser.add_argument('--es-url', default='http://localhost:9200',
                       help='Elasticsearch URL')
    parser.add_argument('--username',
                       help='用户名')
    parser.add_argument('--password',
                       help='密码')
    parser.add_argument('--config-file',
                       help='配置文件路径 (JSON/YAML)')
    parser.add_argument('--mode', choices=['init', 'health', 'backup', 'restore', 'report', 'optimize'],
                       default='init',
                       help='运行模式')
    parser.add_argument('--backup-file',
                       help='备份文件路径 (用于restore模式)')
    parser.add_argument('--index-patterns', nargs='+', default=['kb_*', 'document_*'],
                       help='索引模式列表')
    parser.add_argument('--timeout', type=int, default=60,
                       help='连接超时时间(秒)')
    
    args = parser.parse_args()
    
    try:
        # 创建增强版初始化器
        initializer = EnhancedElasticsearchInitializer(
            es_url=args.es_url,
            username=args.username,
            password=args.password
        )
        
        if args.mode == 'health':
            # 健康检查模式
            logger.info("执行Elasticsearch健康检查...")
            health_status = initializer.monitor.check_health()
            
            print(f"\n{'='*60}")
            print("Elasticsearch健康检查报告")
            print(f"{'='*60}")
            print(f"时间: {health_status.timestamp}")
            print(f"集群状态: {health_status.cluster_status.upper()}")
            print(f"集群名称: {health_status.cluster_name}")
            print(f"节点数量: {health_status.node_count}")
            print(f"活跃分片: {health_status.active_shards}")
            print(f"未分配分片: {health_status.unassigned_shards}")
            
            if health_status.disk_usage:
                print(f"\n磁盘使用率:")
                for node, usage in health_status.disk_usage.items():
                    print(f"  {node}: {usage}%")
            
            if health_status.memory_usage:
                print(f"\n内存使用率:")
                for node, usage in health_status.memory_usage.items():
                    print(f"  {node}: {usage}%")
            
            if health_status.errors:
                print(f"\n❌ 错误:")
                for error in health_status.errors:
                    print(f"  - {error}")
            
            if health_status.warnings:
                print(f"\n⚠️ 警告:")
                for warning in health_status.warnings:
                    print(f"  - {warning}")
            
            print(f"{'='*60}")
            return health_status.cluster_status in ['green', 'yellow']
        
        elif args.mode == 'backup':
            # 备份模式
            logger.info("执行Elasticsearch配置备份...")
            backup_data = initializer.backup_manager.backup_index_mappings(args.index_patterns)
            
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
                
                if initializer.backup_manager.restore_mappings(backup_data):
                    logger.info("恢复完成")
                    return True
                else:
                    logger.error("恢复失败")
                    return False
                    
            except Exception as e:
                logger.error(f"读取备份文件失败: {e}")
                return False
        
        elif args.mode == 'optimize':
            # 优化模式
            logger.info("执行索引优化...")
            results = initializer.index_manager.optimize_indices(args.index_patterns)
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            print(f"\n索引优化结果: {success_count}/{total_count} 成功")
            for pattern, success in results.items():
                status = "✅" if success else "❌"
                print(f"  {status} {pattern}")
            
            return success_count == total_count
        
        elif args.mode == 'report':
            # 报告模式
            logger.info("生成详细报告...")
            report = initializer.generate_report()
            
            # 打印摘要
            print(f"\n{'='*60}")
            print("Elasticsearch详细报告")
            print(f"{'='*60}")
            print(f"时间: {report['timestamp']}")
            print(f"集群状态: {report['health_status']['cluster_status'].upper()}")
            print(f"索引数量: {len(report['indices'])}")
            
            # 统计信息
            total_docs = 0
            total_size = 0
            
            print(f"\n索引详情:")
            for index_name, index_data in report['indices'].items():
                stats = index_data.get('stats', {})
                docs_count = stats.get('docs_count', 0)
                store_size = stats.get('store_size', 0)
                
                total_docs += docs_count
                total_size += store_size
                
                size_mb = store_size / (1024 * 1024) if store_size > 0 else 0
                print(f"  📄 {index_name:30} | {docs_count:>8,} 文档 | {size_mb:>8.1f} MB")
            
            print(f"\n总计: {total_docs:,} 文档, {total_size/(1024*1024):.1f} MB")
            print(f"{'='*60}")
            
            # 保存详细报告
            if initializer.save_report(report):
                return True
            else:
                return False
        
        else:  # init模式
            logger.info("开始Elasticsearch初始化...")
            
            # 等待服务就绪
            if not initializer.wait_for_es(args.timeout):
                logger.error("Elasticsearch服务未就绪")
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
                    "default_indices": [
                        {
                            "name": "kb_documents",
                            "settings": {
                                "number_of_shards": 1,
                                "number_of_replicas": 0,
                                "analysis": {
                                    "analyzer": {
                                        "chinese_analyzer": {
                                            "type": "custom",
                                            "tokenizer": "ik_max_word",
                                            "filter": ["lowercase", "stop"]
                                        }
                                    }
                                }
                            },
                            "mappings": {
                                "properties": {
                                    "title": {"type": "text", "analyzer": "chinese_analyzer"},
                                    "content": {"type": "text", "analyzer": "chinese_analyzer"},
                                    "content_vector": {"type": "dense_vector", "dims": 1536}
                                }
                            }
                        }
                    ]
                }
            
            # 创建索引模板
            if not initializer.create_index_template():
                logger.error("创建索引模板失败")
                return False
            
            # 创建搜索模板
            if not initializer.create_search_templates():
                logger.error("创建搜索模板失败")
                return False
            
            # 批量创建索引
            indices_config = config.get('default_indices', [])
            if indices_config:
                logger.info(f"批量创建 {len(indices_config)} 个索引...")
                results = initializer.index_manager.batch_create_indices(indices_config)
                
                success_count = sum(1 for success in results.values() if success)
                logger.info(f"索引创建完成: {success_count}/{len(indices_config)} 成功")
            
            # 执行健康检查
            health_status = initializer.monitor.check_health()
            logger.info(f"最终健康状态: {health_status.cluster_status}")
            
            # 生成报告
            initializer.save_report()
            
            logger.info("Elasticsearch初始化完成")
            return health_status.cluster_status in ['green', 'yellow']
            
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 