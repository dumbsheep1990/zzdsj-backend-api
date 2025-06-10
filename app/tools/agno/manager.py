# Agno现成工具统一管理器
from typing import List, Any
from agno import KnowledgeTools, ReasoningTools, ThinkingTools
from agno.tools import AgenticSearch, ChunkingTools

# 导入模块化工具管理器
from .reasoning import AgnoReasoningManager, AgnoThinkingManager
from .knowledge import AgnoKnowledgeManager
from .search import AgnoSearchManager
from .chunking import AgnoChunkingManager

class AgnoToolsManager:
    """Agno现成工具统一管理器 - 直接使用不重复开发"""
    
    def __init__(self):
        """直接实例化Agno现成工具 - 使用模块化管理器"""
        
        # 使用模块化管理器实例化各类工具
        self.reasoning_manager = AgnoReasoningManager(structured=True)
        self.thinking_manager = AgnoThinkingManager(max_iterations=5)
        self.knowledge_manager = AgnoKnowledgeManager(think=True, search=True, analyze=True)
        self.search_manager = AgnoSearchManager(search_engine="google", max_results=10)
        self.chunking_manager = AgnoChunkingManager(chunk_size=1000, overlap=200)
        
        # 保持向后兼容性 - 直接访问Agno工具
        self.knowledge_tools = self.knowledge_manager.knowledge_tools
        self.reasoning_tools = self.reasoning_manager.reasoning_tools
        self.thinking_tools = self.thinking_manager.thinking_tools
        self.search_tools = self.search_manager.search_tools
        self.chunking_tools = self.chunking_manager.chunking_tools
    
    def get_knowledge_tools(self) -> KnowledgeTools:
        """获取知识工具"""
        return self.knowledge_tools
    
    def get_reasoning_tools(self) -> ReasoningTools:
        """获取推理工具"""
        return self.reasoning_tools
    
    def get_thinking_tools(self) -> ThinkingTools:
        """获取思考工具"""
        return self.thinking_tools
    
    def get_search_tools(self) -> AgenticSearch:
        """获取搜索工具"""
        return self.search_tools
    
    def get_chunking_tools(self) -> ChunkingTools:
        """获取分块工具"""
        return self.chunking_tools
    
    def get_all_agno_tools(self) -> List[Any]:
        """获取所有Agno现成工具"""
        return [
            self.knowledge_tools,
            self.reasoning_tools,
            self.thinking_tools,
            self.search_tools,
            self.chunking_tools
        ] 