# Schema层与Model层对比分析报告

## 概述

本文档分析了 `app/schemas` 目录下的Schema定义与 `app/models` 层数据库模型的对应关系，识别了缺少的业务表、中间表以及字段不匹配的问题。

## 总体匹配情况

### ✅ 已匹配的模块
- **用户权限系统**: user.py, resource_permission.py ↔ user.py, resource_permission.py
- **知识库系统**: knowledge.py ↔ knowledge.py
- **助手系统**: assistant.py, assistants.py ↔ assistant.py, assistants.py
- **聊天系统**: chat.py ↔ chat.py
- **工具系统**: tool.py ↔ tool.py
- **模型提供商**: model_provider.py ↔ model_provider.py
- **智能体定义**: agent_definition.py ↔ agent_definition.py
- **语音功能**: voice.py ↔ voice.py

## ❌ 缺少的数据表

### 1. Agent链管理系统
**Schema定义**: `app/schemas/agent_chain.py`
**缺少的Model表**:
```sql
-- Agent调用链配置表
CREATE TABLE agent_chains (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    execution_mode VARCHAR(20) NOT NULL DEFAULT 'sequential', -- sequential, parallel, conditional
    agents JSONB NOT NULL, -- Agent引用列表
    conditions JSONB, -- 条件执行配置
    metadata JSONB DEFAULT '{}',
    creator_id VARCHAR(36) REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agent调用链执行记录表
CREATE TABLE agent_chain_executions (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    chain_id VARCHAR(36) NOT NULL REFERENCES agent_chains(id),
    user_id VARCHAR(36) REFERENCES users(id),
    input_data JSONB NOT NULL,
    output_data JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, running, completed, failed
    progress INTEGER DEFAULT 0,
    error_message TEXT,
    context JSONB DEFAULT '{}',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Agent执行步骤表
CREATE TABLE agent_chain_execution_steps (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(36) NOT NULL REFERENCES agent_chain_executions(id),
    agent_id INTEGER NOT NULL,
    step_order INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);
```

### 2. OWL智能体系统扩展
**Schema定义**: `app/schemas/owl.py`, `app/schemas/owl_tool.py`
**缺少的Model表** (部分存在于owl_agent.py但不完整):
```sql
-- OWL工具包表 (在owl_agent.py中已有owl_toolkits，但schema有更多字段)
ALTER TABLE owl_toolkits ADD COLUMN IF NOT EXISTS version VARCHAR(20) DEFAULT '1.0.0';
ALTER TABLE owl_toolkits ADD COLUMN IF NOT EXISTS config JSONB DEFAULT '{}';
ALTER TABLE owl_toolkits ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]';
```

### 3. 统一工具管理系统
**Schema定义**: `app/schemas/unified_tool.py`
**缺少的Model表**:
```sql
-- 统一工具注册表
CREATE TABLE unified_tools (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    tool_type VARCHAR(50) NOT NULL, -- builtin, custom, mcp, external
    source_type VARCHAR(50) NOT NULL, -- internal, mcp_service, external_api
    source_id VARCHAR(36), -- 指向具体的工具源
    category VARCHAR(50),
    tags JSONB DEFAULT '[]',
    schema JSONB NOT NULL,
    config JSONB DEFAULT '{}',
    is_enabled BOOLEAN DEFAULT TRUE,
    version VARCHAR(20) DEFAULT '1.0.0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 工具使用统计表
CREATE TABLE tool_usage_stats (
    id SERIAL PRIMARY KEY,
    tool_id VARCHAR(36) NOT NULL REFERENCES unified_tools(id),
    user_id VARCHAR(36) REFERENCES users(id),
    execution_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    total_execution_time_ms BIGINT DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE(tool_id, user_id, date)
);
```

### 4. 基础工具系统
**Schema定义**: `app/schemas/base_tools.py`
**部分缺少的Model表** (base_tools.py中有部分定义但不完整):
```sql
-- 工具链定义表
CREATE TABLE tool_chains (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tools JSONB NOT NULL, -- 工具链配置
    metadata JSONB DEFAULT '{}',
    creator_id VARCHAR(36) REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 工具链执行记录表
CREATE TABLE tool_chain_executions (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    chain_id VARCHAR(36) NOT NULL REFERENCES tool_chains(id),
    input_data JSONB NOT NULL,
    output_data JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);
```

