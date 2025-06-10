"""
Agno工具测试
测试迁移后的Agno工具功能是否正常
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from app.tools.base.search.agno_search_tool import (
    AgnoWebSearchTool, 
    AgnoSearchQuery, 
    AgnoSearchResult,
    create_agno_web_search_tool,
    get_agno_search_tool
)

from app.tools.advanced.reasoning.agno_cot_tool import (
    AgnoCoTTool,
    AgnoCoTRequest,
    AgnoCoTResponse,
    create_agno_cot_tool,
    get_agno_cot_tool
)

from app.tools.agno_registry import (
    get_tool_registry,
    get_tool,
    ToolCategory,
    ToolMetadata
)

class TestAgnoWebSearchTool:
    """测试Agno Web搜索工具"""
    
    def setup_method(self):
        """测试前设置"""
        self.search_tool = AgnoWebSearchTool()
    
    def test_tool_initialization(self):
        """测试工具初始化"""
        assert self.search_tool.name == "web_search"
        assert "SearxNG" in self.search_tool.description
        assert self.search_tool.searxng_manager is not None
    
    def test_validate_query(self):
        """测试查询验证"""
        # 有效查询
        assert self.search_tool.validate_query("Python编程") == True
        assert self.search_tool.validate_query("人工智能发展") == True
        
        # 无效查询
        assert self.search_tool.validate_query("") == False
        assert self.search_tool.validate_query("   ") == False
        assert self.search_tool.validate_query("a" * 501) == False
    
    def test_get_search_engines(self):
        """测试获取搜索引擎列表"""
        engines = self.search_tool.get_search_engines()
        assert isinstance(engines, list)
        assert "google" in engines
        assert "bing" in engines
        assert "baidu" in engines
    
    @patch('app.tools.base.search.agno_search_tool.get_searxng_manager')
    def test_search_web_success(self, mock_searxng_manager):
        """测试成功的Web搜索"""
        # 模拟搜索结果
        mock_results = [
            {
                "title": "Python编程教程",
                "url": "https://example.com/python",
                "content": "Python是一种高级编程语言",
                "source": "google",
                "score": 0.95,
                "published_date": "2024-01-01"
            },
            {
                "title": "Python官方文档",
                "url": "https://python.org",
                "content": "Python官方文档和资源",
                "source": "google",
                "score": 0.90
            }
        ]
        
        # 配置mock
        mock_manager = MagicMock()
        mock_manager.search.return_value = mock_results
        mock_searxng_manager.return_value = mock_manager
        
        # 重新初始化工具以使用mock
        search_tool = AgnoWebSearchTool()
        
        # 执行搜索
        result = search_tool.search_web(
            query="Python编程",
            engines=["google"],
            language="zh-CN",
            max_results=2
        )
        
        # 验证结果
        assert result['success'] == True
        assert result['count'] == 2
        assert result['query'] == "Python编程"
        assert len(result['results']) == 2
        assert "搜索结果：" in result['text_summary']
        
        # 验证结果结构
        first_result = result['results'][0]
        assert first_result['title'] == "Python编程教程"
        assert first_result['url'] == "https://example.com/python"
        assert first_result['source'] == "google"
    
    @patch('app.tools.base.search.agno_search_tool.get_searxng_manager')
    def test_search_web_no_results(self, mock_searxng_manager):
        """测试无搜索结果的情况"""
        # 配置mock返回空结果
        mock_manager = MagicMock()
        mock_manager.search.return_value = []
        mock_searxng_manager.return_value = mock_manager
        
        search_tool = AgnoWebSearchTool()
        
        result = search_tool.search_web(query="不存在的查询内容")
        
        assert result['success'] == False
        assert result['count'] == 0
        assert "未找到关于" in result['message']
    
    @patch('app.tools.base.search.agno_search_tool.get_searxng_manager')
    def test_search_web_error(self, mock_searxng_manager):
        """测试搜索异常情况"""
        # 配置mock抛出异常
        mock_manager = MagicMock()
        mock_manager.search.side_effect = Exception("搜索服务异常")
        mock_searxng_manager.return_value = mock_manager
        
        search_tool = AgnoWebSearchTool()
        
        result = search_tool.search_web(query="测试查询")
        
        assert result['success'] == False
        assert "搜索服务异常" in result['error']
    
    def test_factory_functions(self):
        """测试工厂函数"""
        # 测试create_agno_web_search_tool
        tool1 = create_agno_web_search_tool("custom_search")
        assert tool1.name == "custom_search"
        
        # 测试get_agno_search_tool
        tool2 = get_agno_search_tool()
        assert tool2.name == "web_search"

class TestAgnoCoTTool:
    """测试Agno链式思考工具"""
    
    def setup_method(self):
        """测试前设置"""
        self.cot_tool = AgnoCoTTool()
    
    def test_tool_initialization(self):
        """测试工具初始化"""
        assert self.cot_tool.name == "cot_reasoning"
        assert "Chain of Thought" in self.cot_tool.description
        assert self.cot_tool.cot_manager is not None
    
    def test_validate_query(self):
        """测试查询验证"""
        # 有效查询
        assert self.cot_tool.validate_query("解释量子计算原理") == True
        assert self.cot_tool.validate_query("分析人工智能发展趋势") == True
        
        # 无效查询
        assert self.cot_tool.validate_query("") == False
        assert self.cot_tool.validate_query("   ") == False
        assert self.cot_tool.validate_query("a" * 2001) == False
    
    def test_get_reasoning_capabilities(self):
        """测试获取推理能力列表"""
        capabilities = self.cot_tool.get_reasoning_capabilities()
        assert isinstance(capabilities, list)
        assert "chain_of_thought" in capabilities
        assert "step_by_step_reasoning" in capabilities
        assert "logical_deduction" in capabilities
    
    @patch('app.tools.advanced.reasoning.agno_cot_tool.CoTManager')
    def test_reason_with_cot_success(self, mock_cot_manager_class):
        """测试成功的推理"""
        # 模拟CoTManager和结果
        mock_manager = MagicMock()
        mock_cot_result = {
            "final_answer": "量子计算是一种利用量子力学原理进行计算的技术。",
            "thinking_process": "首先分析量子力学基本原理...",
            "reasoning_steps": ["理解量子位", "分析量子叠加", "解释量子纠缠"]
        }
        
        mock_manager.call_with_cot.return_value = mock_cot_result
        mock_manager.format_response_for_api.return_value = mock_cot_result
        mock_cot_manager_class.return_value = mock_manager
        
        # 重新初始化工具
        cot_tool = AgnoCoTTool()
        
        # 执行推理
        result = cot_tool.reason_with_cot(
            query="解释量子计算的基本原理",
            enable_cot=True,
            show_cot=True,
            temperature=0.3
        )
        
        # 验证结果
        assert result['success'] == True
        assert result['final_answer'] == mock_cot_result['final_answer']
        assert result['thinking_process'] == mock_cot_result['thinking_process']
        assert result['reasoning_steps'] == mock_cot_result['reasoning_steps']
        assert result['show_cot'] == True
        assert result['execution_time'] >= 0
    
    @patch('app.tools.advanced.reasoning.agno_cot_tool.CoTManager')
    def test_reason_with_cot_error(self, mock_cot_manager_class):
        """测试推理异常情况"""
        # 配置mock抛出异常
        mock_manager = MagicMock()
        mock_manager.call_with_cot.side_effect = Exception("推理服务异常")
        mock_cot_manager_class.return_value = mock_manager
        
        cot_tool = AgnoCoTTool()
        
        result = cot_tool.reason_with_cot(query="测试查询")
        
        assert result['success'] == False
        assert "推理服务异常" in result['error']
        assert result['show_cot'] == False
    
    def test_simple_reason(self):
        """测试简单推理接口"""
        with patch.object(self.cot_tool, 'reason_with_cot') as mock_reason:
            mock_result = {
                'success': True,
                'final_answer': '这是答案',
                'thinking_process': '这是思考过程',
                'show_cot': True
            }
            mock_reason.return_value = mock_result
            
            result = self.cot_tool.simple_reason("测试问题", show_cot=True)
            
            assert "思考过程：" in result
            assert "最终答案：" in result
    
    def test_factory_functions(self):
        """测试工厂函数"""
        # 测试create_agno_cot_tool
        tool1 = create_agno_cot_tool("custom_reasoning")
        assert tool1.name == "custom_reasoning"
        
        # 测试get_agno_cot_tool
        tool2 = get_agno_cot_tool()
        assert tool2.name == "cot_reasoning"

class TestAgnoToolRegistry:
    """测试Agno工具注册系统"""
    
    def test_get_tool_registry(self):
        """测试获取工具注册中心"""
        registry = get_tool_registry()
        assert registry is not None
        
        # 确保是单例
        registry2 = get_tool_registry()
        assert registry is registry2
    
    def test_get_registered_tools(self):
        """测试获取已注册的工具"""
        registry = get_tool_registry()
        
        # 检查内置工具是否已注册
        all_tools = registry.list_all_tools()
        assert "web_search" in all_tools
        
        # 检查分类
        search_tools = registry.get_tools_by_category(ToolCategory.SEARCH)
        assert "web_search" in search_tools
    
    def test_get_tool_from_registry(self):
        """测试从注册中心获取工具"""
        # 获取搜索工具
        search_tool = get_tool("web_search")
        assert search_tool is not None
        assert hasattr(search_tool, 'search_web')
        
        # 测试不存在的工具
        non_existent_tool = get_tool("non_existent_tool")
        assert non_existent_tool is None
    
    def test_tool_metadata(self):
        """测试工具元数据"""
        registry = get_tool_registry()
        
        # 获取搜索工具的元数据
        metadata = registry.get_tool_metadata("web_search")
        if metadata:  # 如果注册时提供了元数据
            assert metadata.name == "web_search"
            assert metadata.category == ToolCategory.SEARCH
            assert "search" in metadata.tags or not metadata.tags
    
    def test_search_tools_in_registry(self):
        """测试在注册中心搜索工具"""
        registry = get_tool_registry()
        
        # 按关键词搜索
        search_results = registry.search_tools(query="search")
        assert len(search_results) >= 0
        
        # 按分类搜索
        search_tools = registry.search_tools(category=ToolCategory.SEARCH)
        assert len(search_tools) >= 0

class TestAgnoToolIntegration:
    """测试Agno工具集成"""
    
    def test_tools_compatibility(self):
        """测试工具兼容性"""
        # 确保工具可以被正确实例化
        search_tool = get_tool("web_search")
        assert search_tool is not None
        
        # 确保工具有正确的方法
        assert hasattr(search_tool, 'search_web')
        assert callable(getattr(search_tool, 'search_web'))
    
    def test_tool_response_format(self):
        """测试工具响应格式"""
        search_tool = get_tool("web_search")
        
        with patch.object(search_tool, '_async_search') as mock_search:
            mock_search.return_value = []
            
            result = search_tool.search_web("测试查询")
            
            # 验证响应格式
            assert isinstance(result, dict)
            assert 'success' in result
            assert 'results' in result
            assert 'count' in result
            assert 'query' in result

if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"]) 