"""
智能体记忆系统 - LlamaIndex框架适配器

提供LlamaIndex框架与记忆系统的集成。
"""

from typing import Dict, Any, List, Optional
from app.memory.interfaces import IMemory, MemoryConfig
from app.memory.manager import get_memory_manager
from llama_index.memory import ChatMemoryBuffer

class LlamaIndexMemoryAdapter:
    """LlamaIndex框架记忆适配器"""
    
    @staticmethod
    async def get_llama_memory(session_id: str) -> ChatMemoryBuffer:
        """获取LlamaIndex格式的记忆"""
        # 获取系统记忆
        memory_manager = get_memory_manager()
        memory = await memory_manager.get_or_create_memory(f"llama:{session_id}")
        
        # 创建LlamaIndex内存缓冲区
        llama_memory = ChatMemoryBuffer.from_defaults()
        
        # 加载现有记忆
        messages = []
        memory_items = await memory.query("", top_k=100)  # 获取所有记忆
        
        for _, item, _ in memory_items:
            if "role" in item and "content" in item:
                messages.append({
                    "role": item["role"],
                    "content": item["content"],
                    "timestamp": item.get("timestamp", 0)
                })
                
        # 按顺序添加到LlamaIndex记忆
        for msg in sorted(messages, key=lambda x: x.get("timestamp", 0)):
            if msg["role"] == "user":
                llama_memory.put_user_message(msg["content"])
            elif msg["role"] == "assistant":
                llama_memory.put_ai_message(msg["content"])
                
        return llama_memory
    
    @staticmethod
    async def save_llama_memory(session_id: str, llama_memory: ChatMemoryBuffer) -> bool:
        """保存LlamaIndex记忆到系统记忆"""
        # 获取系统记忆
        memory_manager = get_memory_manager()
        memory = await memory_manager.get_or_create_memory(f"llama:{session_id}")
        
        # 清空现有记忆
        await memory.clear()
        
        # 获取所有消息
        chat_history = llama_memory.get_messages()
        
        # 保存到系统记忆
        for i, msg in enumerate(chat_history):
            await memory.add(
                key=f"msg_{i}",
                value={
                    "role": "user" if msg.role == "user" else "assistant",
                    "content": msg.content,
                    "timestamp": i  # 使用索引作为时间戳
                }
            )
            
        return True