### 5. 搜索管理系统
**Schema定义**: `app/schemas/search.py`
**缺少的Model表**:
```sql
-- 搜索会话表
CREATE TABLE search_sessions (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) REFERENCES users(id),
    query TEXT NOT NULL,
    search_type VARCHAR(50) NOT NULL, -- semantic, keyword, hybrid
    filters JSONB DEFAULT '{}',
    results JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 搜索结果缓存表
CREATE TABLE search_result_cache (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    query_hash VARCHAR(64) UNIQUE NOT NULL,
    query_text TEXT NOT NULL,
    search_type VARCHAR(50) NOT NULL,
    filters_hash VARCHAR(64),
    results JSONB NOT NULL,
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);
```

### 6. 上下文压缩系统
**Schema定义**: `app/schemas/context_compression.py`
**部分缺少的Model表** (context_compression.py中有部分定义):
```sql
-- 压缩策略表
CREATE TABLE compression_strategies (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50) NOT NULL, -- llm, embedding, keyword
    config JSONB NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 需要在现有的context_compression_executions表中添加字段
ALTER TABLE context_compression_executions ADD COLUMN IF NOT EXISTS strategy_id VARCHAR(36) REFERENCES compression_strategies(id);
ALTER TABLE context_compression_executions ADD COLUMN IF NOT EXISTS compression_ratio FLOAT;
ALTER TABLE context_compression_executions ADD COLUMN IF NOT EXISTS quality_score FLOAT;
```

### 7. LightRAG集成系统
**Schema定义**: `app/schemas/lightrag.py`
**缺少的Model表**:
```sql
-- LightRAG图谱表
CREATE TABLE lightrag_graphs (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    knowledge_base_id INTEGER REFERENCES knowledge_bases(id),
    config JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'building', -- building, ready, error
    node_count INTEGER DEFAULT 0,
    edge_count INTEGER DEFAULT 0,
    last_updated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- LightRAG查询记录表
CREATE TABLE lightrag_queries (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    graph_id VARCHAR(36) NOT NULL REFERENCES lightrag_graphs(id),
    query_text TEXT NOT NULL,
    query_type VARCHAR(20) NOT NULL, -- naive, local, global, hybrid
    results JSONB,
    execution_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 8. 助手问答系统
**Schema定义**: `app/schemas/assistant_qa.py`
**Model层存在但字段不完整**:
```sql
-- 需要在现有的questions表中添加字段
ALTER TABLE questions ADD COLUMN IF NOT EXISTS category VARCHAR(50);
ALTER TABLE questions ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 0;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]';
ALTER TABLE questions ADD COLUMN IF NOT EXISTS feedback_score FLOAT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS feedback_count INTEGER DEFAULT 0;

-- 问题反馈表 (新增)
CREATE TABLE question_feedback (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id),
    user_id VARCHAR(36) REFERENCES users(id),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,
    is_helpful BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 问题标签表 (新增)
CREATE TABLE question_tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    color VARCHAR(7), -- HEX颜色值
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 问题标签关联表 (新增)
CREATE TABLE question_tag_relations (
    question_id INTEGER NOT NULL REFERENCES questions(id),
    tag_id INTEGER NOT NULL REFERENCES question_tags(id),
    PRIMARY KEY (question_id, tag_id)
);
```

## ⚠️ 字段不匹配问题

### 1. Tool系统字段差异
**Schema定义**:
```python
# app/schemas/tool.py
class ToolBase(BaseModel):
    tool_type: str  # Schema中有
    module_path: str  # Schema中有
    class_name: str  # Schema中有
```

**Model定义问题**:
```sql
-- app/models/tool.py 缺少字段
ALTER TABLE tools ADD COLUMN IF NOT EXISTS tool_type VARCHAR(50);
ALTER TABLE tools ADD COLUMN IF NOT EXISTS module_path TEXT;
ALTER TABLE tools ADD COLUMN IF NOT EXISTS class_name VARCHAR(100);

