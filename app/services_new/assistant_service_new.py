"""
助手服务层：统一处理所有助手相关的业务逻辑
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

from app.models.assistant import Assistant, Conversation, Message, AssistantKnowledgeBase
from app.models.knowledge import KnowledgeBase
from app.schemas.assistant import (
    AssistantCreate, AssistantUpdate, AssistantResponse,
    ConversationCreate, ConversationResponse,
    MessageCreate, MessageResponse
)
from app.core.exceptions import NotFoundError, PermissionError, ValidationError

logger = logging.getLogger(__name__)


class AssistantService:
    """助手服务类"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 助手管理 ====================

    async def create_assistant(self, data: Dict[str, Any], user_id: int) -> Assistant:
        """创建助手"""
        try:
            # 设置所有者
            data['owner_id'] = user_id

            # 创建助手实例
            assistant = Assistant(**data)
            self.db.add(assistant)
            self.db.commit()
            self.db.refresh(assistant)

            logger.info(f"Created assistant: {assistant.id} for user: {user_id}")
            return assistant

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create assistant: {str(e)}")
            raise ValidationError(f"创建助手失败: {str(e)}")

    async def get_assistant_by_id(self, assistant_id: int, user_id: Optional[int] = None) -> Optional[Assistant]:
        """获取助手详情"""
        assistant = self.db.query(Assistant).filter(
            Assistant.id == assistant_id,
            Assistant.is_active == True
        ).first()

        if not assistant:
            return None

        # 权限检查：用户只能访问自己的助手或公开助手
        if user_id and not assistant.is_public and assistant.owner_id != user_id:
            raise PermissionError("无权访问该助手")

        return assistant

    async def get_assistants(
            self,
            skip: int = 0,
            limit: int = 100,
            user_id: Optional[int] = None,
            category: Optional[str] = None,
            capabilities: Optional[List[str]] = None,
            is_public: Optional[bool] = None,
            search: Optional[str] = None,
            tags: Optional[List[str]] = None
    ) -> Tuple[List[Assistant], int]:
        """获取助手列表"""
        query = self.db.query(Assistant).filter(Assistant.is_active == True)

        # 用户过滤：用户可以看到自己的助手和公开助手
        if user_id:
            query = query.filter(
                or_(
                    Assistant.owner_id == user_id,
                    Assistant.is_public == True
                )
            )

        # 分类过滤
        if category:
            query = query.filter(Assistant.category == category)

        # 能力过滤
        if capabilities:
            for cap in capabilities:
                query = query.filter(Assistant.capabilities.contains([cap]))

        # 公开性过滤
        if is_public is not None:
            query = query.filter(Assistant.is_public == is_public)

        # 搜索过滤
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Assistant.name.ilike(search_pattern),
                    Assistant.description.ilike(search_pattern)
                )
            )

        # 标签过滤
        if tags:
            for tag in tags:
                query = query.filter(Assistant.tags.contains([tag]))

        # 获取总数
        total = query.count()

        # 分页
        assistants = query.offset(skip).limit(limit).all()

        return assistants, total

    async def update_assistant(self, assistant_id: int, data: Dict[str, Any], user_id: int) -> Assistant:
        """更新助手"""
        assistant = await self.get_assistant_by_id(assistant_id)
        if not assistant:
            raise NotFoundError("助手不存在")

        # 权限检查：只有所有者可以更新
        if assistant.owner_id != user_id:
            raise PermissionError("只有所有者可以更新助手")

        try:
            # 更新字段
            for key, value in data.items():
                if hasattr(assistant, key) and value is not None:
                    setattr(assistant, key, value)

            assistant.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(assistant)

            logger.info(f"Updated assistant: {assistant_id}")
            return assistant

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update assistant: {str(e)}")
            raise ValidationError(f"更新助手失败: {str(e)}")

    async def delete_assistant(self, assistant_id: int, user_id: int) -> bool:
        """删除助手（软删除）"""
        assistant = await self.get_assistant_by_id(assistant_id)
        if not assistant:
            raise NotFoundError("助手不存在")

        # 权限检查：只有所有者可以删除
        if assistant.owner_id != user_id:
            raise PermissionError("只有所有者可以删除助手")

        try:
            assistant.is_active = False
            assistant.updated_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Deleted assistant: {assistant_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete assistant: {str(e)}")
            return False

    # ==================== 知识库管理 ====================

    async def add_knowledge_base(self, assistant_id: int, knowledge_base_id: int, user_id: int) -> bool:
        """关联知识库到助手"""
        # 验证助手
        assistant = await self.get_assistant_by_id(assistant_id)
        if not assistant:
            raise NotFoundError("助手不存在")

        if assistant.owner_id != user_id:
            raise PermissionError("只有所有者可以管理助手知识库")

        # 验证知识库
        knowledge_base = self.db.query(KnowledgeBase).filter(
            KnowledgeBase.id == knowledge_base_id
        ).first()

        if not knowledge_base:
            raise NotFoundError("知识库不存在")

        # 验证用户是否有权限使用该知识库
        if not knowledge_base.is_public and knowledge_base.owner_id != user_id:
            raise PermissionError("无权使用该知识库")

        # 检查是否已关联
        existing = self.db.query(AssistantKnowledgeBase).filter(
            AssistantKnowledgeBase.assistant_id == assistant_id,
            AssistantKnowledgeBase.knowledge_base_id == knowledge_base_id
        ).first()

        if existing:
            return True  # 已存在，直接返回成功

        try:
            # 创建关联
            link = AssistantKnowledgeBase(
                assistant_id=assistant_id,
                knowledge_base_id=knowledge_base_id
            )
            self.db.add(link)
            self.db.commit()

            logger.info(f"Linked knowledge base {knowledge_base_id} to assistant {assistant_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to link knowledge base: {str(e)}")
            raise ValidationError(f"关联知识库失败: {str(e)}")

    async def remove_knowledge_base(self, assistant_id: int, knowledge_base_id: int, user_id: int) -> bool:
        """解除助手与知识库的关联"""
        # 验证助手
        assistant = await self.get_assistant_by_id(assistant_id)
        if not assistant:
            raise NotFoundError("助手不存在")

        if assistant.owner_id != user_id:
            raise PermissionError("只有所有者可以管理助手知识库")

        # 查找关联
        link = self.db.query(AssistantKnowledgeBase).filter(
            AssistantKnowledgeBase.assistant_id == assistant_id,
            AssistantKnowledgeBase.knowledge_base_id == knowledge_base_id
        ).first()

        if not link:
            raise NotFoundError("未找到关联关系")

        try:
            self.db.delete(link)
            self.db.commit()

            logger.info(f"Unlinked knowledge base {knowledge_base_id} from assistant {assistant_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to unlink knowledge base: {str(e)}")
            return False

    async def get_assistant_knowledge_bases(self, assistant_id: int) -> List[KnowledgeBase]:
        """获取助手关联的知识库列表"""
        links = self.db.query(AssistantKnowledgeBase).filter(
            AssistantKnowledgeBase.assistant_id == assistant_id
        ).all()

        kb_ids = [link.knowledge_base_id for link in links]

        if not kb_ids:
            return []

        knowledge_bases = self.db.query(KnowledgeBase).filter(
            KnowledgeBase.id.in_(kb_ids)
        ).all()

        return knowledge_bases

    async def clear_knowledge_bases(self, assistant_id: int, user_id: int) -> bool:
        """清除助手的所有知识库关联"""
        # 验证助手
        assistant = await self.get_assistant_by_id(assistant_id)
        if not assistant:
            raise NotFoundError("助手不存在")

        if assistant.owner_id != user_id:
            raise PermissionError("只有所有者可以管理助手知识库")

        try:
            self.db.query(AssistantKnowledgeBase).filter(
                AssistantKnowledgeBase.assistant_id == assistant_id
            ).delete()
            self.db.commit()

            logger.info(f"Cleared all knowledge bases for assistant {assistant_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to clear knowledge bases: {str(e)}")
            return False

    # ==================== 对话管理 ====================

    async def create_conversation(self, data: ConversationCreate, user_id: int) -> Conversation:
        """创建对话"""
        # 验证助手存在并有权限
        assistant = await self.get_assistant_by_id(data.assistant_id, user_id)
        if not assistant:
            raise NotFoundError("助手不存在")

        try:
            conversation = Conversation(
                assistant_id=data.assistant_id,
                user_id=user_id,
                title=data.title or f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                metadata=data.metadata or {}
            )
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)

            logger.info(f"Created conversation: {conversation.id}")
            return conversation

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create conversation: {str(e)}")
            raise ValidationError(f"创建对话失败: {str(e)}")

    async def get_conversation(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        """获取对话详情"""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()

        return conversation

    async def get_user_conversations(
            self,
            user_id: int,
            assistant_id: Optional[int] = None,
            skip: int = 0,
            limit: int = 100
    ) -> Tuple[List[Conversation], int]:
        """获取用户对话列表"""
        query = self.db.query(Conversation).filter(
            Conversation.user_id == user_id
        )

        if assistant_id:
            query = query.filter(Conversation.assistant_id == assistant_id)

        total = query.count()
        conversations = query.order_by(
            Conversation.updated_at.desc()
        ).offset(skip).limit(limit).all()

        return conversations, total

    # ==================== 统计信息 ====================

    async def get_assistant_statistics(self, assistant_id: int) -> Dict[str, Any]:
        """获取助手统计信息"""
        # 使用次数
        usage_count = self.db.query(Conversation).filter(
            Conversation.assistant_id == assistant_id
        ).count()

        # 消息总数
        message_count = self.db.query(Message).join(Conversation).filter(
            Conversation.assistant_id == assistant_id
        ).count()

        # 用户数
        unique_users = self.db.query(Conversation.user_id).filter(
            Conversation.assistant_id == assistant_id
        ).distinct().count()

        return {
            "usage_count": usage_count,
            "message_count": message_count,
            "unique_users": unique_users,
            "last_used": None  # TODO: 从对话中获取最后使用时间
        }

    async def get_category_statistics(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取分类统计信息"""
        # 基础查询
        query = self.db.query(Assistant).filter(Assistant.is_active == True)

        if user_id:
            query = query.filter(
                or_(
                    Assistant.owner_id == user_id,
                    Assistant.is_public == True
                )
            )

        assistants = query.all()

        # 统计分类
        categories = {}
        for assistant in assistants:
            category = assistant.category or "未分类"

            if category not in categories:
                categories[category] = {
                    "name": category,
                    "count": 0,
                    "public_count": 0,
                    "private_count": 0,
                    "models": set(),
                    "capabilities": set()
                }

            categories[category]["count"] += 1

            if assistant.is_public:
                categories[category]["public_count"] += 1
            else:
                categories[category]["private_count"] += 1

            categories[category]["models"].add(assistant.model)

            if assistant.capabilities:
                for cap in assistant.capabilities:
                    categories[category]["capabilities"].add(cap)

        # 转换集合为列表
        result = []
        for category_data in categories.values():
            category_data["models"] = list(category_data["models"])
            category_data["capabilities"] = list(category_data["capabilities"])
            result.append(category_data)

        return result