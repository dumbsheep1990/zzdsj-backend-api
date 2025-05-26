"""
上下文压缩服务模块
提供上下文压缩功能的高级服务接口
"""

from typing import List, Dict, Any, Optional, Tuple, Union
import time
import uuid
from sqlalchemy.orm import Session
from datetime import datetime

from app.repositories.context_compression_repository import (
    ContextCompressionToolRepository,
    AgentCompressionConfigRepository,
    CompressionExecutionRepository
)
from app.models.context_compression import (
    ContextCompressionTool,
    AgentContextCompressionConfig,
    ContextCompressionExecution
)
from app.schemas.context_compression import (
    CompressionConfig,
    CompressionMethod,
    CompressionPhase,
    CompressedContextResult
)
from app.tools.advanced.context_compression.context_compressor import ContextCompressor


class ContextCompressionService:
    """上下文压缩服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.tool_repo = ContextCompressionToolRepository(db)
        self.config_repo = AgentCompressionConfigRepository(db)
        self.execution_repo = CompressionExecutionRepository(db)
    
    async def compress_context(
        self,
        content: str,
        query: Optional[str] = None,
        agent_id: Optional[int] = None,
        config: Optional[CompressionConfig] = None,
        model_name: Optional[str] = None
    ) -> CompressedContextResult:
        """
        压缩上下文内容
        
        参数:
            content: 要压缩的上下文内容
            query: 可选的查询内容，用于指导压缩
            agent_id: 可选的智能体ID，用于加载智能体的压缩配置
            config: 可选的压缩配置，如果提供则优先使用
            model_name: 可选的模型名称，用于压缩，如果未提供则使用配置中的默认模型
            
        返回:
            压缩结果对象
        """
        start_time = time.time()
        
        # 如果提供了agent_id但没有提供config，则尝试加载智能体的压缩配置
        if agent_id and not config:
            agent_config = self.config_repo.get_by_agent_id(agent_id)
            if agent_config and agent_config.enabled:
                config = CompressionConfig(
                    enabled=agent_config.enabled,
                    method=agent_config.method,
                    top_n=agent_config.top_n,
                    num_children=agent_config.num_children,
                    streaming=agent_config.streaming,
                    rerank_model=agent_config.rerank_model,
                    max_tokens=agent_config.max_tokens,
                    temperature=agent_config.temperature,
                    store_original=agent_config.store_original,
                    use_message_format=agent_config.use_message_format,
                    phase=agent_config.phase
                )
        
        # 如果没有配置，则使用默认配置
        if not config:
            config = CompressionConfig()
        
        # 如果未启用压缩，则直接返回原始内容
        if not config.enabled:
            return CompressedContextResult(
                original_context=content if config.store_original else None,
                compressed_context=content,
                method="none",
                compression_ratio=1.0,
                status="success"
            )
        
        # 创建压缩器实例
        compressor = ContextCompressor(
            model_name=model_name,
            method=config.method,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )
        
        # 执行压缩
        try:
            if config.method == CompressionMethod.TREE_SUMMARIZE:
                compressed_text = await compressor.tree_summarize(
                    content,
                    query=query,
                    num_children=config.num_children
                )
            elif config.method == CompressionMethod.COMPACT_AND_REFINE:
                compressed_text = await compressor.compact_and_refine(
                    content,
                    query=query
                )
            else:
                # 默认使用树状压缩
                compressed_text = await compressor.tree_summarize(
                    content,
                    query=query
                )
            
            # 计算压缩比例
            original_length = len(content)
            compressed_length = len(compressed_text)
            compression_ratio = compressed_length / original_length if original_length > 0 else 1.0
            
            # 创建执行记录
            execution_id = str(uuid.uuid4())
            execution_data = {
                "execution_id": execution_id,
                "agent_id": agent_id,
                "compression_config_id": getattr(agent_config, "id", None) if agent_id and 'agent_config' in locals() else None,
                "query": query,
                "original_content_length": original_length,
                "compressed_content_length": compressed_length,
                "compression_ratio": compression_ratio,
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "status": "success",
                "metadata": {
                    "model_name": model_name,
                    "method": config.method,
                    "config": config.dict(exclude={"enabled", "store_original"})
                }
            }
            self.execution_repo.create(execution_data)
            
            # 返回结果
            return CompressedContextResult(
                original_context=content if config.store_original else None,
                compressed_context=compressed_text,
                method=config.method,
                compression_ratio=compression_ratio,
                execution_time_ms=int((time.time() - start_time) * 1000),
                status="success"
            )
            
        except Exception as e:
            # 创建失败记录
            execution_id = str(uuid.uuid4())
            execution_data = {
                "execution_id": execution_id,
                "agent_id": agent_id,
                "compression_config_id": getattr(agent_config, "id", None) if agent_id and 'agent_config' in locals() else None,
                "query": query,
                "original_content_length": len(content),
                "compressed_content_length": 0,
                "compression_ratio": 0,
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "status": "failed",
                "error": str(e),
                "metadata": {
                    "model_name": model_name,
                    "method": config.method,
                    "config": config.dict(exclude={"enabled", "store_original"})
                }
            }
            self.execution_repo.create(execution_data)
            
            # 返回原始内容作为回退策略
            return CompressedContextResult(
                original_context=content if config.store_original else None,
                compressed_context=content,
                method=config.method,
                compression_ratio=1.0,
                execution_time_ms=int((time.time() - start_time) * 1000),
                status="failed"
            )
    
    # 工具管理方法
    def create_compression_tool(self, tool_data: Dict[str, Any]) -> ContextCompressionTool:
        """创建新的压缩工具"""
        return self.tool_repo.create(tool_data)
    
    def update_compression_tool(self, tool_id: int, tool_data: Dict[str, Any]) -> Optional[ContextCompressionTool]:
        """更新压缩工具"""
        return self.tool_repo.update(tool_id, tool_data)
    
    def delete_compression_tool(self, tool_id: int) -> bool:
        """删除压缩工具"""
        return self.tool_repo.delete(tool_id)
    
    def get_compression_tool(self, tool_id: int) -> Optional[ContextCompressionTool]:
        """获取压缩工具"""
        return self.tool_repo.get_by_id(tool_id)
    
    def get_compression_tools(self, skip: int = 0, limit: int = 100) -> List[ContextCompressionTool]:
        """获取所有压缩工具"""
        return self.tool_repo.get_all(skip, limit)
    
    # 配置管理方法
    def create_agent_config(self, config_data: Dict[str, Any]) -> AgentContextCompressionConfig:
        """创建智能体压缩配置"""
        # 检查是否已存在配置
        existing_config = self.config_repo.get_by_agent_id(config_data["agent_id"])
        if existing_config:
            # 如果已存在，则更新
            return self.update_agent_config(existing_config.id, config_data)
        
        # 否则创建新配置
        return self.config_repo.create(config_data)
    
    def update_agent_config(self, config_id: int, config_data: Dict[str, Any]) -> Optional[AgentContextCompressionConfig]:
        """更新智能体压缩配置"""
        return self.config_repo.update(config_id, config_data)
    
    def delete_agent_config(self, config_id: int) -> bool:
        """删除智能体压缩配置"""
        return self.config_repo.delete(config_id)
    
    def get_agent_config(self, config_id: int) -> Optional[AgentContextCompressionConfig]:
        """根据ID获取智能体压缩配置"""
        return self.config_repo.get_by_id(config_id)
    
    def get_agent_config_by_agent_id(self, agent_id: int) -> Optional[AgentContextCompressionConfig]:
        """根据智能体ID获取压缩配置"""
        return self.config_repo.get_by_agent_id(agent_id)
    
    def get_agent_configs(self, skip: int = 0, limit: int = 100) -> List[AgentContextCompressionConfig]:
        """获取所有智能体压缩配置"""
        return self.config_repo.get_all(skip, limit)
    
    # 执行记录方法
    def get_execution_records(self, 
                              skip: int = 0, 
                              limit: int = 100, 
                              agent_id: Optional[int] = None,
                              config_id: Optional[int] = None) -> List[ContextCompressionExecution]:
        """获取执行记录"""
        if agent_id:
            return self.execution_repo.get_by_agent_id(agent_id, skip, limit)
        elif config_id:
            return self.execution_repo.get_by_config_id(config_id, skip, limit)
        else:
            return self.execution_repo.get_all(skip, limit)
    
    def get_execution_record(self, execution_id: str) -> Optional[ContextCompressionExecution]:
        """根据执行ID获取执行记录"""
        return self.execution_repo.get_by_execution_id(execution_id)
