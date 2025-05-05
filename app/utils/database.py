"""
数据库连接工具模块: 提供SQL连接和会话管理
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import logging
from app.config import settings

# 配置日志
logger = logging.getLogger(__name__)

# 创建SQLAlchemy引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=settings.DB_POOL_SIZE if hasattr(settings, 'DB_POOL_SIZE') else 10,
    max_overflow=settings.DB_MAX_OVERFLOW if hasattr(settings, 'DB_MAX_OVERFLOW') else 20
)

# 创建SessionLocal类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建Base类
Base = declarative_base()

# 获取数据库会话
def get_db():
    """用于FastAPI依赖注入的数据库会话生成器"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class DBSessionManager:
    """数据库会话管理器，提供异步上下文管理"""
    
    @asynccontextmanager
    async def session(self):
        """异步上下文管理器获取会话"""
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"数据库操作失败: {str(e)}")
            raise
        finally:
            db.close()
    
    def execute_with_session(self, operation, *args, **kwargs):
        """执行需要数据库会话的操作"""
        db = SessionLocal()
        try:
            result = operation(db, *args, **kwargs)
            db.commit()
            return result
        except Exception as e:
            db.rollback()
            logger.error(f"数据库操作失败: {str(e)}")
            raise
        finally:
            db.close()
            
    def get_connection_pool_stats(self):
        """获取连接池统计信息"""
        return {
            "pool_size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "checkedin": engine.pool.checkedin(),
        }
    
    def adjust_pool_size(self, pool_size=None, max_overflow=None):
        """调整连接池大小"""
        if pool_size is not None:
            engine.pool._pool.maxsize = pool_size
            logger.info(f"已调整连接池大小为: {pool_size}")
        
        if max_overflow is not None:
            engine.pool._pool.overflow = max_overflow
            logger.info(f"已调整最大溢出为: {max_overflow}")

# 创建会话管理器单例
db_manager = DBSessionManager()

# 异步获取会话
async def get_db_session():
    """异步获取数据库会话"""
    return db_manager.session()

# 检查数据库连接
def check_connection():
    """检查数据库连接是否正常"""
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            if result.scalar() == 1:
                logger.info("数据库连接正常")
                return True
        logger.error("数据库连接失败")
        return False
    except Exception as e:
        logger.error(f"数据库连接出错: {str(e)}")
        return False

# 数据库初始化和填充
def init_db(create_tables=True, seed_data=True):
    """
    初始化数据库
    
    Args:
        create_tables (bool): 是否创建表
        seed_data (bool): 是否填充初始数据
    """
    # 导入所有模型
    from app.models import assistants, knowledge, chat, model_provider, assistant_qa, mcp
    # 导入用户模型
    from app.models import user
    # 导入资源权限模型
    from app.models import resource_permission
    
    if create_tables:
        # 创建表
        logger.info("正在创建数据库表...")
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建完成")
    
    if seed_data:
        logger.info("正在填充初始数据...")
        seed_initial_data()
        logger.info("初始数据填充完成")

def seed_initial_data():
    """填充初始数据"""
    # 使用会话管理器执行
    db_manager.execute_with_session(_seed_model_providers)
    db_manager.execute_with_session(_seed_roles_and_permissions)
    db_manager.execute_with_session(_seed_admin_user)
    db_manager.execute_with_session(_seed_default_resource_quotas)
    # 可以添加更多的种子数据填充函数

def _seed_model_providers(db):
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

