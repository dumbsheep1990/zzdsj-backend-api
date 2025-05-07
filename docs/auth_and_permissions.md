# 用户认证与权限系统设计文档

## 一、系统概述

本文档详细描述了系统的用户认证与权限控制架构，包括基础认证机制、基于角色的权限控制以及细粒度的资源访问管理。该系统旨在提供安全、灵活且易于扩展的用户权限管理解决方案。

## 二、数据模型设计

### 1. 核心用户模型

#### 用户(User)

```python
class User(Base):
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    disabled = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    avatar_url = Column(String(255))
    # 时间戳
    last_login = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

#### 角色(Role)

```python
class Role(Base):
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
```

#### 权限(Permission)

```python
class Permission(Base):
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), unique=True, nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
```

#### 用户设置(UserSettings)

```python
class UserSettings(Base):
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), unique=True)
    language = Column(String(10), default="zh-CN")
    theme = Column(String(20), default="light")
    notification_enabled = Column(Boolean, default=True)
    timezone = Column(String(50), default="Asia/Shanghai")
```

#### API密钥(ApiKey)

```python
class ApiKey(Base):
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), index=True)
    name = Column(String(100), nullable=False)
    key = Column(String(64), unique=True, nullable=False, index=True)
    scopes = Column(ARRAY(String), default=[])
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    last_used_at = Column(DateTime, nullable=True)
```

### 2. 资源权限模型

#### 资源权限(ResourcePermission)

```python
class ResourcePermission(Base):
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), index=True)
    resource_type = Column(Enum(ResourceType), nullable=False)
    resource_id = Column(String(36), nullable=False)
    access_level = Column(Enum(AccessLevel), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

#### 知识库访问权限(KnowledgeBaseAccess)

```python
class KnowledgeBaseAccess(Base):
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), index=True)
    knowledge_base_id = Column(String(36), ForeignKey("knowledge_bases.id"), index=True)
    can_read = Column(Boolean, default=True)
    can_write = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_share = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
```

#### 助手访问权限(AssistantAccess)

```python
class AssistantAccess(Base):
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), index=True)
    assistant_id = Column(String(36), ForeignKey("assistants.id"), index=True)
    can_use = Column(Boolean, default=True)
    can_modify = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_share = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
```

#### 模型配置访问权限(ModelConfigAccess)

```python
class ModelConfigAccess(Base):
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), index=True)
    model_config_id = Column(String(36), ForeignKey("model_configs.id"), index=True)
    can_use = Column(Boolean, default=True)
    can_modify = Column(Boolean, default=False)
    can_share = Column(Boolean, default=False)
    usage_quota = Column(Integer, nullable=True) # 调用配额
    priority_level = Column(Integer, default=0) # 优先级
```

#### MCP配置访问权限(MCPConfigAccess)

```python
class MCPConfigAccess(Base):
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), index=True)
    mcp_config_id = Column(String(36), ForeignKey("mcp_configs.id"), index=True)
    can_use = Column(Boolean, default=True)
    can_modify = Column(Boolean, default=False)
    can_share = Column(Boolean, default=False)
```

#### 用户资源配额(UserResourceQuota)

```python
class UserResourceQuota(Base):
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, index=True)
    max_knowledge_bases = Column(Integer, default=5) # 最大知识库数量
    max_assistants = Column(Integer, default=5) # 最大助手数量
    max_storage_mb = Column(Integer, default=100) # 最大存储空间(MB)
    max_tokens_per_month = Column(Integer, default=100000) # 每月最大令牌数
    max_model_calls_per_day = Column(Integer, default=1000) # 每日最大模型调用次数
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

## 三、认证系统

### 1. 认证方式

系统支持两种认证方式：

1. **用户名/密码认证**：标准的用户凭证登录
2. **API密钥认证**：用于第三方集成和自动化操作

### 2. JWT令牌管理

- **访问令牌(Access Token)**：短期有效(默认30分钟)
- **刷新令牌(Refresh Token)**：长期有效(默认7天)，用于获取新的访问令牌

### 3. 认证流程

```
+--------+                               +--------+
|        |                               |        |
|        |----(1) 认证请求-------------->|        |
|        |      (用户名/密码或API密钥)    |        |
|        |                               |        |
|        |<---(2) 访问令牌&刷新令牌------|        |
|  客户端 |                               |  服务器 |
|        |                               |        |
|        |----(3) 请求资源(访问令牌)----->|        |
|        |                               |        |
|        |<---(4) 受保护资源-------------|        |
|        |                               |        |
|        |----(5) 刷新令牌请求---------->|        |
|        |                               |        |
|        |<---(6) 新的访问令牌&刷新令牌---|        |
+--------+                               +--------+
```

## 四、权限控制系统

### 1. 多层次权限架构

系统采用三层权限控制架构：

1. **系统级权限**：通过角色和权限定义，控制用户对系统功能的访问
2. **资源级权限**：通过资源权限定义，控制用户对特定资源的访问
3. **操作级权限**：控制用户对资源的特定操作(读/写/删除等)

### 2. 角色与权限关系

- **预定义角色**：
  - 超级管理员(Super Admin)：拥有全部权限
  - 管理员(Admin)：拥有除用户管理外的大部分权限
  - 用户(User)：基础用户角色

- **权限分配方式**：
  - 通过角色继承权限
  - 直接分配权限到用户

### 3. 资源访问控制

对于每种资源类型(知识库、助手、模型配置等)，系统提供细粒度的访问控制：

- **访问级别**：
  - 只读(Read)
  - 读写(Write)
  - 管理(Admin)
  - 拥有者(Owner)

- **操作权限**：
  - 使用(Use)
  - 修改(Modify)
  - 删除(Delete)
  - 分享(Share)

### 4. 资源配额管理

系统为不同级别的用户提供资源使用限制：

- **知识库数量**：用户可创建的最大知识库数
- **助手数量**：用户可创建的最大助手数
- **存储空间**：用户可使用的最大存储空间
- **令牌配额**：用户每月可使用的最大令牌数
- **API调用次数**：用户每日可进行的最大模型调用次数

## 五、API接口

### 1. 认证接口

#### 用户注册

```
POST /api/v1/auth/register
```

**请求体**:
```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "full_name": "string"
}
```

#### 用户登录

```
POST /api/v1/auth/login
```

**请求体**:
```json
{
  "username": "string",
  "password": "string"
}
```

**响应**:
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "string",
    "username": "string",
    "email": "string",
    "full_name": "string",
    "roles": ["string"],
    "avatar_url": "string"
  }
}
```

