from celery import Celery
from app.config import settings
import time

# Initialize Celery app
celery_app = Celery(
    "knowledge_qa_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1
)

@celery_app.task(name="process_document")
def process_document_task(document_id: int):
    """
    Process a document in the background
    - Extract content if needed
    - Chunk the document
    - Create embeddings
    - Store in vector database
    """
    from app.core.knowledge.document_processor import process_document
    from sqlalchemy.orm import Session
    from app.utils.database import SessionLocal
    
    # Get database session
    db = SessionLocal()
    try:
        # Process document
        process_document(document_id, db)
        return {"status": "success", "document_id": document_id}
    
    except Exception as e:
        return {"status": "error", "document_id": document_id, "error": str(e)}
    
    finally:
        db.close()

@celery_app.task(name="rebuild_vector_store")
def rebuild_vector_store_task():
    """
    Rebuild the entire vector store
    - Clear existing vector store
    - Process all documents
    - Create embeddings for all documents
    """
    from app.utils.vector_store import init_milvus
    from app.models.knowledge import Document
    from sqlalchemy.orm import Session
    from app.utils.database import SessionLocal
    
    # Get database session
    db = SessionLocal()
    try:
        # Initialize Milvus
        init_milvus()
        
        # Get all documents
        documents = db.query(Document).all()
        
        # Process each document
        for document in documents:
            process_document_task.delay(document.id)
        
        return {"status": "success", "documents_count": len(documents)}
    
    except Exception as e:
        return {"status": "error", "error": str(e)}
    
    finally:
        db.close()

@celery_app.task(name="generate_assistant_response")
def generate_assistant_response_task(conversation_id: int, message_id: int):
    """
    Generate an assistant response in the background
    - Retrieve conversation history
    - Retrieve relevant documents
    - Generate response
    - Save response to database
    """
    from app.core.chat.chat_service import generate_assistant_response
    from app.models.chat import Conversation, Message
    from sqlalchemy.orm import Session
    from app.utils.database import SessionLocal
    
    # Get database session
    db = SessionLocal()
    try:
        # Get conversation
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            return {"status": "error", "error": "Conversation not found"}
        
        # Get message
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            return {"status": "error", "error": "Message not found"}
        
        # Generate response
        result = generate_assistant_response(db, conversation, message)
        
        return {"status": "success", "response_id": result.get("message_id")}
    
    except Exception as e:
        return {"status": "error", "error": str(e)}
    
    finally:
        db.close()
