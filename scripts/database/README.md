# Database Scripts

此目录包含database相关脚本相关的脚本文件。

## 脚本列表

| 脚本名称 | 类型 | 功能描述 |
|---------|------|----------|
| add_enhanced_fields_to_existing_tables.py | Python | - |
| execute_enhanced_db_upgrade.py | Python | - |
| execute_remote_db_upgrade.py | Python | - |
| final_database_check.py | Python | - |
| fix_database_issues.py | Python | - |
| run_complete_db_test.py | Python | - |
| run_db_upgrade_manager.sh | Shell | - |
| run_enhanced_db_test.sh | Shell | - |
| run_enhanced_db_upgrade.sh | Shell | - |
| run_remote_db_upgrade.sh | Shell | - |
| test_remote_postgres.py | Python | - |
| test_remote_postgres_fixed.py | Python | - |
| vector_db_config_migration.py | Python | - |
| verify_knowledge_service_migration.py | Python | - |
| verify_migration.py | Python | - |

## 使用说明

请根据具体脚本的功能和要求来使用。大部分Python脚本可以通过以下方式运行：

```bash
python3 database/script_name.py
```

Shell脚本可以通过以下方式运行：

```bash
chmod +x database/script_name.sh
./database/script_name.sh
```

## 注意事项

- 运行前请确保满足脚本的依赖要求
- 部分脚本可能需要特定的环境变量或配置文件
- 建议在测试环境中先验证脚本功能