#### 令牌刷新

```
POST /api/v1/auth/refresh
```

**请求体**:
```json
{
  "refresh_token": "string"
}
```

### 2. 用户管理接口

#### 获取用户列表

```
GET /api/v1/users
```

#### 创建用户

```
POST /api/v1/users
```

#### 获取用户详情

```
GET /api/v1/users/{user_id}
```

#### 更新用户

```
PUT /api/v1/users/{user_id}
```

#### 删除用户

```
DELETE /api/v1/users/{user_id}
```

### 3. 角色管理接口

#### 获取角色列表

```
GET /api/v1/roles
```

#### 创建角色

```
POST /api/v1/roles
```

#### 获取角色详情

```
GET /api/v1/roles/{role_id}
```

#### 更新角色

```
PUT /api/v1/roles/{role_id}
```

#### 删除角色

```
DELETE /api/v1/roles/{role_id}
```

### 4. 权限管理接口

#### 获取权限列表

```
GET /api/v1/permissions
```

#### 为用户分配权限

```
POST /api/v1/users/{user_id}/permissions
```

**请求体**:
```json
{
  "permission_ids": ["string"]
}
```

### 5. 资源权限接口

#### 获取资源权限列表

```
GET /api/v1/resource-permissions
```

#### 创建资源权限

```
POST /api/v1/resource-permissions
```

**请求体**:
```json
{
  "user_id": "string",
  "resource_type": "string",
  "resource_id": "string",
  "access_level": "string"
}
```

