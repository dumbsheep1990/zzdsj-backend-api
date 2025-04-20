"""
Database Setup Script: Create database schema and initial data
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('db_setup.log')
    ]
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

from app.utils.db_init import init_database, check_database_connection, print_schema_info
from app.utils.swagger_helper import save_db_schema_doc

def setup_database(drop_existing=False, create_initial_data=True):
    """
    Set up the database schema and initial data
    
    Args:
        drop_existing: If True, drop existing tables before creating new ones
        create_initial_data: If True, create initial data after schema creation
    """
    # Check database connection
    logger.info("Checking database connection...")
    if not check_database_connection():
        logger.error("Database connection failed. Please check your database settings.")
        return False
    
    # Initialize database
    logger.info("Initializing database schema...")
    success = init_database(drop_existing=drop_existing)
    
    if success:
        logger.info("Database schema created successfully")
        
        # Generate schema documentation
        logger.info("Generating database schema documentation...")
        schema_path = save_db_schema_doc()
        logger.info(f"Schema documentation saved to {schema_path}")
        
        return True
    else:
        logger.error("Failed to initialize database schema")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up the database for Knowledge Base QA System")
    parser.add_argument("--drop", action="store_true", help="Drop existing tables before creating new ones")
    parser.add_argument("--no-initial-data", action="store_true", help="Skip creating initial data")
    parser.add_argument("--schema-info", action="store_true", help="Print schema information")
    
    args = parser.parse_args()
    
    if args.schema_info:
        print_schema_info()
    else:
        setup_database(
            drop_existing=args.drop, 
            create_initial_data=not args.no_initial_data
        )
