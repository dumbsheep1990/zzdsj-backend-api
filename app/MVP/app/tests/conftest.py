"""
测试配置和fixtures
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient
from app.main import app
from app.config.database import Base, get_async_db
from app.models.user import User
from app.utils.security import get_password_hash

# 测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)
TestingAsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="function")
async def db():
    """异步测试数据库会话"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with TestingAsyncSessionLocal() as session:
        yield session
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def client(db):
    """异步测试客户端"""
    async def override_get_async_db():
        yield db

    app.dependency_overrides[get_async_db] = override_get_async_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    del app.dependency_overrides[get_async_db]


@pytest_asyncio.fixture
async def test_user(db):
    """创建测试用户"""
    user = User(
        email="test@example.com",
        username="testuser", 
        hashed_password=get_password_hash("testpassword"),
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """认证头"""
    from app.utils.security import create_access_token
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}