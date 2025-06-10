"""
Agno框架知识库管理器适配器

将现有的ZZDSJ知识库管理器逻辑迁移到Agno框架，提供统一的知识管理和检索
根据Agno官方文档实现知识库代理和RAG系统
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict

# Agno核心导入 - 根据官方文档语法
from agno.agent import Agent
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.knowledge.text import TextKnowledgeBase
from agno.knowledge.csv import CSVKnowledgeBase
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.embedder.openai import OpenAIEmbedder
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools

# ZZDSJ内部组件导入
from .core import ZZDSJAgnoCore

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeSource:
    """知识源数据结构"""
    source_id: str
    name: str
    type: str  # "pdf", "text", "csv", "url", "file"
    path: str
    status: str  # "active", "processing", "failed", "disabled"
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = None


@dataclass
class KnowledgeBase:
    """知识库数据结构"""
    kb_id: str
    name: str
    description: str
    sources: List[str]  # source_ids
    vector_db_path: str
    embedder_model: str
    created_at: str
    updated_at: str
    status: str  # "active", "building", "failed"
    metadata: Dict[str, Any] = None


class ZZDSJAgnoKnowledgeManager:
    """ZZDSJ Agno知识库管理器适配器"""
    
    def __init__(self, storage_path: str = "tmp/agno_knowledge"):
        """初始化知识库管理器"""
        self.agno_core = ZZDSJAgnoCore()
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 知识库存储
        self.knowledge_bases: Dict[str, KnowledgeBase] = {}
        self.knowledge_sources: Dict[str, KnowledgeSource] = {}
        self.knowledge_agents: Dict[str, Agent] = {}
        
        # 默认配置
        self.default_embedder = OpenAIEmbedder(id="text-embedding-3-small")
        self.default_model = OpenAIChat(id="gpt-4o")
        
        # 初始化默认知识库代理
        self._setup_default_knowledge_agents()
        
        logger.info("Agno知识库管理器初始化完成")

    def _setup_default_knowledge_agents(self):
        """设置默认知识库代理"""
        try:
            # 通用知识问答代理
            general_qa_agent = Agent(
                model=self.default_model,
                name="General Knowledge QA Agent",
                description="通用知识问答代理，能够基于知识库回答问题",
                instructions=[
                    "基于提供的知识库内容回答用户问题",
                    "如果知识库中没有相关信息，明确告知用户",
                    "总是引用相关的知识源",
                    "保持回答的准确性和相关性"
                ],
                markdown=True
            )
            self.knowledge_agents["general_qa"] = general_qa_agent
            
            # 研究助手代理 - 结合知识库和搜索
            research_agent = Agent(
                model=self.default_model,
                name="Research Assistant Agent",
                description="研究助手代理，结合知识库和网络搜索",
                tools=[DuckDuckGoTools()],
                instructions=[
                    "首先搜索知识库中的相关信息",
                    "如果需要最新信息，使用网络搜索补充",
                    "综合知识库和搜索结果提供全面答案",
                    "明确区分知识库信息和搜索结果"
                ],
                show_tool_calls=True,
                markdown=True
            )
            self.knowledge_agents["research"] = research_agent
            
            logger.info("默认知识库代理设置完成")
            
        except Exception as e:
            logger.error(f"设置默认知识库代理失败: {e}")

    async def create_knowledge_source(
        self,
        name: str,
        source_type: str,
        path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """创建知识源"""
        try:
            source_id = str(uuid.uuid4())
            
            source = KnowledgeSource(
                source_id=source_id,
                name=name,
                type=source_type,
                path=path,
                status="processing",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                metadata=metadata or {}
            )
            
            self.knowledge_sources[source_id] = source
            
            # 验证源的可访问性
            if await self._validate_source(source):
                source.status = "active"
            else:
                source.status = "failed"
            
            source.updated_at = datetime.now().isoformat()
            
            logger.info(f"创建知识源: {source_id}, 名称: {name}, 状态: {source.status}")
            return source_id
            
        except Exception as e:
            logger.error(f"创建知识源失败: {e}")
            raise

    async def _validate_source(self, source: KnowledgeSource) -> bool:
        """验证知识源"""
        try:
            if source.type == "pdf" or source.type == "url":
                # 简单验证URL或文件路径
                return True
            elif source.type == "text":
                # 验证文本内容
                return bool(source.path)
            elif source.type == "file":
                # 验证文件存在
                return Path(source.path).exists()
            else:
                return False
        except Exception as e:
            logger.error(f"验证知识源失败: {e}")
            return False

    async def create_knowledge_base(
        self,
        name: str,
        description: str,
        source_ids: List[str],
        embedder_model: str = "text-embedding-3-small"
    ) -> str:
        """创建知识库"""
        try:
            kb_id = str(uuid.uuid4())
            
            # 验证所有源都存在且可用
            valid_sources = []
            for source_id in source_ids:
                if source_id in self.knowledge_sources:
                    source = self.knowledge_sources[source_id]
                    if source.status == "active":
                        valid_sources.append(source_id)
                    else:
                        logger.warning(f"知识源 {source_id} 状态不可用: {source.status}")
                else:
                    logger.warning(f"知识源 {source_id} 不存在")
            
            if not valid_sources:
                raise ValueError("没有可用的知识源")
            
            # 创建向量数据库路径
            vector_db_path = str(self.storage_path / f"vectordb_{kb_id}")
            
            kb = KnowledgeBase(
                kb_id=kb_id,
                name=name,
                description=description,
                sources=valid_sources,
                vector_db_path=vector_db_path,
                embedder_model=embedder_model,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                status="building"
            )
            
            self.knowledge_bases[kb_id] = kb
            
            # 异步构建知识库
            asyncio.create_task(self._build_knowledge_base(kb_id))
            
            logger.info(f"创建知识库: {kb_id}, 名称: {name}")
            return kb_id
            
        except Exception as e:
            logger.error(f"创建知识库失败: {e}")
            raise

    async def _build_knowledge_base(self, kb_id: str):
        """构建知识库"""
        try:
            kb = self.knowledge_bases[kb_id]
            
            # 收集所有知识源的URL/路径
            pdf_urls = []
            texts = []
            csv_paths = []
            
            for source_id in kb.sources:
                source = self.knowledge_sources[source_id]
                
                if source.type == "pdf" or source.type == "url":
                    pdf_urls.append(source.path)
                elif source.type == "text":
                    texts.append(source.path)
                elif source.type == "csv":
                    csv_paths.append(source.path)
            
            # 创建主要的知识库（优先使用PDF）
            main_knowledge_base = None
            
            if pdf_urls:
                main_knowledge_base = PDFUrlKnowledgeBase(
                    urls=pdf_urls,
                    vector_db=LanceDb(
                        uri=kb.vector_db_path,
                        table_name=f"kb_{kb_id}",
                        search_type=SearchType.hybrid,
                        embedder=OpenAIEmbedder(id=kb.embedder_model)
                    )
                )
            elif texts:
                main_knowledge_base = TextKnowledgeBase(
                    texts=texts,
                    vector_db=LanceDb(
                        uri=kb.vector_db_path,
                        table_name=f"kb_{kb_id}",
                        search_type=SearchType.hybrid,
                        embedder=OpenAIEmbedder(id=kb.embedder_model)
                    )
                )
            elif csv_paths:
                # 对于CSV，只使用第一个文件
                main_knowledge_base = CSVKnowledgeBase(
                    path=csv_paths[0],
                    vector_db=LanceDb(
                        uri=kb.vector_db_path,
                        table_name=f"kb_{kb_id}",
                        search_type=SearchType.hybrid,
                        embedder=OpenAIEmbedder(id=kb.embedder_model)
                    )
                )
            
            # 创建知识库代理
            if main_knowledge_base:
                kb_agent = Agent(
                    model=self.default_model,
                    name=f"KB Agent {kb.name}",
                    description=f"专门处理知识库 {kb.name} 的问答代理",
                    knowledge=main_knowledge_base,
                    instructions=[
                        f"基于知识库 '{kb.name}' 回答用户问题",
                        "优先使用知识库中的信息",
                        "如果知识库中没有相关信息，明确告知",
                        "引用具体的知识源"
                    ],
                    markdown=True
                )
                
                self.knowledge_agents[kb_id] = kb_agent
                
                # 更新知识库状态
                kb.status = "active"
                kb.updated_at = datetime.now().isoformat()
                
                logger.info(f"知识库 {kb_id} 构建完成")
            else:
                kb.status = "failed"
                kb.updated_at = datetime.now().isoformat()
                logger.error(f"知识库 {kb_id} 构建失败：没有有效的知识源")
                
        except Exception as e:
            logger.error(f"构建知识库 {kb_id} 失败: {e}")
            if kb_id in self.knowledge_bases:
                self.knowledge_bases[kb_id].status = "failed"
                self.knowledge_bases[kb_id].updated_at = datetime.now().isoformat()

    async def query_knowledge_base(
        self,
        kb_id: str,
        query: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """查询知识库"""
        try:
            if kb_id not in self.knowledge_bases:
                raise ValueError(f"知识库 {kb_id} 不存在")
            
            kb = self.knowledge_bases[kb_id]
            if kb.status != "active":
                raise ValueError(f"知识库 {kb_id} 状态不可用: {kb.status}")
            
            if kb_id not in self.knowledge_agents:
                raise ValueError(f"知识库代理 {kb_id} 不存在")
            
            agent = self.knowledge_agents[kb_id]
            
            # 使用代理查询
            response = agent.print_response(query, stream=False)
            
            return {
                "kb_id": kb_id,
                "query": query,
                "response": str(response),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"查询知识库失败: {e}")
            raise

    async def get_knowledge_base_info(self, kb_id: str) -> Optional[Dict[str, Any]]:
        """获取知识库信息"""
        try:
            if kb_id not in self.knowledge_bases:
                return None
            
            kb = self.knowledge_bases[kb_id]
            kb_dict = asdict(kb)
            
            # 添加源信息
            sources_info = []
            for source_id in kb.sources:
                if source_id in self.knowledge_sources:
                    source = self.knowledge_sources[source_id]
                    sources_info.append({
                        "source_id": source_id,
                        "name": source.name,
                        "type": source.type,
                        "status": source.status
                    })
            
            kb_dict["sources_info"] = sources_info
            return kb_dict
            
        except Exception as e:
            logger.error(f"获取知识库信息失败: {e}")
            return None

    async def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """列出所有知识库"""
        try:
            kb_list = []
            for kb_id, kb in self.knowledge_bases.items():
                kb_info = await self.get_knowledge_base_info(kb_id)
                if kb_info:
                    kb_list.append(kb_info)
            
            return sorted(kb_list, key=lambda x: x['updated_at'], reverse=True)
            
        except Exception as e:
            logger.error(f"列出知识库失败: {e}")
            return []

    async def delete_knowledge_base(self, kb_id: str) -> bool:
        """删除知识库"""
        try:
            if kb_id not in self.knowledge_bases:
                return False
            
            # 删除向量数据库文件
            kb = self.knowledge_bases[kb_id]
            vector_db_path = Path(kb.vector_db_path)
            if vector_db_path.exists():
                import shutil
                shutil.rmtree(vector_db_path)
            
            # 删除代理
            if kb_id in self.knowledge_agents:
                del self.knowledge_agents[kb_id]
            
            # 删除知识库记录
            del self.knowledge_bases[kb_id]
            
            logger.info(f"删除知识库: {kb_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除知识库失败: {e}")
            return False


# 全局知识库管理器实例
_knowledge_manager: Optional[ZZDSJAgnoKnowledgeManager] = None


def get_knowledge_manager() -> ZZDSJAgnoKnowledgeManager:
    """获取全局知识库管理器实例"""
    global _knowledge_manager
    if _knowledge_manager is None:
        _knowledge_manager = ZZDSJAgnoKnowledgeManager()
    return _knowledge_manager 