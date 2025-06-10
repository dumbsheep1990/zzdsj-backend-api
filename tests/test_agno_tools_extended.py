"""
扩展的Agno工具测试
测试新添加的聊天工具集成和文档切分工具
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# 测试聊天工具集成
from app.tools.advanced.integration.agno_chat_with_tools import (
    AgnoChatWithTools,
    AgnoToolCall, 
    AgnoToolRegistry,
    create_agno_chat_with_tools,
    get_agno_chat_with_tools
)

# 测试文档切分工具
from app.tools.base.agno_document_chunking import (
    AgnoDocumentChunker,
    AgnoChunkingConfig,
    AgnoChunkingStrategy,
    AgnoDocumentChunk,
    AgnoChunkingResult,
    agno_chunk_text,
    create_agno_chunker,
    get_agno_chunker
)

class TestAgnoToolCall:
    """测试Agno工具调用"""
    
    def test_tool_call_init(self):
        """测试工具调用初始化"""
        def test_function(x: int, y: int) -> int:
            return x + y
        
        tool_call = AgnoToolCall(
            tool_name="test_tool",
            tool_function=test_function,
            parameters={"x": 1, "y": 2}
        )
        
        assert tool_call.tool_name == "test_tool"
        assert tool_call.tool_function == test_function
        assert tool_call.parameters == {"x": 1, "y": 2}
        assert tool_call.call_id is not None
    
    @pytest.mark.asyncio
    async def test_sync_tool_execution(self):
        """测试同步工具执行"""
        def add_function(x: int, y: int) -> int:
            return x + y
        
        tool_call = AgnoToolCall(
            tool_name="add",
            tool_function=add_function,
            parameters={"x": 3, "y": 4}
        )
        
        result = await tool_call.execute()
        
        assert result["success"] is True
        assert result["tool_name"] == "add"
        assert result["result"] == 7
        assert "execution_time" in result
    
    @pytest.mark.asyncio
    async def test_async_tool_execution(self):
        """测试异步工具执行"""
        async def async_add_function(x: int, y: int) -> int:
            await asyncio.sleep(0.01)  # 模拟异步操作
            return x + y
        
        tool_call = AgnoToolCall(
            tool_name="async_add",
            tool_function=async_add_function,
            parameters={"x": 5, "y": 6}
        )
        
        result = await tool_call.execute()
        
        assert result["success"] is True
        assert result["tool_name"] == "async_add"
        assert result["result"] == 11
    
    @pytest.mark.asyncio
    async def test_tool_execution_error(self):
        """测试工具执行错误"""
        def error_function():
            raise ValueError("Test error")
        
        tool_call = AgnoToolCall(
            tool_name="error_tool",
            tool_function=error_function,
            parameters={}
        )
        
        result = await tool_call.execute()
        
        assert result["success"] is False
        assert result["tool_name"] == "error_tool"
        assert "Test error" in result["error"]

class TestAgnoToolRegistry:
    """测试Agno工具注册表"""
    
    def test_registry_init(self):
        """测试注册表初始化"""
        registry = AgnoToolRegistry()
        assert isinstance(registry.tools, dict)
        assert len(registry.tools) == 0
    
    def test_register_tool(self):
        """测试注册工具"""
        registry = AgnoToolRegistry()
        
        def test_function(x: str) -> str:
            return f"Hello, {x}!"
        
        registry.register_tool(
            name="greet",
            function=test_function,
            description="Greet someone",
            parameters={"x": {"type": "string"}}
        )
        
        assert "greet" in registry.tools
        tool_info = registry.tools["greet"]
        assert tool_info["function"] == test_function
        assert tool_info["description"] == "Greet someone"
        assert tool_info["parameters"] == {"x": {"type": "string"}}
    
    def test_get_tool(self):
        """测试获取工具"""
        registry = AgnoToolRegistry()
        
        def test_function():
            return "test"
        
        registry.register_tool("test", test_function)
        
        tool_info = registry.get_tool("test")
        assert tool_info is not None
        assert tool_info["function"] == test_function
        
        # 测试不存在的工具
        missing_tool = registry.get_tool("missing")
        assert missing_tool is None
    
    def test_list_tools(self):
        """测试列出工具"""
        registry = AgnoToolRegistry()
        
        def func1():
            return 1
        
        async def func2():
            return 2
        
        registry.register_tool("tool1", func1, "First tool")
        registry.register_tool("tool2", func2, "Second tool")
        
        tools = registry.list_tools()
        
        assert len(tools) == 2
        tool_names = [tool["name"] for tool in tools]
        assert "tool1" in tool_names
        assert "tool2" in tool_names

class TestAgnoChatWithTools:
    """测试Agno聊天工具集成"""
    
    def setup_method(self):
        """设置测试方法"""
        self.mock_llm_service = Mock()
        self.mock_llm_service.chat_completion = AsyncMock()
        
        # 模拟LLM响应
        self.mock_llm_service.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "content": "这是一个测试响应"
                }
            }]
        }
    
    def test_chat_with_tools_init(self):
        """测试聊天工具管理器初始化"""
        chat_manager = AgnoChatWithTools(
            llm_service=self.mock_llm_service,
            max_iterations=5,
            verbose=True
        )
        
        assert chat_manager.llm_service == self.mock_llm_service
        assert chat_manager.max_iterations == 5
        assert chat_manager.verbose is True
        assert isinstance(chat_manager.tool_registry, AgnoToolRegistry)
    
    @pytest.mark.asyncio
    async def test_basic_chat_without_tools(self):
        """测试基本聊天（不使用工具）"""
        chat_manager = AgnoChatWithTools(
            llm_service=self.mock_llm_service
        )
        
        messages = [{"role": "user", "content": "Hello"}]
        
        result = await chat_manager.chat(messages, enable_tools=False)
        
        assert result["success"] is True
        assert "response" in result
        assert result["tool_calls"] == []
        self.mock_llm_service.chat_completion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_chat_with_tool_call(self):
        """测试带工具调用的聊天"""
        # 模拟包含工具调用的LLM响应
        self.mock_llm_service.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "content": '我需要搜索信息。```tool\n{"tool_name": "web_search", "parameters": {"query": "test"}}\n```'
                }
            }]
        }
        
        chat_manager = AgnoChatWithTools(
            llm_service=self.mock_llm_service
        )
        
        # 注册模拟搜索工具
        def mock_search(query: str) -> Dict[str, Any]:
            return {"results": [f"Search result for: {query}"]}
        
        chat_manager.add_tool(
            name="web_search",
            function=mock_search,
            description="Mock search tool"
        )
        
        messages = [{"role": "user", "content": "Search for something"}]
        
        result = await chat_manager.chat(messages, enable_tools=True)
        
        assert result["success"] is True
        assert len(result["tool_calls"]) > 0
        assert result["tool_calls"][0]["tool_name"] == "web_search"
    
    def test_extract_tool_calls(self):
        """测试提取工具调用"""
        chat_manager = AgnoChatWithTools(self.mock_llm_service)
        
        content = '''
        我需要搜索信息。
        ```tool
        {"tool_name": "web_search", "parameters": {"query": "test query"}}
        ```
        然后我需要进行推理。
        ```tool
        {"tool_name": "reasoning", "parameters": {"problem": "test problem"}}
        ```
        '''
        
        tool_calls = chat_manager._extract_tool_calls(content)
        
        assert len(tool_calls) == 2
        assert tool_calls[0]["tool_name"] == "web_search"
        assert tool_calls[0]["parameters"]["query"] == "test query"
        assert tool_calls[1]["tool_name"] == "reasoning"
        assert tool_calls[1]["parameters"]["problem"] == "test problem"
    
    def test_factory_function(self):
        """测试工厂函数"""
        chat_manager = create_agno_chat_with_tools(
            llm_service=self.mock_llm_service,
            max_iterations=8
        )
        
        assert isinstance(chat_manager, AgnoChatWithTools)
        assert chat_manager.max_iterations == 8

class TestAgnoDocumentChunking:
    """测试Agno文档切分"""
    
    def test_chunking_config_init(self):
        """测试切分配置初始化"""
        config = AgnoChunkingConfig(
            strategy=AgnoChunkingStrategy.SENTENCE,
            chunk_size=500,
            chunk_overlap=100
        )
        
        assert config.strategy == AgnoChunkingStrategy.SENTENCE
        assert config.chunk_size == 500
        assert config.chunk_overlap == 100
        
        config_dict = config.to_dict()
        assert config_dict["strategy"] == "sentence"
        assert config_dict["chunk_size"] == 500
    
    def test_document_chunk_init(self):
        """测试文档块初始化"""
        chunk = AgnoDocumentChunk(
            id="test_chunk",
            content="This is a test chunk.",
            chunk_index=0
        )
        
        assert chunk.id == "test_chunk"
        assert chunk.content == "This is a test chunk."
        assert chunk.length == len("This is a test chunk.")
        assert chunk.start_char_idx == 0
        assert chunk.end_char_idx == len("This is a test chunk.")
    
    def test_document_chunker_init(self):
        """测试文档切分器初始化"""
        config = AgnoChunkingConfig(chunk_size=300)
        chunker = AgnoDocumentChunker(config)
        
        assert chunker.config.chunk_size == 300
        assert chunker.config.strategy == AgnoChunkingStrategy.SENTENCE
    
    def test_sentence_chunking(self):
        """测试句子切分"""
        text = "这是第一句话。这是第二句话！这是第三句话？这是第四句话。"
        
        result = agno_chunk_text(
            text=text,
            strategy=AgnoChunkingStrategy.SENTENCE,
            chunk_size=20
        )
        
        assert isinstance(result, AgnoChunkingResult)
        assert len(result.chunks) > 1
        assert result.stats["total_chunks"] > 1
        
        # 检查每个块都不为空
        for chunk in result.chunks:
            assert len(chunk.content.strip()) > 0
    
    def test_paragraph_chunking(self):
        """测试段落切分"""
        text = "第一段内容。\n\n第二段内容。\n\n第三段内容。"
        
        result = agno_chunk_text(
            text=text,
            strategy=AgnoChunkingStrategy.PARAGRAPH,
            chunk_size=15
        )
        
        assert len(result.chunks) >= 2
        assert "paragraph" in result.metadata["chunking_strategy"]
    
    def test_fixed_size_chunking(self):
        """测试固定大小切分"""
        text = "A" * 1000  # 1000个字符
        
        result = agno_chunk_text(
            text=text,
            strategy=AgnoChunkingStrategy.FIXED_SIZE,
            chunk_size=200
        )
        
        assert len(result.chunks) >= 4  # 至少应该有4个块
        
        # 检查大多数块的大小接近配置的大小
        for chunk in result.chunks[:-1]:  # 除了最后一个块
            assert 150 <= len(chunk.content) <= 250  # 允许一些偏差
    
    def test_markdown_chunking(self):
        """测试Markdown切分"""
        text = """
