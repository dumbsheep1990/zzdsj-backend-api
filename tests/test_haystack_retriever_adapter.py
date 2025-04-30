"""
测试Haystack检索器适配器，验证能否将Haystack问答系统封装为LlamaIndex检索器
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from typing import List, Dict, Any

from app.frameworks.llamaindex.adapters.haystack_retriever import (
    HaystackRetriever,
    create_haystack_retriever,
    get_contexts_from_knowledge_base
)
from llama_index.core.schema import NodeWithScore
from llama_index.core.callbacks import CallbackManager
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.query_engine import BaseQueryEngine


@pytest.fixture
def mock_extract_answers():
    """模拟extract_answers函数"""
    with patch("app.frameworks.llamaindex.adapters.haystack_retriever.extract_answers") as mock_extract:
        mock_extract.return_value = [
            {
                "answer": "测试答案1",
                "context": "测试上下文1",
                "score": 0.9,
                "document_id": "doc1"
            },
            {
                "answer": "测试答案2",
                "context": "测试上下文2",
                "score": 0.8,
                "document_id": "doc2"
            }
        ]
        yield mock_extract


@pytest.fixture
def mock_query_index():
    """模拟query_index函数"""
    with patch("app.frameworks.llamaindex.adapters.haystack_retriever.query_index") as mock_query:
        mock_query.return_value = [
            {
                "content": "测试文档内容1",
                "metadata": {"doc_id": "doc1", "source": "source1"},
                "score": 0.9
            },
            {
                "content": "测试文档内容2",
                "metadata": {"doc_id": "doc2", "source": "source2"},
                "score": 0.8
            }
        ]
        yield mock_query


@pytest.fixture
def mock_knowledge_base_service():
    """模拟KnowledgeBaseService"""
    with patch("app.frameworks.llamaindex.adapters.haystack_retriever.KnowledgeBaseService") as mock_service_class:
        mock_service = MagicMock()
        mock_service.get_by_id.return_value = {
            "id": 1,
            "name": "测试知识库",
            "description": "测试描述",
            "config": {"index_name": "test_index"}
        }
        mock_service_class.return_value = mock_service
        yield mock_service


class TestHaystackRetrieverAdapter:
    """测试Haystack检索器适配器"""
    
    def test_haystack_retriever_initialization(self):
        """测试HaystackRetriever初始化"""
        retriever = HaystackRetriever(
            knowledge_base_id=1,
            model_name="test-model",
            top_k=3
        )
        
        # 验证
        assert retriever.knowledge_base_id == 1
        assert retriever.model_name == "test-model"
        assert retriever.top_k == 3
        assert isinstance(retriever.callback_manager, CallbackManager)
    
    @pytest.mark.asyncio
    async def test_haystack_retriever_aretrieve(self, mock_extract_answers):
        """测试HaystackRetriever的异步检索方法"""
        retriever = HaystackRetriever(
            knowledge_base_id=1,
            model_name="test-model",
            top_k=3
        )
        
        # 模拟上下文
        contexts = [
            {
                "content": "文档内容1",
                "metadata": {"doc_id": "doc1"}
            },
            {
                "content": "文档内容2",
                "metadata": {"doc_id": "doc2"}
            }
        ]
        
        # 调用异步检索方法
        nodes = await retriever._aretrieve(
            "测试查询",
            contexts=contexts
        )
        
        # 验证extract_answers的调用
        mock_extract_answers.assert_called_once_with(
            question="测试查询",
            contexts=contexts,
            model_name="test-model",
            top_k=3
        )
        
        # 验证返回的节点
        assert len(nodes) == 2
        assert isinstance(nodes[0], NodeWithScore)
        assert nodes[0].text == "测试答案1"
        assert nodes[0].score == 0.9
        assert nodes[0].metadata["document_id"] == "doc1"
        assert nodes[0].metadata["context"] == "测试上下文1"
    
    @pytest.mark.asyncio
    async def test_get_contexts_from_knowledge_base(self, mock_query_index, mock_knowledge_base_service):
        """测试从知识库获取上下文"""
        # 调用函数
        contexts = await get_contexts_from_knowledge_base(
            knowledge_base_id=1,
            query="测试查询",
            top_k=3
        )
        
        # 验证知识库服务调用
        mock_knowledge_base_service.get_by_id.assert_called_once_with(1)
        
        # 验证query_index调用
        mock_query_index.assert_called_once_with(
            index_name="test_index",
            query_text="测试查询",
            top_k=3
        )
        
        # 验证返回的上下文
        assert len(contexts) == 2
        assert contexts[0]["content"] == "测试文档内容1"
        assert contexts[0]["metadata"]["doc_id"] == "doc1"
        assert contexts[0]["score"] == 0.9
    
    @pytest.mark.asyncio
    async def test_create_haystack_retriever(self, mock_knowledge_base_service):
        """测试创建Haystack检索器的工厂函数"""
        # 使用工厂函数
        retriever = create_haystack_retriever(
            knowledge_base_id=1,
            model_name="test-model",
            top_k=5
        )
        
        # 验证
        assert isinstance(retriever, HaystackRetriever)
        assert retriever.knowledge_base_id == 1
        assert retriever.model_name == "test-model"
        assert retriever.top_k == 5
    
    def test_as_query_engine(self):
        """测试转换为查询引擎"""
        # 创建检索器
        retriever = HaystackRetriever(
            knowledge_base_id=1,
            model_name="test-model",
            top_k=3
        )
        
        # 转换为查询引擎
        engine = retriever.as_query_engine()
        
        # 验证
        assert isinstance(engine, BaseQueryEngine)
        assert hasattr(engine, "query")


if __name__ == "__main__":
    pytest.main(["-xvs", "test_haystack_retriever_adapter.py"])
