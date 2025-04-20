"""
Assistant API Module: Provides endpoints for interacting with AI assistants,
supporting various modalities (text, image, voice) and different interface formats
"""

from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks, Request
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
import asyncio
import json
import os
import uuid
import logging
from datetime import datetime

from app.models.database import get_db
from app.models.assistant import Assistant, Conversation, Message
from app.models.knowledge import KnowledgeBase
from app.schemas.assistant import (
    AssistantCreate,
    AssistantUpdate,
    AssistantResponse,
    AssistantList,
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    AssistantCapability,
)
from app.schemas.chat import ChatRequest, ChatResponse, MultimodalChatRequest, VoiceChatRequest
from app.frameworks.agno import AgnoAgent, create_knowledge_agent
from app.utils.object_storage import upload_file, get_file_url
from app.utils.rate_limiter import RateLimiter
from app.utils.template_renderer import render_assistant_page
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Rate limiter for API endpoints
rate_limiter = RateLimiter(
    requests_per_minute=settings.API_RATE_LIMIT,
    burst_limit=settings.API_BURST_LIMIT
)

@router.post("/", response_model=AssistantResponse)
async def create_assistant(
    assistant: AssistantCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new assistant
    """
    # Create assistant record
    db_assistant = Assistant(
        name=assistant.name,
        description=assistant.description,
        model=assistant.model,
        capabilities=assistant.capabilities,
        configuration=assistant.configuration,
        system_prompt=assistant.system_prompt
    )
    
    # Add knowledge base relationships if specified
    if assistant.knowledge_base_ids:
        knowledge_bases = db.query(KnowledgeBase).filter(
            KnowledgeBase.id.in_(assistant.knowledge_base_ids)
        ).all()
        
        if len(knowledge_bases) != len(assistant.knowledge_base_ids):
            raise HTTPException(status_code=400, detail="One or more knowledge bases not found")
        
        db_assistant.knowledge_bases = knowledge_bases
    
    # Add to database
    db.add(db_assistant)
    db.commit()
    db.refresh(db_assistant)
    
    # Generate access URL for the assistant
    access_url = f"{settings.BASE_URL}/assistants/web/{db_assistant.id}"
    db_assistant.access_url = access_url
    db.commit()
    
    return db_assistant

@router.get("/", response_model=AssistantList)
async def list_assistants(
    skip: int = 0,
    limit: int = 100,
    capabilities: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List all assistants with optional capability filtering
    """
    query = db.query(Assistant)
    
    # Filter by capabilities if specified
    if capabilities:
        for capability in capabilities:
            query = query.filter(Assistant.capabilities.contains([capability]))
    
    assistants = query.offset(skip).limit(limit).all()
    return {"assistants": assistants, "total": query.count()}

@router.get("/{assistant_id}", response_model=AssistantResponse)
async def get_assistant(
    assistant_id: int,
    db: Session = Depends(get_db)
):
    """
    Get assistant details by ID
    """
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    return assistant

@router.put("/{assistant_id}", response_model=AssistantResponse)
async def update_assistant(
    assistant_id: int,
    assistant_update: AssistantUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an assistant
    """
    db_assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not db_assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    # Update basic fields
    update_data = assistant_update.dict(exclude_unset=True)
    
    # Handle knowledge base relationships separately
    if "knowledge_base_ids" in update_data:
        kb_ids = update_data.pop("knowledge_base_ids")
        if kb_ids:
            knowledge_bases = db.query(KnowledgeBase).filter(
                KnowledgeBase.id.in_(kb_ids)
            ).all()
            
            if len(knowledge_bases) != len(kb_ids):
                raise HTTPException(status_code=400, detail="One or more knowledge bases not found")
            
            db_assistant.knowledge_bases = knowledge_bases
    
    # Update remaining fields
    for key, value in update_data.items():
        setattr(db_assistant, key, value)
    
    db.commit()
    db.refresh(db_assistant)
    return db_assistant

@router.delete("/{assistant_id}")
async def delete_assistant(
    assistant_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete an assistant
    """
    db_assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not db_assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    db.delete(db_assistant)
    db.commit()
    return {"message": "Assistant deleted successfully"}

@router.post("/{assistant_id}/conversations", response_model=ConversationResponse)
async def create_conversation(
    assistant_id: int,
    conversation: ConversationCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new conversation with an assistant
    """
    # Check if assistant exists
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    # Create conversation
    db_conversation = Conversation(
        assistant_id=assistant_id,
        title=conversation.title or f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        metadata=conversation.metadata
    )
    
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    
    return db_conversation

@router.get("/{assistant_id}/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    assistant_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all conversations for an assistant
    """
    conversations = db.query(Conversation).filter(
        Conversation.assistant_id == assistant_id
    ).offset(skip).limit(limit).all()
    
    return conversations

@router.post("/{assistant_id}/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def create_message(
    assistant_id: int,
    conversation_id: int,
    message: MessageCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Add a message to a conversation and get a response from the assistant
    """
    # Check if conversation exists and belongs to the assistant
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.assistant_id == assistant_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Create user message
    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=message.content,
        metadata=message.metadata
    )
    
    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    
    # Create placeholder for assistant response
    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content="",
        metadata={"status": "processing"}
    )
    
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    
    # Process the response in the background
    background_tasks.add_task(
        process_assistant_response,
        assistant_id,
        conversation_id,
        assistant_message.id,
        message.content,
        db
    )
    
    return user_message

async def process_assistant_response(
    assistant_id: int, 
    conversation_id: int, 
    message_id: int, 
    user_query: str,
    db: Session
):
    """Process the assistant response in the background"""
    try:
        # Get a new database session (since we're in a background task)
        db = next(get_db())
        
        # Get the assistant and conversation
        assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
        if not assistant:
            raise ValueError(f"Assistant {assistant_id} not found")
        
        # Create an Agno agent for this assistant
        knowledge_base_ids = [str(kb.id) for kb in assistant.knowledge_bases]
        agent = create_knowledge_agent(
            kb_ids=knowledge_base_ids,
            agent_name=assistant.name
        )
        
        # Get the response
        response = await agent.query(user_query, conversation_id=str(conversation_id))
        
        # Update the message
        message = db.query(Message).filter(Message.id == message_id).first()
        if message:
            message.content = response["response"]
            message.metadata = {
                "status": "completed",
                "sources": response.get("sources", []),
                "completed_at": datetime.now().isoformat()
            }
            db.commit()
    
    except Exception as e:
        logger.error(f"Error processing assistant response: {str(e)}")
        # Update message with error
        db = next(get_db())
        message = db.query(Message).filter(Message.id == message_id).first()
        if message:
            message.content = f"Error generating response: {str(e)}"
            message.metadata = {
                "status": "error",
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            }
            db.commit()

@router.get("/{assistant_id}/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def list_messages(
    assistant_id: int,
    conversation_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all messages in a conversation
    """
    # Check if conversation exists and belongs to the assistant
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.assistant_id == assistant_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).offset(skip).limit(limit).all()
    
    return messages

# OpenAI-compatible API endpoints

@router.post("/{assistant_id}/chat/completions")
async def chat_completions(
    assistant_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    OpenAI-compatible chat completions API
    Supports text, multimodal, and voice inputs based on assistant capabilities
    """
    # Apply rate limiting
    client_ip = request.client.host
    if not rate_limiter.allow_request(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Get the assistant
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    # Parse request body based on content type
    body = await request.json()
    
    # Determine request type based on assistant capabilities
    # and message content
    request_type = "text"
    if "multimodal" in assistant.capabilities and any("image_url" in msg.get("content", {}) for msg in body.get("messages", [])):
        request_type = "multimodal"
    elif "voice" in assistant.capabilities and body.get("input_type") == "audio":
        request_type = "voice"
    
    # Extract conversation ID from metadata or create new one
    conversation_id = body.get("conversation_id")
    if not conversation_id:
        # Create new conversation
        db_conversation = Conversation(
            assistant_id=assistant_id,
            title=f"API Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            metadata={"source": "api"}
        )
        db.add(db_conversation)
        db.commit()
        conversation_id = db_conversation.id
    else:
        # Verify conversation exists and belongs to this assistant
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.assistant_id == assistant_id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Process messages
    messages = body.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="No messages provided")
    
    # Get last user message
    user_message = None
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_message = msg
            break
    
    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")
    
    # Create user message in database
    content = user_message.get("content", "")
    # Handle different content types
    if isinstance(content, list):  # multimodal content
        content_text = ""
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                content_text += item.get("text", "")
            # Store image URLs in metadata
        
        db_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=content_text,
            metadata={"multimodal_content": content}
        )
    else:  # text content
        db_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=content,
            metadata={}
        )
    
    db.add(db_message)
    db.commit()
    
    # Create placeholder for assistant response
    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content="",
        metadata={"status": "processing"}
    )
    
    db.add(assistant_message)
    db.commit()
    
    # Process the response in the background
    background_tasks.add_task(
        process_api_response,
        assistant_id,
        conversation_id,
        assistant_message.id,
        user_message,
        request_type,
        db
    )
    
    # Return an immediate response with the message ID
    return JSONResponse({
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": assistant.model,
        "message_id": assistant_message.id,
        "conversation_id": conversation_id,
        "status": "processing",
        "poll_url": f"/api/v1/assistants/{assistant_id}/messages/{assistant_message.id}/status"
    })

@router.get("/{assistant_id}/messages/{message_id}/status")
async def get_message_status(
    assistant_id: int,
    message_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the status of an assistant message
    Used for polling the status of asynchronous responses
    """
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Get the conversation and verify it belongs to the assistant
    conversation = db.query(Conversation).filter(
        Conversation.id == message.conversation_id
    ).first()
    
    if not conversation or conversation.assistant_id != assistant_id:
        raise HTTPException(status_code=404, detail="Message not found for this assistant")
    
    status = message.metadata.get("status", "unknown")
    
    if status == "completed":
        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": db.query(Assistant).filter(Assistant.id == assistant_id).first().model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": message.content
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": message.metadata.get("usage", {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }),
            "sources": message.metadata.get("sources", [])
        }
    elif status == "error":
        return {
            "status": "error",
            "error": message.metadata.get("error", "Unknown error"),
            "created": int(datetime.now().timestamp())
        }
    else:
        return {
            "status": status,
            "created": int(datetime.now().timestamp())
        }

async def process_api_response(
    assistant_id: int,
    conversation_id: int,
    message_id: int,
    user_message: Dict[str, Any],
    request_type: str,
    db: Session
):
    """Process the API response in the background"""
    try:
        # Get a new database session
        db = next(get_db())
        
        # Get the assistant
        assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
        if not assistant:
            raise ValueError(f"Assistant {assistant_id} not found")
        
        # Create an Agno agent for this assistant
        knowledge_base_ids = [str(kb.id) for kb in assistant.knowledge_bases]
        agent = create_knowledge_agent(
            kb_ids=knowledge_base_ids,
            agent_name=assistant.name
        )
        
        # Extract query based on request type
        if request_type == "text":
            query = user_message.get("content", "")
        elif request_type == "multimodal":
            # Extract text content from multimodal message
            content = user_message.get("content", [])
            query = ""
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    query += item.get("text", "")
                # Image handling would be implemented here
        elif request_type == "voice":
            # Voice content would be processed here
            query = user_message.get("content", "")
        
        # Get the response
        response = await agent.query(query, conversation_id=str(conversation_id))
        
        # Update the message
        message = db.query(Message).filter(Message.id == message_id).first()
        if message:
            message.content = response["response"]
            message.metadata = {
                "status": "completed",
                "sources": response.get("sources", []),
                "completed_at": datetime.now().isoformat(),
                "usage": {
                    "prompt_tokens": len(query) // 4,  # Crude estimation
                    "completion_tokens": len(response["response"]) // 4,
                    "total_tokens": (len(query) + len(response["response"])) // 4
                }
            }
            db.commit()
    
    except Exception as e:
        logger.error(f"Error processing API response: {str(e)}")
        # Update message with error
        db = next(get_db())
        message = db.query(Message).filter(Message.id == message_id).first()
        if message:
            message.content = f"Error generating response"
            message.metadata = {
                "status": "error",
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            }
            db.commit()

@router.get("/web/{assistant_id}", response_class=HTMLResponse)
async def get_assistant_web_page(
    assistant_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a web page for interacting with an assistant
    """
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    # Render the assistant web page
    html_content = render_assistant_page(assistant)
    return HTMLResponse(content=html_content)

# Screenshot functionality
@router.post("/{assistant_id}/screenshot")
async def create_screenshot(
    assistant_id: int,
    conversation_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a screenshot of a conversation with an assistant
    """
    # Check if conversation exists and belongs to the assistant
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.assistant_id == assistant_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Generate screenshot in background
    background_tasks.add_task(
        generate_conversation_screenshot,
        assistant_id,
        conversation_id
    )
    
    return {
        "status": "processing",
        "message": "Screenshot generation in progress",
        "status_url": f"/api/v1/assistants/{assistant_id}/screenshots/{conversation_id}/status"
    }

@router.get("/{assistant_id}/screenshots/{conversation_id}/status")
async def get_screenshot_status(
    assistant_id: int,
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the status of a screenshot generation task
    """
    # Check if conversation exists
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.assistant_id == assistant_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check if screenshot metadata exists
    screenshot_info = conversation.metadata.get("screenshot", {})
    status = screenshot_info.get("status", "not_started")
    
    if status == "completed":
        return {
            "status": "completed",
            "url": screenshot_info.get("url"),
            "created_at": screenshot_info.get("created_at")
        }
    elif status == "error":
        return {
            "status": "error",
            "error": screenshot_info.get("error", "Unknown error"),
            "created_at": screenshot_info.get("created_at")
        }
    else:
        return {
            "status": status,
            "message": "Screenshot generation in progress"
        }

async def generate_conversation_screenshot(assistant_id: int, conversation_id: int):
    """Generate a screenshot of a conversation"""
    try:
        # Get a new database session
        db = next(get_db())
        
        # Update conversation metadata to indicate processing
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.assistant_id == assistant_id
        ).first()
        
        if not conversation:
            return
        
        # Update status to processing
        metadata = conversation.metadata or {}
        metadata["screenshot"] = {
            "status": "processing",
            "started_at": datetime.now().isoformat()
        }
        conversation.metadata = metadata
        db.commit()
        
        # In a real implementation, you would:
        # 1. Render the conversation to HTML
        # 2. Use a headless browser to capture screenshot
        # 3. Upload to object storage
        # 4. Update the conversation metadata with the URL
        
        # For now, simulate a delay
        await asyncio.sleep(2)
        
        # Generate a mock screenshot URL
        screenshot_url = f"{settings.BASE_URL}/static/screenshots/conversation_{conversation_id}.png"
        
        # Update conversation metadata
        metadata = conversation.metadata or {}
        metadata["screenshot"] = {
            "status": "completed",
            "url": screenshot_url,
            "created_at": datetime.now().isoformat()
        }
        conversation.metadata = metadata
        db.commit()
    
    except Exception as e:
        logger.error(f"Error generating screenshot: {str(e)}")
        
        # Update metadata with error
        db = next(get_db())
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.assistant_id == assistant_id
        ).first()
        
        if conversation:
            metadata = conversation.metadata or {}
            metadata["screenshot"] = {
                "status": "error",
                "error": str(e),
                "created_at": datetime.now().isoformat()
            }
            conversation.metadata = metadata
            db.commit()
