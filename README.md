# Knowledge Base Q&A System Backend

A Python-based backend service for a knowledge base Q&A system with assistant management, similar to Dify. This system provides fine-grained control over knowledge base question and answer capabilities.

## Architecture Overview

The backend is designed with a modular architecture that integrates multiple frameworks and services:

### Core Components

- **FastAPI**: High-performance REST API framework
- **PostgreSQL**: Relational database for structured data
- **Milvus**: Vector database for embeddings and similarity search
- **Redis**: Caching and pub/sub messaging
- **MinIO**: Object storage for document files
- **RabbitMQ**: Message queue for asynchronous processing
- **Nacos**: Service discovery and configuration management
- **Celery**: Distributed task queue for background processing

### AI/ML Integration

- **LangChain**: Framework for LLM application development
- **HayStack**: Framework for question-answering systems
- **LlamaIndex**: Data framework for LLM applications
- **Agno**: Agent framework for autonomous actions

## Directory Structure

```
zz-backend-lite/
├── app/
│   ├── api/                # FastAPI routes
│   │   ├── assistants.py   # Assistant management endpoints
│   │   ├── knowledge.py    # Knowledge base management endpoints
│   │   └── chat.py         # Chat interface endpoints
│   ├── core/               # Core business logic
│   │   ├── assistants/     # Assistant management logic
│   │   ├── knowledge/      # Knowledge base management
│   │   └── chat/           # Chat interaction logic
│   ├── frameworks/         # AI framework integrations
│   │   ├── haystack/       # Haystack integration
│   │   ├── langchain/      # LangChain integration
│   │   ├── llamaindex/     # LlamaIndex integration
│   │   └── agents/         # Agent framework (Agno)
│   ├── models/             # Database models
│   │   ├── assistants.py   # Assistant models
│   │   ├── knowledge.py    # Knowledge base models
│   │   └── chat.py         # Chat models
│   ├── schemas/            # Pydantic schemas
│   ├── utils/              # Utility functions
│   │   ├── database.py     # Database utilities
│   │   ├── vector_store.py # Milvus integration
│   │   ├── redis_client.py # Redis integration
│   │   ├── object_storage.py # MinIO integration
│   │   ├── message_queue.py # RabbitMQ integration
│   │   └── service_discovery.py # Nacos integration
│   └── worker.py           # Celery worker tasks
│   └── config.py           # Application configuration
├── main.py                 # Application entry point
├── .env.example            # Environment variable template
├── docker-compose.yml      # Infrastructure setup
└── requirements.txt        # Dependencies
```

## Getting Started

### Prerequisites

- Python 3.9+
- Docker and Docker Compose (for infrastructure)

### Setup Infrastructure

1. Start the required infrastructure services:

```bash
docker-compose up -d
```

This will launch PostgreSQL, Milvus, Redis, MinIO, RabbitMQ, and Nacos.

2. Configure environment variables:

```bash
cp .env.example .env
# Edit .env with your specific settings, especially API keys
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Initialize database schema (first run):

```bash
alembic upgrade head
```

5. Start the backend service:

```bash
python main.py
```

6. Start the Celery worker for background tasks:

```bash
celery -A app.worker worker --loglevel=info
```

## API Endpoints

The service exposes several RESTful API endpoints:

### Assistant Management

- `GET /api/assistants/` - List all assistants
- `POST /api/assistants/` - Create a new assistant
- `GET /api/assistants/{assistant_id}` - Get assistant details
- `PUT /api/assistants/{assistant_id}` - Update assistant
- `DELETE /api/assistants/{assistant_id}` - Delete/deactivate assistant

### Knowledge Base Management

- `GET /api/knowledge/` - List all knowledge bases
- `POST /api/knowledge/` - Create a new knowledge base
- `GET /api/knowledge/{knowledge_base_id}` - Get knowledge base details
- `PUT /api/knowledge/{knowledge_base_id}` - Update knowledge base
- `DELETE /api/knowledge/{knowledge_base_id}` - Delete knowledge base
- `GET /api/knowledge/{knowledge_base_id}/documents` - List documents
- `POST /api/knowledge/{knowledge_base_id}/documents` - Add a document

### Chat Interface

- `GET /api/chat/conversations` - List conversations
- `POST /api/chat/conversations` - Create a new conversation
- `GET /api/chat/conversations/{conversation_id}` - Get conversation with messages
- `POST /api/chat/` - Send a message and get AI response

## Assistant Capabilities

Each assistant can be configured with different capabilities:

- **Customer Support**: Handle customer service queries
- **Question Answering**: Respond to general knowledge questions
- **Service Introduction**: Provide information about services

## Knowledge Base Integration

Assistants can be linked to multiple knowledge bases, enabling them to answer questions based on specific document collections. Documents are automatically processed:

1. Documents are uploaded and parsed based on file type
2. Content is chunked into manageable segments
3. Embeddings are generated for each chunk
4. Chunks are stored in Milvus for vector similarity search
5. When questions are asked, relevant chunks are retrieved to inform the AI response

## Advanced Features

### Distributed Processing

Long-running tasks like document processing are handled asynchronously using Celery and RabbitMQ, preventing API timeouts.

### Service Discovery

The service registers itself with Nacos, enabling other services to discover and communicate with it dynamically.

### Scalability

The architecture supports horizontal scaling:
- Stateless API servers can be deployed behind a load balancer
- Multiple Celery workers can process tasks in parallel
- Infrastructure components like Milvus and PostgreSQL support clustering

## Customization

The system can be extended in several ways:

- Add new document parsers in `app/core/knowledge/document_processor.py`
- Implement additional AI frameworks in the `app/frameworks/` directory
- Create new assistant capabilities by extending the data models and core service logic

## Security Considerations

- API keys and sensitive data should be properly secured in the `.env` file
- MinIO bucket permissions should be carefully configured
- Consider implementing proper authentication and authorization for production use
