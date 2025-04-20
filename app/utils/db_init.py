"""
Database Initialization Module: Provides tools for initializing and migrating the database schema
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Any, Optional
import alembic.config
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)

# Import models to ensure they're registered with Base.metadata
from app.models.database import Base
from app.models.knowledge import KnowledgeBase, Document, DocumentChunk
from app.models.assistant import Assistant, Conversation, Message, assistant_knowledge_base
from app.models.chat import ChatSession, ChatMessage
from app.config import settings

def get_db_url() -> str:
    """Get database URL from settings"""
    return f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

def init_database(drop_existing: bool = False):
    """
    Initialize the database schema
    
    Args:
        drop_existing: If True, drop existing tables before creating new ones
    """
    try:
        # Create database engine
        engine = create_engine(get_db_url())
        
        # Drop all tables if requested
        if drop_existing:
            logger.info("Dropping all existing tables...")
            Base.metadata.drop_all(engine)
            logger.info("All tables dropped successfully")
        
        # Create all tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully")
        
        # Create session for initial data
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check if we should create initial data
        if settings.CREATE_INITIAL_DATA:
            create_initial_data(session)
        
        session.close()
        
        return True
    
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        return False

def check_database_connection():
    """
    Check if the database connection is working
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        # Create engine
        engine = create_engine(get_db_url())
        
        # Attempt to connect
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            
            if row and row[0] == 1:
                logger.info("Database connection successful")
                return True
            else:
                logger.error("Database connection failed")
                return False
    
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        return False

def create_initial_data(session):
    """
    Create initial data in the database
    
    Args:
        session: SQLAlchemy session
    """
    logger.info("Creating initial data...")
    
    try:
        # Check if a default knowledge base already exists
        kb_exists = session.query(KnowledgeBase).filter_by(name="General Knowledge").first()
        
        if not kb_exists:
            # Create a default knowledge base
            kb = KnowledgeBase(
                name="General Knowledge",
                description="General purpose knowledge base for common questions",
                status="active"
            )
            session.add(kb)
            session.commit()
            logger.info(f"Created default knowledge base: {kb.name}")
        
        # Check if a default assistant exists
        assistant_exists = session.query(Assistant).filter_by(name="General Assistant").first()
        
        if not assistant_exists:
            # Create a default assistant
            assistant = Assistant(
                name="General Assistant",
                description="General purpose assistant for answering questions",
                model="gpt-4",
                capabilities=["text", "retrieval"],
                system_prompt="You are a helpful assistant that answers questions based on the knowledge base."
            )
            
            # Link to the default knowledge base
            kb = session.query(KnowledgeBase).filter_by(name="General Knowledge").first()
            if kb:
                assistant.knowledge_bases = [kb]
            
            session.add(assistant)
            session.commit()
            logger.info(f"Created default assistant: {assistant.name}")
        
        logger.info("Initial data created successfully")
    
    except Exception as e:
        logger.error(f"Error creating initial data: {str(e)}")
        session.rollback()

def print_schema_info():
    """
    Print information about the database schema
    """
    # Get all models
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
    
    print("\n=== DATABASE SCHEMA INFORMATION ===\n")
    
    for model in models:
        print(f"Table: {model.__tablename__}")
        print("Columns:")
        for column in model.__table__.columns:
            print(f"  - {column.name}: {column.type} {'PRIMARY KEY' if column.primary_key else ''} {'NULLABLE' if column.nullable else 'NOT NULL'}")
        print("Relationships:")
        for relationship in model.__mapper__.relationships:
            print(f"  - {relationship.key}: {relationship.target}")
        print("\n" + "-" * 40 + "\n")
    
    print("Association Tables:")
    print(f"  - {assistant_knowledge_base.name}")
    for column in assistant_knowledge_base.columns:
        print(f"    - {column.name}: {column.type} {'PRIMARY KEY' if column.primary_key else ''}")
    print("\n" + "=" * 40 + "\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database initialization tools")
    parser.add_argument("--check", action="store_true", help="Check database connection")
    parser.add_argument("--init", action="store_true", help="Initialize database schema")
    parser.add_argument("--drop", action="store_true", help="Drop existing tables before initialization")
    parser.add_argument("--info", action="store_true", help="Print schema information")
    
    args = parser.parse_args()
    
    if args.check:
        check_database_connection()
    
    if args.init:
        init_database(drop_existing=args.drop)
    
    if args.info:
        print_schema_info()
    
    if not (args.check or args.init or args.info):
        parser.print_help()
