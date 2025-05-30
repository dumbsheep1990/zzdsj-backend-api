# ZZ-Backend-Lite 数据库架构分析

## 概述

本文档详细分析了 `app/models` 层下所有数据库模型的定义，整理了完整的数据库架构设计。系统采用 PostgreSQL 数据库，支持 JSONB、UUID 等高级特性。

## 架构特点

- **分层设计**: 按功能模块组织表结构
- **权限控制**: 完整的 RBAC 权限体系
- **资源管理**: 细粒度的资源访问控制
- **扩展性**: 支持多种 AI 框架集成
- **审计追踪**: 完整的操作历史记录

## 数据库表分类

### 1. 用户权限系统 (User & Permission System)

#### 核心用户表
- **users**: 用户基础信息
  - 支持 UUID 主键和自增 ID
  - 包含用户名、邮箱、密码等基础信息
  - 支持超级管理员标识

- **roles**: 角色定义
  - 支持默认角色设置
  - 角色描述和创建时间

- **permissions**: 权限定义
  - 权限名称、代码、描述
  - 资源类型关联

#### 关联表
- **user_role**: 用户角色多对多关联
- **role_permission**: 角色权限多对多关联

#### 用户扩展表
- **user_settings**: 用户个人设置
  - UI 主题、语言、通知设置
- **api_keys**: 用户 API 密钥管理
  - 支持密钥过期和使用追踪

### 2. 资源权限控制 (Resource Access Control)

#### 通用权限表
- **resource_permissions**: 通用资源权限控制
  - 支持多种资源类型和访问级别

#### 专用权限表
- **knowledge_base_access**: 知识库访问权限
- **assistant_access**: 助手访问权限  
- **model_config_access**: 模型配置访问权限
- **mcp_config_access**: MCP 配置访问权限

#### 配额管理
- **user_resource_quotas**: 用户资源配额
  - 知识库数量、存储空间、API 调用限制等

### 3. 知识库系统 (Knowledge Base System)

#### 核心表
- **knowledge_bases**: 知识库基础信息
  - 支持多种类型（default, csv, pdf, web）
  - 嵌入模型配置、文档统计

- **documents**: 文档管理
  - 文件路径、大小、MIME 类型
  - 处理状态追踪

- **document_chunks**: 文档分块
  - 向量嵌入 ID、令牌计数
  - 支持检索优化

### 4. AI 助手系统 (AI Assistant System)

#### 助手定义
- **assistants**: AI 助手配置
  - 模型选择、能力配置
  - 系统提示词、访问 URL

#### 对话管理
- **conversations**: 对话会话
- **messages**: 对话消息
- **message_references**: 消息文档引用

#### 问答系统
- **questions**: 问答助手问题库
- **question_document_segments**: 问题文档关联

#### 关联表
- **assistant_knowledge_base**: 助手知识库关联
- **assistant_knowledge_graphs**: 助手知识图谱关联

### 5. 智能体系统 (Agent System)

#### 智能体定义
- **agent_definitions**: 智能体定义
  - 基础类型、配置、工作流定义
- **agent_templates**: 智能体模板
- **agent_tool_association**: 智能体工具关联

#### 运行时管理
- **agent_runs**: 智能体运行记录
- **agent_memories**: 智能体记忆存储
- **agent_config**: 智能体配置
- **agent_tool**: 智能体工具配置

### 6. 工具系统 (Tool System)

#### 工具定义
- **tools**: 工具定义表
  - 函数定义、实现类型、权限级别
  - 支持多种框架（python, api, mcp, model）

#### 执行记录
- **tool_executions**: 工具执行历史
  - 输入参数、输出结果、执行时间

### 7. MCP 服务系统 (MCP Service System)

#### 服务管理
- **mcp_service_config**: MCP 服务配置
  - Docker 容器管理、资源限制
  - 服务状态追踪

#### 工具管理
- **mcp_tool**: MCP 工具定义
- **mcp_tool_execution**: MCP 工具执行历史

### 8. 模型提供商系统 (Model Provider System)

- **model_providers**: 模型提供商配置
  - 支持多种提供商（OpenAI, Zhipu, DeepSeek 等）
- **model_info**: 模型详细信息
  - 能力配置、默认模型设置

### 9. 系统配置 (System Configuration)

- **config_categories**: 配置类别
- **system_configs**: 系统配置项
  - 支持多种数据类型、验证规则
  - 敏感信息加密存储
- **config_history**: 配置变更历史

### 10. 其他功能表

#### 语音功能
- **voice_settings**: 用户语音设置
  - STT/TTS 模型配置、语音参数

#### 系统监控
- **service_health_records**: 服务健康检查记录

## 数据类型使用

### 主键策略
- **UUID**: 用户、角色、权限等核心实体
- **SERIAL**: 知识库、文档、助手等业务实体

### JSON 字段
- **JSONB**: PostgreSQL 优化的 JSON 存储
- 用于配置、元数据、参数等灵活数据

### 时间戳
- **TIMESTAMP WITH TIME ZONE**: 统一使用带时区的时间戳
- 自动更新触发器支持

## 索引策略

### 基础索引
- 所有外键字段
- 常用查询字段（用户名、邮箱、名称等）
- 时间字段（创建时间、更新时间）

### 复合索引
- 资源权限查询优化
- MCP 工具唯一性约束
- 智能体工具唯一性约束

## 约束和触发器

### 外键约束
- 级联删除策略
- 引用完整性保证

### 触发器
- 自动更新时间戳
- 数据一致性维护

## 视图定义

### 统计视图
- **user_permissions_view**: 用户权限汇总
- **assistant_stats_view**: 助手使用统计
- **knowledge_base_stats_view**: 知识库统计

## 初始数据

### 默认配置
- 系统配置类别和基础配置项
- 默认角色和权限定义
- 管理员账户（admin/admin123）

### 权限分配
- 管理员：所有权限
- 普通用户：基础读取权限
- 开发者：开发调试权限

## 扩展性考虑

### 模块化设计
- 每个功能模块相对独立
- 支持渐进式功能扩展

### 配置驱动
- 系统行为通过配置表控制
- 支持运行时配置修改

### 多租户支持
- 用户级别的资源隔离
- 细粒度权限控制

## 性能优化

### 查询优化
- 合理的索引设计
- 视图简化复杂查询

### 存储优化
- JSONB 字段压缩存储
- 分区表支持（可扩展）

## 安全考虑

### 数据保护
- 敏感信息加密存储
- 密码哈希处理

### 访问控制
- 完整的 RBAC 体系
- 资源级别权限控制

### 审计追踪
- 配置变更历史
- 操作执行记录

## 维护建议

### 定期维护
- 清理过期数据
- 重建统计信息
- 检查约束完整性

### 监控指标
- 表大小增长
- 查询性能
- 索引使用率

### 备份策略
- 定期全量备份
- 增量备份支持
- 关键数据实时同步

## 总结

该数据库架构设计完整、灵活，支持复杂的 AI 应用场景。通过模块化设计和完善的权限体系，能够满足企业级应用的需求。建议在实际部署时根据具体业务需求进行适当调整和优化。 