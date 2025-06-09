# Testing Scripts

此目录包含testing相关脚本相关的脚本文件。

## 脚本列表

| 脚本名称 | 类型 | 功能描述 |
|---------|------|----------|
| postgres_enhanced_test.py | Python | - |
| run_complete_system_test.sh | Shell | - |
| simple_connection_test.py | Python | - |
| simple_enhanced_test.py | Python | - |
| test_adapters.py | Python | - |
| test_backend_file_api.py | Python | - |
| test_core_refactoring.py | Python | - |
| test_module_refactoring.py | Python | - |
| test_refactoring_core.py | Python | - |
| test_text_core_direct.py | Python | - |
| test_text_module_integration.py | Python | - |
| test_text_module_refinement.py | Python | - |
| test_text_module_simple.py | Python | - |

## 使用说明

请根据具体脚本的功能和要求来使用。大部分Python脚本可以通过以下方式运行：

```bash
python3 testing/script_name.py
```

Shell脚本可以通过以下方式运行：

```bash
chmod +x testing/script_name.sh
./testing/script_name.sh
```

## 注意事项

- 运行前请确保满足脚本的依赖要求
- 部分脚本可能需要特定的环境变量或配置文件
- 建议在测试环境中先验证脚本功能

