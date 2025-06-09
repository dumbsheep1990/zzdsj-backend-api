"""
用户模型（简化版）
"""
from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from .assistants.base import BaseModel


class User(BaseModel):
    """用户模型"""
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # 关系
    assistants = relationship("Assistant", back_populates="owner")
    conversations = relationship("Conversation", back_populates="user")