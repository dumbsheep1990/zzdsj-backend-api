# Monitoring Scripts

此目录包含monitoring相关脚本相关的脚本文件。

## 脚本列表

| 脚本名称 | 类型 | 功能描述 |
|---------|------|----------|
| check_db_progress.py | Python | - |
| check_remote_table_structure.py | Python | - |

## 使用说明

请根据具体脚本的功能和要求来使用。大部分Python脚本可以通过以下方式运行：

```bash
python3 monitoring/script_name.py
```

Shell脚本可以通过以下方式运行：

```bash
chmod +x monitoring/script_name.sh
./monitoring/script_name.sh
```

## 注意事项

- 运行前请确保满足脚本的依赖要求
- 部分脚本可能需要特定的环境变量或配置文件
- 建议在测试环境中先验证脚本功能

