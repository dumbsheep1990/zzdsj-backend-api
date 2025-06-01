#!/usr/bin/env python3
"""
Storage模块重构验证脚本
测试新架构的功能和向后兼容性
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_core_components():
    """测试核心组件"""
    print("🧪 测试Storage核心组件...")
    
    try:
        from app.utils.storage.core import StorageComponent, StorageConfig, create_config_from_settings
        
        # 测试配置
        config = StorageConfig()
        assert config.vector_store_type == "milvus"
        assert config.object_store_type == "minio"
        
        print("✅ 核心组件测试通过")
        return True
    except Exception as e:
        print(f"❌ 核心组件测试失败: {e}")
        return False


async def test_vector_storage():
    """测试向量存储"""
    print("🧪 测试Vector Storage...")
    
    try:
        from app.utils.storage.vector_storage import VectorStore, get_vector_store
        
        # 创建向量存储实例
        config = {
            "vector_store_type": "milvus",
            "vector_store_host": "localhost",
            "vector_store_port": 19530
        }
        
        vector_store = VectorStore("test", config)
        assert vector_store.name == "test"
        assert not vector_store.is_initialized()
        
        # 测试全局实例
        global_store = get_vector_store()
        assert global_store is not None
        
        print("✅ Vector Storage测试通过")
        return True
    except Exception as e:
        print(f"❌ Vector Storage测试失败: {e}")
        return False


async def test_object_storage():
    """测试对象存储"""
    print("🧪 测试Object Storage...")
    
    try:
        from app.utils.storage.object_storage import ObjectStore, get_object_store
        
        # 创建对象存储实例
        config = {
            "object_store_type": "minio",
            "object_store_endpoint": "localhost:9000"
        }
        
        object_store = ObjectStore("test", config)
        assert object_store.name == "test"
        assert not object_store.is_initialized()
        
        # 测试全局实例
        global_store = get_object_store()
        assert global_store is not None
        
        print("✅ Object Storage测试通过")
        return True
    except Exception as e:
        print(f"❌ Object Storage测试失败: {e}")
        return False


async def test_storage_detection():
    """测试存储检测"""
    print("🧪 测试Storage Detection...")
    
    try:
        from app.utils.storage.detection import StorageDetector, detect_storage_type
        
        # 创建检测器实例
        detector = StorageDetector("test")
        await detector.initialize()
        
        assert detector.is_initialized()
        
        print("✅ Storage Detection测试通过")
        return True
    except Exception as e:
        print(f"❌ Storage Detection测试失败: {e}")
        return False


async def test_backward_compatibility():
    """测试向后兼容性"""
    print("🧪 测试向后兼容性...")
    
    try:
        # 测试向量存储向后兼容
        from app.utils.storage.vector_storage.legacy_support import init_milvus, get_collection
        
        # 测试对象存储向后兼容
        from app.utils.storage.object_storage.legacy_support import get_minio_client, upload_file
        
        # 测试存储检测向后兼容
        from app.utils.storage.detection.legacy_support import check_milvus, check_elasticsearch
        
        print("✅ 向后兼容性测试通过")
        return True
    except Exception as e:
        print(f"❌ 向后兼容性测试失败: {e}")
        return False


async def test_main_storage_imports():
    """测试主Storage模块导入"""
    print("🧪 测试主Storage模块导入...")
    
    try:
        # 测试新接口导入
        from app.utils.storage import (
            StorageComponent, VectorStore, ObjectStore, StorageDetector
        )
        
        # 测试向后兼容接口导入
        from app.utils.storage import (
            init_milvus, get_minio_client, check_milvus, check_elasticsearch
        )
        
        print("✅ 主Storage模块导入测试通过")
        return True
    except Exception as e:
        print(f"❌ 主Storage模块导入测试失败: {e}")
        return False


async def run_all_tests():
    """运行所有测试"""
    print("🚀 开始Storage模块重构验证测试...")
    print("=" * 50)
    
    tests = [
        test_core_components,
        test_vector_storage,
        test_object_storage,
        test_storage_detection,
        test_backward_compatibility,
        test_main_storage_imports
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ 测试执行异常: {e}")
            failed += 1
        
        print()  # 添加空行分隔
    
    print("=" * 50)
    print(f"📊 测试结果: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("🎉 所有测试通过！Storage模块重构成功完成。")
    else:
        print("⚠️  部分测试失败，请检查相关模块。")
    
    return failed == 0


def main():
    """主函数"""
    # 运行异步测试
    result = asyncio.run(run_all_tests())
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main() 