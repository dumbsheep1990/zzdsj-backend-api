"""
Agentic文档切分工具集成模块
提供与现有系统的集成接口和便利功能
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime

# 导入核心组件
from .agentic_chunking import (
    AgenticDocumentChunker,
    AgenticChunkingConfig,
    AgenticChunkingStrategy,
    ChunkQuality,
    create_agentic_chunker,
    agentic_chunk_text,
    agentic_chunk_document,
    batch_agentic_chunking
)

# 导入系统组件
from app.tools.base.document_chunking import ChunkingResult, DocumentChunk
from app.frameworks.llamaindex.embeddings import get_embedding_model
from app.utils.storage.vector_storage import get_vector_store
from app.models.knowledge import KnowledgeBase, Document
from app.utils.core.database import get_db

logger = logging.getLogger(__name__)

class AgenticChunkingToolType(str, Enum):
    """Agentic切分工具类型"""
    SEMANTIC_CHUNKER = "semantic_chunker"           # 语义切分器
    TOPIC_AWARE_CHUNKER = "topic_aware_chunker"     # 主题感知切分器
    SMART_PARAGRAPH_CHUNKER = "smart_paragraph_chunker"  # 智能段落切分器
    CONVERSATION_CHUNKER = "conversation_chunker"    # 对话切分器
    TECHNICAL_DOC_CHUNKER = "technical_doc_chunker"  # 技术文档切分器

@dataclass
class AgenticChunkingProfile:
    """Agentic切分配置文件"""
    name: str
    description: str
    strategy: AgenticChunkingStrategy
    config: AgenticChunkingConfig
    use_cases: List[str]
    recommended_for: List[str]

class AgenticChunkingToolManager:
    """Agentic切分工具管理器"""
    
    def __init__(self):
        """初始化工具管理器"""
        self.chunkers: Dict[str, AgenticDocumentChunker] = {}
        self.profiles: Dict[str, AgenticChunkingProfile] = {}
        self.stats = {
            "total_documents_processed": 0,
            "successful_processing": 0,
            "failed_processing": 0,
            "average_processing_time": 0.0,
            "total_chunks_generated": 0
        }
        
        # 初始化预定义配置文件
        self._init_predefined_profiles()
        
        logger.info("Agentic切分工具管理器初始化完成")
    
    def _init_predefined_profiles(self):
        """初始化预定义配置文件"""
        profiles = [
            AgenticChunkingProfile(
                name="semantic_chunker",
                description="基于语义边界的智能切分，适合通用文档",
                strategy=AgenticChunkingStrategy.SEMANTIC_BOUNDARY,
                config=AgenticChunkingConfig(
                    strategy=AgenticChunkingStrategy.SEMANTIC_BOUNDARY,
                    max_chunk_size=4000,
                    min_chunk_size=200,
                    chunk_overlap=150,
                    semantic_threshold=0.75,
                    quality_threshold=0.8
                ),
                use_cases=["通用文档处理", "知识库构建", "RAG系统"],
                recommended_for=["新闻文章", "博客文章", "通用文本"]
            ),
            AgenticChunkingProfile(
                name="topic_aware_chunker",
                description="主题转换感知切分，适合多主题文档",
                strategy=AgenticChunkingStrategy.TOPIC_TRANSITION,
                config=AgenticChunkingConfig(
                    strategy=AgenticChunkingStrategy.TOPIC_TRANSITION,
                    max_chunk_size=5000,
                    min_chunk_size=300,
                    chunk_overlap=200,
                    topic_coherence_weight=0.8,
                    quality_threshold=0.75
                ),
                use_cases=["多主题文档", "学术论文", "报告文档"],
                recommended_for=["研究报告", "学术文献", "综合性文档"]
            ),
            AgenticChunkingProfile(
                name="smart_paragraph_chunker",
                description="智能段落切分，保持段落完整性",
                strategy=AgenticChunkingStrategy.PARAGRAPH_AWARE,
                config=AgenticChunkingConfig(
                    strategy=AgenticChunkingStrategy.PARAGRAPH_AWARE,
                    max_chunk_size=3500,
                    min_chunk_size=150,
                    chunk_overlap=100,
                    preserve_structure=True,
                    structure_preservation_weight=0.7
                ),
                use_cases=["结构化文档", "书籍章节", "教学材料"],
                recommended_for=["教科书", "手册", "结构化文档"]
            ),
            AgenticChunkingProfile(
                name="conversation_chunker",
                description="对话流切分，适合对话和问答内容",
                strategy=AgenticChunkingStrategy.CONVERSATION_FLOW,
                config=AgenticChunkingConfig(
                    strategy=AgenticChunkingStrategy.CONVERSATION_FLOW,
                    max_chunk_size=2500,
                    min_chunk_size=100,
                    chunk_overlap=50,
                    preserve_structure=True
                ),
                use_cases=["客服对话", "问答记录", "聊天记录"],
                recommended_for=["客服记录", "FAQ", "对话数据"]
            ),
            AgenticChunkingProfile(
                name="technical_doc_chunker",
                description="技术文档切分，保留代码和技术结构",
                strategy=AgenticChunkingStrategy.TECHNICAL_DOCUMENT,
                config=AgenticChunkingConfig(
                    strategy=AgenticChunkingStrategy.TECHNICAL_DOCUMENT,
                    max_chunk_size=6000,
                    min_chunk_size=200,
                    chunk_overlap=300,
                    preserve_structure=True,
                    quality_threshold=0.85
                ),
                use_cases=["技术文档", "API文档", "代码注释"],
                recommended_for=["技术规范", "开发文档", "API手册"]
            )
        ]
        
        for profile in profiles:
            self.profiles[profile.name] = profile
    
    def get_chunker(self, tool_type: str) -> AgenticDocumentChunker:
        """获取或创建切分器"""
        if tool_type not in self.chunkers:
            if tool_type not in self.profiles:
                raise ValueError(f"未知的切分工具类型: {tool_type}")
            
            profile = self.profiles[tool_type]
            self.chunkers[tool_type] = AgenticDocumentChunker(profile.config)
        
        return self.chunkers[tool_type]
    
    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """获取可用工具列表"""
        tools = {}
        for name, profile in self.profiles.items():
            tools[name] = {
                "name": profile.name,
                "description": profile.description,
                "strategy": profile.strategy.value,
                "use_cases": profile.use_cases,
                "recommended_for": profile.recommended_for,
                "config": profile.config.to_dict()
            }
        return tools
    
    async def chunk_with_tool(self, 
                            content: str,
                            tool_type: str,
                            metadata: Optional[Dict[str, Any]] = None) -> ChunkingResult:
        """使用指定工具进行切分"""
        start_time = datetime.now()
        
        try:
            chunker = self.get_chunker(tool_type)
            result = await chunker.chunk_document(content, metadata)
            
            # 更新统计
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(len(result.chunks), True, processing_time)
            
            return result
            
        except Exception as e:
            logger.error(f"切分失败 (工具: {tool_type}): {str(e)}")
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(0, False, processing_time)
            raise
    
    async def auto_select_and_chunk(self, 
                                  content: str,
                                  content_type: Optional[str] = None,
                                  metadata: Optional[Dict[str, Any]] = None) -> ChunkingResult:
        """自动选择最佳工具并进行切分"""
        # 分析内容特征
        tool_type = self._analyze_content_and_select_tool(content, content_type, metadata)
        
        logger.info(f"自动选择切分工具: {tool_type}")
        
        return await self.chunk_with_tool(content, tool_type, metadata)
    
    def _analyze_content_and_select_tool(self, 
                                       content: str,
                                       content_type: Optional[str] = None,
                                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """分析内容特征并选择最佳工具"""
        content_lower = content.lower()
        
        # 基于内容类型的选择
        if content_type:
            type_mapping = {
                "conversation": "conversation_chunker",
                "dialogue": "conversation_chunker",
                "chat": "conversation_chunker",
                "technical": "technical_doc_chunker",
                "api": "technical_doc_chunker",
                "code": "technical_doc_chunker",
                "manual": "smart_paragraph_chunker",
                "book": "smart_paragraph_chunker",
                "academic": "topic_aware_chunker",
                "research": "topic_aware_chunker",
                "report": "topic_aware_chunker"
            }
            
            for key, tool in type_mapping.items():
                if key in content_type.lower():
                    return tool
        
        # 基于内容特征的选择
        
        # 检查是否是对话内容
        dialogue_indicators = ['问:', '答:', 'Q:', 'A:', '用户:', '客服:', '助手:']
        if any(indicator in content for indicator in dialogue_indicators):
            return "conversation_chunker"
        
        # 检查是否是技术文档
        tech_indicators = ['```', 'def ', 'class ', 'function', 'import ', '#include', 'API', 'endpoint']
        if any(indicator in content for indicator in tech_indicators):
            return "technical_doc_chunker"
        
        # 检查段落结构
        paragraph_count = content.count('\n\n')
        if paragraph_count > 5 and len(content) > 2000:
            return "smart_paragraph_chunker"
        
        # 检查主题多样性（简化检测）
        topic_keywords = ['第一', '第二', '第三', '首先', '其次', '最后', '另外', '此外']
        topic_indicators = sum(1 for keyword in topic_keywords if keyword in content)
        if topic_indicators > 3:
            return "topic_aware_chunker"
        
        # 默认使用语义切分
        return "semantic_chunker"
    
    async def batch_chunk_documents(self, 
                                  documents: List[Dict[str, Any]],
                                  auto_select: bool = True,
                                  default_tool: str = "semantic_chunker",
                                  max_workers: int = 5) -> List[ChunkingResult]:
        """批量处理文档"""
        semaphore = asyncio.Semaphore(max_workers)
        
        async def process_document(doc: Dict[str, Any]) -> ChunkingResult:
            async with semaphore:
                content = doc.get("content", "")
                content_type = doc.get("content_type")
                metadata = doc.get("metadata", {})
                
                if auto_select:
                    return await self.auto_select_and_chunk(content, content_type, metadata)
                else:
                    tool_type = doc.get("tool_type", default_tool)
                    return await self.chunk_with_tool(content, tool_type, metadata)
        
        tasks = [process_document(doc) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"文档 {i} 处理失败: {str(result)}")
                final_results.append(ChunkingResult(
                    chunks=[],
                    total_chunks=0,
                    chunk_sizes=[],
                    processing_metadata={"error": str(result), "document_index": i}
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    def create_custom_profile(self, 
                            name: str,
                            description: str,
                            config: AgenticChunkingConfig,
                            use_cases: List[str] = None,
                            recommended_for: List[str] = None) -> str:
        """创建自定义配置文件"""
        profile = AgenticChunkingProfile(
            name=name,
            description=description,
            strategy=config.strategy,
            config=config,
            use_cases=use_cases or [],
            recommended_for=recommended_for or []
        )
        
        self.profiles[name] = profile
        logger.info(f"创建自定义配置文件: {name}")
        
        return name
    
    def _update_stats(self, chunk_count: int, success: bool, processing_time: float):
        """更新统计信息"""
        self.stats["total_documents_processed"] += 1
        
        if success:
            self.stats["successful_processing"] += 1
            self.stats["total_chunks_generated"] += chunk_count
        else:
            self.stats["failed_processing"] += 1
        
        # 更新平均处理时间
        total_docs = self.stats["total_documents_processed"]
        current_avg = self.stats["average_processing_time"]
        self.stats["average_processing_time"] = (
            (current_avg * (total_docs - 1) + processing_time) / total_docs
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_documents_processed": 0,
            "successful_processing": 0,
            "failed_processing": 0,
            "average_processing_time": 0.0,
            "total_chunks_generated": 0
        }

# 全局工具管理器实例
_agentic_chunking_manager = None

def get_agentic_chunking_manager() -> AgenticChunkingToolManager:
    """获取全局Agentic切分工具管理器"""
    global _agentic_chunking_manager
    if _agentic_chunking_manager is None:
        _agentic_chunking_manager = AgenticChunkingToolManager()
    return _agentic_chunking_manager

# 便利函数

async def smart_chunk_text(content: str,
                         content_type: Optional[str] = None,
                         tool_type: Optional[str] = None,
                         **kwargs) -> ChunkingResult:
    """智能文本切分便利函数"""
    manager = get_agentic_chunking_manager()
    
    if tool_type:
        return await manager.chunk_with_tool(content, tool_type, kwargs.get("metadata"))
    else:
        return await manager.auto_select_and_chunk(content, content_type, kwargs.get("metadata"))

async def smart_chunk_knowledge_base(kb_id: str,
                                   auto_select: bool = True,
                                   tool_type: str = "semantic_chunker",
                                   batch_size: int = 10) -> Dict[str, Any]:
    """智能切分知识库文档"""
    try:
        db = next(get_db())
        
        # 获取知识库
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise ValueError(f"知识库不存在: {kb_id}")
        
        # 获取文档
        documents = db.query(Document).filter(Document.knowledge_base_id == kb_id).all()
        
        if not documents:
            return {"status": "success", "message": "知识库中没有文档", "results": []}
        
        logger.info(f"开始切分知识库 {kb_id} 中的 {len(documents)} 个文档")
        
        # 准备文档数据
        doc_data = []
        for doc in documents:
            doc_data.append({
                "content": doc.content or "",
                "content_type": doc.mime_type,
                "metadata": {
                    "document_id": doc.id,
                    "title": doc.title,
                    "file_path": doc.file_path,
                    "original_metadata": doc.metadata
                }
            })
        
        # 批量处理
        manager = get_agentic_chunking_manager()
        
        all_results = []
        for i in range(0, len(doc_data), batch_size):
            batch = doc_data[i:i + batch_size]
            batch_results = await manager.batch_chunk_documents(
                batch, 
                auto_select=auto_select, 
                default_tool=tool_type
            )
            all_results.extend(batch_results)
        
        # 统计结果
        total_chunks = sum(result.total_chunks for result in all_results)
        successful_docs = sum(1 for result in all_results if result.total_chunks > 0)
        
        return {
            "status": "success",
            "knowledge_base_id": kb_id,
            "total_documents": len(documents),
            "successful_documents": successful_docs,
            "total_chunks": total_chunks,
            "results": all_results,
            "stats": manager.get_stats()
        }
        
    except Exception as e:
        logger.error(f"知识库切分失败: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "knowledge_base_id": kb_id
        }

def get_chunking_recommendations(content_sample: str, 
                               content_type: Optional[str] = None) -> Dict[str, Any]:
    """获取切分建议"""
    manager = get_agentic_chunking_manager()
    
    # 分析内容
    recommended_tool = manager._analyze_content_and_select_tool(content_sample, content_type)
    available_tools = manager.get_available_tools()
    
    # 内容特征分析
    content_length = len(content_sample)
    paragraph_count = content_sample.count('\n\n')
    sentence_count = len([s for s in content_sample.split('.') if s.strip()])
    
    features = {
        "content_length": content_length,
        "paragraph_count": paragraph_count,
        "sentence_count": sentence_count,
        "estimated_chunks": max(1, content_length // 2000),  # 估算块数
        "complexity": "high" if paragraph_count > 10 else "medium" if paragraph_count > 3 else "low"
    }
    
    return {
        "recommended_tool": recommended_tool,
        "recommended_config": available_tools[recommended_tool],
        "content_features": features,
        "all_available_tools": available_tools,
        "recommendations": [
            f"基于内容分析，推荐使用 {recommended_tool}",
            f"预计生成约 {features['estimated_chunks']} 个文档块",
            f"内容复杂度: {features['complexity']}"
        ]
    }

# 导出主要组件
__all__ = [
    "AgenticChunkingToolManager",
    "AgenticChunkingProfile",
    "AgenticChunkingToolType",
    "get_agentic_chunking_manager",
    "smart_chunk_text",
    "smart_chunk_knowledge_base",
    "get_chunking_recommendations"
] 