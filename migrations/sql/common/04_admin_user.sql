-- 管理员用户初始化脚本 (通用)
-- 创建系统管理员用户

-- 系统管理员用户 (密码哈希对应密码: Admin@123)
INSERT INTO users (
    id, 
    username, 
    email, 
    full_name, 
    hashed_password, 
    is_active, 
    is_superuser, 
    created_at, 
    updated_at
)
VALUES (
    'admin-00000000-0000-0000-0000-000000000000', 
    'admin', 
    'admin@zzdsj.com', 
    '系统管理员', 
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 
    true, 
    true, 
    CURRENT_TIMESTAMP, 
    CURRENT_TIMESTAMP
);

-- 添加系统管理员角色到管理员用户
INSERT INTO user_roles (user_id, role_id)
VALUES ('admin-00000000-0000-0000-0000-000000000000', '1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p');
