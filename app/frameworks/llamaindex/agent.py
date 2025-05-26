"""
LlamaIndex代理模块: 提供与LLM代理交互功能
替代LangChain作为统一入口点
"""

from typing import List, Dict, Any, Optional
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.agent import ReActAgent
from llama_index.agent.openai import OpenAIAgent
from app.frameworks.llamaindex.core import get_llm, get_service_context
from app.frameworks.llamaindex.retrieval import get_query_engine
from app.repositories.knowledge import KnowledgeBaseRepository
from app.config import settings
import logging
# 导入统一知识库服务
from app.services.unified_knowledge_service import get_unified_knowledge_service

logger = logging.getLogger(__name__)

class KnowledgeAgent:
    """LlamaIndex知识代理类，替代LangChain代理"""
    
    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        model: Optional[str] = None,
        knowledge_bases: Optional[List[str]] = None,
        settings_data: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.description = description
        self.model = model or settings.DEFAULT_MODEL
        self.settings_data = settings_data or {}
        self.knowledge_bases = knowledge_bases or []
        
        # 初始化代理
        self.service_context = get_service_context(model_name=self.model)
        # 移除同步初始化，改为在需要时异步初始化
        self.agent = None
    
    async def _initialize_agent(self):
        """初始化LlamaIndex代理"""
        try:
            # 获取查询引擎工具
            tools = await self._get_knowledge_tools()
            
            # 添加MCP工具
            from app.frameworks.llamaindex.tools import get_all_mcp_tools
            mcp_tools = get_all_mcp_tools()
            tools.extend(mcp_tools)
            
            # 获取系统消息
            system_prompt = self.settings_data.get("system_prompt", "")
            if not system_prompt:
                system_prompt = f"你是{self.name}，一个知识丰富的助手。"
                if self.description:
                    system_prompt += f" {self.description}"
            
            # 创建LLM
            llm = get_llm(model_name=self.model)
            
            # 创建代理
            agent = OpenAIAgent.from_tools(
                tools,
                llm=llm,
                system_prompt=system_prompt,
                verbose=True
            )
            
            return agent
            
        except Exception as e:
            logger.error(f"初始化LlamaIndex代理时出错: {str(e)}")
            raise
    
    async def _get_knowledge_tools(self):
        """获取知识库工具"""
        tools = []
        
        # 添加知识库工具
        for kb_id in self.knowledge_bases:
            try:
                # 创建知识库查询引擎
                kb_engine = await self._create_kb_engine(kb_id)
                if kb_engine:
                    # 获取知识库信息
                    from app.config import get_db
                    db = next(get_db())
                    kb_repo = KnowledgeBaseRepository(db)
                    kb = kb_repo.get_by_id(kb_id)
                    
                    # 创建工具
                    kb_tool = QueryEngineTool(
                        query_engine=kb_engine,
                        metadata=ToolMetadata(
                            name=f"kb_{kb_id}",
                            description=f"在知识库「{kb.name}」中搜索信息: {kb.description or ''}"
                        )
                    )
                    tools.append(kb_tool)
                    
            except Exception as e:
                logger.error(f"创建知识库工具时出错 (KB ID: {kb_id}): {str(e)}")
        
        # 如果没有知识库工具，添加一个通用工具
        if not tools:
            dummy_index = VectorStoreIndex([])
            dummy_engine = dummy_index.as_query_engine()
            dummy_tool = QueryEngineTool(
                query_engine=dummy_engine,
                metadata=ToolMetadata(
                    name="general_qa",
                    description="回答一般问题，不依赖知识库"
                )
            )
            tools.append(dummy_tool)
        
        return tools
    
    async def _create_kb_engine(self, kb_id: str):
        """为知识库创建查询引擎"""
        try:
            from app.config import get_db
            from app.frameworks.llamaindex.indexing import load_or_create_index
            
            db = next(get_db())
            knowledge_service = get_unified_knowledge_service(db)
            
            # 检查知识库是否存在
            kb = await knowledge_service.get_knowledge_base(kb_id)
            if not kb:
                logger.warning(f"知识库不存在: {kb_id}")
                return None
            
            # 加载索引
            collection_name = f"kb_{kb_id}"
            index = load_or_create_index(collection_name=collection_name)
            
            # 创建查询引擎
            engine = get_query_engine(
                index, 
                similarity_top_k=5,
                similarity_cutoff=0.7
            )
            
            return engine
            
        except Exception as e:
            logger.error(f"为知识库创建查询引擎时出错 (KB ID: {kb_id}): {str(e)}")
            return None
    
    async def query(self, query: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        查询代理
        
        参数:
            query: 查询字符串
            conversation_id: 对话ID（可选）
            
        返回:
            代理响应
        """
        try:
            # 确保代理已初始化
            if self.agent is None:
                self.agent = await self._initialize_agent()
            
            # 执行查询
            response = await self.agent.aquery(query)
            
            # 格式化响应
            result = {
                "answer": response.response,
                "sources": []
            }
            
            # 添加源信息（如果有）
            if hasattr(response, "source_nodes"):
                for node in response.source_nodes:
                    result["sources"].append({
                        "content": node.text,
                        "metadata": node.metadata,
                        "score": node.score if node.score is not None else 1.0
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"查询LlamaIndex代理时出错: {str(e)}")
            raise

async def create_llamaindex_agent(
    name: str,
    description: Optional[str] = None,
    knowledge_bases: Optional[List[str]] = None,
    model: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None
) -> KnowledgeAgent:
    """
    创建LlamaIndex代理实例
    
    参数:
        name: 代理名称
        description: 代理描述
        knowledge_bases: 知识库ID列表
        model: 使用的模型
        settings: 其他设置
        
    返回:
        LlamaIndex代理实例
    """
    return KnowledgeAgent(
        name=name,
        description=description,
        model=model,
        knowledge_bases=knowledge_bases,
        settings_data=settings
    )
