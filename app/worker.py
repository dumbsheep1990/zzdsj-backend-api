from celery import Celery
from app.config import settings
import time
from app.utils.core.database import SessionLocal

# 初始化Celery应用
celery_app = Celery(
    "knowledge_qa_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# 配置Celery
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
    在后台处理文档
    - 根据需要提取内容
    - 对文档进行分块
    - 创建向量嵌入
    - 存储到向量数据库
    """
    from core.knowledge.document_processor import process_document
    from sqlalchemy.orm import Session
    
    # 获取数据库会话
    db = SessionLocal()
    try:
        # 处理文档
        process_document(document_id, db)
        return {"status": "success", "document_id": document_id}
    
    except Exception as e:
        return {"status": "error", "document_id": document_id, "error": str(e)}
    
    finally:
        db.close()

@celery_app.task(name="rebuild_vector_store")
def rebuild_vector_store_task():
    """
    重建整个向量存储
    - 清除现有向量存储
    - 处理所有文档
    - 为所有文档创建嵌入向量
    """
    from app.utils.vector_store import init_milvus
    from app.models.knowledge import Document
    from sqlalchemy.orm import Session
    
    # 获取数据库会话
    db = SessionLocal()
    try:
        # 初始化Milvus
        init_milvus()
        
        # 获取所有文档
        documents = db.query(Document).all()
        
        # 处理每个文档
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
    在后台生成助手回复
    - 检索对话历史
    - 检索相关文档
    - 生成回复
    - 将回复保存到数据库
    """
    from core.chat.chat_service import generate_assistant_response
    from app.models.chat import Conversation, Message
    from sqlalchemy.orm import Session
    
    # 获取数据库会话
    db = SessionLocal()
    try:
        # 获取对话
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            return {"status": "error", "error": "对话未找到"}
        
        # 获取消息
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            return {"status": "error", "error": "消息未找到"}
        
        # 生成回复
        result = generate_assistant_response(db, conversation, message)
        
        return {"status": "success", "response_id": result.get("message_id")}
    
    except Exception as e:
        return {"status": "error", "error": str(e)}
    
    finally:
        db.close()
