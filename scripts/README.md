
# Scripts Directory

## 📁 目录说明

此目录包含项目的配置管理和环境管理脚本。

## 🔧 核心脚本

### env_manager.py
环境管理主脚本，提供以下功能：
- 环境切换和验证
- 配置文件管理
- 启动脚本生成
- 配置备份和恢复

使用方法：
```bash
# 列出所有环境
python scripts/env_manager.py list

# 切换环境
python scripts/env_manager.py switch development

# 验证环境配置
python scripts/env_manager.py validate

# 查看配置摘要
python scripts/env_manager.py summary

# 创建启动脚本
python scripts/env_manager.py create-script development

# 备份当前配置
python scripts/env_manager.py backup

# 查看状态
python scripts/env_manager.py status
```

### test_config_loading.py
配置加载测试脚本，验证配置系统功能：
- 多环境配置加载测试
- 最小配置测试
- 配置继承机制测试
- 配置验证测试
- 配置导出测试

使用方法：
```bash
python scripts/test_config_loading.py
```

## 🎯 可选脚本

### config_system_demo.py
配置系统演示脚本，展示配置管理功能的使用示例。

### advanced_config_demo.py  
高级配置演示脚本，展示高级配置管理功能。

### verify_knowledge_service_migration.py
服务迁移验证脚本，用于特定的服务迁移验证任务。

## 📖 使用指南

1. **环境管理**：使用 `env_manager.py` 进行环境切换和配置管理
2. **配置测试**：使用 `test_config_loading.py` 验证配置系统
3. **功能演示**：使用demo脚本了解配置系统功能

## 🔗 相关文档

- [配置系统使用指南](../docs/CONFIG_USAGE_GUIDE.md)
- [最小配置使用指南](../docs/MINIMAL_CONFIG_GUIDE.md)
- [启动流程改进总结](../docs/STARTUP_IMPROVEMENTS.md)

---

*最后更新: 2024-12-02*

# 项目脚本索引

本文档提供了项目中所有脚本的完整索引和使用指南。

## 目录结构

```
scripts/
├── database/       # 数据库相关脚本
├── testing/        # 测试验证脚本  
├── config/         # 配置管理脚本
├── storage/        # 存储系统脚本
├── deployment/     # 部署运行脚本
├── maintenance/    # 维护修复脚本
├── monitoring/     # 监控检查脚本
└── misc/          # 其他未分类脚本
```

## 快速导航


### Config (11 个脚本)

系统配置和环境管理脚本

- [`advanced_config_demo.py`](./config/advanced_config_demo.py)
- [`config_system_demo.py`](./config/config_system_demo.py)
- [`env_manager.py`](./config/env_manager.py)
- [`final_config_check.py`](./config/final_config_check.py)
- [`init_elasticsearch.py`](./config/init_elasticsearch.py)
- [`init_minio.py`](./config/init_minio.py)
- [`quick_config_check.py`](./config/quick_config_check.py)
- [`setup_permissions.py`](./config/setup_permissions.py)
- [`simple_config_check.py`](./config/simple_config_check.py)
- [`storage_config.py`](./config/storage_config.py)
- [`test_config_loading.py`](./config/test_config_loading.py)

### Database (15 个脚本)

数据库操作、迁移、升级相关脚本

- [`add_enhanced_fields_to_existing_tables.py`](./database/add_enhanced_fields_to_existing_tables.py)
- [`execute_enhanced_db_upgrade.py`](./database/execute_enhanced_db_upgrade.py)
- [`execute_remote_db_upgrade.py`](./database/execute_remote_db_upgrade.py)
- [`final_database_check.py`](./database/final_database_check.py)
- [`fix_database_issues.py`](./database/fix_database_issues.py)
- [`run_complete_db_test.py`](./database/run_complete_db_test.py)
- [`run_db_upgrade_manager.sh`](./database/run_db_upgrade_manager.sh)
- [`run_enhanced_db_test.sh`](./database/run_enhanced_db_test.sh)
- [`run_enhanced_db_upgrade.sh`](./database/run_enhanced_db_upgrade.sh)
- [`run_remote_db_upgrade.sh`](./database/run_remote_db_upgrade.sh)
- [`test_remote_postgres.py`](./database/test_remote_postgres.py)
- [`test_remote_postgres_fixed.py`](./database/test_remote_postgres_fixed.py)
- [`vector_db_config_migration.py`](./database/vector_db_config_migration.py)
- [`verify_knowledge_service_migration.py`](./database/verify_knowledge_service_migration.py)
- [`verify_migration.py`](./database/verify_migration.py)

