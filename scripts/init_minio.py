#!/usr/bin/env python3
"""
MinIO对象存储初始化脚本
配置MinIO作为用户端文件上传的默认存储引擎
确保存储桶、访问策略等配置正确
"""

import json
import sys
import time
import logging
from typing import Dict, Any, Optional
from minio import Minio
from minio.error import S3Error, ResponseError
import urllib3

# 禁用SSL警告（开发环境）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    
    def create_default_directories(self, bucket_name: str) -> bool:
        """创建默认目录结构"""
        try:
            default_dirs = [
                "documents/",
                "images/", 
                "videos/",
                "audios/",
                "temp/",
                "processed/",
                "backups/"
            ]
            
            # 创建空对象作为目录占位符
            for dir_path in default_dirs:
                self.client.put_object(
                    bucket_name,
                    dir_path + ".keep",
                    data=b"# This file maintains the directory structure",
                    length=len(b"# This file maintains the directory structure"),
                    content_type="text/plain"
                )
            
            logger.info(f"成功创建默认目录结构: {', '.join(default_dirs)}")
            return True
            
        except Exception as e:
            logger.error(f"创建目录结构失败: {e}")
            return False
    
    def test_file_operations(self, bucket_name: str) -> bool:
        """测试文件操作"""
        test_file_name = "test/connectivity-test.txt"
        test_content = f"MinIO连接测试 - {time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        try:
            # 测试上传
            self.client.put_object(
                bucket_name,
                test_file_name,
                data=test_content.encode('utf-8'),
                length=len(test_content.encode('utf-8')),
                content_type="text/plain"
            )
            logger.info("文件上传测试成功")
            
            # 测试下载
            response = self.client.get_object(bucket_name, test_file_name)
            downloaded_content = response.read().decode('utf-8')
            response.close()
            response.release_conn()
            
            if downloaded_content == test_content:
                logger.info("文件下载测试成功")
            else:
                logger.error("文件下载内容不匹配")
                return False
            
            # 测试删除
            self.client.remove_object(bucket_name, test_file_name)
            logger.info("文件删除测试成功")
            
            return True
            
        except Exception as e:
            logger.error(f"文件操作测试失败: {e}")
            return False
    
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        try:
            buckets = list(self.client.list_buckets())
            
            info = {
                "endpoint": self.endpoint,
                "secure": self.secure,
                "total_buckets": len(buckets),
                "buckets": []
            }
            
            for bucket in buckets:
                bucket_info = {
                    "name": bucket.name,
                    "creation_date": bucket.creation_date.isoformat() if bucket.creation_date else None
                }
                
                # 尝试获取存储桶中的对象数量（限制为前1000个）
                try:
                    objects = list(self.client.list_objects(bucket.name, max_keys=1000))
                    bucket_info["object_count"] = len(objects)
                    bucket_info["total_size"] = sum(obj.size for obj in objects if obj.size)
                except:
                    bucket_info["object_count"] = "unknown"
                    bucket_info["total_size"] = "unknown"
                
                info["buckets"].append(bucket_info)
            
            return info
            
        except Exception as e:
            logger.error(f"获取存储信息失败: {e}")
            return {"error": str(e)}
    
    def initialize_all(self, config: Dict[str, Any]) -> bool:
        """执行完整初始化"""
        logger.info("开始初始化MinIO对象存储...")
        
        success_steps = 0
        total_steps = 6
        
        # 1. 等待MinIO就绪
        if self.wait_for_minio():
            success_steps += 1
        else:
            return False
        
        # 2. 创建默认存储桶
        bucket_name = config.get("bucket_name", "knowledge-docs")
        if self.create_bucket(bucket_name):
            success_steps += 1
        
        # 3. 设置访问策略
        policy_type = config.get("policy_type", "private")
        if self.set_bucket_policy(bucket_name, policy_type):
            success_steps += 1
        
        # 4. 设置生命周期规则
        if self.setup_lifecycle_rules(bucket_name):
            success_steps += 1
        
        # 5. 创建目录结构
        if self.create_default_directories(bucket_name):
            success_steps += 1
        
        # 6. 测试文件操作
        if self.test_file_operations(bucket_name):
            success_steps += 1
        
        success = success_steps == total_steps
        
        if success:
            logger.info("✅ MinIO对象存储初始化完成")
            logger.info("MinIO已配置为默认文件上传存储引擎")
            
            # 显示存储信息
            storage_info = self.get_storage_info()
            if "error" not in storage_info:
                logger.info(f"存储桶总数: {storage_info['total_buckets']}")
                for bucket in storage_info['buckets']:
                    logger.info(f"  - {bucket['name']}: {bucket['object_count']} 个对象")
        else:
            logger.error(f"❌ 初始化部分失败 ({success_steps}/{total_steps})")
        
        return success


def main():
    """主函数"""
    import os
    
    # 从环境变量获取配置
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
    bucket_name = os.getenv("MINIO_BUCKET", "knowledge-docs")
    
    # 配置参数
    config = {
        "bucket_name": bucket_name,
        "policy_type": "private",  # 文档存储应该是私有的
        "region": "us-east-1"
    }
    
    try:
        initializer = MinIOInitializer(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        
        success = initializer.initialize_all(config)
        
        if success:
            print("\n🎉 MinIO对象存储配置成功!")
            print("📋 已完成的配置:")
            print("   ✓ 存储桶创建")
            print("   ✓ 访问策略设置")
            print("   ✓ 生命周期规则")
            print("   ✓ 目录结构创建")
            print("   ✓ 文件操作测试")
            print("\n💡 MinIO现在可以作为默认文件上传存储引擎使用")
            print(f"   📁 存储桶: {bucket_name}")
            print(f"   🔗 端点: {endpoint}")
            print(f"   🔒 安全模式: {'启用' if secure else '关闭'}")
            sys.exit(0)
        else:
            print("\n❌ 配置过程中出现错误，请检查日志")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 