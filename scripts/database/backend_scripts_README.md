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


