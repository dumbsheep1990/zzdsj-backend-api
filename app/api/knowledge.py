from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
import os
import json
from datetime import datetime

from app.models.database import get_db
from app.models.knowledge import KnowledgeBase, Document, DocumentChunk
from app.schemas.knowledge import (
    KnowledgeBase as KnowledgeBaseSchema,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseWithStats,
    Document as DocumentSchema,
    DocumentCreate,
    DocumentUpdate,
    KnowledgeBaseStats,
    DocumentListResponse
)
from app.frameworks.agno import KnowledgeBaseProcessor
from app.utils.object_storage import upload_file, get_file_url

router = APIRouter()

@router.get("/", response_model=List[KnowledgeBaseWithStats])
def get_knowledge_bases(
    skip: int = 0, 
    limit: int = 100,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all knowledge bases with statistics, supporting search and filtering.
    """
    query = db.query(KnowledgeBase)
    
    if is_active is not None:
        query = query.filter(KnowledgeBase.is_active == is_active)
    
    if search:
        query = query.filter(KnowledgeBase.name.ilike(f"%{search}%") | 
                           KnowledgeBase.description.ilike(f"%{search}%"))
    
    # Get basic knowledge base data
    knowledge_bases = query.offset(skip).limit(limit).all()
    
    # Enrich with stats
    result = []
    for kb in knowledge_bases:
        # Get document count and file type distribution
        doc_count = db.query(func.count(Document.id)).filter(
            Document.knowledge_base_id == kb.id
        ).scalar()
        
        # Get file type distribution
        file_types_query = db.query(
            Document.mime_type, 
            func.count(Document.id)
        ).filter(
            Document.knowledge_base_id == kb.id
        ).group_by(Document.mime_type).all()
        
        file_types = {mime_type: count for mime_type, count in file_types_query}
        
        # Get token count
        token_count = db.query(func.sum(DocumentChunk.token_count)).join(
            Document, DocumentChunk.document_id == Document.id
        ).filter(
            Document.knowledge_base_id == kb.id
        ).scalar() or 0
        
        # Create enriched model
        kb_with_stats = KnowledgeBaseWithStats(
            **{k: getattr(kb, k) for k in kb.__table__.columns.keys()},
            document_count=doc_count,
            total_tokens=token_count,
            file_types=file_types
        )
        
        result.append(kb_with_stats)
    
    return result

@router.post("/", response_model=KnowledgeBaseSchema)
async def create_knowledge_base(
    knowledge_base: KnowledgeBaseCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new knowledge base, initializing Agno integration.
    """
    # Create database record
    db_knowledge_base = KnowledgeBase(
        name=knowledge_base.name,
        description=knowledge_base.description,
        settings=knowledge_base.settings,
        type=knowledge_base.type,
        embedding_model=knowledge_base.embedding_model
    )
    db.add(db_knowledge_base)
    db.commit()
    db.refresh(db_knowledge_base)
    
    # Initialize Agno knowledge base in background
    background_tasks.add_task(
        initialize_agno_knowledge_base,
        db_knowledge_base.id,
        db
    )
    
    return db_knowledge_base

async def initialize_agno_knowledge_base(kb_id: int, db: Session):
    """Initialize an Agno knowledge base for the given database record"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        print(f"Knowledge base {kb_id} not found for Agno initialization")
        return
    
    try:
        # Initialize Agno KB processor
        kb_processor = KnowledgeBaseProcessor(
            kb_id=str(kb_id),
            name=kb.name
        )
        
        # Generate a unique Agno KB ID
        import uuid
        agno_kb_id = f"agno-kb-{uuid.uuid4()}"
        
        # Update database record with Agno KB ID
        kb.agno_kb_id = agno_kb_id
        db.commit()
        
        print(f"Initialized Agno knowledge base for {kb.name} with ID {agno_kb_id}")
    except Exception as e:
        print(f"Error initializing Agno knowledge base: {e}")
        # Update record with error
        kb.settings = {**kb.settings, "initialization_error": str(e)}
        db.commit()

@router.get("/{knowledge_base_id}", response_model=KnowledgeBaseWithStats)
def get_knowledge_base(
    knowledge_base_id: int,
    db: Session = Depends(get_db)
):
    """
    Get knowledge base by ID with detailed statistics.
    """
    # Get knowledge base
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    # Get document stats
    doc_count = db.query(func.count(Document.id)).filter(
        Document.knowledge_base_id == knowledge_base_id
    ).scalar()
    
    # Get file type distribution
    file_types_query = db.query(
        Document.mime_type, 
        func.count(Document.id)
    ).filter(
        Document.knowledge_base_id == knowledge_base_id
    ).group_by(Document.mime_type).all()
    
    file_types = {mime_type: count for mime_type, count in file_types_query}
    
    # Get token count
    token_count = db.query(func.sum(DocumentChunk.token_count)).join(
        Document, DocumentChunk.document_id == Document.id
    ).filter(
        Document.knowledge_base_id == knowledge_base_id
    ).scalar() or 0
    
    # Create enriched response
    kb_with_stats = KnowledgeBaseWithStats(
        **{k: getattr(knowledge_base, k) for k in knowledge_base.__table__.columns.keys()},
        document_count=doc_count,
        total_tokens=token_count,
        file_types=file_types
    )
    
    return kb_with_stats

@router.get("/{knowledge_base_id}/stats", response_model=KnowledgeBaseStats)
def get_knowledge_base_stats(
    knowledge_base_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed knowledge base statistics.
    """
    # Check if knowledge base exists
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    # Get document counts by status
    doc_count = db.query(func.count(Document.id)).filter(
        Document.knowledge_base_id == knowledge_base_id
    ).scalar()
    
    processed_count = db.query(func.count(Document.id)).filter(
        Document.knowledge_base_id == knowledge_base_id,
        Document.status == "indexed"
    ).scalar()
    
    pending_count = db.query(func.count(Document.id)).filter(
        Document.knowledge_base_id == knowledge_base_id,
        Document.status.in_(["pending", "processing"])
    ).scalar()
    
    error_count = db.query(func.count(Document.id)).filter(
        Document.knowledge_base_id == knowledge_base_id,
        Document.status == "error"
    ).scalar()
    
    # Get file type distribution
    file_types_query = db.query(
        Document.mime_type, 
        func.count(Document.id)
    ).filter(
        Document.knowledge_base_id == knowledge_base_id
    ).group_by(Document.mime_type).all()
    
    file_types = {mime_type: count for mime_type, count in file_types_query}
    
    # Get token count
    token_count = db.query(func.sum(DocumentChunk.token_count)).join(
        Document, DocumentChunk.document_id == Document.id
    ).filter(
        Document.knowledge_base_id == knowledge_base_id
    ).scalar() or 0
    
    return KnowledgeBaseStats(
        document_count=doc_count,
        total_tokens=token_count or 0,
        processed_count=processed_count,
        pending_count=pending_count,
        error_count=error_count,
        file_types=file_types
    )

@router.put("/{knowledge_base_id}", response_model=KnowledgeBaseSchema)
def update_knowledge_base(
    knowledge_base_id: int,
    knowledge_base_update: KnowledgeBaseUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a knowledge base.
    """
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    # Update fields that are provided
    update_data = knowledge_base_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(knowledge_base, field, value)
    
    db.commit()
    db.refresh(knowledge_base)
    return knowledge_base

@router.delete("/{knowledge_base_id}")
def delete_knowledge_base(
    knowledge_base_id: int,
    permanent: bool = False,
    db: Session = Depends(get_db)
):
    """
    Delete or deactivate a knowledge base.
    """
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    if permanent:
        # Delete documents and chunks
        documents = db.query(Document).filter(Document.knowledge_base_id == knowledge_base_id).all()
        for doc in documents:
            # Delete chunks
            db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
        
        # Delete documents
        db.query(Document).filter(Document.knowledge_base_id == knowledge_base_id).delete()
        
        # Delete knowledge base
        db.delete(knowledge_base)
        db.commit()
        
        return {"message": "Knowledge base permanently deleted"}
    else:
        # Soft delete by setting is_active to False
        knowledge_base.is_active = False
        db.commit()
        
        return {"message": "Knowledge base deactivated successfully"}

# Document management endpoints
@router.get("/{knowledge_base_id}/documents", response_model=DocumentListResponse)
def get_documents(
    knowledge_base_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    mime_type: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    db: Session = Depends(get_db)
):
    """
    Get all documents in a knowledge base with pagination, filtering, and sorting.
    """
    # Check if knowledge base exists
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    # Build base query
    query = db.query(Document).filter(Document.knowledge_base_id == knowledge_base_id)
    
    # Apply filters
    if search:
        query = query.filter(Document.title.ilike(f"%{search}%"))
    
    if status:
        query = query.filter(Document.status == status)
    
    if mime_type:
        query = query.filter(Document.mime_type == mime_type)
    
    # Get total count
    total_count = query.count()
    
    # Apply sorting
    if sort_by:
        sort_column = getattr(Document, sort_by, Document.created_at)
        if sort_order.lower() == "desc":
            sort_column = sort_column.desc()
        else:
            sort_column = sort_column.asc()
        query = query.order_by(sort_column)
    
    # Apply pagination
    skip = (page - 1) * page_size
    query = query.offset(skip).limit(page_size)
    
    # Get results
    documents = query.all()
    
    return DocumentListResponse(
        items=documents,
        total=total_count,
        page=page,
        page_size=page_size
    )

@router.post("/{knowledge_base_id}/documents", response_model=DocumentSchema)
async def create_document(
    knowledge_base_id: int,
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    file: Optional[UploadFile] = File(None),
    content: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Add a new document to a knowledge base either by uploading a file or providing content directly.
    Uses Agno for document processing and indexing.
    """
    # Check if knowledge base exists
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    if file is None and content is None:
        raise HTTPException(status_code=400, detail="Either file or content must be provided")
    
    # Create document record
    document = Document(
        knowledge_base_id=knowledge_base_id,
        title=title,
        status="pending"
    )
    
    if file:
        # Process uploaded file
        file_content = await file.read()
        mime_type = file.content_type
        file_size = len(file_content)
        
        document.mime_type = mime_type
        document.file_size = file_size
        
        if mime_type.startswith("text/"):
            document.content = file_content.decode()
        
        # Upload file to object storage (MinIO)
        file_path = f"knowledge-bases/{knowledge_base_id}/documents/{file.filename}"
        upload_result = upload_file(
            file_data=file.file,
            object_name=file_path,
            content_type=mime_type
        )
        
        document.file_path = file_path
        document.metadata = {
            "filename": file.filename,
            "content_type": mime_type,
            "size": file_size,
            "upload_date": datetime.now().isoformat()
        }
    else:
        # Save direct content
        document.content = content
        document.mime_type = "text/plain"
        document.file_size = len(content.encode())
        document.metadata = {
            "source": "direct_input",
            "content_type": "text/plain",
            "size": len(content.encode()),
            "creation_date": datetime.now().isoformat()
        }
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Process document with Agno in background
    background_tasks.add_task(
        process_document_with_agno,
        document.id,
        db
    )
    
    return document

async def process_document_with_agno(document_id: int, db: Session):
    """Process a document using Agno's knowledge base capabilities"""
    # Get document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        print(f"Document {document_id} not found for Agno processing")
        return
    
    # Update status
    document.status = "processing"
    db.commit()
    
    try:
        # Get knowledge base
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == document.knowledge_base_id).first()
        if not kb:
            raise ValueError(f"Knowledge base {document.knowledge_base_id} not found")
        
        # Initialize Agno KB processor
        kb_processor = KnowledgeBaseProcessor(
            kb_id=str(kb.id),
            name=kb.name
        )
        
        # Prepare document data
        doc_data = {
            "content": document.content,
            "metadata": {
                **document.metadata,
                "document_id": document.id,
                "title": document.title,
                "mime_type": document.mime_type
            }
        }
        
        # Add document to Agno knowledge base
        result = await kb_processor.add_document(doc_data)
        
        # Store chunk information
        # In a real implementation, we'd extract actual chunks from the result
        # For now, we'll create simulated chunks
        from app.utils.text_processing import count_tokens
        
        if document.content:
            # Calculate token count
            token_count = count_tokens(document.content)
            
            # For simulation, create chunks (in real implementation this would come from Agno)
            chunk_size = 1000
            chunks = [document.content[i:i+chunk_size] for i in range(0, len(document.content), chunk_size)]
            
            for i, chunk_text in enumerate(chunks):
                chunk = DocumentChunk(
                    document_id=document.id,
                    content=chunk_text,
                    metadata={
                        "chunk_index": i,
                        "document_id": document.id
                    },
                    embedding_id=f"doc-{document.id}-chunk-{i}",
                    token_count=count_tokens(chunk_text)
                )
                db.add(chunk)
            
            # Update document and knowledge base stats
            document.status = "indexed"
            kb.total_documents += 1
            kb.total_tokens += token_count
            
            db.commit()
        else:
            document.status = "error"
            document.error_message = "No content to process"
            db.commit()
    
    except Exception as e:
        # Update document status to error
        document.status = "error"
        document.error_message = str(e)
        db.commit()
        print(f"Error processing document with Agno: {e}")

@router.get("/{knowledge_base_id}/documents/{document_id}", response_model=DocumentSchema)
def get_document(
    knowledge_base_id: int,
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a document by ID.
    """
    document = db.query(Document).filter(
        Document.knowledge_base_id == knowledge_base_id,
        Document.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return document

@router.delete("/{knowledge_base_id}/documents/{document_id}")
async def delete_document(
    knowledge_base_id: int,
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Delete a document from the knowledge base.
    """
    document = db.query(Document).filter(
        Document.knowledge_base_id == knowledge_base_id,
        Document.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete document chunks first
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    
    # Delete document from database
    db.delete(document)
    db.commit()
    
    # Remove from Agno in background
    background_tasks.add_task(
        remove_document_from_agno,
        knowledge_base_id,
        document_id
    )
    
    return {"message": "Document deleted successfully"}

async def remove_document_from_agno(knowledge_base_id: int, document_id: int):
    """Remove a document from Agno knowledge base"""
    try:
        # Initialize Agno KB processor
        kb_processor = KnowledgeBaseProcessor(
            kb_id=str(knowledge_base_id)
        )
        
        # Remove document from Agno
        await kb_processor.remove_document(document_id=str(document_id))
        
        print(f"Successfully removed document {document_id} from Agno knowledge base {knowledge_base_id}")
    except Exception as e:
        print(f"Error removing document from Agno: {e}")
        # In a production system, we might want to:
        # 1. Log this error to a monitoring system
        # 2. Add to a retry queue
        # 3. Update the document status in the database

# Helper function for token counting since we're not importing
# Agno directly yet
def count_tokens(text: str) -> int:
    """Count tokens in a text string (placeholder function)"""
    import re
    # Simple approximation: ~4 chars per token
    return len(re.findall(r'\S+', text)) + len(text) // 4
