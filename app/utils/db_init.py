"""
数据库初始化模块：提供初始化和迁移数据库模式的工具
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Any, Optional
import alembic.config
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 将父目录添加到路径以便导入
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)

# 导入模型以确保它们注册到Base.metadata
from app.models.database import Base
from app.models.knowledge import KnowledgeBase, Document, DocumentChunk
from app.models.assistant import Assistant, Conversation, Message, assistant_knowledge_base
from app.models.chat import ChatSession, ChatMessage
from app.config import settings

def get_db_url() -> str:
    """从设置中获取数据库URL"""
    return f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

def init_database(drop_existing: bool = False):
    """
    初始化数据库模式
    
    参数:
        drop_existing: 如果为True，在创建新表前删除现有表
    """
    try:
        # 创建数据库引擎
        engine = create_engine(get_db_url())
        
        # 如果请求则删除所有表
        if drop_existing:
            logger.info("正在删除所有现有表...")
            Base.metadata.drop_all(engine)
            logger.info("所有表删除成功")
        
        # 创建所有表
        logger.info("正在创建数据库表...")
        Base.metadata.create_all(engine)
        logger.info("数据库表创建成功")
        
        # 创建会话用于初始数据
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # 检查是否应该创建初始数据
        if settings.CREATE_INITIAL_DATA:
            create_initial_data(session)
        
        session.close()
        
        return True
    
    except Exception as e:
        logger.error(f"初始化数据库时出错: {str(e)}")
        return False

def check_database_connection():
    """
    检查数据库连接是否正常
    
    返回:
        如果连接成功则为True，否则为False
    """
    try:
        # 创建引擎
        engine = create_engine(get_db_url())
        
        # 尝试连接
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            
            if row and row[0] == 1:
                logger.info("数据库连接成功")
                return True
            else:
                logger.error("数据库连接失败")
                return False
    
    except Exception as e:
        logger.error(f"连接数据库时出错: {str(e)}")
        return False

def create_initial_data(session):
    """
    在数据库中创建初始数据
    
    参数:
        session: SQLAlchemy会话
    """
    logger.info("正在创建初始数据...")
    
    try:
        # 检查默认知识库是否已存在
        kb_exists = session.query(KnowledgeBase).filter_by(name="通用知识").first()
        
        if not kb_exists:
            # 创建默认知识库
            kb = KnowledgeBase(
                name="通用知识",
                description="用于常见问题的通用知识库",
                status="active"
            )
            session.add(kb)
            session.commit()
            logger.info(f"创建了默认知识库: {kb.name}")
        
        # 检查默认助手是否存在
        assistant_exists = session.query(Assistant).filter_by(name="通用助手").first()
        
        if not assistant_exists:
            # 创建默认助手
            assistant = Assistant(
                name="通用助手",
                description="用于回答问题的通用助手",
                model="gpt-4",
                capabilities=["text", "retrieval"],
                system_prompt="你是一个基于知识库回答问题的有用助手。"
            )
            
            # 链接到默认知识库
            kb = session.query(KnowledgeBase).filter_by(name="通用知识").first()
            if kb:
                assistant.knowledge_bases = [kb]
            
            session.add(assistant)
            session.commit()
            logger.info(f"创建了默认助手: {assistant.name}")
        
        logger.info("初始数据创建成功")
    
    except Exception as e:
        logger.error(f"创建初始数据时出错: {str(e)}")
        session.rollback()

def print_schema_info():
    """
    打印数据库模式的信息
    """
    # 获取所有模型
    models = [
        KnowledgeBase,
        Document,
        DocumentChunk,
        Assistant,
        Conversation,
        Message,
        ChatSession,
        ChatMessage
    ]
    
    print("\n=== 数据库模式信息 ===\n")
    
    for model in models:
        print(f"表: {model.__tablename__}")
        print("列:")
        for column in model.__table__.columns:
            print(f"  - {column.name}: {column.type} {'主键' if column.primary_key else ''} {'可空' if column.nullable else '非空'}")
        print("关系:")
        for relationship in model.__mapper__.relationships:
            print(f"  - {relationship.key}: {relationship.target}")
        print("\n" + "-" * 40 + "\n")
    
    print("关联表:")
    print(f"  - {assistant_knowledge_base.name}")
    for column in assistant_knowledge_base.columns:
        print(f"    - {column.name}: {column.type} {'主键' if column.primary_key else ''}")
    print("\n" + "=" * 40 + "\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库初始化工具")
    parser.add_argument("--check", action="store_true", help="检查数据库连接")
    parser.add_argument("--init", action="store_true", help="初始化数据库模式")
    parser.add_argument("--drop", action="store_true", help="在初始化前删除现有表")
    parser.add_argument("--info", action="store_true", help="打印模式信息")
    
    args = parser.parse_args()
    
    if args.check:
        check_database_connection()
    
    if args.init:
        init_database(drop_existing=args.drop)
    
    if args.info:
        print_schema_info()
