"""
LightRAG工作目录管理器模块
用于管理LightRAG工作目录的创建、配置和维护
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any
import psycopg2
from psycopg2.extras import DictCursor

from app.config import settings
from app.utils.common.logger import setup_logger
from app.frameworks.lightrag.config import lightrag_config

# 尝试导入 LightRAG
try:
    from lightrag import LightRAG, QueryParam
    HAS_LIGHTRAG = True
except ImportError:
    HAS_LIGHTRAG = False
    logging.warning("LightRAG 库未安装，将使用模拟模式")

logger = setup_logger("lightrag_workdir_manager")

class WorkdirManager:
    """LightRAG 工作目录管理器
    
    用于管理多个 LightRAG 工作目录和实例，支持数据隔离和统一查询接口
    """
    
    def __init__(self):
        """初始化工作目录管理器"""
        self.config = lightrag_config
        self.db_conn_params = {
            "host": self.config.pg_host,
            "port": self.config.pg_port,
            "user": self.config.pg_user,
            "password": self.config.pg_password,
            "database": self.config.pg_db
        }
        self.rag_instances: Dict[str, Any] = {}
        
        # 确保工作目录基础目录存在
        os.makedirs(self.config.base_dir, exist_ok=True)
    
    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(**self.db_conn_params)
    
    async def initialize_database(self):
        """初始化数据库结构"""
        if not self.config.enabled or self.config.graph_db_type != "postgres":
            logger.warning("LightRAG未启用或未使用PostgreSQL，跳过数据库初始化")
            return
        
        sql_init = """
        -- 检查和创建必要的扩展
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE EXTENSION IF NOT EXISTS age;
        
        -- 创建工作目录元数据表
        CREATE TABLE IF NOT EXISTS public.lightrag_workdirs (
            id SERIAL PRIMARY KEY,
            workdir_path TEXT NOT NULL UNIQUE,
            schema_name TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 创建函数用于初始化工作目录schema
        CREATE OR REPLACE FUNCTION initialize_lightrag_workdir(p_workdir_path TEXT, p_display_name TEXT, p_description TEXT)
        RETURNS INT AS $$
        DECLARE
            schema_name TEXT;
            new_id INT;
        BEGIN
            -- 生成schema名称
            schema_name := 'lightrag_' || replace(replace(p_workdir_path, '-', '_'), '/', '_');
            
            -- 创建schema
            EXECUTE 'CREATE SCHEMA IF NOT EXISTS ' || schema_name;
            
            -- 为AGE创建图
            EXECUTE 'LOAD ''age''; SET search_path = ag_catalog, "$user", public; SELECT create_graph(''' || schema_name || ''')'; 
            
            -- 记录工作目录信息
            INSERT INTO public.lightrag_workdirs (workdir_path, schema_name, display_name, description)
            VALUES (p_workdir_path, schema_name, p_display_name, p_description)
            RETURNING id INTO new_id;
            
            RETURN new_id;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql_init)
                conn.commit()
            logger.info("LightRAG数据库初始化完成")
        except Exception as e:
            logger.error(f"初始化LightRAG数据库结构时出错: {str(e)}")
            raise
    
    async def list_workdirs(self) -> List[Dict]:
        """列出所有工作目录
        
        Returns:
            包含工作目录信息的字典列表
        """
        if not self.config.enabled:
            logger.warning("LightRAG未启用，无法列出工作目录")
            return []
            
        try:
            with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT * FROM public.lightrag_workdirs ORDER BY last_accessed DESC")
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"列出工作目录时出错: {str(e)}")
            return []
    
    async def create_workdir(self, path: str, display_name: str, description: str = "") -> int:
        """创建新的工作目录
        
        Args:
            path: 工作目录路径
            display_name: 显示名称
            description: 描述信息
            
        Returns:
            新创建的工作目录ID
        """
        if not self.config.enabled:
            raise ValueError("LightRAG未启用，无法创建工作目录")
            
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT initialize_lightrag_workdir(%s, %s, %s)",
                        (path, display_name, description)
                    )
                    workdir_id = cur.fetchone()[0]
                    conn.commit()
                    
                    # 创建工作目录物理路径
                    workdir_path = os.path.join(self.config.base_dir, path)
                    os.makedirs(workdir_path, exist_ok=True)
                    
                    return workdir_id
        except Exception as e:
            logger.error(f"创建工作目录时出错: {str(e)}")
            raise
    
    async def get_workdir_info(self, workdir_path: str) -> Optional[Dict]:
        """获取工作目录信息
        
        Args:
            workdir_path: 工作目录路径
            
        Returns:
            工作目录信息字典，如果不存在则返回None
        """
        if not self.config.enabled:
            logger.warning("LightRAG未启用，无法获取工作目录信息")
            return None
            
        try:
            with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM public.lightrag_workdirs WHERE workdir_path = %s",
                        (workdir_path,)
                    )
                    row = cur.fetchone()
                    if row:
                        return dict(row)
                    return None
        except Exception as e:
            logger.error(f"获取工作目录信息时出错: {str(e)}")
            return None
    
    async def get_rag_instance(self, workdir_path: str) -> Any:
        """获取指定工作目录的LightRAG实例
        
        Args:
            workdir_path: 工作目录路径
            
        Returns:
            LightRAG实例
        """
        if not HAS_LIGHTRAG:
            raise ImportError("LightRAG库未安装，无法创建RAG实例")
            
        if not self.config.enabled:
            raise ValueError("LightRAG未启用，无法获取RAG实例")
            
        if workdir_path not in self.rag_instances:
            workdir_info = await self.get_workdir_info(workdir_path)
            if not workdir_info:
                raise ValueError(f"工作目录 {workdir_path} 不存在")
                
            # 更新访问时间
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE public.lightrag_workdirs SET last_accessed = CURRENT_TIMESTAMP WHERE id = %s",
                        (workdir_info['id'],)
                    )
                    conn.commit()
            
            # 设置环境变量
            os.environ["POSTGRES_HOST"] = self.config.pg_host
            os.environ["POSTGRES_PORT"] = str(self.config.pg_port)
            os.environ["POSTGRES_USER"] = self.config.pg_user
            os.environ["POSTGRES_PASSWORD"] = self.config.pg_password
            os.environ["POSTGRES_DATABASE"] = self.config.pg_db
            os.environ["AGE_GRAPH_NAME"] = workdir_info['schema_name']
            
            # 初始化LightRAG实例
            rag = LightRAG(
                working_dir=os.path.join(self.config.base_dir, workdir_path),
                llm_model_func=self._get_llm_func(),
                embedding_func=self._get_embedding_func(),
                kv_storage="PGKVStorage",
                doc_status_storage="PGDocStatusStorage",
                graph_storage="PGGraphStorage",
                vector_storage="PGVectorStorage",
                # 为每个存储类型指定Schema
                kv_storage_cls_kwargs={"schema": workdir_info['schema_name']},
                doc_status_storage_cls_kwargs={"schema": workdir_info['schema_name']},
                graph_storage_cls_kwargs={
                    "schema": workdir_info['schema_name'],
                    "graph_name": workdir_info['schema_name']  # AGE图名称
                },
                vector_db_storage_cls_kwargs={
                    "schema": workdir_info['schema_name'],
                    "cosine_better_than_threshold": 0.4
                }
            )
            
            await rag.initialize_storages()
            self.rag_instances[workdir_path] = rag
        
        return self.rag_instances[workdir_path]
    
    def _get_llm_func(self):
        """获取LLM函数
        
        Returns:
            LLM模型函数
        """
        from core.model_manager import get_model_manager
        
        # 获取模型管理器
        model_manager = get_model_manager()
        
        # 根据配置选择不同的模型函数
        # 如果使用OpenAI
        if settings.DEFAULT_CHAT_MODEL_PROVIDER == "openai":
            from lightrag.llm.openai import openai_complete_if_cache
            # 使用我们项目的模型管理器获取API密钥和设置
            api_key = model_manager.get_api_key("openai")
            api_base = model_manager.get_api_base("openai")
            model_name = settings.DEFAULT_CHAT_MODEL_NAME or "gpt-4o-mini"
            
            return lambda prompt, **kwargs: openai_complete_if_cache(
                model_name,
                prompt,
                base_url=api_base,
                api_key=api_key,
                **kwargs
            )
        # 如果使用其他模型提供商，可以在此添加
        else:
            # 使用默认的调用方式
            llm = model_manager.get_llm()
            return lambda prompt, **kwargs: llm.generate(prompt, **kwargs)
    
    def _get_embedding_func(self):
        """获取嵌入函数
        
        Returns:
            嵌入模型函数
        """
        from core.model_manager import get_model_manager
        from lightrag.utils import EmbeddingFunc
        
        # 获取模型管理器
        model_manager = get_model_manager()
        
        # 根据配置选择不同的嵌入模型
        # 如果使用OpenAI
        if settings.DEFAULT_EMBEDDING_MODEL_PROVIDER == "openai":
            from lightrag.llm.openai import openai_embed
            
            # 使用我们项目的模型管理器获取API密钥和设置
            api_key = model_manager.get_api_key("openai")
            api_base = model_manager.get_api_base("openai")
            model_name = settings.DEFAULT_EMBEDDING_MODEL_NAME or "text-embedding-3-small"
            
            return EmbeddingFunc(
                embedding_dim=1536,  # OpenAI embedding维度
                max_token_size=8192,
                func=lambda texts: openai_embed(
                    texts, 
                    model=model_name,
                    base_url=api_base,
                    api_key=api_key
                )
            )
        # 如果使用其他嵌入模型，可以在此添加
        else:
            # 使用默认的嵌入模型
            embedding_model = model_manager.get_embedding_model()
            return EmbeddingFunc(
                embedding_dim=self.config.embedding_dim,
                max_token_size=self.config.max_token_size,
                func=lambda texts: [embedding_model.get_text_embedding(text) for text in texts]
            )
    
    async def query(self, workdir_path: str, question: str, mode: str = "hybrid") -> str:
        """在指定工作目录执行查询
        
        Args:
            workdir_path: 工作目录路径
            question: 查询问题
            mode: 查询模式 (hybrid, vector, graph)
            
        Returns:
            查询结果
        """
        if not HAS_LIGHTRAG:
            raise ImportError("LightRAG库未安装，无法执行查询")
            
        rag = await self.get_rag_instance(workdir_path)
        return await rag.aquery(question, param=QueryParam(mode=mode))
    
    async def query_all(self, question: str, mode: str = "hybrid") -> Dict[str, str]:
        """查询所有工作目录并返回结果
        
        Args:
            question: 查询问题
            mode: 查询模式 (hybrid, vector, graph)
            
        Returns:
            各工作目录的查询结果字典
        """
        if not HAS_LIGHTRAG:
            raise ImportError("LightRAG库未安装，无法执行查询")
            
        workdirs = await self.list_workdirs()
        results = {}
        
        # 并行查询所有工作目录
        tasks = []
        for workdir in workdirs:
            task = asyncio.create_task(
                self.query(workdir['workdir_path'], question, mode)
            )
            tasks.append((workdir['workdir_path'], task))
        
        # 收集结果
        for workdir_path, task in tasks:
            try:
                results[workdir_path] = await task
            except Exception as e:
                logger.error(f"查询工作目录 {workdir_path} 时出错: {str(e)}")
                results[workdir_path] = f"错误: {str(e)}"
        
        return results

# 全局单例
_workdir_manager = None

def get_workdir_manager() -> WorkdirManager:
    """获取工作目录管理器单例
    
    Returns:
        WorkdirManager实例
    """
    global _workdir_manager
    if _workdir_manager is None:
        _workdir_manager = WorkdirManager()
    return _workdir_manager
