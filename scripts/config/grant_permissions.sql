-- =====================================================
-- PostgreSQL用户权限授予脚本
-- 为 zzdsj 用户授予必要的数据库和schema权限
-- =====================================================

-- 连接到 zzdsj 数据库后，使用具有管理员权限的用户执行以下命令

-- 1. 授予数据库级别权限
GRANT CREATE ON DATABASE zzdsj TO zzdsj;
GRANT CONNECT ON DATABASE zzdsj TO zzdsj;
GRANT TEMPORARY ON DATABASE zzdsj TO zzdsj;

-- 2. 授予 public schema 权限
GRANT CREATE ON SCHEMA public TO zzdsj;
GRANT USAGE ON SCHEMA public TO zzdsj;

-- 3. 授予序列权限（用于SERIAL类型）
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO zzdsj;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO zzdsj;

-- 4. 授予表权限
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO zzdsj;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO zzdsj;

-- 5. 授予函数和过程权限
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO zzdsj;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO zzdsj;

-- 6. 如果需要，可以将用户设为数据库拥有者（可选，谨慎使用）
-- ALTER DATABASE zzdsj OWNER TO zzdsj;

-- 验证权限
\echo '检查权限授予结果:'

-- 检查数据库权限
SELECT 
    datname,
    has_database_privilege('zzdsj', datname, 'CREATE') as can_create,
    has_database_privilege('zzdsj', datname, 'CONNECT') as can_connect
FROM pg_database 
WHERE datname = 'zzdsj';

-- 检查schema权限
SELECT 
    has_schema_privilege('zzdsj', 'public', 'CREATE') as can_create_in_public,
    has_schema_privilege('zzdsj', 'public', 'USAGE') as can_use_public;

\echo '权限授予完成！' 