-- 同时需要更新现有字段
ALTER TABLE tools ALTER COLUMN implementation_type SET DEFAULT 'python';
```

### 2. Assistant系统字段差异
**Schema与Model字段对比**:
```sql
-- Schema中有但Model中缺少的字段
ALTER TABLE assistants ADD COLUMN IF NOT EXISTS access_url VARCHAR(255);
ALTER TABLE assistants ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- 字段类型不匹配
-- Schema: capabilities: List[str]
-- Model: capabilities: JSONB
-- 建议保持Model的JSONB类型，Schema层做适配
```

### 3. 用户权限系统字段差异
**Resource Permission字段对比**:
```sql
-- Schema中的assistant_id是字符串，但Model中assistants表用的是INTEGER
-- 建议在Schema层进行类型转换，或者统一主键类型策略

-- knowledge_base_id在Schema中是字符串，Model中是INTEGER
-- 同样需要在Schema层进行适配
```

### 4. Agent Definition字段差异
**Model层缺少的字段**:
```sql
-- 需要在agent_definitions表中添加
ALTER TABLE agent_definitions ADD COLUMN IF NOT EXISTS is_system BOOLEAN DEFAULT FALSE;
```

## 🔧 建议的解决方案

### 1. 立即需要创建的数据表
按优先级排序：

**高优先级**:
1. `agent_chains` - Agent链管理核心表
2. `agent_chain_executions` - Agent链执行记录
3. `unified_tools` - 统一工具管理
4. `search_sessions` - 搜索会话管理

**中优先级**:
1. `lightrag_graphs` - LightRAG图谱管理
2. `compression_strategies` - 压缩策略管理
3. `tool_chains` - 工具链定义

**低优先级**:
1. `question_feedback` - 问答反馈系统
2. `tool_usage_stats` - 工具使用统计
3. `search_result_cache` - 搜索缓存

### 2. 字段修复策略

**方案A: 修改Model层 (推荐)**
- 在现有表中添加缺少的字段
- 保持向后兼容性
- 更新数据库迁移脚本

**方案B: 修改Schema层**
- 调整Schema定义以匹配现有Model
- 在API层进行数据转换
- 保持数据库结构不变

### 3. 主键策略统一
**问题**: 部分表使用UUID，部分使用自增ID
**建议**: 
- 新表统一使用UUID主键
- 现有自增ID表保持不变
- Schema层处理类型转换

### 4. 实施步骤

1. **第一阶段**: 创建缺少的核心表
   ```sql
   -- 执行新表创建脚本
   -- 更新数据库初始化脚本
   ```

2. **第二阶段**: 修复字段不匹配
   ```sql
   -- 执行字段添加和修改脚本
   -- 更新现有数据
   ```

3. **第三阶段**: Schema层适配
   ```python
   # 更新Schema定义以匹配Model
   # 添加数据验证和转换逻辑
   ```

4. **第四阶段**: 测试和验证
   ```python
   # 创建单元测试
   # 验证API接口
   # 确保数据一致性
   ```

## 📊 缺少表统计

| 模块 | Schema文件 | 缺少表数量 | 优先级 |
|------|------------|------------|--------|
| Agent链管理 | agent_chain.py | 3 | 高 |
| 统一工具 | unified_tool.py | 2 | 高 |
| 搜索系统 | search.py | 2 | 中 |
| LightRAG | lightrag.py | 2 | 中 |
| 基础工具 | base_tools.py | 2 | 中 |
| 问答助手 | assistant_qa.py | 3 | 低 |
| 上下文压缩 | context_compression.py | 1 | 低 |

**总计**: 需要新增 **15个数据表** 和修复 **8个字段不匹配** 问题。

## 🎯 下一步行动

1. **立即执行**: 创建高优先级表的SQL脚本
2. **本周内**: 修复字段不匹配问题
3. **下周**: 创建中优先级表
4. **月内**: 完成所有表的创建和测试

建议先从Agent链管理系统开始，因为这是核心功能，其他功能模块都可能依赖于它。 