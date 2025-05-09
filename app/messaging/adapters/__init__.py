"""
适配器模块
提供与现有系统的集成接口
"""

from app.messaging.adapters.base import BaseAdapter
from app.messaging.adapters.llama_index import LlamaIndexAdapter
from app.messaging.adapters.chat import ChatAdapter
from app.messaging.adapters.agent import AgentAdapter
from app.messaging.adapters.knowledge import KnowledgeAdapter

__all__ = [
    'BaseAdapter',
    'LlamaIndexAdapter',
    'ChatAdapter',
    'AgentAdapter',
    'KnowledgeAdapter'
]
