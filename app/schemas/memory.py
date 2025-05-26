"""
智能体记忆系统 - API模式

定义记忆系统的Pydantic模式。
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class MemoryConfigSchema(BaseModel):
    """记忆配置模式"""
    memory_type: str = Field("SHORT_TERM", description="记忆类型: SHORT_TERM, SEMANTIC, WORKING, EPISODIC, PROCEDURAL, NONE")
    ttl: Optional[int] = Field(None, description="记忆生存时间(秒)")
    max_items: Optional[int] = Field(None, description="最大记忆项数")
    max_tokens: Optional[int] = Field(None, description="最大记忆token数")
    retrieval_strategy: str = Field("recency", description="检索策略: recency, relevance")
    storage_backend: str = Field("in_memory", description="存储后端: in_memory, redis, postgres")
    vector_backend: Optional[str] = Field(None, description="向量后端: milvus, elasticsearch, pgvector")
    
    class Config:
        schema_extra = {
            "example": {
                "memory_type": "SHORT_TERM",
                "ttl": 3600,
                "max_items": 50,
                "retrieval_strategy": "recency",
                "storage_backend": "redis"
            }
        }

class MemoryCreateRequest(BaseModel):
    """创建记忆请求"""
    config: Optional[MemoryConfigSchema] = Field(None, description="记忆配置")
    content: Optional[Dict[str, Any]] = Field(None, description="初始记忆内容")
    
    class Config:
        schema_extra = {
            "example": {
                "config": {
                    "memory_type": "SHORT_TERM",
                    "ttl": 3600,
                    "max_items": 50
                },
                "content": {
                    "greeting": {
                        "role": "system",
                        "content": "这是一条初始化记忆"
                    }
                }
            }
        }

class MemoryUpdateRequest(BaseModel):
    """更新记忆请求"""
    config: Optional[MemoryConfigSchema] = Field(None, description="记忆配置")
    
    class Config:
        schema_extra = {
            "example": {
                "config": {
                    "ttl": 7200,
                    "max_items": 100
                }
            }
        }

class MemoryResponse(BaseModel):
    """记忆响应"""
    memory_id: str
    agent_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    config: Dict[str, Any]
    status: str = "active"
    
    class Config:
        schema_extra = {
            "example": {
                "memory_id": "550e8400-e29b-41d4-a716-446655440000",
                "agent_id": "agent-123",
                "created_at": "2025-05-22T03:05:04",
                "updated_at": "2025-05-22T03:15:04",
                "config": {
                    "memory_type": "SHORT_TERM",
                    "ttl": 3600,
                    "max_items": 50
                },
                "status": "active"
            }
        }

class MemoryItem(BaseModel):
    """记忆项"""
    key: str
    content: Dict[str, Any]
    relevance_score: Optional[float] = None
    
    class Config:
        schema_extra = {
            "example": {
                "key": "msg_1",
                "content": {
                    "role": "user",
                    "content": "你好，智能助手"
                },
                "relevance_score": 0.95
            }
        }

class MemoryQueryRequest(BaseModel):
    """记忆查询请求"""
    query: str = Field("", description="查询文本")
    top_k: int = Field(5, description="返回结果数量")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "最近的对话",
                "top_k": 5
            }
        }

class MemoryQueryResponse(BaseModel):
    """记忆查询响应"""
    agent_id: str
    query: str
    results: List[MemoryItem]
    total: int
    
    class Config:
        schema_extra = {
            "example": {
                "agent_id": "agent-123",
                "query": "最近的对话",
                "results": [
                    {
                        "key": "msg_1",
                        "content": {
                            "role": "user",
                            "content": "你好，智能助手"
                        },
                        "relevance_score": 0.95
                    }
                ],
                "total": 1
            }
        }
