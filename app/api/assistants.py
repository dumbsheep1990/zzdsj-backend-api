from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.assistants import Assistant, AssistantKnowledgeBase
from app.schemas.assistants import (
    Assistant as AssistantSchema,
    AssistantCreate,
    AssistantUpdate,
    AssistantWithKnowledgeBases
)

router = APIRouter()

@router.get("/", response_model=List[AssistantSchema])
def get_assistants(
    skip: int = 0, 
    limit: int = 100, 
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Get all assistants with optional filtering.
    """
    query = db.query(Assistant)
    
    if is_active is not None:
        query = query.filter(Assistant.is_active == is_active)
    
    return query.offset(skip).limit(limit).all()

@router.post("/", response_model=AssistantSchema)
def create_assistant(
    assistant: AssistantCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new assistant.
    """
    db_assistant = Assistant(
        name=assistant.name,
        description=assistant.description,
        model_id=assistant.model_id,
        capabilities=assistant.capabilities
    )
    db.add(db_assistant)
    db.commit()
    db.refresh(db_assistant)
    return db_assistant

@router.get("/{assistant_id}", response_model=AssistantWithKnowledgeBases)
def get_assistant(
    assistant_id: int,
    db: Session = Depends(get_db)
):
    """
    Get assistant by ID with associated knowledge bases.
    """
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    return assistant

@router.put("/{assistant_id}", response_model=AssistantSchema)
def update_assistant(
    assistant_id: int,
    assistant_update: AssistantUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an assistant.
    """
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    # Update fields that are provided
    update_data = assistant_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(assistant, field, value)
    
    db.commit()
    db.refresh(assistant)
    return assistant

@router.delete("/{assistant_id}")
def delete_assistant(
    assistant_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete or deactivate an assistant.
    """
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    # Soft delete by setting is_active to False
    assistant.is_active = False
    db.commit()
    
    return {"message": "Assistant deactivated successfully"}

@router.post("/{assistant_id}/knowledge-bases/{knowledge_base_id}")
def link_knowledge_base(
    assistant_id: int,
    knowledge_base_id: int,
    db: Session = Depends(get_db)
):
    """
    Link a knowledge base to an assistant.
    """
    # Check if assistant exists
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    # Check if knowledge base exists
    from app.models.knowledge import KnowledgeBase
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    # Check if the link already exists
    existing_link = db.query(AssistantKnowledgeBase).filter(
        AssistantKnowledgeBase.assistant_id == assistant_id,
        AssistantKnowledgeBase.knowledge_base_id == knowledge_base_id
    ).first()
    
    if existing_link:
        return {"message": "Knowledge base is already linked to this assistant"}
    
    # Create the link
    link = AssistantKnowledgeBase(
        assistant_id=assistant_id,
        knowledge_base_id=knowledge_base_id
    )
    db.add(link)
    db.commit()
    
    return {"message": "Knowledge base linked to assistant successfully"}
