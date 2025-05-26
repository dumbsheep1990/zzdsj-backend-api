"""
智能体记忆系统模块

此模块实现了一个灵活、可扩展的智能体记忆系统，
支持多种记忆类型、多种存储后端，并与各种AI框架集成。
"""

from app.memory.interfaces import IMemory, IMemoryFactory, MemoryConfig, MemoryType
from app.memory.manager import get_memory_manager
