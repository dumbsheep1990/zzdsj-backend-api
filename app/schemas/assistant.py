"""
Assistant Schemas Module: Pydantic models for assistant API requests and responses
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AssistantCapability(str, Enum):
    """Enum for assistant capabilities"""
    TEXT = "text"
    MULTIMODAL = "multimodal"
    VOICE = "voice"
    CODE = "code"
    RETRIEVAL = "retrieval"
    REASONING = "reasoning"
    TOOLS = "tools"


class AssistantBase(BaseModel):
    """Base assistant schema with common attributes"""
    name: str = Field(..., description="Name of the assistant", max_length=100)
    description: Optional[str] = Field(None, description="Description of the assistant's purpose")
    model: str = Field(..., description="Model used by the assistant", max_length=100)
    capabilities: List[str] = Field(
        default=["text"],
        description="List of assistant capabilities (text, multimodal, voice, etc.)"
    )
    configuration: Optional[Dict[str, Any]] = Field(
        None,
        description="Assistant-specific configuration"
    )
    system_prompt: Optional[str] = Field(
        None,
        description="System prompt to guide assistant behavior"
    )


class AssistantCreate(AssistantBase):
    """Schema for creating a new assistant"""
    knowledge_base_ids: Optional[List[int]] = Field(
        None,
        description="List of knowledge base IDs to associate with the assistant"
    )


class AssistantUpdate(BaseModel):
    """Schema for updating an assistant"""
    name: Optional[str] = Field(None, description="Name of the assistant", max_length=100)
    description: Optional[str] = Field(None, description="Description of the assistant's purpose")
    model: Optional[str] = Field(None, description="Model used by the assistant", max_length=100)
    capabilities: Optional[List[str]] = Field(
        None,
        description="List of assistant capabilities (text, multimodal, voice, etc.)"
    )
    configuration: Optional[Dict[str, Any]] = Field(
        None,
        description="Assistant-specific configuration"
    )
    system_prompt: Optional[str] = Field(
        None,
        description="System prompt to guide assistant behavior"
    )
    knowledge_base_ids: Optional[List[int]] = Field(
        None,
        description="List of knowledge base IDs to associate with the assistant"
    )


class AssistantResponse(AssistantBase):
    """Schema for assistant response"""
    id: int
    access_url: Optional[str] = Field(None, description="URL for accessing the assistant's web interface")
    created_at: datetime
    updated_at: Optional[datetime] = None
    knowledge_base_ids: List[int] = Field([], description="IDs of associated knowledge bases")
    
    class Config:
        orm_mode = True


class AssistantList(BaseModel):
    """Schema for listing assistants"""
    assistants: List[AssistantResponse]
    total: int


class ConversationBase(BaseModel):
    """Base conversation schema"""
    title: Optional[str] = Field(None, description="Title of the conversation")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Arbitrary metadata")


class ConversationCreate(ConversationBase):
    """Schema for creating a new conversation"""
    pass


class ConversationResponse(ConversationBase):
    """Schema for conversation response"""
    id: int
    assistant_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    message_count: int = 0
    
    class Config:
        orm_mode = True


class MessageBase(BaseModel):
    """Base message schema"""
    content: str = Field(..., description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")


class MessageCreate(MessageBase):
    """Schema for creating a new message"""
    pass


class MessageResponse(MessageBase):
    """Schema for message response"""
    id: int
    conversation_id: int
    role: str
    created_at: datetime
    
    class Config:
        orm_mode = True


class AssistantSummary(BaseModel):
    """Summary of an assistant for listing and display"""
    id: int
    name: str
    description: Optional[str] = None
    capabilities: List[str]
    model: str
    access_url: Optional[str] = None
    
    class Config:
        orm_mode = True


class ApiKeyCreate(BaseModel):
    """Schema for creating an API key"""
    name: str = Field(..., description="Name for the API key")
    assistant_id: Optional[int] = Field(None, description="Optionally restrict key to a specific assistant")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date")


class ApiKeyResponse(BaseModel):
    """Schema for API key response"""
    id: int
    name: str
    key: str
    assistant_id: Optional[int] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True
