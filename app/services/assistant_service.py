"""
助手服务模块
提供助手相关的业务逻辑和数据访问封装
"""

from app.utils.service_decorators import register_service

from typing import List, Dict, Any, Optional, Union
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime

from app.models.assistant import Assistant, Conversation, Message
from app.models.knowledge import KnowledgeBase
from app.schemas.assistant import (
    AssistantCreate,
    AssistantUpdate,
    ConversationCreate,
    MessageCreate
)

@register_service(service_type="assistant", priority="high", description="AI助手管理服务")
class AssistantService:
    """
    助手服务类，提供对Assistant模型的业务逻辑和数据访问操作
    """
    
    def __init__(self, db: Session):
        """
        初始化助手服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    async def get_assistants(
        self, 
        skip: int = 0, 
        limit: int = 100,
        capabilities: Optional[List[str]] = None
    ) -> List[Assistant]:
        """
        获取助手列表，支持按能力过滤
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            capabilities: 过滤的能力列表
            
        Returns:
            List[Assistant]: 助手列表
        """
        query = self.db.query(Assistant)
        
        # 如果指定了能力，按能力过滤
        if capabilities:
            for capability in capabilities:
                query = query.filter(Assistant.capabilities.contains([capability]))
        
        assistants = query.offset(skip).limit(limit).all()
        return assistants
    
    async def get_assistant_by_id(self, assistant_id: int) -> Optional[Assistant]:
        """
        通过ID获取助手详情
        
        Args:
            assistant_id: 助手ID
            
        Returns:
            Optional[Assistant]: 助手详情或None
        """
        assistant = self.db.query(Assistant).filter(Assistant.id == assistant_id).first()
        return assistant
    
    async def create_assistant(self, assistant_data: AssistantCreate) -> Assistant:
        """
        创建新助手
        
        Args:
            assistant_data: 助手创建数据
            
        Returns:
            Assistant: 创建的助手对象
            
        Raises:
            HTTPException: 如果创建过程中出错
        """
        # 创建助手记录
        db_assistant = Assistant(
            name=assistant_data.name,
            description=assistant_data.description,
            model=assistant_data.model,
            capabilities=assistant_data.capabilities,
            configuration=assistant_data.configuration,
            system_prompt=assistant_data.system_prompt
        )
        
        # 如果指定了知识库，添加知识库关系
        if assistant_data.knowledge_base_ids:
            knowledge_bases = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.id.in_(assistant_data.knowledge_base_ids)
            ).all()
            
            if len(knowledge_bases) != len(assistant_data.knowledge_base_ids):
                raise HTTPException(status_code=400, detail="一个或多个知识库未找到")
            
            db_assistant.knowledge_bases = knowledge_bases
        
        # 添加到数据库
        try:
            self.db.add(db_assistant)
            self.db.commit()
            self.db.refresh(db_assistant)
            
            # 为助手生成访问URL
            from app.config import settings
            access_url = f"{settings.BASE_URL}/assistants/web/{db_assistant.id}"
            db_assistant.access_url = access_url
            self.db.commit()
            
            return db_assistant
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建助手失败: {str(e)}"
            )
    
    async def update_assistant(self, assistant_id: int, assistant_update: AssistantUpdate) -> Assistant:
        """
        更新助手信息
        
        Args:
            assistant_id: 助手ID
            assistant_update: 助手更新数据
            
        Returns:
            Assistant: 更新后的助手对象
            
        Raises:
            HTTPException: 如果助手不存在或更新失败
        """
        db_assistant = await self.get_assistant_by_id(assistant_id)
        if not db_assistant:
            raise HTTPException(status_code=404, detail="助手未找到")
        
        # 更新基本字段
        update_data = assistant_update.dict(exclude_unset=True)
        
        # 单独处理知识库关系
        if "knowledge_base_ids" in update_data:
            kb_ids = update_data.pop("knowledge_base_ids")
            if kb_ids:
                knowledge_bases = self.db.query(KnowledgeBase).filter(
                    KnowledgeBase.id.in_(kb_ids)
                ).all()
                
                if len(knowledge_bases) != len(kb_ids):
                    raise HTTPException(status_code=400, detail="一个或多个知识库未找到")
                
                db_assistant.knowledge_bases = knowledge_bases
        
        # 更新剩余字段
        for field, value in update_data.items():
            setattr(db_assistant, field, value)
        
        try:
            self.db.commit()
            self.db.refresh(db_assistant)
            return db_assistant
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新助手失败: {str(e)}"
            )
    
    async def delete_assistant(self, assistant_id: int) -> bool:
        """
        删除助手
        
        Args:
            assistant_id: 助手ID
            
        Returns:
            bool: 是否删除成功
            
        Raises:
            HTTPException: 如果助手不存在
        """
        db_assistant = await self.get_assistant_by_id(assistant_id)
        if not db_assistant:
            raise HTTPException(status_code=404, detail="助手未找到")
        
        try:
            # 首先删除关联的对话和消息
            conversations = self.db.query(Conversation).filter(
                Conversation.assistant_id == assistant_id
            ).all()
            
            for conversation in conversations:
                # 删除对话中的所有消息
                self.db.query(Message).filter(
                    Message.conversation_id == conversation.id
                ).delete()
            
            # 删除所有对话
            self.db.query(Conversation).filter(
                Conversation.assistant_id == assistant_id
            ).delete()
            
            # 删除助手
            self.db.delete(db_assistant)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除助手失败: {str(e)}"
            )
    
    # 助手会话相关方法
    async def get_conversations(
        self,
        assistant_id: Optional[int] = None,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Conversation]:
        """
        获取会话列表，支持按助手ID和用户ID过滤
        
        Args:
            assistant_id: 可选的助手ID过滤
            user_id: 可选的用户ID过滤
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[Conversation]: 会话列表
        """
        query = self.db.query(Conversation)
        
        if assistant_id:
            query = query.filter(Conversation.assistant_id == assistant_id)
        
        if user_id:
            query = query.filter(Conversation.user_id == user_id)
        
        return query.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit).all()
    
    async def get_conversation_by_id(self, conversation_id: int) -> Optional[Conversation]:
        """
        通过ID获取会话详情
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            Optional[Conversation]: 会话详情或None
        """
        return self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
    
    async def create_conversation(self, conversation_data: ConversationCreate) -> Conversation:
        """
        创建新会话
        
        Args:
            conversation_data: 会话创建数据
            
        Returns:
            Conversation: 创建的会话对象
            
        Raises:
            HTTPException: 如果助手不存在或创建失败
        """
        # 检查助手是否存在
        assistant = await self.get_assistant_by_id(conversation_data.assistant_id)
        if not assistant:
            raise HTTPException(status_code=404, detail="未找到助手")
        
        db_conversation = Conversation(
            assistant_id=conversation_data.assistant_id,
            user_id=conversation_data.user_id,
            title=conversation_data.title,
            metadata=conversation_data.metadata
        )
        
        try:
            self.db.add(db_conversation)
            self.db.commit()
            self.db.refresh(db_conversation)
            return db_conversation
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建会话失败: {str(e)}"
            )
    
    async def update_conversation(self, conversation_id: int, update_data: Dict[str, Any]) -> Conversation:
        """
        更新会话信息
        
        Args:
            conversation_id: 会话ID
            update_data: 更新的字段数据
            
        Returns:
            Conversation: 更新后的会话对象
            
        Raises:
            HTTPException: 如果会话不存在或更新失败
        """
        conversation = await self.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="未找到会话")
        
        # 更新提供的字段
        for field, value in update_data.items():
            setattr(conversation, field, value)
        
        try:
            self.db.commit()
            self.db.refresh(conversation)
            return conversation
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新会话失败: {str(e)}"
            )
    
    async def delete_conversation(self, conversation_id: int) -> bool:
        """
        删除会话
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            bool: 是否删除成功
            
        Raises:
            HTTPException: 如果会话不存在或删除失败
        """
        conversation = await self.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="未找到会话")
        
        try:
            # 首先删除所有消息
            self.db.query(Message).filter(Message.conversation_id == conversation_id).delete()
            
            # 删除会话
            self.db.delete(conversation)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除会话失败: {str(e)}"
            )
    
    # 消息相关方法
    async def create_message(self, message_data: MessageCreate) -> Message:
        """
        创建新消息
        
        Args:
            message_data: 消息创建数据
            
        Returns:
            Message: 创建的消息对象
            
        Raises:
            HTTPException: 如果会话不存在或创建失败
        """
        # 检查会话是否存在
        conversation = await self.get_conversation_by_id(message_data.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="未找到会话")
        
        db_message = Message(
            conversation_id=message_data.conversation_id,
            role=message_data.role,
            content=message_data.content,
            metadata=message_data.metadata
        )
        
        try:
            self.db.add(db_message)
            
            # 更新会话的更新时间
            conversation.updated_at = datetime.now()
            
            self.db.commit()
            self.db.refresh(db_message)
            return db_message
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建消息失败: {str(e)}"
            )
