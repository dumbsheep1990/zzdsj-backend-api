"""
上下文压缩服务层
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.services.base import BaseService
from app.models.compression import CompressionTool, AgentCompressionConfig
from app.schemas.context_compression import (
    CompressionToolCreate,
    AgentCompressionConfigCreate,
    CompressionConfig,
    CompressedContextResult
)


class CompressionService(BaseService):
    """上下文压缩服务"""

    async def compress_context(
            self,
            content: str,
            query: Optional[str] = None,
            agent_id: Optional[int] = None,
            config: Optional[CompressionConfig] = None,
            model_name: Optional[str] = None
    ) -> CompressedContextResult:
        """压缩上下文"""
        # 如果指定了agent_id，获取其配置
        if agent_id and not config:
            agent_config = await self.get_agent_config_by_agent_id(agent_id)
            if agent_config:
                config = agent_config.config

        # 执行压缩逻辑
        # TODO: 实现实际的压缩逻辑
        compressed_content = content[:1000]  # 示例：简单截断

        return CompressedContextResult(
            original_length=len(content),
            compressed_length=len(compressed_content),
            content=compressed_content,
            compression_ratio=len(compressed_content) / len(content),
            metadata={"model": model_name} if model_name else {}
        )

    async def create_tool(self, data: CompressionToolCreate) -> CompressionTool:
        """创建压缩工具"""
        tool = CompressionTool(**data.dict())
        self.db.add(tool)
        self.db.commit()
        self.db.refresh(tool)
        return tool

    async def get_tools(self, skip: int = 0, limit: int = 100) -> List[CompressionTool]:
        """获取压缩工具列表"""
        return self.db.query(CompressionTool).offset(skip).limit(limit).all()

    async def get_agent_config_by_agent_id(self, agent_id: int) -> Optional[AgentCompressionConfig]:
        """根据代理ID获取压缩配置"""
        return self.db.query(AgentCompressionConfig).filter(
            AgentCompressionConfig.agent_id == agent_id
        ).first()
