"""
助手仓库模块: 提供对助手实体的数据访问
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.models.assistant import Assistant, assistant_knowledge_base
from app.models.knowledge import KnowledgeBase
from app.repositories.base import BaseRepository

class AssistantRepository(BaseRepository[Assistant]):
    """助手仓库"""
    
    def __init__(self, db: Session):
        super().__init__(Assistant, db)
    
    def get_with_knowledge_bases(self, assistant_id: str) -> Optional[Assistant]:
        """获取助手及其关联的知识库"""
        return self.db.query(Assistant).options(
            joinedload(Assistant.knowledge_bases)
        ).filter(Assistant.id == assistant_id).first()
    
    def get_by_framework(self, framework: str, skip: int = 0, limit: int = 100) -> List[Assistant]:
        """获取特定框架的所有助手"""
        return self.db.query(Assistant).filter(Assistant.framework == framework).offset(skip).limit(limit).all()
    
    def search_assistants(self, query: str, skip: int = 0, limit: int = 20) -> List[Assistant]:
        """搜索助手"""
        search = f"%{query}%"
        return self.db.query(Assistant).filter(
            or_(
                Assistant.name.ilike(search),
                Assistant.description.ilike(search)
            )
        ).offset(skip).limit(limit).all()
    
    def add_knowledge_base(self, assistant_id: str, kb_id: str) -> bool:
        """为助手添加知识库"""
        try:
            assistant = self.get_by_id(assistant_id)
            kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            
            if assistant and kb:
                # 检查关联是否已存在
                exists = self.db.query(assistant_knowledge_base).filter(
                    assistant_knowledge_base.c.assistant_id == assistant_id,
                    assistant_knowledge_base.c.knowledge_base_id == kb_id
                ).first() is not None
                
                if not exists:
                    # 添加知识库到助手
                    assistant.knowledge_bases.append(kb)
                    self.db.commit()
                
                return True
            
            return False
        except Exception as e:
            self.db.rollback()
            raise
    
    def remove_knowledge_base(self, assistant_id: str, kb_id: str) -> bool:
        """移除助手的知识库"""
        try:
            assistant = self.get_with_knowledge_bases(assistant_id)
            
            if assistant:
                # 查找要移除的知识库
                kb_to_remove = None
                for kb in assistant.knowledge_bases:
                    if kb.id == kb_id:
                        kb_to_remove = kb
                        break
                
                if kb_to_remove:
                    # 移除关联
                    assistant.knowledge_bases.remove(kb_to_remove)
                    self.db.commit()
                    return True
            
            return False
        except Exception as e:
            self.db.rollback()
            raise
    
    def get_knowledge_bases(self, assistant_id: str) -> List[KnowledgeBase]:
        """获取助手关联的所有知识库"""
        assistant = self.get_with_knowledge_bases(assistant_id)
        if assistant:
            return assistant.knowledge_bases
        return []
