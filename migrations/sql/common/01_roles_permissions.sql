-- 角色与权限初始化脚本 (通用)
-- 创建基础角色

-- 系统管理员角色
INSERT INTO roles (id, name, description, is_system, created_at, updated_at)
VALUES ('1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p', '系统管理员', '拥有系统所有权限的超级管理员', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 知识库管理员角色
INSERT INTO roles (id, name, description, is_system, created_at, updated_at)
VALUES ('2b3c4d5e-6f7g-8h9i-0j1k-2l3m4n5o6p7q', '知识库管理员', '管理所有知识库及文档', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 助手管理员角色
INSERT INTO roles (id, name, description, is_system, created_at, updated_at)
VALUES ('3c4d5e6f-7g8h-9i0j-1k2l-3m4n5o6p7q8r', '助手管理员', '管理所有AI助手', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 普通用户角色
INSERT INTO roles (id, name, description, is_system, created_at, updated_at)
VALUES ('4d5e6f7g-8h9i-0j1k-2l3m-4n5o6p7q8r9s', '普通用户', '标准用户权限', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 访客角色
INSERT INTO roles (id, name, description, is_system, created_at, updated_at)
VALUES ('5e6f7g8h-9i0j-1k2l-3m4n-5o6p7q8r9s0t', '访客', '有限的只读权限', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 框架开发者角色
INSERT INTO roles (id, name, description, is_system, created_at, updated_at)
VALUES ('6f7g8h9i-0j1k-2l3m-4n5o-6p7q8r9s0t1u', '框架开发者', '拥有对框架和智能体工具的开发权限', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 创建基础权限

-- 用户管理权限
INSERT INTO permissions (id, name, code, description, category, created_at, updated_at)
VALUES ('a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6', '用户管理', 'user:manage', '创建、编辑和删除用户', 'user', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 角色管理权限
INSERT INTO permissions (id, name, code, description, category, created_at, updated_at)
VALUES ('b2c3d4e5-f6g7-h8i9-j0k1-l2m3n4o5p6q7', '角色管理', 'role:manage', '创建、编辑和删除角色', 'user', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 权限分配权限
INSERT INTO permissions (id, name, code, description, category, created_at, updated_at)
VALUES ('c3d4e5f6-g7h8-i9j0-k1l2-m3n4o5p6q7r8', '权限分配', 'permission:assign', '分配和撤销权限', 'user', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 知识库管理权限
INSERT INTO permissions (id, name, code, description, category, created_at, updated_at)
VALUES ('d4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '知识库管理', 'knowledge:manage', '创建、编辑和删除知识库', 'knowledge', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 文档管理权限
INSERT INTO permissions (id, name, code, description, category, created_at, updated_at)
VALUES ('e5f6g7h8-i9j0-k1l2-m3n4-o5p6q7r8s9t0', '文档管理', 'document:manage', '上传、编辑和删除文档', 'knowledge', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 助手管理权限
INSERT INTO permissions (id, name, code, description, category, created_at, updated_at)
VALUES ('f6g7h8i9-j0k1-l2m3-n4o5-p6q7r8s9t0u1', '助手管理', 'assistant:manage', '创建、编辑和删除助手', 'assistant', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 对话使用权限
INSERT INTO permissions (id, name, code, description, category, created_at, updated_at)
VALUES ('g7h8i9j0-k1l2-m3n4-o5p6-q7r8s9t0u1v2', '对话使用', 'chat:use', '使用对话功能', 'chat', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 系统配置权限
INSERT INTO permissions (id, name, code, description, category, created_at, updated_at)
VALUES ('h8i9j0k1-l2m3-n4o5-p6q7-r8s9t0u1v2w3', '系统配置', 'system:config', '修改系统配置', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 模型提供商管理权限
INSERT INTO permissions (id, name, code, description, category, created_at, updated_at)
VALUES ('i9j0k1l2-m3n4-o5p6-q7r8-s9t0u1v2w3x4', '模型提供商管理', 'model:manage', '管理模型提供商', 'model', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 智能体管理权限
INSERT INTO permissions (id, name, code, description, category, created_at, updated_at)
VALUES ('j0k1l2m3-n4o5-p6q7-r8s9-t0u1v2w3x4y5', '智能体管理', 'agent:manage', '创建和管理智能体', 'agent', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 工具开发权限
INSERT INTO permissions (id, name, code, description, category, created_at, updated_at)
VALUES ('k1l2m3n4-o5p6-q7r8-s9t0-u1v2w3x4y5z6', '工具开发', 'tool:develop', '开发和测试智能体工具', 'agent', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 框架配置权限
INSERT INTO permissions (id, name, code, description, category, created_at, updated_at)
VALUES ('l2m3n4o5-p6q7-r8s9-t0u1-v2w3x4y5z6a7', '框架配置', 'framework:config', '配置和管理AI框架', 'framework', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 角色-权限关系

-- 系统管理员拥有所有权限
INSERT INTO role_permissions (role_id, permission_id)
SELECT '1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p', id FROM permissions;

-- 知识库管理员权限
INSERT INTO role_permissions (role_id, permission_id)
VALUES 
('2b3c4d5e-6f7g-8h9i-0j1k-2l3m4n5o6p7q', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9'),
('2b3c4d5e-6f7g-8h9i-0j1k-2l3m4n5o6p7q', 'e5f6g7h8-i9j0-k1l2-m3n4-o5p6q7r8s9t0'),
('2b3c4d5e-6f7g-8h9i-0j1k-2l3m4n5o6p7q', 'g7h8i9j0-k1l2-m3n4-o5p6-q7r8s9t0u1v2');

-- 助手管理员权限
INSERT INTO role_permissions (role_id, permission_id)
VALUES 
('3c4d5e6f-7g8h-9i0j-1k2l-3m4n5o6p7q8r', 'f6g7h8i9-j0k1-l2m3-n4o5-p6q7r8s9t0u1'),
('3c4d5e6f-7g8h-9i0j-1k2l-3m4n5o6p7q8r', 'g7h8i9j0-k1l2-m3n4-o5p6-q7r8s9t0u1v2'),
('3c4d5e6f-7g8h-9i0j-1k2l-3m4n5o6p7q8r', 'j0k1l2m3-n4o5-p6q7-r8s9-t0u1v2w3x4y5');

-- 普通用户权限
INSERT INTO role_permissions (role_id, permission_id)
VALUES 
('4d5e6f7g-8h9i-0j1k-2l3m-4n5o6p7q8r9s', 'g7h8i9j0-k1l2-m3n4-o5p6-q7r8s9t0u1v2');

-- 框架开发者权限
INSERT INTO role_permissions (role_id, permission_id)
VALUES 
('6f7g8h9i-0j1k-2l3m-4n5o-6p7q8r9s0t1u', 'k1l2m3n4-o5p6-q7r8-s9t0-u1v2w3x4y5z6'),
('6f7g8h9i-0j1k-2l3m-4n5o-6p7q8r9s0t1u', 'l2m3n4o5-p6q7-r8s9-t0u1-v2w3x4y5z6a7'),
('6f7g8h9i-0j1k-2l3m-4n5o-6p7q8r9s0t1u', 'g7h8i9j0-k1l2-m3n4-o5p6-q7r8s9t0u1v2'),
('6f7g8h9i-0j1k-2l3m-4n5o-6p7q8r9s0t1u', 'j0k1l2m3-n4o5-p6q7-r8s9-t0u1v2w3x4y5');