#### 获取知识库访问权限

```
GET /api/v1/knowledge-bases/{knowledge_base_id}/access
```

#### 设置知识库访问权限

```
POST /api/v1/knowledge-bases/{knowledge_base_id}/access
```

**请求体**:
```json
{
  "user_id": "string",
  "can_read": true,
  "can_write": false,
  "can_delete": false,
  "can_share": false,
  "is_admin": false
}
```

#### 获取助手访问权限

```
GET /api/v1/assistants/{assistant_id}/access
```

#### 设置助手访问权限

```
POST /api/v1/assistants/{assistant_id}/access
```

### 6. 资源配额接口

#### 获取用户资源配额

```
GET /api/v1/users/{user_id}/quotas
```

#### 设置用户资源配额

```
POST /api/v1/users/{user_id}/quotas
```

**请求体**:
```json
{
  "max_knowledge_bases": 10,
  "max_assistants": 10,
  "max_storage_mb": 500,
  "max_tokens_per_month": 500000,
  "max_model_calls_per_day": 5000
}
```

## 六、安全性考虑

### 1. 密码处理

- 使用bcrypt算法进行密码哈希
- 实施密码强度策略(最小长度、复杂度要求)
- 密码从不以明文形式存储或传输

### 2. 令牌安全

- 访问令牌设置较短有效期(30分钟)
- 令牌加密和签名使用强密钥
- 实施令牌撤销机制

### 3. API安全

- 限制API调用速率防止滥用
- 针对敏感操作实施双重验证
- 详细记录权限变更操作

### 4. 数据保护

- 敏感数据传输使用TLS/SSL加密
- 实施最小权限原则
- 定期审计权限设置

## 七、实现注意事项

### 1. 依赖注入

使用FastAPI的Depends机制实现权限检查：

```python
def require_permission(permission_code: str):
    def dependency(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
        user = get_current_user(token, db)
        if not has_permission(user, permission_code):
            raise HTTPException(status_code=403, detail="权限不足")
        return user
    return dependency

# 使用示例
@router.get("/protected-resource")
def protected_endpoint(user: User = Depends(require_permission("resource:read"))):
    return {"message": "你有权访问此资源"}
```

### 2. 资源权限检查

```python
def check_resource_access(resource_type: ResourceType, resource_id: str, user_id: str, 
                         required_level: AccessLevel, db: Session):
    # 超级管理员直接授权
    user = db.query(User).filter(User.id == user_id).one_or_none()
    if user and user.is_superuser:
        return True
    
    # 检查资源权限
    permission = db.query(ResourcePermission).filter(
        ResourcePermission.user_id == user_id,
        ResourcePermission.resource_type == resource_type,
        ResourcePermission.resource_id == resource_id
    ).one_or_none()
    
    if permission and permission.access_level >= required_level:
        return True
    
    # 检查特定资源类型的访问权限
    if resource_type == ResourceType.KNOWLEDGE_BASE:
        access = db.query(KnowledgeBaseAccess).filter(
            KnowledgeBaseAccess.user_id == user_id,
            KnowledgeBaseAccess.knowledge_base_id == resource_id
        ).one_or_none()
        
        if access:
            # 根据所需权限级别检查
            if required_level == AccessLevel.READ and access.can_read:
                return True
            if required_level == AccessLevel.WRITE and access.can_write:
                return True
            if required_level == AccessLevel.ADMIN and access.is_admin:
                return True
    
    # 类似地处理其他资源类型
    
    return False
```

### 3. 资源配额使用检查

```python
def check_quota_available(user_id: str, quota_type: str, amount: int, db: Session) -> bool:
    quota = db.query(UserResourceQuota).filter(UserResourceQuota.user_id == user_id).one_or_none()
    if not quota:
        return False
    
    if quota_type == "knowledge_bases":
        # 统计用户已有知识库数量
        current_count = db.query(KnowledgeBase).filter(KnowledgeBase.owner_id == user_id).count()
        return current_count + amount <= quota.max_knowledge_bases
    
    elif quota_type == "storage":
        # 检查存储空间
        current_usage_mb = get_user_storage_usage(user_id, db)
        return current_usage_mb + amount <= quota.max_storage_mb
    
    # 其他配额类型处理...
    
    return False
```

