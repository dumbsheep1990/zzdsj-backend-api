# API层迁移执行计划

**日期：** 2025年5月30日

## 概述

根据现有的API迁移进度和项目架构要求，本文档制定了剩余API文件的迁移和重构计划。迁移策略遵循以下原则：

1. 前端服务接口（frontend目录）：根据前端页面功能进行模块划分
2. 后端服务接口（其他目录）：根据三层架构设计和服务层职责划分模块
3. 第三方接口（v1目录）：为外部调用提供稳定API

## 待迁移文件清单

| 原始文件 | 目标路径 | 优先级 | 复杂度 |
|---------|---------|-------|-------|
| app/api/system_config.py | app/api/frontend/system/config.py | 高 | 中 |
| app/api/sensitive_word.py | app/api/frontend/system/sensitive_word.py | 中 | 低 |
| app/api/mcp.py | app/api/frontend/mcp/client.py | 高 | 高 |
| app/api/mcp_service.py | app/api/frontend/mcp/service.py | 高 | 高 |
| app/api/resource_permission.py | app/api/frontend/security/permissions.py | 中 | 中 |
| app/api/lightrag.py | app/api/frontend/knowledge/lightrag.py | 低 | 低 (已完成迁移桥接) |

## 目录结构准备

需要确保以下目录存在：

```
app/api/frontend/system/
app/api/frontend/mcp/
app/api/frontend/security/
```

## 迁移步骤详解

### 1. 系统模块迁移

#### 1.1 系统配置API迁移

1. 创建 `app/api/frontend/system/config.py` 文件
2. 实现系统配置API的所有功能
3. 更新路由前缀为 `/api/frontend/system`
4. 添加适当的依赖注入和权限控制
5. 修改 `app/api/system_config.py` 添加迁移桥接代码

示例桥接代码：
```python
"""
系统配置API - 提供配置管理和系统自检API
[迁移桥接] - 该文件已迁移至 app/api/frontend/system/config.py
"""

from fastapi import APIRouter
import logging

# 导入新的API模块
from app.api.frontend.system.config import router as new_router

# 创建路由
router = APIRouter()
logger = logging.getLogger(__name__)

# 记录迁移警告
logger.warning("使用已弃用的app/api/system_config.py，该文件已迁移至app/api/frontend/system/config.py")

# 将所有请求转发到新的路由处理器
for route in new_router.routes:
    router.routes.append(route)
```

#### 1.2 敏感词管理API迁移

1. 创建 `app/api/frontend/system/sensitive_word.py` 文件
2. 实现敏感词管理API的所有功能
3. 更新路由前缀为 `/api/frontend/system/sensitive-words`
4. 修改 `app/api/sensitive_word.py` 添加迁移桥接代码

### 2. MCP服务模块迁移

#### 2.1 MCP客户端API迁移

1. 创建 `app/api/frontend/mcp/client.py` 文件
2. 将`mcp.py`中的客户端API功能迁移到新文件
3. 更新路由前缀为 `/api/frontend/mcp`
4. 修改 `app/api/mcp.py` 添加迁移桥接代码

#### 2.2 MCP服务管理API迁移

1. 创建 `app/api/frontend/mcp/service.py` 文件
2. 将`mcp_service.py`中的服务管理API功能迁移到新文件
3. 更新路由前缀为 `/api/frontend/mcp/services`
4. 修改 `app/api/mcp_service.py` 添加迁移桥接代码

### 3. 资源权限模块迁移

1. 创建 `app/api/frontend/security/permissions.py` 文件
2. 实现资源权限管理API的所有功能
3. 更新路由前缀为 `/api/frontend/security/permissions`
4. 修改 `app/api/resource_permission.py` 添加迁移桥接代码

## 迁移优化建议

1. **统一错误处理**：在新API中实现一致的错误处理模式
2. **权限控制优化**：使用统一的权限检查装饰器
3. **依赖注入标准化**：采用一致的依赖注入模式
4. **响应格式标准化**：使用`ResponseFormatter`确保所有API返回格式一致
5. **API文档完善**：为每个端点添加详细的文档字符串

## 测试策略

1. 为每个迁移的API编写单元测试
2. 确保原始路径和新路径都能正常工作
3. 验证权限控制和依赖注入功能
4. 测试异常情况和边界条件

## 迁移顺序和时间安排

建议按以下顺序进行迁移：

1. **第一阶段**（1天）：系统模块迁移
   - 系统配置API
   - 敏感词管理API

2. **第二阶段**（2天）：MCP服务模块迁移
   - MCP客户端API
   - MCP服务管理API

3. **第三阶段**（1天）：资源权限模块迁移
   - 资源权限管理API

## 迁移注意事项

1. 保持所有功能的完整性和一致性
2. 确保URL路径和参数的兼容性
3. 适当记录和处理废弃警告
4. 更新API文档和路由配置
5. 确保新路径在主路由表中正确注册

## 迁移完成后的工作

1. 更新`migration_progress.md`文件，记录迁移完成情况
2. 更新主路由配置文件，确保所有新路径正确注册
3. 运行全面测试，确保所有API正常工作
4. 考虑添加废弃警告，计划未来完全移除旧API路径
