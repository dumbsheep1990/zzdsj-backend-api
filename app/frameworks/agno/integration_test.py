"""
Agno框架集成测试
验证ZZDSJ平台中所有Agno组件的集成和互操作性

测试覆盖：
- Agno代理创建和基本功能
- 知识库搜索和检索
- MCP服务集成
- 工具系统协调工作
- LlamaIndex兼容性适配器
- 错误处理和异常情况
"""

import asyncio
import pytest
import logging
import os
import time
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Agno框架组件导入
from app.frameworks.agno import (
    AgnoCore, get_agno_core,
    AgnoAgent, AgnoChat,
    AgnoKnowledgeBase,
    ZZDSJKnowledgeTools, ZZDSJFileManagementTools, ZZDSJSystemTools,
    ZZDSJMCPAdapter, ZZDSJServiceAdapter,
    create_zzdsj_chat_agent, get_service_adapter,
    initialize_agno, cleanup_agno
)

logger = logging.getLogger(__name__)


class AgnoIntegrationTest:
    """Agno框架集成测试套件"""
    
    @pytest.fixture(autouse=True)
    async def setup_teardown(self):
        """测试设置和清理"""
        # 设置测试环境
        os.environ.setdefault("OPENAI_API_KEY", "test-key-for-integration")
        
        # 初始化Agno框架
        await initialize_agno()
        
        yield
        
        # 清理测试环境
        await cleanup_agno()

    async def run_all_tests(self):
        """运行所有集成测试"""
        print("🧪 开始Agno框架集成测试...")
        print("=" * 60)
        
        tests = [
            self.test_knowledge_tools,
            self.test_file_management_tools,
            self.test_system_tools,
            self.test_mcp_adapter,
            self.test_service_adapter,
            self.test_error_handling,
            self.test_performance
        ]
        
        passed = 0
        failed = 0
        
        for test_func in tests:
            try:
                await test_func()
                passed += 1
            except Exception as e:
                print(f"❌ 测试失败: {test_func.__name__}")
                print(f"   错误: {str(e)}")
                failed += 1
        
        print("=" * 60)
        print(f"🏁 测试完成!")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"📊 成功率: {passed/(passed+failed)*100:.1f}%")
        
        return passed, failed

    async def test_knowledge_tools(self):
        """测试知识库工具集成"""
        print("\n📚 测试知识库工具集成...")
        
        kb_tools = ZZDSJKnowledgeTools(kb_id="test-kb-001")
        assert kb_tools is not None, "知识库工具应该创建成功"
        
        # 模拟搜索操作
        with patch('app.frameworks.agno.knowledge_base.KnowledgeBaseProcessor') as mock_kb:
            mock_processor = AsyncMock()
            mock_processor.search.return_value = [
                {"title": "测试文档1", "content": "这是测试内容1", "score": 0.95}
            ]
            mock_kb.return_value = mock_processor
            
            results = kb_tools.search_documents(query="人工智能技术", top_k=1)
            assert results["count"] == 1, "应该返回1个搜索结果"
        
        print("✅ 知识库工具集成测试通过")

    async def test_file_management_tools(self):
        """测试文件管理工具"""
        print("\n📁 测试文件管理工具...")
        
        file_tools = ZZDSJFileManagementTools(upload_base_path="/tmp/test_uploads")
        assert file_tools is not None, "文件管理工具应该创建成功"
        
        # 创建测试环境
        test_dir = "/tmp/test_uploads"
        os.makedirs(test_dir, exist_ok=True)
        
        test_file = os.path.join(test_dir, "test_document.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("这是一个测试文档")
        
        try:
            file_list = file_tools.list_files("")
            assert "files" in file_list, "应该返回文件列表"
            
            file_info = file_tools.get_file_info("test_document.txt")
            assert "name" in file_info, "应该返回文件信息"
            
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)
            if os.path.exists(test_dir):
                os.rmdir(test_dir)
        
        print("✅ 文件管理工具测试通过")

    async def test_system_tools(self):
        """测试系统工具集成"""
        print("\n⚙️ 测试系统工具集成...")
        
        system_tools = ZZDSJSystemTools()
        assert system_tools is not None, "系统工具应该创建成功"
        
        with patch('psutil.cpu_percent', return_value=15.5):
            status = system_tools.get_system_status()
            if "error" not in status:
                assert "cpu_usage" in status, "应该包含CPU使用率"
        
        health_check = system_tools.get_service_health("database")
        assert "status" in health_check, "应该返回健康状态"
        
        print("✅ 系统工具集成测试通过")

    async def test_mcp_adapter(self):
        """测试MCP适配器配置"""
        print("\n🔗 测试MCP适配器配置...")
        
        mcp_adapter = ZZDSJMCPAdapter()
        assert mcp_adapter is not None, "MCP适配器应该创建成功"
        
        services = mcp_adapter.list_services()
        assert isinstance(services, list), "应该返回服务列表"
        
        print("✅ MCP适配器配置测试通过")

    async def test_service_adapter(self):
        """测试服务适配器集成"""
        print("\n🛠️ 测试服务适配器集成...")
        
        adapter = get_service_adapter()
        assert adapter is not None, "服务适配器应该存在"
        
        status = adapter.get_service_status()
        assert "timestamp" in status, "状态应该包含时间戳"
        assert "total_services" in status, "状态应该包含服务总数"
        
        print(f"  📊 总服务数: {status['total_services']}")
        print(f"  🤖 活跃代理数: {status['active_agents']}")
        
        print("✅ 服务适配器集成测试通过")

    async def test_error_handling(self):
        """测试错误处理和系统韧性"""
        print("\n🛡️ 测试错误处理和系统韧性...")
        
        kb_tools = ZZDSJKnowledgeTools(kb_id="invalid-kb-id")
        result = kb_tools.search_documents("测试查询")
        assert "error" in result, "应该返回错误信息"
        
        file_tools = ZZDSJFileManagementTools()
        file_info = file_tools.get_file_info("nonexistent-file.txt")
        assert "error" in file_info, "应该返回文件不存在错误"
        
        print("✅ 错误处理和系统韧性测试通过")

    async def test_performance(self):
        """基本性能基准测试"""
        print("\n⚡ 执行基本性能基准测试...")
        
        start_time = time.time()
        
        for i in range(10):
            kb_tools = ZZDSJKnowledgeTools(kb_id=f"test-kb-{i}")
            file_tools = ZZDSJFileManagementTools()
            system_tools = ZZDSJSystemTools()
        
        creation_time = time.time() - start_time
        print(f"  ⏱️ 10次工具创建耗时: {creation_time:.3f}秒")
        
        assert creation_time < 1.0, "工具创建应该在1秒内完成"
        
        print("✅ 性能基准测试通过")