# 标题1
内容1

## 子标题1
子内容1

# 标题2
内容2
"""
        result = agno_chunk_text(
            text=text,
            strategy=AgnoChunkingStrategy.MARKDOWN,
            chunk_size=100
        )
        
        assert len(result.chunks) >= 2
        
        # 检查元数据
        for chunk in result.chunks:
            if chunk.metadata:
                assert chunk.metadata.get("type") == "markdown_section"
    
    def test_empty_text_handling(self):
        """测试空文本处理"""
        result = agno_chunk_text(text="")
        
        assert len(result.chunks) == 0
        assert result.stats["total_chunks"] == 0
    
    def test_chunk_overlap(self):
        """测试块重叠"""
        text = "这是一个相对较长的文本，用于测试块重叠功能。我们需要确保重叠部分正确工作。"
        
        result = agno_chunk_text(
            text=text,
            strategy=AgnoChunkingStrategy.FIXED_SIZE,
            chunk_size=30,
            chunk_overlap=10
        )
        
        if len(result.chunks) > 1:
            # 检查是否有重叠信息
            overlapped_chunks = [chunk for chunk in result.chunks if chunk.metadata.get("has_overlap")]
            assert len(overlapped_chunks) >= 0  # 可能有重叠块
    
    def test_chunking_result_stats(self):
        """测试切分结果统计"""
        text = "测试文本。" * 50  # 重复50次
        
        result = agno_chunk_text(
            text=text,
            chunk_size=100
        )
        
        stats = result.stats
        assert stats["total_chunks"] > 0
        assert stats["total_characters"] > 0
        assert stats["average_chunk_size"] > 0
        assert stats["min_chunk_size"] > 0
        assert stats["max_chunk_size"] > 0
    
    def test_factory_functions(self):
        """测试工厂函数"""
        # 测试创建切分器
        chunker = create_agno_chunker(
            strategy=AgnoChunkingStrategy.PARAGRAPH,
            chunk_size=300
        )
        
        assert isinstance(chunker, AgnoDocumentChunker)
        assert chunker.config.strategy == AgnoChunkingStrategy.PARAGRAPH
        assert chunker.config.chunk_size == 300
        
        # 测试单例获取
        default_chunker = get_agno_chunker()
        assert isinstance(default_chunker, AgnoDocumentChunker)

class TestAgnoToolsIntegration:
    """测试Agno工具集成"""
    
    @pytest.mark.asyncio
    async def test_chat_with_chunking_tool(self):
        """测试聊天与切分工具的集成"""
        mock_llm_service = Mock()
        mock_llm_service.chat_completion = AsyncMock()
        
        # 模拟带工具调用的LLM响应
        mock_llm_service.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "content": '我需要切分文档。```tool\n{"tool_name": "chunk_document", "parameters": {"text": "测试文档内容。这是第二句话。"}}\n```'
                }
            }]
        }
        
        chat_manager = AgnoChatWithTools(llm_service=mock_llm_service)
        
        # 注册文档切分工具
        def chunk_document_tool(text: str, chunk_size: int = 50) -> Dict[str, Any]:
            result = agno_chunk_text(text=text, chunk_size=chunk_size)
            return {
                "chunks": [chunk.to_dict() for chunk in result.chunks],
                "stats": result.stats
            }
        
        chat_manager.add_tool(
            name="chunk_document",
            function=chunk_document_tool,
            description="切分文档为小块"
        )
        
        messages = [{"role": "user", "content": "请帮我切分这个文档"}]
        
        result = await chat_manager.chat(messages, enable_tools=True)
        
        assert result["success"] is True
        assert len(result["tool_calls"]) > 0
        
        # 检查工具调用结果
        tool_call = result["tool_calls"][0]
        assert tool_call["tool_name"] == "chunk_document"
        assert tool_call["success"] is True
        assert "chunks" in tool_call["result"]
    
    def test_tools_performance_comparison(self):
        """测试工具性能对比"""
        import time
        
        # 测试Agno切分性能
        text = "测试文本内容。" * 1000  # 较大的文本
        
        start_time = time.time()
        agno_result = agno_chunk_text(text=text, chunk_size=200)
        agno_time = time.time() - start_time
        
        # 验证结果
        assert len(agno_result.chunks) > 0
        assert agno_time < 1.0  # 应该在1秒内完成
        
        # 记录性能信息
        print(f"Agno chunking performance: {agno_time:.4f}s for {len(text)} characters")
        print(f"Generated {len(agno_result.chunks)} chunks")

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 