"""
集成服务模块: 提供统一的API入口点，替代LangChain作为协调层
"""

from typing import List, Dict, Any, Optional
from app.frameworks.llamaindex.core import (
    get_service_context,
    create_router,
    process_query,
    format_prompt
)
from app.frameworks.llamaindex.chat import create_chat_engine
from app.frameworks.llamaindex.indexing import load_or_create_index
from app.frameworks.agno import get_agent
from app.frameworks.haystack import get_retriever
from app.config import settings

class IntegrationService:
    """集成服务，将各个框架组合在一起，替代LangChain作为统一入口"""
    
    def __init__(self):
        # 初始化核心组件
        self.service_context = get_service_context()
        
    async def query(
        self, 
        query: str, 
        collection_name: str,
        system_prompt: Optional[str] = None,
        use_agent: bool = False,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        统一查询入口点
        
        参数:
            query: 用户查询
            collection_name: 集合名称或知识库ID
            system_prompt: 系统提示
            use_agent: 是否使用代理
            history: 对话历史
            
        返回:
            查询结果
        """
        # 加载索引
        index = load_or_create_index(collection_name=collection_name)
        
        if use_agent:
            # 使用Agno代理
            agent = get_agent("default")
            result = await agent.run(
                query=query,
                history=history,
                tools=[{"type": "retriever", "retriever": get_retriever()}]
            )
            return {
                "answer": result.response,
                "metadata": {
                    "agent_thoughts": result.thoughts,
                    "sources": result.sources
                }
            }
        else:
            # 使用LlamaIndex直接查询
            chat_engine = create_chat_engine(
                system_prompt=system_prompt
            )
            
            # 处理历史消息
            if history:
                for msg in history:
                    if msg["role"] == "user":
                        chat_engine.memory.put({"role": "user", "content": msg["content"]})
                    elif msg["role"] == "assistant":
                        chat_engine.memory.put({"role": "assistant", "content": msg["content"]})
            
            # 处理查询
            return await process_query(query, chat_engine, history, system_prompt)
    
    async def query_knowledge_bases(
        self,
        query: str,
        kb_ids: List[str],
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        查询多个知识库
        
        参数:
            query: 用户查询
            kb_ids: 知识库ID列表
            system_prompt: 系统提示
            history: 对话历史
            
        返回:
            查询结果
        """
        # 为每个知识库创建查询引擎
        query_engines = []
        for kb_id in kb_ids:
            try:
                # 加载索引
                collection_name = f"kb_{kb_id}"
                index = load_or_create_index(collection_name=collection_name)
                
                # 创建查询引擎
                engine = index.as_query_engine(
                    similarity_top_k=5,
                    service_context=self.service_context
                )
                
                # 获取知识库信息
                from app.config import get_db
                from app.repositories.knowledge import KnowledgeBaseRepository
                
                db = next(get_db())
                kb_repo = KnowledgeBaseRepository(db)
                kb = kb_repo.get_by_id(kb_id)
                
                # 添加到查询引擎列表
                query_engines.append({
                    "name": f"kb_{kb_id}",
                    "description": f"在知识库「{kb.name}」中搜索: {kb.description or ''}",
                    "engine": engine
                })
                
            except Exception as e:
                import logging
                logging.error(f"为知识库创建查询引擎时出错 (KB ID: {kb_id}): {str(e)}")
        
        # 如果没有可用的查询引擎，回退到通用聊天
        if not query_engines:
            chat_engine = create_chat_engine(
                system_prompt=system_prompt
            )
            return await process_query(query, chat_engine, history, system_prompt)
        
        # 创建路由器
        router = create_router(
            query_engines=query_engines,
            service_context=self.service_context
        )
        
        # 执行查询
        return await process_query(query, router, history, system_prompt)
    
    def format_system_prompt(self, assistant_data: Dict[str, Any]) -> str:
        """格式化助手系统提示"""
        return format_prompt(
            "assistant",
            assistant_name=assistant_data.get("name", "AI助手"),
            assistant_description=assistant_data.get("description", "我是一个AI助手"),
            capabilities=assistant_data.get("capabilities", "我可以回答问题、提供信息和参考相关知识。")
        )
