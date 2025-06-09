"""
助手仓储实现
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import delete, select, and_, or_, func
from sqlalchemy.orm import selectinload
from .base import AsyncBaseRepository
from app.models.assistants.assistant import Assistant, AssistantKnowledgeBase
from sqlalchemy.ext.asyncio import AsyncSession

class AsyncAssistantRepository(AsyncBaseRepository[Assistant]):
    """异步助手仓储"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Assistant)

    async def get_by_owner(self, owner_id: int, skip: int = 0, limit: int = 100) -> List[Assistant]:
        """获取用户的助手列表"""
        stmt = select(Assistant).where(
            and_(
                Assistant.owner_id == owner_id,
                Assistant.is_active == True
            )
        ).offset(skip).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_public_assistants(self, skip: int = 0, limit: int = 100) -> List[Assistant]:
        """获取公开助手列表"""
        stmt = select(Assistant).where(
            and_(
                Assistant.is_public == True,
                Assistant.is_active == True
            )
        ).offset(skip).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def search(
        self, 
        query: str = "", 
        user_id: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> Tuple[List[Assistant], int]:
        """搜索助手"""
        # 构建基础查询
        stmt = select(Assistant).where(Assistant.is_active == True)

        # 权限筛选
        if user_id:
            stmt = stmt.where(
                or_(
                    Assistant.owner_id == user_id,
                    Assistant.is_public == True
                )
            )
        else:
            stmt = stmt.where(Assistant.is_public == True)

        # 文本搜索
        if query:
            stmt = stmt.where(
                or_(
                    Assistant.name.ilike(f"%{query}%"),
                    Assistant.description.ilike(f"%{query}%")
                )
            )

        # 其他筛选
        if filters:
            if filters.get("category"):
                stmt = stmt.where(Assistant.category == filters["category"])
            if filters.get("capabilities"):
                stmt = stmt.where(Assistant.capabilities.overlap(filters["capabilities"]))

         # 获取总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()
        
        # 获取分页结果
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        assistants = result.scalars().all()
        
        return assistants, total

    async def add_knowledge_base(self, assistant_id: int, knowledge_base_id: int) -> bool:
        """添加知识库关联"""
        try:
            link = AssistantKnowledgeBase(
                assistant_id=assistant_id,
                knowledge_base_id=knowledge_base_id
            )
            self.db.add(link)
            await self.db.commit()  # ✅ 改为异步
            return True
        except Exception as e:
            await self.db.rollback()  # ✅ 改为异步
            self.logger.error(f"Failed to add knowledge base: {str(e)}")
            return False

    async def remove_knowledge_base(self, assistant_id: int, knowledge_base_id: int) -> bool:
        """移除知识库关联"""
        try:
            # ✅ 改为异步删除
            stmt = delete(AssistantKnowledgeBase).where(
                and_(
                    AssistantKnowledgeBase.assistant_id == assistant_id,
                    AssistantKnowledgeBase.knowledge_base_id == knowledge_base_id
                )
            )
            await self.db.execute(stmt)
            await self.db.commit()  # ✅ 改为异步
            return True
        except Exception as e:
            await self.db.rollback()  # ✅ 改为异步
            self.logger.error(f"Failed to remove knowledge base: {str(e)}")
            return False

    async def get_knowledge_bases(self, assistant_id: int) -> List[int]:
        """获取助手的知识库ID列表"""
        # ✅ 改为异步查询
        stmt = select(AssistantKnowledgeBase).where(
            AssistantKnowledgeBase.assistant_id == assistant_id
        )
        result = await self.db.execute(stmt)
        links = result.scalars().all()
        return [link.knowledge_base_id for link in links]

    async def soft_delete(self, id: int) -> bool:
        """软删除助手"""
        return await self.update(id, is_active=False)