"""
LlamaIndex框架集成
集成LlamaIndex核心功能，提供文档处理、向量检索、聊天和函数调用等功能
"""

# 基础组件导出
from app.frameworks.llamaindex.indexing import (
    create_llamaindex_index,
    load_llamaindex_index,
    get_node_parser,
    get_milvus_vector_store,
    get_elasticsearch_vector_store
)

from app.frameworks.llamaindex.retrieval import (
    get_retriever,
    retrieve_documents,
    get_query_engine
)

from app.frameworks.llamaindex.document_processor import (
    DocumentProcessor,
    DocumentSplitterFactory
)

# 工具和功能调用导出
from app.frameworks.llamaindex.tool_utils import (
    get_web_search_tool,
    get_all_tools
)

from app.frameworks.llamaindex.function_calling import (
    FunctionCallingAdapter,
    FunctionCallingConfig,
    FunctionCallingStrategy,
    create_function_calling_adapter
)

from app.frameworks.llamaindex.model_with_tools import (
    ModelWithTools,
    create_model_with_tools
)

from app.frameworks.llamaindex.chat_with_tools import (
    ChatWithTools,
    create_chat_with_tools
)


__all__ = [
    # 索引和检索
    "create_llamaindex_index",
    "load_llamaindex_index",
    "get_node_parser",
    "get_milvus_vector_store",
    "get_elasticsearch_vector_store",
    "get_retriever",
    "retrieve_documents",
    "get_query_engine",
    
    # 文档处理
    "DocumentProcessor",
    "DocumentSplitterFactory",
    
    # 工具和函数调用
    "get_web_search_tool",
    "get_all_tools",
    "FunctionCallingAdapter",
    "FunctionCallingConfig",
    "FunctionCallingStrategy",
    "create_function_calling_adapter",
    "ModelWithTools",
    "create_model_with_tools",
    "ChatWithTools",
    "create_chat_with_tools"
]