## 八、数据库初始化

系统启动时自动创建默认角色、权限和超级管理员账户：

```python
def seed_initial_data(db: Session):
    # 创建默认角色
    _create_default_roles(db)
    
    # 创建默认权限
    _create_default_permissions(db)
    
    # 创建超级管理员账户
    _create_admin_account(db)
    
    # 设置默认资源配额
    _seed_default_resource_quotas(db)
    
def _seed_default_resource_quotas(db: Session):
    """为不同角色的用户设置默认资源配额"""
    
    # 获取所有角色
    super_admin_role = db.query(Role).filter(Role.name == "Super Admin").first()
    admin_role = db.query(Role).filter(Role.name == "Admin").first()
    user_role = db.query(Role).filter(Role.name == "User").first()
    
    # 获取拥有这些角色的所有用户
    if super_admin_role:
        super_admin_users = db.query(User).join(
            user_role_table, User.id == user_role_table.c.user_id
        ).filter(user_role_table.c.role_id == super_admin_role.id).all()
        
        # 为超级管理员设置配额
        for user in super_admin_users:
            # 检查是否已存在配额
            existing_quota = db.query(UserResourceQuota).filter(
                UserResourceQuota.user_id == user.id
            ).first()
            
            if not existing_quota:
                quota = UserResourceQuota(
                    user_id=user.id,
                    max_knowledge_bases=100,
                    max_assistants=100,
                    max_storage_mb=10240,  # 10GB
                    max_tokens_per_month=10000000,  # 1千万tokens
                    max_model_calls_per_day=100000
                )
                db.add(quota)
    
    # 为管理员和普通用户设置类似的配额...
    
    db.commit()
```

## 九、前端集成

### 1. 认证组件

- **登录表单**：用户名/密码登录界面
- **注册表单**：新用户注册界面
- **令牌管理**：前端存储和刷新令牌的机制

### 2. 权限UI组件

- **用户管理界面**：管理用户、角色和权限的管理界面
- **资源共享对话框**：用于设置资源共享权限的UI组件
- **配额显示**：显示用户资源使用情况和限制的UI组件

### 3. 权限验证指令

Angular/Vue指令示例，用于根据用户权限显示或隐藏UI元素：

```html
<!-- Vue示例 -->
<button v-permission="'knowledge:create'">创建知识库</button>

<!-- Angular示例 -->
<button *appHasPermission="'knowledge:create'">创建知识库</button>

<!-- React示例 -->
<PermissionGuard permission="knowledge:create">
  <button>创建知识库</button>
</PermissionGuard>
```

## 十、测试策略

### 1. 单元测试

- 权限检查函数的测试
- 令牌生成和验证的测试
- 资源配额检查函数的测试

### 2. 集成测试

- API端点的认证测试
- 资源访问权限的测试
- 角色和权限分配的测试

### 3. 安全测试

- 密码策略合规性测试
- 权限边界测试
- 令牌过期和刷新机制测试

## 十一、扩展计划

### 1. 短期扩展

- 实现OAuth2.0/OpenID Connect集成
- 添加双因素认证(2FA)功能
- 实现更细粒度的活动日志记录

### 2. 中期扩展

- 添加LDAP/Active Directory集成
- 实现单点登录(SSO)功能
- 添加基于组织和团队的权限模型

### 3. 长期扩展

- 实现基于属性的访问控制(ABAC)
- 添加行级安全策略
- 实现自定义权限工作流

## 十二、结论

本文档描述了一个全面的用户认证与权限管理系统，提供了灵活且安全的用户访问控制解决方案。通过结合基于角色的权限控制和细粒度的资源访问管理，系统能够满足复杂的权限需求，同时保持良好的可扩展性和易用性。