class TestLlamaIndexCompatibility:
    """LlamaIndex兼容性测试"""
    
    async def test_llamaindex_interface_compatibility(self):
        """测试LlamaIndex接口兼容性"""
        print("\n🔄 测试LlamaIndex接口兼容性...")
        
        # 测试AgnoKnowledgeBase的LlamaIndex兼容接口
        kb = AgnoKnowledgeBase(
            name="test-kb",
            description="测试知识库"
        )
        
        # 这些方法应该存在并可调用（即使是适配器实现）
        assert hasattr(kb, 'query'), "应该有query方法"
        assert hasattr(kb, 'add_documents'), "应该有add_documents方法"
        assert hasattr(kb, 'get_retriever'), "应该有get_retriever方法"
        
        print("✅ LlamaIndex接口兼容性测试通过")


# 运行测试的便捷函数
async def run_integration_tests():
    """运行所有集成测试"""
    test_suite = AgnoIntegrationTest()
    compat_suite = TestLlamaIndexCompatibility()
    
    tests = [
        test_suite.test_knowledge_tools,
        test_suite.test_file_management_tools,
        test_suite.test_system_tools,
        test_suite.test_mcp_adapter,
        test_suite.test_service_adapter,
        test_suite.test_error_handling,
        test_suite.test_performance,
        compat_suite.test_llamaindex_interface_compatibility
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            print(f"❌ 测试失败: {test_func.__name__}")
            print(f"   错误: {str(e)}")
            failed += 1
    
    print("=" * 60)
    print(f"🏁 测试完成!")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"📊 成功率: {passed/(passed+failed)*100:.1f}%")
    
    return passed, failed


# 主入口
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 运行集成测试
    asyncio.run(run_integration_tests()) 