"""
Swagger Helper Module: Enhances API documentation and provides schema information
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from typing import Dict, Any, List, Optional, Type
import inspect
import json
import os
from pathlib import Path

# Import models
from app.models.database import Base
from app.models.knowledge import KnowledgeBase, Document, DocumentChunk
from app.models.assistant import Assistant, Conversation, Message
from app.models.chat import ChatSession, ChatMessage
from app.schemas.knowledge import KnowledgeBaseCreate, DocumentCreate
from app.schemas.assistant import AssistantCreate, ConversationCreate

def add_schema_examples(app: FastAPI, examples: Dict[str, Dict[str, Any]]):
    """
    Add examples to the OpenAPI schema
    
    Args:
        app: FastAPI application
        examples: Dictionary of examples, keyed by schema name
    """
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        
        # Add examples to components/schemas
        schemas = openapi_schema.get("components", {}).get("schemas", {})
        for schema_name, example in examples.items():
            if schema_name in schemas:
                schemas[schema_name]["example"] = example
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi

def generate_model_examples():
    """Generate example data for models"""
    examples = {
        "KnowledgeBaseCreate": {
            "name": "Technical Documentation",
            "description": "Knowledge base for product documentation and technical guides",
            "framework": "langchain",
            "embedding_model": "text-embedding-ada-002"
        },
        "DocumentCreate": {
            "title": "API Reference Guide",
            "content_type": "text/markdown",
            "source": "https://example.com/docs/api-reference",
            "metadata": {
                "author": "API Team",
                "version": "1.2.3",
                "category": "reference"
            }
        },
        "AssistantCreate": {
            "name": "Technical Support Assistant",
            "description": "Specialized in answering technical support questions",
            "model": "gpt-4",
            "capabilities": ["text", "code", "retrieval"],
            "system_prompt": "You are a technical support assistant. Use the knowledge base to provide accurate, helpful answers.",
            "knowledge_base_ids": [1, 2]
        },
        "ConversationCreate": {
            "title": "API Integration Help",
            "metadata": {
                "user_id": "user-123",
                "language": "en"
            }
        }
    }
    
    return examples

def generate_db_schema_html():
    """
    Generate HTML documentation of the database schema
    
    Returns:
        HTML string with database schema visualization
    """
    models = [
        KnowledgeBase, Document, DocumentChunk,
        Assistant, Conversation, Message,
        ChatSession, ChatMessage
    ]
    
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Knowledge Base QA System - Database Schema</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            h1 {
                color: #2c3e50;
                border-bottom: 2px solid #eee;
                padding-bottom: 10px;
            }
            h2 {
                color: #3498db;
                margin-top: 30px;
            }
            .model {
                margin-bottom: 40px;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 20px;
                background-color: #f9f9f9;
            }
            .model-header {
                background-color: #3498db;
                color: white;
                padding: 10px;
                margin: -20px -20px 20px -20px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            .columns {
                margin-bottom: 20px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                text-align: left;
                padding: 12px;
                border-bottom: 1px solid #ddd;
            }
            th {
                background-color: #f2f2f2;
            }
            tr:hover {
                background-color: #f5f5f5;
            }
            .relationships {
                margin-top: 20px;
            }
            .relationship {
                padding: 10px;
                margin-bottom: 10px;
                background-color: #e8f4f8;
                border-radius: 5px;
            }
            .pk {
                font-weight: bold;
                color: #e74c3c;
            }
            .fk {
                color: #2980b9;
            }
            .schema-diagram {
                width: 100%;
                overflow-x: auto;
                margin-top: 40px;
                padding: 20px;
                background-color: #fff;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
        </style>
    </head>
    <body>
        <h1>Knowledge Base QA System - Database Schema</h1>
        <p>This document describes the database schema for the Knowledge Base QA System.</p>
    """
    
    # Add models
    for model in models:
        html += f"""
        <div class="model">
            <div class="model-header">
                <h2>{model.__name__} ({model.__tablename__})</h2>
            </div>
            <div class="columns">
                <h3>Columns</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Type</th>
                            <th>Primary Key</th>
                            <th>Nullable</th>
                            <th>Default</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for column in model.__table__.columns:
            html += f"""
                        <tr>
                            <td class="{'pk' if column.primary_key else 'fk' if column.foreign_keys else ''}">{column.name}</td>
                            <td>{column.type}</td>
                            <td>{"Yes" if column.primary_key else "No"}</td>
                            <td>{"Yes" if column.nullable else "No"}</td>
                            <td>{column.default if column.default is not None else "None"}</td>
                            <td>{get_column_description(model, column.name)}</td>
                        </tr>
            """
        
        html += """
                    </tbody>
                </table>
            </div>
        """
        
        # Add relationships
        html += """
            <div class="relationships">
                <h3>Relationships</h3>
        """
        
        for relationship in model.__mapper__.relationships:
            html += f"""
                <div class="relationship">
                    <p><strong>{relationship.key}</strong> -> {relationship.target.name}</p>
                    <p>Type: {relationship.direction.name}</p>
                </div>
            """
        
        html += """
            </div>
        </div>
        """
    
    # Add schema diagram
    html += """
        <div class="schema-diagram">
            <h2>Schema Diagram</h2>
            <p>The diagram below shows the relationships between the database tables.</p>
            <pre>