def _seed_roles_and_permissions(db):
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
        
        # 助手管理
        "assistant:read": {"name": "查看助手", "description": "查看助手信息", "resource": "assistant"},
        "assistant:create": {"name": "创建助手", "description": "创建新助手", "resource": "assistant"},
        "assistant:update": {"name": "更新助手", "description": "更新助手信息", "resource": "assistant"},
        "assistant:delete": {"name": "删除助手", "description": "删除助手", "resource": "assistant"},
        
        # 知识库管理
        "knowledge:read": {"name": "查看知识库", "description": "查看知识库信息", "resource": "knowledge"},
        "knowledge:create": {"name": "创建知识库", "description": "创建新知识库", "resource": "knowledge"},
        "knowledge:update": {"name": "更新知识库", "description": "更新知识库信息", "resource": "knowledge"},
        "knowledge:delete": {"name": "删除知识库", "description": "删除知识库", "resource": "knowledge"},
        
        # 对话管理
        "chat:read": {"name": "查看对话", "description": "查看对话记录", "resource": "chat"},
        "chat:create": {"name": "创建对话", "description": "创建新对话", "resource": "chat"},
        "chat:delete": {"name": "删除对话", "description": "删除对话", "resource": "chat"},
        
        # 模型管理
        "model:read": {"name": "查看模型", "description": "查看模型信息", "resource": "model"},
        "model:create": {"name": "创建模型", "description": "创建新模型", "resource": "model"},
        "model:update": {"name": "更新模型", "description": "更新模型信息", "resource": "model"},
        "model:delete": {"name": "删除模型", "description": "删除模型", "resource": "model"},
    }
    
    # 创建默认权限
    db_permissions = {}
    for code, details in permissions.items():
        permission = db.query(Permission).filter_by(code=code).first()
        if not permission:
            logger.info(f"创建权限: {details['name']}")
            permission = Permission(
                name=details["name"],
                code=code,
                description=details["description"],
                resource=details["resource"]
            )
            db.add(permission)
            db.flush()  # 刷新以获取ID
        db_permissions[code] = permission
    
    # 创建角色
    # 1. 超级管理员角色
    admin_role = db.query(Role).filter_by(name="超级管理员").first()
    if not admin_role:
        logger.info("创建角色: 超级管理员")
        admin_role = Role(
            name="超级管理员",
            description="系统超级管理员，拥有所有权限",
            is_default=False
        )
        # 为超级管理员分配所有权限
        for permission in db_permissions.values():
            admin_role.permissions.append(permission)
        db.add(admin_role)
    
    # 2. 普通用户角色
    user_role = db.query(Role).filter_by(name="普通用户").first()
    if not user_role:
        logger.info("创建角色: 普通用户")
        user_role = Role(
            name="普通用户",
            description="普通用户，拥有基本功能使用权限",
            is_default=True
        )
        # 为普通用户分配基本权限
        basic_permissions = [
            "assistant:read", "knowledge:read", "chat:read", "chat:create", 
            "model:read"
        ]
        for code in basic_permissions:
            if code in db_permissions:
                user_role.permissions.append(db_permissions[code])
        db.add(user_role)
    
    # 3. 管理员角色
    manager_role = db.query(Role).filter_by(name="管理员").first()
    if not manager_role:
        logger.info("创建角色: 管理员")
        manager_role = Role(
            name="管理员",
            description="系统管理员，拥有大部分管理权限",
            is_default=False
        )
        # 为管理员分配管理权限
        manager_permissions = [
            "user:read", "role:read", "permission:read", 
            "assistant:read", "assistant:create", "assistant:update", 
            "knowledge:read", "knowledge:create", "knowledge:update", 
            "chat:read", "chat:create", "chat:delete", 
            "model:read", "model:create", "model:update"
        ]
        for code in manager_permissions:
            if code in db_permissions:
                manager_role.permissions.append(db_permissions[code])
        db.add(manager_role)

def _seed_admin_user(db):
    """创建初始管理员用户"""
    from app.models.user import User, Role
    from app.utils.auth import get_password_hash
    
    # 检查是否已存在超级管理员
    admin_user = db.query(User).filter_by(username="admin").first()
    if not admin_user:
        # 获取超级管理员角色
        admin_role = db.query(Role).filter_by(name="超级管理员").first()
        if not admin_role:
            logger.error("未找到超级管理员角色，无法创建管理员用户")
            return
        
        # 创建超级管理员用户
        logger.info("创建初始超级管理员用户: admin")
        hashed_password = get_password_hash("Admin@123456")  # 初始密码
        admin_user = User(
            username="admin",
            email="admin@example.com",
            hashed_password=hashed_password,
            full_name="System Administrator",
            is_superuser=True
        )
        admin_user.roles.append(admin_role)
        db.add(admin_user)
        
        # 创建用户设置
        from app.models.user import UserSettings
        db.add(UserSettings(user_id=admin_user.id))
        logger.info("初始超级管理员用户创建成功")

def _seed_default_resource_quotas(db):
    """创建默认的用户资源配额设置"""
    from app.models.resource_permission import UserResourceQuota
    from app.models.user import User
    
    # 为每个已有用户创建默认资源配额（如果不存在）
    users = db.query(User).all()
    for user in users:
        # 检查用户是否已有资源配额设置
        existing_quota = db.query(UserResourceQuota).filter_by(user_id=user.id).first()
        if not existing_quota:
            logger.info(f"为用户 {user.username} 创建默认资源配额")
            
            # 根据用户角色设置不同配额
            if user.is_superuser:
                # 超级管理员无限制
                quota = UserResourceQuota(
                    user_id=user.id,
                    max_knowledge_bases=100,
                    max_knowledge_base_size_mb=10240,  # 10GB
                    max_assistants=50,
                    daily_model_tokens=1000000,  # 100万tokens
                    monthly_model_tokens=30000000,  # 3000万tokens
                    max_mcp_calls_per_day=10000,
                    max_storage_mb=102400,  # 100GB
                    rate_limit_per_minute=500
                )
            else:
                # 检查是否为管理员角色
                is_manager = False
                for role in user.roles:
                    if role.name == "管理员":
                        is_manager = True
                        break
                
                if is_manager:
                    # 管理员配额
                    quota = UserResourceQuota(
                        user_id=user.id,
                        max_knowledge_bases=20,
                        max_knowledge_base_size_mb=5120,  # 5GB
                        max_assistants=15,
                        daily_model_tokens=100000,  # 10万tokens
                        monthly_model_tokens=3000000,  # 300万tokens
                        max_mcp_calls_per_day=1000,
                        max_storage_mb=20480,  # 20GB
                        rate_limit_per_minute=200
                    )
                else:
                    # 普通用户配额
                    quota = UserResourceQuota(
                        user_id=user.id,
                        max_knowledge_bases=5,
                        max_knowledge_base_size_mb=1024,  # 1GB
                        max_assistants=3,
                        daily_model_tokens=10000,  # 1万tokens
                        monthly_model_tokens=300000,  # 30万tokens
                        max_mcp_calls_per_day=100,
                        max_storage_mb=2048,  # 2GB
                        rate_limit_per_minute=60
                    )
            
            db.add(quota)
