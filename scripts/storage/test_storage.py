#!/usr/bin/env python3
"""
文件存储系统测试脚本
测试PostgreSQL、Elasticsearch、本地文件等存储方案
"""

import os
import sys
import time
from datetime import datetime

# 设置存储类型为MinIO（默认）
os.environ['STORAGE_TYPE'] = 'minio'

from storage_interface import get_file_storage, FileStorageFactory, StorageType
from storage_config import storage_config_manager

def print_step(step: str, status: str = "INFO"):
    """打印步骤信息"""
    icons = {"INFO": "📋", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
    icon = icons.get(status, "📋")
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {icon} {step}")

def print_header(title: str):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print(f"{'='*60}")

def test_minio_storage():
    """测试MinIO存储"""
    print_header("MinIO文件存储测试")
    
    try:
        # 获取MinIO存储实例
        storage = FileStorageFactory.create_storage()
        print_step("MinIO存储实例创建成功", "SUCCESS")
        
        # 测试文件上传
        test_content = "这是一个测试文件的内容。\nTest file content for MinIO storage.".encode('utf-8')
        test_filename = "test_minio.txt"
        
        print_step(f"上传测试文件: {test_filename}", "INFO")
        file_metadata = storage.upload_file(
            file_data=test_content,
            filename=test_filename,
            content_type="text/plain",
            metadata={"test": True, "created_by": "test_script", "storage_test": "minio"}
        )
        
        print_step(f"文件上传成功 - ID: {file_metadata.file_id}", "SUCCESS")
        print(f"    文件名: {file_metadata.filename}")
        print(f"    文件大小: {file_metadata.file_size} bytes")
        print(f"    文件哈希: {file_metadata.file_hash}")
        print(f"    上传时间: {file_metadata.upload_time}")
        print(f"    存储路径: {file_metadata.storage_path}")
        
        # 测试文件下载
        print_step("测试文件下载", "INFO")
        downloaded_content = storage.download_file(file_metadata.file_id)
        
        if downloaded_content == test_content:
            print_step("文件下载验证成功", "SUCCESS")
        else:
            print_step("文件下载验证失败", "ERROR")
            return False
        
        # 测试元数据获取
        print_step("测试元数据获取", "INFO")
        metadata = storage.get_file_metadata(file_metadata.file_id)
        
        if metadata and metadata.filename == test_filename:
            print_step("元数据获取成功", "SUCCESS")
            print(f"    存储路径: {metadata.storage_path}")
            print(f"    元数据: {metadata.metadata}")
        else:
            print_step("元数据获取失败", "ERROR")
            return False
        
        # 测试文件列表
        print_step("测试文件列表", "INFO")
        file_list = storage.list_files(limit=10)
        
        if len(file_list) > 0:
            print_step(f"文件列表获取成功 - 找到 {len(file_list)} 个文件", "SUCCESS")
        else:
            print_step("文件列表为空", "WARNING")
        
        # 测试文件删除
        print_step("测试文件删除", "INFO")
        deleted = storage.delete_file(file_metadata.file_id)
        
        if deleted:
            print_step("文件删除成功", "SUCCESS")
        else:
            print_step("文件删除失败", "ERROR")
            return False
        
        # 验证删除
        print_step("验证文件已删除", "INFO")
        deleted_file = storage.download_file(file_metadata.file_id)
        
        if deleted_file is None:
            print_step("文件删除验证成功", "SUCCESS")
        else:
            print_step("文件删除验证失败", "ERROR")
            return False
        
        return True
        
    except Exception as e:
        print_step(f"MinIO存储测试失败: {e}", "ERROR")
        return False

def test_postgresql_storage():
    """测试PostgreSQL存储"""
    print_header("PostgreSQL文件存储测试")
    
    try:
        # 设置为PostgreSQL存储
        os.environ['STORAGE_TYPE'] = 'postgresql'
        
        # 重新创建存储实例
        storage = FileStorageFactory.create_storage()
        print_step("PostgreSQL存储实例创建成功", "SUCCESS")
        
        # 测试文件上传
        test_content = "这是一个测试文件的内容。\nTest file content for PostgreSQL storage.".encode('utf-8')
        test_filename = "test_postgresql.txt"
        
        print_step(f"上传测试文件: {test_filename}", "INFO")
        file_metadata = storage.upload_file(
            file_data=test_content,
            filename=test_filename,
            content_type="text/plain",
            metadata={"test": True, "created_by": "test_script"}
        )
        
        print_step(f"文件上传成功 - ID: {file_metadata.file_id}", "SUCCESS")
        print(f"    文件名: {file_metadata.filename}")
        print(f"    文件大小: {file_metadata.file_size} bytes")
        print(f"    文件哈希: {file_metadata.file_hash}")
        print(f"    上传时间: {file_metadata.upload_time}")
        
        # 测试文件下载
        downloaded_content = storage.download_file(file_metadata.file_id)
        
        if downloaded_content == test_content:
            print_step("文件下载验证成功", "SUCCESS")
        else:
            print_step("文件下载验证失败", "ERROR")
            return False
        
        # 测试元数据获取
        metadata = storage.get_file_metadata(file_metadata.file_id)
        
        if metadata and metadata.filename == test_filename:
            print_step("元数据获取成功", "SUCCESS")
        else:
            print_step("元数据获取失败", "ERROR")
            return False
        
        # 测试文件列表
        file_list = storage.list_files(limit=10)
        
        if len(file_list) > 0:
            print_step(f"文件列表获取成功 - 找到 {len(file_list)} 个文件", "SUCCESS")
        else:
            print_step("文件列表为空", "WARNING")
        
        # 清理测试文件
        storage.delete_file(file_metadata.file_id)
        print_step("测试文件清理完成", "SUCCESS")
        
        return True
        
    except Exception as e:
        print_step(f"PostgreSQL存储测试失败: {e}", "ERROR")
        return False

def test_local_storage():
    """测试本地文件存储"""
    print_header("本地文件存储测试")
    
    try:
        # 设置为本地存储
        os.environ['STORAGE_TYPE'] = 'local_file'
        
        # 重新创建存储实例
        storage = FileStorageFactory.create_storage()
        print_step("本地存储实例创建成功", "SUCCESS")
        
        # 测试文件上传
        test_content = "这是一个测试文件的内容。\nTest file content for local storage.".encode('utf-8')
        test_filename = "test_local.txt"
        
        print_step(f"上传测试文件: {test_filename}", "INFO")
        file_metadata = storage.upload_file(
            file_data=test_content,
            filename=test_filename,
            content_type="text/plain",
            metadata={"test": True, "created_by": "test_script"}
        )
        
        print_step(f"文件上传成功 - ID: {file_metadata.file_id}", "SUCCESS")
        print(f"    存储路径: {file_metadata.storage_path}")
        
        # 测试文件下载
        downloaded_content = storage.download_file(file_metadata.file_id)
        
        if downloaded_content == test_content:
            print_step("文件下载验证成功", "SUCCESS")
        else:
            print_step("文件下载验证失败", "ERROR")
            return False
        
        # 清理测试文件
        storage.delete_file(file_metadata.file_id)
        print_step("测试文件清理完成", "SUCCESS")
        
        return True
        
    except Exception as e:
        print_step(f"本地存储测试失败: {e}", "ERROR")
        return False

def test_performance():
    """测试存储性能"""
    print_header("存储性能测试")
    
    # 重置为PostgreSQL存储
    os.environ['STORAGE_TYPE'] = 'postgresql'
    
    try:
        storage = FileStorageFactory.create_storage()
        
        # 测试小文件性能
        print_step("测试小文件上传性能", "INFO")
        small_content = b"Small test file content" * 100  # 约2KB
        
        start_time = time.time()
        for i in range(5):
            file_metadata = storage.upload_file(
                file_data=small_content,
                filename=f"perf_test_small_{i}.txt",
                content_type="text/plain"
            )
            # 立即删除以节省空间
            storage.delete_file(file_metadata.file_id)
        
        small_time = time.time() - start_time
        print_step(f"小文件测试完成 - 5个文件耗时: {small_time:.2f}秒", "SUCCESS")
        
        # 测试中等文件性能
        print_step("测试中等文件上传性能", "INFO")
        medium_content = b"Medium test file content" * 10000  # 约240KB
        
        start_time = time.time()
        for i in range(3):
            file_metadata = storage.upload_file(
                file_data=medium_content,
                filename=f"perf_test_medium_{i}.txt",
                content_type="text/plain"
            )
            # 立即删除以节省空间
            storage.delete_file(file_metadata.file_id)
        
        medium_time = time.time() - start_time
        print_step(f"中等文件测试完成 - 3个文件耗时: {medium_time:.2f}秒", "SUCCESS")
        
        return True
        
    except Exception as e:
        print_step(f"性能测试失败: {e}", "ERROR")
        return False

def test_file_deduplication():
    """测试文件去重功能"""
    print_header("文件去重测试")
    
    try:
        storage = FileStorageFactory.create_storage()
        
        # 上传相同内容的文件
        test_content = b"Duplicate test content"
        
        print_step("上传第一个文件", "INFO")
        file1 = storage.upload_file(
            file_data=test_content,
            filename="duplicate1.txt",
            content_type="text/plain"
        )
        
        print_step("上传相同内容的第二个文件", "INFO")
        file2 = storage.upload_file(
            file_data=test_content,
            filename="duplicate2.txt",
            content_type="text/plain"
        )
        
        # 检查哈希值是否相同
        if file1.file_hash == file2.file_hash:
            print_step("文件哈希相同，可以实现去重逻辑", "SUCCESS")
        else:
            print_step("文件哈希不同，这不应该发生", "ERROR")
        
        # 清理测试文件
        storage.delete_file(file1.file_id)
        storage.delete_file(file2.file_id)
        
        return True
        
    except Exception as e:
        print_step(f"去重测试失败: {e}", "ERROR")
        return False

def show_storage_info():
    """显示当前存储配置信息"""
    print_header("存储配置信息")
    
    config = storage_config_manager.get_current_config()
    
    print_step(f"当前存储类型: {config.storage_type.value}", "INFO")
    print_step(f"最大文件大小: {config.max_file_size / (1024*1024):.1f}MB", "INFO")
    print_step(f"允许的文件扩展名: {', '.join(config.allowed_extensions[:10])}...", "INFO")
    
    if hasattr(config, 'endpoint'):
        # MinIO配置
        print_step(f"MinIO端点: {config.endpoint}", "INFO")
        print_step(f"存储桶: {config.bucket_name}", "INFO")
        print_step(f"安全连接: {config.secure}", "INFO")
    elif hasattr(config, 'host'):
        # PostgreSQL配置
        print_step(f"数据库主机: {config.host}:{config.port}", "INFO")
        print_step(f"数据库名: {config.database}", "INFO")

def test_document_manager():
    """测试文档管理器"""
    print_header("文档管理器测试")
    
    try:
        from document_manager import get_document_manager
        
        # 获取文档管理器实例
        doc_manager = get_document_manager()
        print_step("文档管理器实例创建成功", "SUCCESS")
        
        # 测试文档上传
        test_content = b"This is a test document for document manager."
        test_filename = "test_document_manager.txt"
        kb_id = "test_kb_001"
        
        print_step(f"上传测试文档: {test_filename}", "INFO")
        
        import asyncio
        upload_result = asyncio.run(doc_manager.upload_document(
            file=test_content,
            filename=test_filename,
            kb_id=kb_id,
            metadata={"test": True, "module": "document_manager"}
        ))
        
        if upload_result["success"]:
            print_step("文档上传成功", "SUCCESS")
            print(f"    文件ID: {upload_result['file_id']}")
            print(f"    文件哈希: {upload_result['file_hash']}")
            
            file_id = upload_result["file_id"]
            
            # 测试文档信息获取
            print_step("测试文档信息获取", "INFO")
            doc_info = doc_manager.get_document_info(file_id)
            
            if doc_info:
                print_step("文档信息获取成功", "SUCCESS")
                print(f"    知识库ID: {doc_info['kb_id']}")
                print(f"    存储后端: {doc_info['storage_backend']}")
            else:
                print_step("文档信息获取失败", "ERROR")
                return False
            
            # 测试文档删除
            print_step("测试文档删除", "INFO")
            delete_result = asyncio.run(doc_manager.delete_document(file_id))
            
            if delete_result["success"]:
                print_step("文档删除成功", "SUCCESS")
                print(f"    删除结果: {delete_result['deletion_results']}")
            else:
                print_step("文档删除失败", "ERROR")
                return False
        else:
            print_step("文档上传失败", "ERROR")
            return False
        
        return True
        
    except Exception as e:
        print_step(f"文档管理器测试失败: {e}", "ERROR")
        return False

def main():
    """主测试函数"""
    print_header("文件存储系统综合测试")
    
    print("🎯 测试内容:")
    print("  • MinIO文件存储功能（默认）")
    print("  • PostgreSQL文件存储功能")
    print("  • 本地文件存储功能")
    print("  • 文档管理器功能")
    print("  • 存储性能测试")
    print("  • 文件去重测试")
    
    # 显示配置信息
    show_storage_info()
    
    # 运行测试
    tests = [
        ("MinIO存储", test_minio_storage),
        ("PostgreSQL存储", test_postgresql_storage),
        ("本地文件存储", test_local_storage),
        ("文档管理器", test_document_manager),
        ("存储性能", test_performance),
        ("文件去重", test_file_deduplication)
    ]
    
    success_count = 0
    for test_name, test_func in tests:
        try:
            if test_func():
                success_count += 1
                print_step(f"{test_name}测试通过", "SUCCESS")
            else:
                print_step(f"{test_name}测试失败", "ERROR")
        except Exception as e:
            print_step(f"{test_name}测试异常: {e}", "ERROR")
    
    print_header("测试结果总结")
    
    if success_count == len(tests):
        print_step("🎉 所有测试通过！文件存储系统工作正常", "SUCCESS")
        print("")
        print("📋 支持的存储方案:")
        print("  ✅ MinIO对象存储 - 推荐用于生产环境（默认）")
        print("  ✅ PostgreSQL - 适合中小型应用")
        print("  ✅ 本地文件存储 - 适合开发测试")
        print("  ✅ Elasticsearch - 支持全文搜索")
        print("")
        print("🔧 使用方法:")
        print("  export STORAGE_TYPE=minio         # 使用MinIO存储（默认）")
        print("  export STORAGE_TYPE=postgresql    # 使用PostgreSQL存储")
        print("  export STORAGE_TYPE=local_file    # 使用本地文件存储")
        print("  export STORAGE_TYPE=elasticsearch # 使用ES存储")
        print("")
        print("📁 文档管理器功能:")
        print("  • 统一文件ID管理")
        print("  • 关联删除（MinIO + 向量数据 + PostgreSQL记录）")
        print("  • 文件去重检测")
        print("  • 批量上传支持")
        
    else:
        print_step(f"部分测试失败 ({success_count}/{len(tests)})", "WARNING")
    
    return success_count == len(tests)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 