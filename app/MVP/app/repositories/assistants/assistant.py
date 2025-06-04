"""
助手仓储实现
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import and_, or_
from app.repositories.assistants.base import BaseRepository
from app.models.assistants.assistant import Assistant, AssistantKnowledgeBase


class AssistantRepository(BaseRepository[Assistant]):
    """助手仓储"""

    def __init__(self, db):
        super().__init__(db, Assistant)

    async def get_by_owner(self, owner_id: int, skip: int = 0, limit: int = 100) -> List[Assistant]:
        """获取用户的助手列表"""
        return self.db.query(Assistant).filter(
            Assistant.owner_id == owner_id,
            Assistant.is_active == True
        ).offset(skip).limit(limit).all()

    async def get_public_assistants(self, skip: int = 0, limit: int = 100) -> List[Assistant]:
        """获取公开助手列表"""
        return self.db.query(Assistant).filter(
            Assistant.is_public == True,
            Assistant.is_active == True
        ).offset(skip).limit(limit).all()

    async def search(
            self,
            query: str,
            user_id: Optional[int] = None,
            filters: Optional[Dict[str, Any]] = None,
            skip: int = 0,
            limit: int = 100
    ) -> Tuple[List[Assistant], int]:
        """搜索助手"""
        search_query = self.db.query(Assistant).filter(
            Assistant.is_active == True
        )

        # 用户权限过滤
        if user_id:
            search_query = search_query.filter(
                or_(
                    Assistant.owner_id == user_id,
                    Assistant.is_public == True
                )
            )
        else:
            search_query = search_query.filter(Assistant.is_public == True)

        # 搜索条件
        if query:
            search_pattern = f"%{query}%"
            search_query = search_query.filter(
                or_(
                    Assistant.name.ilike(search_pattern),
                    Assistant.description.ilike(search_pattern)
                )
            )

        # 额外过滤条件
        if filters:
            if "category" in filters:
                search_query = search_query.filter(Assistant.category == filters["category"])

            if "capabilities" in filters:
                for cap in filters["capabilities"]:
                    search_query = search_query.filter(Assistant.capabilities.contains([cap]))

            if "tags" in filters:
                for tag in filters["tags"]:
                    search_query = search_query.filter(Assistant.tags.contains([tag]))

            if "model" in filters:
                search_query = search_query.filter(Assistant.model == filters["model"])

        # 获取总数
        total = search_query.count()

        # 分页
        assistants = search_query.offset(skip).limit(limit).all()

        return assistants, total

    async def add_knowledge_base(self, assistant_id: int, knowledge_base_id: int) -> bool:
        """添加知识库关联"""
        try:
            link = AssistantKnowledgeBase(
                assistant_id=assistant_id,
                knowledge_base_id=knowledge_base_id
            )
            self.db.add(link)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to add knowledge base: {str(e)}")
            return False

    async def remove_knowledge_base(self, assistant_id: int, knowledge_base_id: int) -> bool:
        """移除知识库关联"""
        try:
            self.db.query(AssistantKnowledgeBase).filter(
                AssistantKnowledgeBase.assistant_id == assistant_id,
                AssistantKnowledgeBase.knowledge_base_id == knowledge_base_id
            ).delete()
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to remove knowledge base: {str(e)}")
            return False

    async def get_knowledge_bases(self, assistant_id: int) -> List[int]:
        """获取助手的知识库ID列表"""
        links = self.db.query(AssistantKnowledgeBase).filter(
            AssistantKnowledgeBase.assistant_id == assistant_id
        ).all()
        return [link.knowledge_base_id for link in links]

    async def soft_delete(self, id: int) -> bool:
        """软删除助手"""
        return await self.update(id, is_active=False)