+------------------+       +---------------+       +-------------------+
| KnowledgeBase    |       | Document      |       | DocumentChunk     |
+------------------+       +---------------+       +-------------------+
| id               |<----->| id            |<----->| id                |
| name             |       | knowledge_base|       | document_id       |
| description      |       | title         |       | content           |
| status           |       | content_type  |       | metadata          |
| framework        |       | source        |       | embedding         |
| embedding_model  |       | metadata      |       | created_at        |
| created_at       |       | status        |       +-------------------+
| updated_at       |       | created_at    |
+--------^---------+       | updated_at    |
         |                 +---------------+
         |
         |                 +---------------+       +---------------+       +---------------+
         |                 | Assistant     |       | Conversation  |       | Message       |
         |                 +---------------+       +---------------+       +---------------+
         +---------------->| id            |<----->| id            |<----->| id            |
                           | name          |       | assistant_id  |       | conversation_id|
                           | description   |       | title         |       | role          |
                           | model         |       | metadata      |       | content       |
                           | capabilities  |       | created_at    |       | metadata      |
                           | created_at    |       | updated_at    |       | created_at    |
                           | updated_at    |       +---------------+       +---------------+
                           +---------------+
                                  
            </pre>
        </div>
    """
    
    html += """
    </body>
    </html>
    """
    
    return html

def get_column_description(model: Type, column_name: str) -> str:
    """Get a description for a column based on model docstrings"""
    # This is a simplified implementation
    # In a real project, you might want to parse docstrings or maintain a separate
    # mapping of column descriptions
    
    description_map = {
        # KnowledgeBase
        "KnowledgeBase.id": "Primary key",
        "KnowledgeBase.name": "Name of the knowledge base",
        "KnowledgeBase.description": "Description of the knowledge base",
        "KnowledgeBase.status": "Status of the knowledge base (active, inactive, processing)",
        "KnowledgeBase.framework": "AI framework used for this knowledge base",
        "KnowledgeBase.embedding_model": "Model used for generating embeddings",
        
        # Document
        "Document.id": "Primary key",
        "Document.knowledge_base_id": "Foreign key to knowledge base",
        "Document.title": "Document title",
        "Document.content_type": "MIME type of the document",
        "Document.source": "Source URL or identifier",
        "Document.metadata": "JSON metadata for the document",
        "Document.status": "Processing status of the document",
        
        # DocumentChunk
        "DocumentChunk.id": "Primary key",
        "DocumentChunk.document_id": "Foreign key to document",
        "DocumentChunk.content": "Text content of the chunk",
        "DocumentChunk.metadata": "JSON metadata for the chunk",
        "DocumentChunk.embedding": "Vector embedding of the chunk",
        
        # Assistant
        "Assistant.id": "Primary key",
        "Assistant.name": "Name of the assistant",
        "Assistant.description": "Description of the assistant's purpose",
        "Assistant.model": "AI model used by the assistant",
        "Assistant.capabilities": "List of assistant capabilities (text, multimodal, voice, etc.)",
        "Assistant.configuration": "Assistant-specific configuration",
        "Assistant.system_prompt": "System prompt to guide assistant behavior",
        
        # Conversation
        "Conversation.id": "Primary key",
        "Conversation.assistant_id": "Foreign key to assistant",
        "Conversation.title": "Conversation title",
        "Conversation.metadata": "JSON metadata for the conversation",
        
        # Message
        "Message.id": "Primary key",
        "Message.conversation_id": "Foreign key to conversation",
        "Message.role": "Role of the message sender (user, assistant, system)",
        "Message.content": "Message content",
        "Message.metadata": "JSON metadata for the message",
        
        # ChatSession
        "ChatSession.id": "Primary key",
        "ChatSession.title": "Chat session title",
        "ChatSession.metadata": "JSON metadata for the chat session",
        
        # ChatMessage
        "ChatMessage.id": "Primary key",
        "ChatMessage.session_id": "Foreign key to chat session",
        "ChatMessage.role": "Role of the message sender",
        "ChatMessage.content": "Message content",
        "ChatMessage.metadata": "JSON metadata for the message",
    }
    
    key = f"{model.__name__}.{column_name}"
    return description_map.get(key, "")

def save_db_schema_doc():
    """Save database schema documentation to HTML file"""
    static_dir = Path("static")
    if not static_dir.exists():
        static_dir.mkdir(parents=True)
    
    schema_html = generate_db_schema_html()
    schema_path = static_dir / "db_schema.html"
    
    with open(schema_path, "w", encoding="utf-8") as f:
        f.write(schema_html)
    
    print(f"Database schema documentation saved to {schema_path}")
    return schema_path.resolve()

if __name__ == "__main__":
    save_db_schema_doc()