### Deployment (5 个脚本)

服务启动和部署脚本

- [`start_celery.sh`](./deployment/start_celery.sh)
- [`start_development.sh`](./deployment/start_development.sh)
- [`start_minimal.sh`](./deployment/start_minimal.sh)
- [`start_with_hybrid_search.sh`](./deployment/start_with_hybrid_search.sh)
- [`validate_hybrid_search.py`](./deployment/validate_hybrid_search.py)

### Maintenance (6 个脚本)

系统维护和修复脚本

- [`cleanup_scripts.py`](./maintenance/cleanup_scripts.py)
- [`fix_all_uuid_defaults.py`](./maintenance/fix_all_uuid_defaults.py)
- [`fix_remote_demo_data.py`](./maintenance/fix_remote_demo_data.py)
- [`fix_triggers.py`](./maintenance/fix_triggers.py)
- [`fix_uuid_issue.py`](./maintenance/fix_uuid_issue.py)
- [`recreate_missing_tables.py`](./maintenance/recreate_missing_tables.py)

### Misc (4 个脚本)

其他功能脚本

- [`document_manager.py`](./misc/document_manager.py)
- [`enhanced_document_manager.py`](./misc/enhanced_document_manager.py)
- [`knowledge_document_integration.py`](./misc/knowledge_document_integration.py)
- [`main.py`](./misc/main.py)

### Monitoring (2 个脚本)

系统监控和状态检查脚本

- [`check_db_progress.py`](./monitoring/check_db_progress.py)
- [`check_remote_table_structure.py`](./monitoring/check_remote_table_structure.py)

### Storage (5 个脚本)

存储系统(MinIO、ES、向量数据库)相关脚本

- [`init_core_storage.py`](./storage/init_core_storage.py)
- [`storage_interface.py`](./storage/storage_interface.py)
- [`test_core_storage_requirements.py`](./storage/test_core_storage_requirements.py)
- [`test_storage.py`](./storage/test_storage.py)
- [`validate_storage_system.py`](./storage/validate_storage_system.py)

### Testing (13 个脚本)

各种测试验证脚本

- [`postgres_enhanced_test.py`](./testing/postgres_enhanced_test.py)
- [`run_complete_system_test.sh`](./testing/run_complete_system_test.sh)
- [`simple_connection_test.py`](./testing/simple_connection_test.py)
- [`simple_enhanced_test.py`](./testing/simple_enhanced_test.py)
- [`test_adapters.py`](./testing/test_adapters.py)
- [`test_backend_file_api.py`](./testing/test_backend_file_api.py)
- [`test_core_refactoring.py`](./testing/test_core_refactoring.py)
- [`test_module_refactoring.py`](./testing/test_module_refactoring.py)
- [`test_refactoring_core.py`](./testing/test_refactoring_core.py)
- [`test_text_core_direct.py`](./testing/test_text_core_direct.py)
- [`test_text_module_integration.py`](./testing/test_text_module_integration.py)
- [`test_text_module_refinement.py`](./testing/test_text_module_refinement.py)
- [`test_text_module_simple.py`](./testing/test_text_module_simple.py)


## 使用建议

1. **首次使用**: 从 `config/` 目录的配置脚本开始
2. **系统测试**: 使用 `testing/` 目录的各种测试脚本
3. **数据库操作**: 参考 `database/` 目录的相关脚本
4. **生产部署**: 使用 `deployment/` 目录的启动脚本
5. **日常维护**: 参考 `maintenance/` 和 `monitoring/` 目录

## 注意事项

- 所有脚本都经过重新整理，请更新你的引用路径
- 运行前请仔细阅读各脚本的文档和注释
- 建议在测试环境中先验证功能再用于生产环境

---

*此索引由 `organize_scripts.py` 自动生成*

