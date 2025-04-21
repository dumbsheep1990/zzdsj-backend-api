"""
Swagger助手模块：增强API文档并提供模式信息
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from typing import Dict, Any, List, Optional, Type
import inspect
import json
import os
from pathlib import Path

# 导入模型
from app.models.database import Base
from app.models.knowledge import KnowledgeBase, Document, DocumentChunk
from app.models.assistant import Assistant, Conversation, Message
from app.models.chat import ChatSession, ChatMessage
from app.schemas.knowledge import KnowledgeBaseCreate, DocumentCreate
from app.schemas.assistant import AssistantCreate, ConversationCreate

def add_schema_examples(app: FastAPI, examples: Dict[str, Dict[str, Any]]):
    """
    向OpenAPI模式添加示例
    
    参数:
        app: FastAPI应用
        examples: 示例字典，以模式名称为键
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
        
        # 向components/schemas添加示例
        schemas = openapi_schema.get("components", {}).get("schemas", {})
        for schema_name, example in examples.items():
            if schema_name in schemas:
                schemas[schema_name]["example"] = example
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi

def generate_model_examples():
    """生成模型的示例数据"""
    examples = {
        "KnowledgeBaseCreate": {
            "name": "技术文档",
            "description": "产品文档和技术指南的知识库",
            "framework": "langchain",
            "embedding_model": "text-embedding-ada-002"
        },
        "DocumentCreate": {
            "title": "API参考指南",
            "content_type": "text/markdown",
            "source": "https://example.com/docs/api-reference",
            "metadata": {
                "author": "API团队",
                "version": "1.2.3",
                "category": "reference"
            }
        },
        "AssistantCreate": {
            "name": "技术支持助手",
            "description": "专门回答技术支持问题",
            "model": "gpt-4",
            "capabilities": ["text", "code", "retrieval"],
            "system_prompt": "你是一个技术支持助手。使用知识库提供准确、有用的答案。",
            "knowledge_base_ids": [1, 2]
        },
        "ConversationCreate": {
            "title": "API集成帮助",
            "metadata": {
                "user_id": "user-123",
                "language": "zh"
            }
        }
    }
    
    return examples

def generate_db_schema_html():
    """
    生成数据库模式的HTML文档
    
    返回:
        包含数据库模式可视化的HTML字符串
    """
    models = [
        KnowledgeBase, Document, DocumentChunk,
        Assistant, Conversation, Message,
        ChatSession, ChatMessage
    ]
    
    html = """
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>知识库QA系统 - 数据库模式</title>
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
        <h1>知识库QA系统 - 数据库模式</h1>
        <p>本文档描述了知识库QA系统的数据库模式。</p>
    """
    
    # 添加模型
    for model in models:
        html += f"""
        <div class="model">
            <div class="model-header">
                <h2>{model.__name__} ({model.__tablename__})</h2>
            </div>
            <div class="columns">
                <h3>列</h3>
                <table>
                    <thead>
                        <tr>
                            <th>名称</th>
                            <th>类型</th>
                            <th>主键</th>
                            <th>可为空</th>
                            <th>默认值</th>
                            <th>描述</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for column in model.__table__.columns:
            html += f"""
                        <tr>
                            <td class="{'pk' if column.primary_key else 'fk' if column.foreign_keys else ''}">{column.name}</td>
                            <td>{column.type}</td>
                            <td>{"是" if column.primary_key else "否"}</td>
                            <td>{"是" if column.nullable else "否"}</td>
                            <td>{column.default if column.default is not None else "无"}</td>
                            <td>{get_column_description(model, column.name)}</td>
                        </tr>
            """
        
        html += """
                    </tbody>
                </table>
            </div>
        """
        
        # 添加关系
        html += """
            <div class="relationships">
                <h3>关系</h3>
        """
        
        for relationship in model.__mapper__.relationships:
            html += f"""
                <div class="relationship">
                    <p><strong>{relationship.key}</strong> -> {relationship.target.name}</p>
                    <p>类型: {relationship.direction.name}</p>
                </div>
            """
        
        html += """
            </div>
        </div>
        """
    
    # 添加模式图
    html += """
        <div class="schema-diagram">
            <h2>模式图</h2>
            <p>下图显示了数据库表之间的关系。</p>
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
    """根据模型文档字符串获取列的描述"""
    # 这是一个简化的实现
    # 在实际项目中，你可能需要解析文档字符串或维护一个单独的
    # 列描述映射
    
    description_map = {
        # KnowledgeBase
        "KnowledgeBase.id": "主键",
        "KnowledgeBase.name": "知识库名称",
        "KnowledgeBase.description": "知识库描述",
        "KnowledgeBase.status": "知识库状态（active活动，inactive非活动，processing处理中）",
        "KnowledgeBase.framework": "用于此知识库的AI框架",
        "KnowledgeBase.embedding_model": "用于生成嵌入的模型",
        
        # Document
        "Document.id": "主键",
        "Document.knowledge_base_id": "知识库外键",
        "Document.title": "文档标题",
        "Document.content_type": "文档的MIME类型",
        "Document.source": "源URL或标识符",
        "Document.metadata": "文档的JSON元数据",
        "Document.status": "文档的处理状态",
        
        # DocumentChunk
        "DocumentChunk.id": "主键",
        "DocumentChunk.document_id": "文档外键",
        "DocumentChunk.content": "块的文本内容",
        "DocumentChunk.metadata": "块的JSON元数据",
        "DocumentChunk.embedding": "块的向量嵌入",
        
        # Assistant
        "Assistant.id": "主键",
        "Assistant.name": "助手名称",
        "Assistant.description": "助手目的的描述",
        "Assistant.model": "助手使用的AI模型",
        "Assistant.capabilities": "助手能力列表（文本、多模态、语音等）",
        "Assistant.configuration": "助手特定配置",
        "Assistant.system_prompt": "指导助手行为的系统提示",
        
        # Conversation
        "Conversation.id": "主键",
        "Conversation.assistant_id": "助手外键",
        "Conversation.title": "对话标题",
        "Conversation.metadata": "对话的JSON元数据",
        
        # Message
        "Message.id": "主键",
        "Message.conversation_id": "对话外键",
        "Message.role": "消息发送者的角色（用户、助手、系统）",
        "Message.content": "消息内容",
        "Message.metadata": "消息的JSON元数据",
        
        # ChatSession
        "ChatSession.id": "主键",
        "ChatSession.title": "聊天会话标题",
        "ChatSession.metadata": "聊天会话的JSON元数据",
        
        # ChatMessage
        "ChatMessage.id": "主键",
        "ChatMessage.session_id": "聊天会话外键",
        "ChatMessage.role": "消息发送者的角色",
        "ChatMessage.content": "消息内容",
        "ChatMessage.metadata": "消息的JSON元数据",
    }
    
    key = f"{model.__name__}.{column_name}"
    return description_map.get(key, "")

def save_db_schema_doc():
    """保存数据库模式文档到HTML文件"""
    static_dir = Path("static")
    if not static_dir.exists():
        static_dir.mkdir(parents=True)
    
    schema_html = generate_db_schema_html()
    schema_path = static_dir / "db_schema.html"
    
    with open(schema_path, "w", encoding="utf-8") as f:
        f.write(schema_html)
    
    print(f"数据库模式文档已保存至 {schema_path}")
    return schema_path.resolve()

if __name__ == "__main__":
    save_db_schema_doc()
