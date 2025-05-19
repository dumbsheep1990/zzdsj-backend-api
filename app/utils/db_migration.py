"""
数据库迁移与初始化工具
提供基于不同数据库类型的迁移脚本生成和数据库初始化功能
"""

import os
import sys
import logging
import importlib
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.utils.db_config import (
    detect_database_type, 
    DatabaseType, 
    get_connection_params,
    is_postgres, 
    is_mysql, 
    is_sqlite
)
from app.config import settings

logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Alembic配置文件路径
ALEMBIC_CONFIG_PATH = PROJECT_ROOT / "alembic.ini"

def get_alembic_config() -> Config:
    """
    获取Alembic配置
    
    返回:
        Alembic配置对象
    """
    alembic_cfg = Config(str(ALEMBIC_CONFIG_PATH))
    
    # 设置迁移脚本位置
    alembic_cfg.set_main_option("script_location", "migrations")
    
    # 从应用配置获取数据库URL
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    
    return alembic_cfg

def create_migration(message: str) -> str:
    """
    创建新的数据库迁移脚本
    
    参数:
        message: 迁移说明
        
    返回:
        创建的迁移脚本路径
    """
    try:
        alembic_cfg = get_alembic_config()
        
        # 自动生成迁移脚本
        revision = command.revision(
            alembic_cfg,
            message=message,
            autogenerate=True
        )
        
        return f"成功创建迁移脚本: {revision}"
    except Exception as e:
        logger.error(f"创建迁移脚本失败: {str(e)}")
        return f"创建迁移脚本失败: {str(e)}"

def apply_migrations() -> str:
    """
    应用所有未应用的迁移脚本
    
    返回:
        操作结果描述
    """
    try:
        alembic_cfg = get_alembic_config()
        
        # 升级到最新版本
        command.upgrade(alembic_cfg, "head")
        
        return "成功应用所有迁移"
    except Exception as e:
        logger.error(f"应用迁移失败: {str(e)}")
        return f"应用迁移失败: {str(e)}"

def downgrade_migrations(target: str = "-1") -> str:
    """
    回滚迁移
    
    参数:
        target: 目标版本（默认回滚一个版本）
        
    返回:
        操作结果描述
    """
    try:
        alembic_cfg = get_alembic_config()
        
        # 执行回滚
        command.downgrade(alembic_cfg, target)
        
        return f"成功回滚到版本: {target}"
    except Exception as e:
        logger.error(f"回滚迁移失败: {str(e)}")
        return f"回滚迁移失败: {str(e)}"

def list_migrations() -> List[Dict[str, Any]]:
    """
    列出所有迁移版本
    
    返回:
        迁移版本列表
    """
    try:
        from alembic.script import ScriptDirectory
        
        alembic_cfg = get_alembic_config()
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        
        # 获取所有版本
        revisions = []
        for sc in script_dir.walk_revisions():
            revisions.append({
                "revision": sc.revision,
                "down_revision": sc.down_revision,
                "message": sc.doc,
                "created_date": sc.created_date.isoformat() if sc.created_date else None
            })
        
        return revisions
    except Exception as e:
        logger.error(f"获取迁移列表失败: {str(e)}")
        return []

def get_db_engine():
    """
    获取数据库引擎
    
    返回:
        SQLAlchemy引擎实例
    """
    return create_engine(settings.DATABASE_URL)

def get_db_session():
    """
    获取数据库会话
    
    返回:
        SQLAlchemy会话实例
    """
    engine = get_db_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def get_db_type_specific_script(script_name: str) -> Optional[str]:
    """
    获取针对当前数据库类型的SQL脚本内容
    
    参数:
        script_name: 脚本名称
        
    返回:
        SQL脚本内容或None
    """
    db_type = detect_database_type()
    
    # 构建脚本路径
    script_dir = PROJECT_ROOT / "migrations" / "sql" / db_type
    script_path = script_dir / f"{script_name}.sql"
    
    # 检查脚本是否存在
    if not script_path.exists():
        # 尝试获取通用脚本
        script_path = PROJECT_ROOT / "migrations" / "sql" / "common" / f"{script_name}.sql"
        if not script_path.exists():
            return None
    
    # 读取脚本内容
    with open(script_path, "r", encoding="utf-8") as f:
        return f.read()

def execute_sql_script(script: str, session: Optional[Session] = None) -> bool:
    """
    执行SQL脚本
    
    参数:
        script: SQL脚本内容
        session: 可选的数据库会话，如果未提供将创建新会话
        
    返回:
        是否执行成功
    """
    close_session = False
    
    try:
        # 如果未提供会话，创建新会话
        if session is None:
            session = get_db_session()
            close_session = True
        
        # 拆分SQL脚本为单独的语句
        statements = []
        current_statement = []
        
        # 处理PostgreSQL特定语法和MySQL语法的兼容性
        for line in script.splitlines():
            # 忽略注释和空行
            line = line.strip()
            if not line or line.startswith("--"):
                continue
            
            # 收集语句
            current_statement.append(line)
            
            # 语句结束判断
            if line.endswith(";"):
                statements.append(" ".join(current_statement))
                current_statement = []
        
        # 处理最后一个未结束的语句
        if current_statement:
            statements.append(" ".join(current_statement))
        
        # 执行所有语句
        for stmt in statements:
            # 跳过空语句
            if not stmt.strip():
                continue
                
            # 处理数据库特定语法
            if is_postgres():
                # PostgreSQL特定转换
                pass
            elif is_mysql():
                # MySQL特定转换
                pass
            
            # 执行语句
            session.execute(text(stmt))
        
        # 提交事务
        session.commit()
        return True
    
    except Exception as e:
        logger.error(f"执行SQL脚本失败: {str(e)}")
        
        # 回滚事务
        if session is not None:
            session.rollback()
        
        return False
    
    finally:
        # 关闭会话
        if close_session and session is not None:
            session.close()

def initialize_database() -> bool:
    """
    初始化数据库结构和基础数据
    
    返回:
        是否初始化成功
    """
    try:
        logger.info("开始初始化数据库...")
        
        # 1. 应用所有迁移
        apply_migrations()
        
        # 2. 获取会话
        session = get_db_session()
        
        try:
            # 3. 执行初始化脚本
            # 按顺序执行初始化脚本
            init_scripts = [
                "01_roles_permissions", 
                "02_system_configs",
                "03_model_providers",
                "04_admin_user",
                "05_framework_configs", 
                "06_agent_templates",
                "07_system_tools"
            ]
            
            for script_name in init_scripts:
                sql_script = get_db_type_specific_script(script_name)
                if sql_script:
                    logger.info(f"执行初始化脚本: {script_name}")
                    if not execute_sql_script(sql_script, session):
                        logger.error(f"执行脚本 {script_name} 失败")
                else:
                    logger.warning(f"找不到初始化脚本: {script_name}")
            
            return True
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"初始化数据库失败: {str(e)}")
        return False

def create_framework_integration_migrations() -> str:
    """
    创建框架集成相关的迁移脚本
    
    返回:
        操作结果描述
    """
    return create_migration("add_framework_integration_tables")

def update_agent_tools_schema() -> str:
    """
    更新智能体工具相关表结构
    
    返回:
        操作结果描述
    """
    return create_migration("update_agent_tools_schema")
