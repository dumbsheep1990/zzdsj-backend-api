from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.models.chat import Conversation, Message, MessageReference
from app.models.assistants import Assistant, AssistantKnowledgeBase
from app.frameworks.llamaindex.embeddings import similarity_search

async def process_chat_request(
    assistant_id: int,
    conversation_id: int,
    user_message: Message,
    db: Session
) -> Dict[str, Any]:
    """
    Process a chat request by retrieving relevant information and generating a response.
    """
    # Get assistant information
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise ValueError(f"Assistant with ID {assistant_id} not found")
    
    # Get conversation
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise ValueError(f"Conversation with ID {conversation_id} not found")
    
    # Get conversation history
    conversation_messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()
    
    # Get knowledge bases linked to the assistant
    knowledge_base_ids = [
        link.knowledge_base_id for link in db.query(AssistantKnowledgeBase).filter(
            AssistantKnowledgeBase.assistant_id == assistant_id
        ).all()
    ]
    
    # Retrieve relevant information from knowledge bases
    references = []
    if knowledge_base_ids:
        # Search for relevant information using embeddings
        relevant_docs = similarity_search(user_message.content, top_k=5)
        references = relevant_docs
    
    # Generate LLM response
    response_content = await generate_response(
        assistant=assistant,
        conversation_history=conversation_messages,
        references=references,
        user_message=user_message.content
    )
    
    # Create assistant message
    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=response_content,
        metadata={"model": assistant.model_id}
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    
    # Save references if any
    for reference in references:
        if 'metadata' in reference and 'chunk_id' in reference['metadata']:
            message_ref = MessageReference(
                message_id=assistant_message.id,
                document_chunk_id=reference['metadata']['chunk_id'],
                relevance_score=reference.get('score', 0.0)
            )
            db.add(message_ref)
    
    db.commit()
    
    # Update conversation title if it's the first message
    if len(conversation_messages) == 1:  # Only the user message exists
        conversation.title = user_message.content[:50] + ("..." if len(user_message.content) > 50 else "")
        db.commit()
    
    return {
        "conversation_id": conversation_id,
        "message": assistant_message,
        "references": references
    }

async def generate_response(
    assistant: Assistant,
    conversation_history: List[Message],
    references: List[Dict[str, Any]],
    user_message: str
) -> str:
    """
    Generate a response using the appropriate LLM framework based on assistant configuration.
    """
    from app.frameworks.llamaindex.chat import generate_response as llamaindex_generate_response
    from app.config import settings

    # 准备对话历史
    formatted_history = []

    # 转换对话历史为LlamaIndex格式
    for message in conversation_history:
        formatted_history.append({
            "role": message.role,
            "content": message.content
        })

    # 添加系统消息
    system_message = f"You are a helpful AI assistant named {assistant.name}."

    if assistant.description:
        system_message += f" {assistant.description}"

    # 添加参考文档
    references_formatted = []
    if references:
        for ref in references:
            references_formatted.append({
                "content": ref["content"],
                "metadata": ref.get("metadata", {})
            })

    # 初始化模型名称
    model_name = assistant.model_id if assistant.model_id else settings.DEFAULT_MODEL

    # 生成响应
    response = await llamaindex_generate_response(
        system_prompt=system_message,
        conversation_history=formatted_history,
        references=references_formatted,
        model_name=model_name,
        temperature=0.7
    )

    return response
