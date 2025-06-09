"""
Agentic文档切分工具
基于Agno框架的智能文档切分，使用LLM确定语义边界和自然断点
提供比传统固定大小切分更智能的文档分段能力
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
import hashlib
from datetime import datetime
import json
import re

# 导入LLM模型
from app.frameworks.llamaindex.llm import get_llm_model
from app.utils.core.database import get_db
from app.models.knowledge import Document
from app.tools.base.document_chunking import ChunkingResult, DocumentChunk

logger = logging.getLogger(__name__)

class AgenticChunkingStrategy(str, Enum):
    """Agentic切分策略枚举"""
    SEMANTIC_BOUNDARY = "semantic_boundary"      # 语义边界切分
    TOPIC_TRANSITION = "topic_transition"       # 主题转换切分
    PARAGRAPH_AWARE = "paragraph_aware"         # 段落感知切分
    CONVERSATION_FLOW = "conversation_flow"     # 对话流切分
    TECHNICAL_DOCUMENT = "technical_document"   # 技术文档切分

@dataclass
class AgenticChunkingConfig:
    """Agentic切分配置"""
    strategy: AgenticChunkingStrategy = AgenticChunkingStrategy.SEMANTIC_BOUNDARY
    max_chunk_size: int = 5000                 # 最大块大小（字符数）
    min_chunk_size: int = 100                  # 最小块大小
    chunk_overlap: int = 200                   # 块重叠大小
    llm_model: str = "gpt-4o-mini"             # 用于切分的LLM模型
    language: str = "zh"                       # 文档语言
    preserve_structure: bool = True            # 是否保留文档结构
    quality_threshold: float = 0.8             # 切分质量阈值
    max_retries: int = 3                       # 最大重试次数
    
    # 策略特定配置
    semantic_threshold: float = 0.7            # 语义相似度阈值
    topic_coherence_weight: float = 0.6        # 主题一致性权重
    structure_preservation_weight: float = 0.4 # 结构保留权重
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy": self.strategy.value,
            "max_chunk_size": self.max_chunk_size,
            "min_chunk_size": self.min_chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "llm_model": self.llm_model,
            "language": self.language,
            "preserve_structure": self.preserve_structure,
            "quality_threshold": self.quality_threshold,
            "max_retries": self.max_retries,
            "semantic_threshold": self.semantic_threshold,
            "topic_coherence_weight": self.topic_coherence_weight,
            "structure_preservation_weight": self.structure_preservation_weight
        }

@dataclass
class ChunkQuality:
    """切分质量评估"""
    semantic_coherence: float = 0.0          # 语义连贯性得分
    size_appropriateness: float = 0.0        # 大小合适性得分
    boundary_naturalness: float = 0.0        # 边界自然性得分
    structure_preservation: float = 0.0      # 结构保留得分
    overall_score: float = 0.0               # 总体得分
    
    def calculate_overall_score(self):
        """计算总体得分"""
        self.overall_score = (
            self.semantic_coherence * 0.3 +
            self.size_appropriateness * 0.2 +
            self.boundary_naturalness * 0.3 +
            self.structure_preservation * 0.2
        )
        return self.overall_score

class AgenticDocumentChunker:
    """Agentic文档切分器"""
    
    def __init__(self, config: AgenticChunkingConfig = None):
        """
        初始化Agentic文档切分器
        
        Args:
            config: 切分配置
        """
        self.config = config or AgenticChunkingConfig()
        self.llm = None
        self._init_llm()
        
        # 切分统计
        self.stats = {
            "total_processed": 0,
            "successful_chunks": 0,
            "failed_chunks": 0,
            "average_quality": 0.0,
            "processing_time": 0.0
        }
        
        logger.info(f"初始化Agentic文档切分器: {self.config.strategy.value}")
    
    def _init_llm(self):
        """初始化LLM模型"""
        try:
            self.llm = get_llm_model(self.config.llm_model)
            logger.info(f"LLM模型初始化成功: {self.config.llm_model}")
        except Exception as e:
            logger.error(f"LLM模型初始化失败: {str(e)}")
            self.llm = None
    
    async def chunk_document(self, 
                           content: str, 
                           metadata: Optional[Dict[str, Any]] = None) -> ChunkingResult:
        """
        对文档进行Agentic切分
        
        Args:
            content: 文档内容
            metadata: 文档元数据
            
        Returns:
            切分结果
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"开始Agentic文档切分，策略: {self.config.strategy.value}")
            
            # 预处理文档
            processed_content = self._preprocess_content(content)
            
            # 创建初始小块
            mini_chunks = self._create_mini_chunks(processed_content)
            
            # 使用LLM进行智能分组
            grouped_chunks = await self._llm_group_chunks(mini_chunks, metadata)
            
            # 后处理和优化
            final_chunks = self._post_process_chunks(grouped_chunks, processed_content)
            
            # 质量评估
            quality_scores = self._evaluate_chunk_quality(final_chunks, processed_content)
            
            # 创建结果
            result = self._create_chunking_result(final_chunks, quality_scores, metadata)
            
            # 更新统计
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(len(final_chunks), True, processing_time, quality_scores)
            
            logger.info(f"Agentic切分完成，生成 {len(final_chunks)} 个块")
            return result
            
        except Exception as e:
            logger.error(f"Agentic文档切分失败: {str(e)}")
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(0, False, processing_time, [])
            
            # 回退到基础切分
            return await self._fallback_chunking(content, metadata)
    
    def _preprocess_content(self, content: str) -> str:
        """预处理文档内容"""
        # 清理多余空白
        content = re.sub(r'\s+', ' ', content.strip())
        
        # 保留重要结构标记
        if self.config.preserve_structure:
            # 保留段落标记
            content = re.sub(r'\n\s*\n', '\n\n', content)
            # 保留标题标记
            content = re.sub(r'([.!?])\s*\n+([A-Z])', r'\1\n\n\2', content)
        
        return content
    
    def _create_mini_chunks(self, content: str) -> List[str]:
        """创建初始小块"""
        mini_chunk_size = 300  # 约300字符的小块
        sentences = self._split_into_sentences(content)
        
        mini_chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= mini_chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk.strip():
                    mini_chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
        
        if current_chunk.strip():
            mini_chunks.append(current_chunk.strip())
        
        return mini_chunks
    
    def _split_into_sentences(self, content: str) -> List[str]:
        """将文本分割为句子"""
        # 简单的句子分割（可以用更复杂的NLP工具替换）
        sentence_endings = r'[.!?]+[\s\n]+'
        sentences = re.split(sentence_endings, content)
        return [s.strip() for s in sentences if s.strip()]
    
    async def _llm_group_chunks(self, 
                              mini_chunks: List[str], 
                              metadata: Optional[Dict[str, Any]] = None) -> List[List[str]]:
        """使用LLM对小块进行智能分组"""
        if not self.llm:
            logger.warning("LLM不可用，使用默认分组策略")
            return self._default_grouping(mini_chunks)
        
        try:
            # 构建提示词
            prompt = self._build_chunking_prompt(mini_chunks, metadata)
            
            # 调用LLM
            response = await self._call_llm(prompt)
            
            # 解析LLM响应
            grouped_chunks = self._parse_llm_response(response, mini_chunks)
            
            return grouped_chunks
            
        except Exception as e:
            logger.error(f"LLM分组失败: {str(e)}")
            return self._default_grouping(mini_chunks)
    
    def _build_chunking_prompt(self, 
                              mini_chunks: List[str], 
                              metadata: Optional[Dict[str, Any]] = None) -> str:
        """构建切分提示词"""
        strategy_instructions = self._get_strategy_instructions()
        
        # 标记小块
        marked_chunks = []
        for i, chunk in enumerate(mini_chunks):
            marked_chunks.append(f"[CHUNK_{i}] {chunk}")
        
        prompt = f"""
你是一个专业的文档切分专家。请分析以下已标记的文本小块，并将它们分组为语义连贯的大块。

切分策略: {self.config.strategy.value}
语言: {self.config.language}
最大块大小: {self.config.max_chunk_size} 字符
最小块大小: {self.config.min_chunk_size} 字符

{strategy_instructions}

已标记的文本小块:
{chr(10).join(marked_chunks)}

请按照以下JSON格式返回分组结果:
{{
    "groups": [
        {{"chunk_ids": [0, 1, 2], "reasoning": "原因说明"}},
        {{"chunk_ids": [3, 4], "reasoning": "原因说明"}},
        ...
    ],
    "quality_assessment": "整体切分质量评估"
}}

要求:
1. 每组的总字符数不应超过{self.config.max_chunk_size}
2. 每组应包含语义相关的内容
3. 保持文本的逻辑连贯性
4. 在自然的段落或主题边界处分割
"""
        
        if metadata:
            prompt += f"\n文档元数据: {json.dumps(metadata, ensure_ascii=False)}"
        
        return prompt
    
    def _get_strategy_instructions(self) -> str:
        """获取策略特定的指令"""
        instructions = {
            AgenticChunkingStrategy.SEMANTIC_BOUNDARY: """
优先在语义边界处分割，确保每个块包含完整的语义单元。
关注句子和段落的语义连贯性。
""",
            AgenticChunkingStrategy.TOPIC_TRANSITION: """
在主题转换的自然边界处分割。
识别主题变化的信号，如新段落、标题或话题转折。
""",
            AgenticChunkingStrategy.PARAGRAPH_AWARE: """
尊重段落结构，优先在段落边界分割。
保持段落内容的完整性，避免中途打断。
""",
            AgenticChunkingStrategy.CONVERSATION_FLOW: """
适合对话或问答格式的内容。
保持问答对的完整性，按对话轮次分组。
""",
            AgenticChunkingStrategy.TECHNICAL_DOCUMENT: """
适合技术文档，保留代码块、列表和技术术语的完整性。
在技术概念的自然边界处分割。
"""
        }
        
        return instructions.get(self.config.strategy, instructions[AgenticChunkingStrategy.SEMANTIC_BOUNDARY])
    
    async def _call_llm(self, prompt: str) -> str:
        """调用LLM"""
        try:
            # 这里需要根据实际的LLM接口进行调用
            # 假设使用OpenAI或类似的接口
            response = await self.llm.acomplete(prompt)
            return response.text if hasattr(response, 'text') else str(response)
        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}")
            raise
    
    def _parse_llm_response(self, response: str, mini_chunks: List[str]) -> List[List[str]]:
        """解析LLM响应"""
        try:
            # 提取JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                raise ValueError("无法找到JSON响应")
            
            data = json.loads(json_match.group())
            groups = data.get('groups', [])
            
            # 转换为字符串列表
            grouped_chunks = []
            for group in groups:
                chunk_ids = group.get('chunk_ids', [])
                group_chunks = [mini_chunks[i] for i in chunk_ids if 0 <= i < len(mini_chunks)]
                if group_chunks:
                    grouped_chunks.append(group_chunks)
            
            return grouped_chunks
            
        except Exception as e:
            logger.error(f"解析LLM响应失败: {str(e)}")
            return self._default_grouping(mini_chunks)
    
    def _default_grouping(self, mini_chunks: List[str]) -> List[List[str]]:
        """默认分组策略（回退方案）"""
        grouped_chunks = []
        current_group = []
        current_size = 0
        
        for chunk in mini_chunks:
            chunk_size = len(chunk)
            
            if current_size + chunk_size <= self.config.max_chunk_size:
                current_group.append(chunk)
                current_size += chunk_size
            else:
                if current_group:
                    grouped_chunks.append(current_group)
                current_group = [chunk]
                current_size = chunk_size
        
        if current_group:
            grouped_chunks.append(current_group)
        
        return grouped_chunks
    
    def _post_process_chunks(self, 
                           grouped_chunks: List[List[str]], 
                           original_content: str) -> List[DocumentChunk]:
        """后处理和优化切分结果"""
        final_chunks = []
        
        for i, group in enumerate(grouped_chunks):
            # 合并组内容
            content = " ".join(group).strip()
            
            # 跳过过小的块
            if len(content) < self.config.min_chunk_size:
                continue
            
            # 创建文档块
            chunk = DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                content=content,
                start_index=self._find_content_start(content, original_content),
                end_index=self._find_content_end(content, original_content),
                metadata={
                    "chunk_index": i,
                    "chunk_size": len(content),
                    "mini_chunks_count": len(group),
                    "strategy": self.config.strategy.value,
                    "language": self.config.language
                }
            )
            
            final_chunks.append(chunk)
        
        # 添加重叠内容
        if self.config.chunk_overlap > 0:
            final_chunks = self._add_chunk_overlap(final_chunks)
        
        return final_chunks
    
    def _find_content_start(self, content: str, original: str) -> int:
        """查找内容在原文中的起始位置"""
        # 简化实现，实际可能需要更复杂的匹配算法
        start = original.find(content[:50])  # 使用前50个字符匹配
        return max(0, start)
    
    def _find_content_end(self, content: str, original: str) -> int:
        """查找内容在原文中的结束位置"""
        start = self._find_content_start(content, original)
        return start + len(content)
    
    def _add_chunk_overlap(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """添加块重叠"""
        if len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = []
        
        for i, chunk in enumerate(chunks):
            content = chunk.content
            
            # 添加前一个块的结尾
            if i > 0:
                prev_chunk = chunks[i-1]
                overlap_size = min(self.config.chunk_overlap, len(prev_chunk.content))
                overlap_content = prev_chunk.content[-overlap_size:]
                content = overlap_content + " " + content
            
            # 添加下一个块的开头
            if i < len(chunks) - 1:
                next_chunk = chunks[i+1]
                overlap_size = min(self.config.chunk_overlap, len(next_chunk.content))
                overlap_content = next_chunk.content[:overlap_size]
                content = content + " " + overlap_content
            
            # 更新块内容
            chunk.content = content
            chunk.metadata["has_overlap"] = i > 0 or i < len(chunks) - 1
            overlapped_chunks.append(chunk)
        
        return overlapped_chunks
    
    def _evaluate_chunk_quality(self, 
                               chunks: List[DocumentChunk], 
                               original_content: str) -> List[ChunkQuality]:
        """评估切分质量"""
        quality_scores = []
        
        for chunk in chunks:
            quality = ChunkQuality()
            
            # 语义连贯性（简化评估）
            quality.semantic_coherence = self._evaluate_semantic_coherence(chunk.content)
            
            # 大小合适性
            quality.size_appropriateness = self._evaluate_size_appropriateness(chunk.content)
            
            # 边界自然性
            quality.boundary_naturalness = self._evaluate_boundary_naturalness(chunk.content)
            
            # 结构保留
            quality.structure_preservation = self._evaluate_structure_preservation(chunk.content)
            
            # 计算总体得分
            quality.calculate_overall_score()
            
            quality_scores.append(quality)
        
        return quality_scores
    
    def _evaluate_semantic_coherence(self, content: str) -> float:
        """评估语义连贯性"""
        # 简化实现：检查句子完整性和连接词
        sentences = self._split_into_sentences(content)
        if not sentences:
            return 0.0
        
        # 检查句子完整性
        complete_sentences = sum(1 for s in sentences if s.strip().endswith(('.', '!', '?', '。', '！', '？')))
        completeness_score = complete_sentences / len(sentences)
        
        # 检查连接词
        connectives = ['因此', '所以', '但是', '然而', '而且', '并且', '另外', '此外']
        has_connectives = any(conn in content for conn in connectives)
        
        return (completeness_score + (0.1 if has_connectives else 0)) * 0.9
    
    def _evaluate_size_appropriateness(self, content: str) -> float:
        """评估大小合适性"""
        size = len(content)
        
        if size < self.config.min_chunk_size:
            return 0.0
        elif size > self.config.max_chunk_size:
            return 0.5
        else:
            # 理想大小范围
            ideal_min = self.config.max_chunk_size * 0.3
            ideal_max = self.config.max_chunk_size * 0.8
            
            if ideal_min <= size <= ideal_max:
                return 1.0
            elif size < ideal_min:
                return size / ideal_min
            else:
                return ideal_max / size
    
    def _evaluate_boundary_naturalness(self, content: str) -> float:
        """评估边界自然性"""
        # 检查开头和结尾是否自然
        content = content.strip()
        
        # 开头检查
        starts_naturally = (
            content[0].isupper() or  # 大写字母开头
            content.startswith(('第', '一', '二', '三', '四', '五')) or  # 数字开头
            content.startswith(('在', '当', '如果', '虽然'))  # 常见句子开头
        )
        
        # 结尾检查
        ends_naturally = content.endswith(('.', '。', '!', '！', '?', '？'))
        
        return (0.5 if starts_naturally else 0.0) + (0.5 if ends_naturally else 0.0)
    
    def _evaluate_structure_preservation(self, content: str) -> float:
        """评估结构保留"""
        if not self.config.preserve_structure:
            return 1.0
        
        # 检查是否保留了段落结构
        has_paragraphs = '\n\n' in content
        has_lists = any(marker in content for marker in ['1.', '2.', '•', '-'])
        
        return 0.5 + (0.25 if has_paragraphs else 0.0) + (0.25 if has_lists else 0.0)
    
    def _create_chunking_result(self, 
                              chunks: List[DocumentChunk], 
                              quality_scores: List[ChunkQuality],
                              metadata: Optional[Dict[str, Any]] = None) -> ChunkingResult:
        """创建切分结果"""
        # 计算平均质量分数
        avg_quality = sum(q.overall_score for q in quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        return ChunkingResult(
            chunks=chunks,
            total_chunks=len(chunks),
            chunk_sizes=[len(chunk.content) for chunk in chunks],
            processing_metadata={
                "strategy": self.config.strategy.value,
                "average_quality": avg_quality,
                "config": self.config.to_dict(),
                "quality_scores": [
                    {
                        "semantic_coherence": q.semantic_coherence,
                        "size_appropriateness": q.size_appropriateness,
                        "boundary_naturalness": q.boundary_naturalness,
                        "structure_preservation": q.structure_preservation,
                        "overall_score": q.overall_score
                    } for q in quality_scores
                ],
                "original_metadata": metadata
            }
        )
    
    async def _fallback_chunking(self, 
                                content: str, 
                                metadata: Optional[Dict[str, Any]] = None) -> ChunkingResult:
        """回退切分方案"""
        logger.info("使用回退切分方案")
        
        # 简单的句子边界切分
        sentences = self._split_into_sentences(content)
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.config.max_chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk.strip():
                    chunk = DocumentChunk(
                        chunk_id=str(uuid.uuid4()),
                        content=current_chunk.strip(),
                        start_index=0,  # 简化实现
                        end_index=len(current_chunk),
                        metadata={
                            "chunk_index": chunk_index,
                            "chunk_size": len(current_chunk.strip()),
                            "is_fallback": True,
                            "strategy": "fallback_sentence_boundary"
                        }
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                current_chunk = sentence + " "
        
        if current_chunk.strip():
            chunk = DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                content=current_chunk.strip(),
                start_index=0,
                end_index=len(current_chunk),
                metadata={
                    "chunk_index": chunk_index,
                    "chunk_size": len(current_chunk.strip()),
                    "is_fallback": True,
                    "strategy": "fallback_sentence_boundary"
                }
            )
            chunks.append(chunk)
        
        return ChunkingResult(
            chunks=chunks,
            total_chunks=len(chunks),
            chunk_sizes=[len(chunk.content) for chunk in chunks],
            processing_metadata={
                "strategy": "fallback",
                "is_fallback": True,
                "original_strategy": self.config.strategy.value,
                "original_metadata": metadata
            }
        )
    
    def _update_stats(self, 
                     chunk_count: int, 
                     success: bool, 
                     processing_time: float,
                     quality_scores: List[ChunkQuality]):
        """更新统计信息"""
        self.stats["total_processed"] += 1
        if success:
            self.stats["successful_chunks"] += chunk_count
            if quality_scores:
                avg_quality = sum(q.overall_score for q in quality_scores) / len(quality_scores)
                self.stats["average_quality"] = (
                    (self.stats["average_quality"] * (self.stats["total_processed"] - 1) + avg_quality) /
                    self.stats["total_processed"]
                )
        else:
            self.stats["failed_chunks"] += 1
        
        self.stats["processing_time"] += processing_time
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
    
    def update_config(self, new_config: AgenticChunkingConfig):
        """更新配置"""
        self.config = new_config
        self._init_llm()
        logger.info(f"配置已更新: {self.config.strategy.value}")

# 工厂函数和便利接口

def create_agentic_chunker(strategy: AgenticChunkingStrategy = AgenticChunkingStrategy.SEMANTIC_BOUNDARY,
                          max_chunk_size: int = 5000,
                          **kwargs) -> AgenticDocumentChunker:
    """创建Agentic文档切分器"""
    config = AgenticChunkingConfig(
        strategy=strategy,
        max_chunk_size=max_chunk_size,
        **kwargs
    )
    return AgenticDocumentChunker(config)

async def agentic_chunk_text(content: str,
                           strategy: AgenticChunkingStrategy = AgenticChunkingStrategy.SEMANTIC_BOUNDARY,
                           max_chunk_size: int = 5000,
                           **kwargs) -> ChunkingResult:
    """便利函数：对文本进行Agentic切分"""
    chunker = create_agentic_chunker(strategy, max_chunk_size, **kwargs)
    return await chunker.chunk_document(content)

async def agentic_chunk_document(document_id: str,
                               strategy: AgenticChunkingStrategy = AgenticChunkingStrategy.SEMANTIC_BOUNDARY,
                               **kwargs) -> ChunkingResult:
    """便利函数：对数据库中的文档进行Agentic切分"""
    try:
        # 获取数据库会话
        db = next(get_db())
        
        # 查询文档
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"文档不存在: {document_id}")
        
        # 准备元数据
        metadata = {
            "document_id": document_id,
            "title": document.title,
            "mime_type": document.mime_type,
            "file_path": document.file_path,
            "original_metadata": document.metadata
        }
        
        # 执行切分
        chunker = create_agentic_chunker(strategy, **kwargs)
        result = await chunker.chunk_document(document.content, metadata)
        
        return result
        
    except Exception as e:
        logger.error(f"文档切分失败: {str(e)}")
        raise

# 批量处理功能

async def batch_agentic_chunking(contents: List[str],
                               strategy: AgenticChunkingStrategy = AgenticChunkingStrategy.SEMANTIC_BOUNDARY,
                               max_workers: int = 5,
                               **kwargs) -> List[ChunkingResult]:
    """批量Agentic切分"""
    chunker = create_agentic_chunker(strategy, **kwargs)
    
    # 使用信号量控制并发
    semaphore = asyncio.Semaphore(max_workers)
    
    async def process_content(content: str) -> ChunkingResult:
        async with semaphore:
            return await chunker.chunk_document(content)
    
    # 并发处理
    tasks = [process_content(content) for content in contents]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 处理异常
    final_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"批量处理中的错误: {str(result)}")
            # 创建一个空结果
            final_results.append(ChunkingResult(
                chunks=[],
                total_chunks=0,
                chunk_sizes=[],
                processing_metadata={"error": str(result)}
            ))
        else:
            final_results.append(result)
    
    return final_results

