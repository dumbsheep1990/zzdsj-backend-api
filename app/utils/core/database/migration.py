"""
数据库迁移模块
处理数据库表创建、初始化和数据填充
"""

import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from .connection import get_db_connection, Base
from .session_manager import get_session_manager

logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """数据库迁移器"""
    
    def __init__(self):
        self.db_connection = get_db_connection()
        self.session_manager = get_session_manager()
    
    def init_db(self, create_tables: bool = True, seed_data: bool = True) -> bool:
        """
        初始化数据库
        
        Args:
            create_tables: 是否创建表
            seed_data: 是否填充初始数据
            
        Returns:
            初始化是否成功
        """
        try:
            # 导入所有模型以确保表定义被加载
            self._import_all_models()
            
            if create_tables:
                logger.info("正在创建数据库表...")
                self._create_tables()
                logger.info("数据库表创建完成")
            
            if seed_data:
                logger.info("正在填充初始数据...")
                self._seed_initial_data()
                logger.info("初始数据填充完成")
                
            return True
        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            return False
    
    def _import_all_models(self):
        """导入所有模型"""
        try:
            # 导入所有模型
            from app.models import assistants, knowledge, chat, model_provider, assistant_qa, mcp
            from app.models import user
            from app.models import resource_permission
            logger.info("所有模型导入完成")
        except Exception as e:
            logger.error(f"模型导入失败: {str(e)}")
            raise
    
    def _create_tables(self):
        """创建所有表"""
        try:
            engine = self.db_connection.get_engine()
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            logger.error(f"创建表失败: {str(e)}")
            raise
    
    def _seed_initial_data(self):
        """填充初始数据"""
        try:
            # 使用会话管理器执行种子数据填充
            self.session_manager.execute_with_session(self._seed_model_providers)
            self.session_manager.execute_with_session(self._seed_roles_and_permissions)
            self.session_manager.execute_with_session(self._seed_admin_user)
            self.session_manager.execute_with_session(self._seed_default_resource_quotas)
        except Exception as e:
            logger.error(f"初始数据填充失败: {str(e)}")
            raise
    
    def _seed_model_providers(self, db: Session):
        """填充模型提供商初始数据"""
        from app.models.model_provider import ModelProvider
        
        # 检查默认的模型提供商是否已存在
        existing_provider = db.query(ModelProvider).filter_by(name="OpenAI").first()
        if existing_provider is None:
            # 创建默认模型提供商
            logger.info("创建默认模型提供商: OpenAI")
            default_provider = ModelProvider(
                name="OpenAI",
                provider_type="openai",
                api_base="https://api.openai.com/v1",
                is_default=True,
                is_active=True,
                models=["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
            )
            db.add(default_provider)
            
            # 添加其他模型提供商
            logger.info("创建模型提供商: Azure OpenAI")
            azure_provider = ModelProvider(
                name="Azure OpenAI",
                provider_type="azure",
                api_base="https://your-resource-name.openai.azure.com",
                is_default=False,
                is_active=False,
                models=["gpt-35-turbo", "gpt-4"]
            )
            db.add(azure_provider)
    
    def _seed_roles_and_permissions(self, db: Session):
        """填充角色和权限初始数据"""
        from app.models.user import Role, Permission
        
        # 创建基本权限
        permissions = {
            # 用户权限
            "user:read": {"name": "查看用户", "description": "查看用户信息", "resource": "user"},
            "user:create": {"name": "创建用户", "description": "创建新用户", "resource": "user"},
            "user:update": {"name": "更新用户", "description": "更新用户信息", "resource": "user"},
            "user:delete": {"name": "删除用户", "description": "删除用户", "resource": "user"},
            
            # 角色权限
            "role:read": {"name": "查看角色", "description": "查看角色信息", "resource": "role"},
            "role:create": {"name": "创建角色", "description": "创建新角色", "resource": "role"},
            "role:update": {"name": "更新角色", "description": "更新角色信息", "resource": "role"},
            "role:delete": {"name": "删除角色", "description": "删除角色", "resource": "role"},
            
            # 权限管理
            "permission:read": {"name": "查看权限", "description": "查看权限列表", "resource": "permission"},
        }
        
        # 创建权限
        for code, perm_data in permissions.items():
            existing_perm = db.query(Permission).filter_by(code=code).first()
            if not existing_perm:
                permission = Permission(
                    code=code,
                    name=perm_data["name"],
                    description=perm_data["description"],
                    resource=perm_data["resource"]
                )
                db.add(permission)
        
        # 创建默认角色
        admin_role = db.query(Role).filter_by(name="admin").first()
        if not admin_role:
            admin_role = Role(
                name="admin",
                display_name="管理员",
                description="系统管理员角色"
            )
            db.add(admin_role)
            db.flush()  # 获取ID
            
            # 为管理员角色分配所有权限
            all_permissions = db.query(Permission).all()
            admin_role.permissions = all_permissions
    
    def _seed_admin_user(self, db: Session):
        """创建管理员用户"""
        from app.models.user import User, Role
        from app.utils.auth import get_password_hash
        
        # 检查管理员用户是否已存在
        admin_user = db.query(User).filter_by(username="admin").first()
        if not admin_user:
            admin_role = db.query(Role).filter_by(name="admin").first()
            admin_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                is_superuser=True,
                is_active=True
            )
            if admin_role:
                admin_user.roles = [admin_role]
            db.add(admin_user)
            logger.info("创建默认管理员用户: admin")
    
    def _seed_default_resource_quotas(self, db: Session):
        """创建默认资源配额"""
        from app.models.resource_permission import ResourceQuota
        
        # 检查默认配额是否已存在
        existing_quota = db.query(ResourceQuota).filter_by(quota_type="default").first()
        if not existing_quota:
            default_quota = ResourceQuota(
                quota_type="default",
                max_conversations=100,
                max_knowledge_bases=10,
                max_assistants=5,
                max_storage_mb=1000
            )
            db.add(default_quota)
            logger.info("创建默认资源配额")
    
    def check_migration_status(self) -> Dict[str, Any]:
        """检查迁移状态"""
        try:
            # 检查数据库连接
            connection_ok = self.db_connection.check_connection()
            
            # 检查表是否存在
            engine = self.db_connection.get_engine()
            tables_exist = len(Base.metadata.tables) > 0
            
            # 检查基础数据是否存在
            session = self.db_connection.create_session()
            try:
                from app.models.user import User
                user_count = session.query(User).count()
                has_users = user_count > 0
            except:
                has_users = False
            finally:
                session.close()
            
            return {
                "connection_ok": connection_ok,
                "tables_exist": tables_exist,
                "has_users": has_users,
                "status": "ok" if all([connection_ok, tables_exist]) else "needs_migration"
            }
        except Exception as e:
            logger.error(f"检查迁移状态失败: {str(e)}")
            return {
                "connection_ok": False,
                "tables_exist": False,
                "has_users": False,
                "status": "error",
                "error": str(e)
            }


# 全局迁移器实例
_migrator = None


def get_migrator() -> DatabaseMigrator:
    """获取全局数据库迁移器实例"""
    global _migrator
    if _migrator is None:
        _migrator = DatabaseMigrator()
    return _migrator 