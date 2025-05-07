# LlamaIndex框架适配器修复记录

## 问题概述

在集成Agno和Haystack框架作为LlamaIndex工具的过程中，发现LlamaIndex 0.10.68版本API有变更，导致多处导入错误和类不兼容问题。

主要问题：
- `QueryEngine` → `BaseQueryEngine`
- `ToolCallbackQueryEngine` 类不可用
- 导入路径变更

## 解决方案

### 1. 导入路径修正

所有文件中更新了导入路径：
```python
# 修改前
from llama_index.core.query_engine import QueryEngine

# 修改后
from llama_index.core.query_engine import BaseQueryEngine
```

### 2. 自定义查询引擎实现

为解决`ToolCallbackQueryEngine`不可用问题，简化设计：

**Agno适配器：**
```python
def as_query_engine(self) -> BaseQueryEngine:
    class AgnoQueryEngine(BaseQueryEngine):
        def __init__(self, tool: AgnoAgentTool):
            self.tool = tool
            super().__init__()
        
        async def aquery(self, query_str: str):
            result = await self.tool(query_str)
            return Response(response=result)
    
    return AgnoQueryEngine(self)
```

**Haystack检索器：**
```python
def as_query_engine(self) -> BaseQueryEngine:
    class HaystackQueryEngine(BaseQueryEngine):
        def __init__(self, retriever: HaystackRetriever):
            self.retriever = retriever
            super().__init__()
        
        async def aquery(self, query_str: str):
            nodes = await self.retriever._aretrieve(query_str)
            # 处理结果并返回响应...
    
    return HaystackQueryEngine(self)
```

### 3. 工具注册中心优化

```python
# 类型注解更新
self._tools: Dict[str, Union[BaseTool, BaseQueryEngine]] = {}

# 类型检查更新
elif isinstance(tool, BaseQueryEngine):
    # 包装为QueryEngineTool...
```

## 测试验证

创建简化版测试脚本，验证核心功能：
- 工具注册中心基本功能
- 适配器模式基本原理

```
测试结果:
✓ 注册中心初始化成功
✓ 注册和获取功能正常
✓ 链式调用功能正常
✓ 适配器模式实现正确
```

## 设计原则应用

- **SOLID原则**：单一职责、接口隔离、依赖倒置
- **简化依赖**：减少对特定API组件的耦合
- **保持兼容**：维持原有接口和功能完整性

## 后续计划

1. **验证与测试**
   - 业务环境中验证适配器功能
   - 更完整的集成测试

2. **业务层集成**
   - 更新`assistant_qa_manager.py`使用统一路由
   - 测试不同知识库和模型组合

3. **性能优化**
   - 添加缓存减少重复查询
   - 优化工具选择逻辑

通过本次修改，成功解决了版本兼容性问题，并优化了适配器设计，为后续扩展提供了更灵活的架构基础。
