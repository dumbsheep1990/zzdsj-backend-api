from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

# Base Conversation Schema
class ConversationBase(BaseModel):
    assistant_id: int
    user_id: Optional[str] = None
    title: Optional[str] = "New Conversation"
    metadata: Optional[Dict[str, Any]] = {}

# Create Conversation Schema
class ConversationCreate(ConversationBase):
    pass

# Update Conversation Schema
class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# Conversation Schema (for responses)
class Conversation(ConversationBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

# Message Base Schema
class MessageBase(BaseModel):
    role: str  # user, assistant, system
    content: str
    metadata: Optional[Dict[str, Any]] = {}

# Create Message Schema
class MessageCreate(MessageBase):
    conversation_id: int

# Message Schema (for responses)
class Message(MessageBase):
    id: int
    conversation_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

# Conversation with Messages
class ConversationWithMessages(Conversation):
    messages: List[Message] = []
    
    class Config:
        orm_mode = True

# Reference Schema (for citation information)
class MessageReference(BaseModel):
    id: int
    message_id: int
    document_chunk_id: int
    relevance_score: float
    
    class Config:
        orm_mode = True

# Chat Request Schema
class ChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    assistant_id: int
    message: str
    user_id: Optional[str] = None

# Chat Response Schema
class ChatResponse(BaseModel):
    conversation_id: int
    message: Message
    references: Optional[List[Dict[str, Any]]] = None