if __name__ == "__main__":
    # 示例用法
    async def main():
        # 示例文本
        sample_text = """
        人工智能（Artificial Intelligence，简称AI）是计算机科学的一个分支，它企图了解智能的实质，
        并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
        
        机器学习是人工智能的一个重要分支，它让计算机能够不需要明确编程就能学习。
        机器学习专注于开发能够访问数据并利用数据学习的计算机程序。
        
        深度学习是机器学习的一个子集，它模仿人脑的工作方式来处理数据并创建用于决策的模式。
        深度学习使用多层神经网络来建模和理解复杂模式。
        """
        
        # 测试不同策略
        strategies = [
            AgenticChunkingStrategy.SEMANTIC_BOUNDARY,
            AgenticChunkingStrategy.TOPIC_TRANSITION,
            AgenticChunkingStrategy.PARAGRAPH_AWARE
        ]
        
        for strategy in strategies:
            print(f"\n=== 测试策略: {strategy.value} ===")
            
            try:
                result = await agentic_chunk_text(
                    sample_text,
                    strategy=strategy,
                    max_chunk_size=1000,
                    language="zh"
                )
                
                print(f"生成块数: {result.total_chunks}")
                print(f"平均质量: {result.processing_metadata.get('average_quality', 0):.2f}")
                
                for i, chunk in enumerate(result.chunks):
                    print(f"\n块 {i+1} (大小: {len(chunk.content)}):")
                    print(chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content)
                    
            except Exception as e:
                print(f"策略 {strategy.value} 测试失败: {str(e)}")
    
    # 运行示例
    asyncio.run(main()) 