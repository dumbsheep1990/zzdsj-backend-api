"""
LangChain Chat Module: Handles chat-based interactions with LLMs
Uses LangChain's powerful chat models and prompt templates
"""

from typing import List, Dict, Any, Optional
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from app.config import settings

def get_chat_model(model_name: Optional[str] = None, temperature: Optional[float] = None):
    """Get a LangChain chat model instance"""
    model = model_name or settings.DEFAULT_MODEL
    temp = temperature or float(settings.get_config("llm", "temperature", default=0.7))
    
    return ChatOpenAI(
        model_name=model,
        openai_api_key=settings.OPENAI_API_KEY,
        temperature=temp
    )

async def generate_response(
    system_prompt: str, 
    conversation_history: List[Dict[str, str]],
    references: Optional[List[Dict[str, Any]]] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None
) -> str:
    """
    Generate a response using LangChain's chat models
    
    Args:
        system_prompt: System instructions for the LLM
        conversation_history: List of message dicts with 'role' and 'content' keys
        references: Optional list of reference documents to include in context
        model_name: Optional model name override
        temperature: Optional temperature parameter override
        
    Returns:
        Generated response text
    """
    # Initialize chat model
    chat = get_chat_model(model_name, temperature)
    
    # Prepare messages
    messages = []
    
    # Add system message with references if available
    if references:
        reference_text = "\n\nRelevant information from knowledge base:"
        for i, ref in enumerate(references):
            reference_text += f"\n\nDocument {i+1}:\n{ref.get('content', '')}"
        
        system_prompt += reference_text
    
    messages.append(SystemMessage(content=system_prompt))
    
    # Add conversation history
    for message in conversation_history:
        if message["role"] == "user":
            messages.append(HumanMessage(content=message["content"]))
        elif message["role"] == "assistant":
            messages.append(AIMessage(content=message["content"]))
    
    # Generate response
    response = await chat.ainvoke(messages)
    
    return response.content

def create_prompt_template(template_name: str, **kwargs) -> str:
    """
    Create a prompt from a template
    
    This function loads predefined templates and fills them with provided values
    """
    # Define templates
    templates = {
        "qa": (
            "You are a helpful assistant answering questions based on the provided context.\n"
            "If the answer is not in the context, say that you don't know.\n"
            "Context: {context}\n\n"
            "Question: {question}"
        ),
        "summarize": (
            "Summarize the following text in a concise manner:\n\n{text}"
        ),
        "assistant": (
            "You are {assistant_name}, {assistant_description}\n"
            "Respond to the user in a helpful and accurate manner based on the following capabilities:\n"
            "{capabilities}"
        )
    }
    
    # Get template
    if template_name not in templates:
        raise ValueError(f"Template '{template_name}' not found")
    
    template = templates[template_name]
    
    # Fill template with provided values
    return template.format(**kwargs)
