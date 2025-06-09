# Agentic文档切分工具使用指南

## 概述

基于Agno框架的Agentic文档切分工具是一个智能文档分段系统，使用大语言模型(LLM)来确定文档的自然语义边界，而不是简单地按固定大小或规则进行切分。这种方法能够显著提高RAG(检索增强生成)系统的性能。

## 核心特性

### 🧠 智能语义边界识别
- 使用LLM分析文档内容，识别自然的语义断点
- 保持相关内容的完整性和连贯性
- 避免任意切断句子、段落或概念

### 📊 多种切分策略
- **语义边界切分**: 基于语义相关性的智能分段
- **主题转换切分**: 识别主题变化进行分段
- **段落感知切分**: 尊重文档段落结构
- **对话流切分**: 适合对话和问答内容
- **技术文档切分**: 保留代码块和技术结构

### 🎯 质量评估系统
- 语义连贯性评分
- 大小合适性评分
- 边界自然性评分
- 结构保留性评分

### ⚙️ 灵活配置选项
- 可调节的块大小范围
- 可配置的重叠策略
- 支持多种语言
- 自定义质量阈值

## 快速开始

### 基本使用

```python
from app.tools.advanced.agentic_chunking import (
    AgenticDocumentChunker,
    AgenticChunkingConfig,
    AgenticChunkingStrategy
)

# 创建配置
config = AgenticChunkingConfig(
    strategy=AgenticChunkingStrategy.SEMANTIC_BOUNDARY,
    max_chunk_size=4000,
    min_chunk_size=200,
    language="zh"
)

# 创建切分器
chunker = AgenticDocumentChunker(config)

# 执行切分
result = await chunker.chunk_document(document_content)

print(f"生成 {result.total_chunks} 个文档块")
for chunk in result.chunks:
    print(f"块大小: {len(chunk.content)} 字符")
```

### 便利函数使用

```python
from app.tools.advanced.agentic_chunking import agentic_chunk_text

# 简单文本切分
result = await agentic_chunk_text(
    content="您的文档内容...",
    strategy=AgenticChunkingStrategy.TOPIC_TRANSITION,
    max_chunk_size=3000
)
```

### 智能自动切分

```python
from app.tools.advanced.agentic_chunking_integration import (
    smart_chunk_text,
    get_chunking_recommendations
)

# 获取切分建议
recommendations = get_chunking_recommendations(content_sample)
print(f"推荐工具: {recommendations['recommended_tool']}")

# 智能自动切分
result = await smart_chunk_text(
    content="您的文档内容...",
    content_type="technical_document"
)
```

## 切分策略详解

### 1. 语义边界切分 (SEMANTIC_BOUNDARY)
**适用场景**: 通用文档、新闻文章、博客文章

**特点**:
- 基于语义相似度进行切分
- 保持相关概念的完整性
- 适合大多数文档类型

**配置建议**:
```python
config = AgenticChunkingConfig(
    strategy=AgenticChunkingStrategy.SEMANTIC_BOUNDARY,
    max_chunk_size=4000,
    semantic_threshold=0.75,
    quality_threshold=0.8
)
```

### 2. 主题转换切分 (TOPIC_TRANSITION)
**适用场景**: 学术论文、研究报告、多主题文档

**特点**:
- 识别主题变化的信号
- 在主题边界处进行切分
- 保持每个主题的完整性

**配置建议**:
```python
config = AgenticChunkingConfig(
    strategy=AgenticChunkingStrategy.TOPIC_TRANSITION,
    max_chunk_size=5000,
    topic_coherence_weight=0.8
)
```

### 3. 段落感知切分 (PARAGRAPH_AWARE)
**适用场景**: 结构化文档、教科书、手册

**特点**:
- 尊重文档的段落结构
- 避免在段落中间切分
- 保持格式和结构的完整性

**配置建议**:
```python
config = AgenticChunkingConfig(
    strategy=AgenticChunkingStrategy.PARAGRAPH_AWARE,
    max_chunk_size=3500,
    preserve_structure=True,
    structure_preservation_weight=0.7
)
```

### 4. 对话流切分 (CONVERSATION_FLOW)
**适用场景**: 客服对话、问答记录、聊天记录

**特点**:
- 保持问答对的完整性
- 按对话轮次分组
- 适合交互式内容

**配置建议**:
```python
config = AgenticChunkingConfig(
    strategy=AgenticChunkingStrategy.CONVERSATION_FLOW,
    max_chunk_size=2500,
    min_chunk_size=100
)
```

### 5. 技术文档切分 (TECHNICAL_DOCUMENT)
**适用场景**: API文档、技术规范、代码文档

**特点**:
- 保留代码块的完整性
- 保持技术概念的连贯性
- 识别技术结构边界

**配置建议**:
```python
config = AgenticChunkingConfig(
    strategy=AgenticChunkingStrategy.TECHNICAL_DOCUMENT,
    max_chunk_size=6000,
    preserve_structure=True,
    quality_threshold=0.85
)
```

## 工具管理器使用

### 获取工具管理器

```python
from app.tools.advanced.agentic_chunking_integration import (
    get_agentic_chunking_manager
)

manager = get_agentic_chunking_manager()
```

### 查看可用工具

```python
tools = manager.get_available_tools()
for tool_name, tool_info in tools.items():
    print(f"工具: {tool_name}")
    print(f"描述: {tool_info['description']}")
    print(f"适用场景: {tool_info['use_cases']}")
```

### 批量处理文档

```python
documents = [
    {
        "content": "文档内容1...",
        "content_type": "technical",
        "metadata": {"source": "doc1"}
    },
    {
        "content": "文档内容2...",
        "content_type": "academic",
        "metadata": {"source": "doc2"}
    }
]

results = await manager.batch_chunk_documents(
    documents,
    auto_select=True,  # 自动选择最佳策略
    max_workers=5      # 并发处理数量
)
```

## 知识库集成

### 切分知识库文档

```python
from app.tools.advanced.agentic_chunking_integration import (
    smart_chunk_knowledge_base
)

result = await smart_chunk_knowledge_base(
    kb_id="your_knowledge_base_id",
    auto_select=True,
    batch_size=10
)

print(f"处理状态: {result['status']}")
print(f"成功文档: {result['successful_documents']}")
print(f"总块数: {result['total_chunks']}")
```

## 质量评估

### 理解质量指标

1. **语义连贯性 (semantic_coherence)**
   - 评估块内容的语义连贯性
   - 检查句子完整性和逻辑连接

2. **大小合适性 (size_appropriateness)**
   - 评估块大小是否在理想范围内
   - 避免过大或过小的块

3. **边界自然性 (boundary_naturalness)**
   - 评估切分边界是否自然
   - 检查开头和结尾的完整性

4. **结构保留性 (structure_preservation)**
   - 评估是否保留了文档结构
   - 检查段落和格式的完整性

### 质量分析示例

```python
result = await chunker.chunk_document(content)

for i, chunk in enumerate(result.chunks):
    quality = result.processing_metadata["quality_scores"][i]
    print(f"块 {i+1} 质量分析:")
    print(f"  语义连贯性: {quality['semantic_coherence']:.3f}")
    print(f"  大小合适性: {quality['size_appropriateness']:.3f}")
    print(f"  边界自然性: {quality['boundary_naturalness']:.3f}")
    print(f"  结构保留性: {quality['structure_preservation']:.3f}")
    print(f"  总体得分: {quality['overall_score']:.3f}")
```

## 自定义配置

### 创建自定义配置文件

```python
custom_config = AgenticChunkingConfig(
    strategy=AgenticChunkingStrategy.SEMANTIC_BOUNDARY,
    max_chunk_size=2000,    # 自定义最大块大小
    min_chunk_size=500,     # 自定义最小块大小
    chunk_overlap=150,      # 块重叠大小
    llm_model="gpt-4",      # 指定LLM模型
    language="zh",          # 文档语言
    semantic_threshold=0.8, # 语义阈值
    quality_threshold=0.85  # 质量阈值
)
```

### 注册自定义配置文件

```python
manager = get_agentic_chunking_manager()

custom_profile_name = manager.create_custom_profile(
    name="custom_academic",
    description="自定义学术文档切分配置",
    config=custom_config,
    use_cases=["学术论文", "研究报告"],
    recommended_for=["科研文档", "学位论文"]
)
```

## 最佳实践

### 1. 选择合适的策略
- **通用文档**: 使用 `SEMANTIC_BOUNDARY`
- **技术文档**: 使用 `TECHNICAL_DOCUMENT`
- **对话记录**: 使用 `CONVERSATION_FLOW`
- **学术论文**: 使用 `TOPIC_TRANSITION`
- **结构化文档**: 使用 `PARAGRAPH_AWARE`

### 2. 优化配置参数
- **块大小**: 根据模型的上下文窗口调整
- **重叠大小**: 保持上下文连续性，通常设置为块大小的10-20%
- **质量阈值**: 根据应用要求调整，高质量应用设置为0.8以上

### 3. 批量处理建议
- 使用合适的并发数量（推荐3-5个workers）
- 对相似类型的文档进行批次处理
- 监控处理进度和质量指标

### 4. 错误处理
- 设置回退策略
- 监控LLM可用性
- 记录处理日志

## 性能监控

### 获取处理统计

```python
stats = manager.get_stats()
print(f"处理文档总数: {stats['total_documents_processed']}")
print(f"成功处理: {stats['successful_processing']}")
print(f"失败处理: {stats['failed_processing']}")
print(f"平均处理时间: {stats['average_processing_time']:.2f}秒")
print(f"生成块总数: {stats['total_chunks_generated']}")
```

### 重置统计信息

```python
manager.reset_stats()
```

## 运行演示

执行演示脚本来体验功能：

```bash
cd /Users/wxn/Desktop/ZZDSJ/zzdsj-backend-api
python scripts/demo/agentic_chunking_demo.py
```

演示包含以下功能：
1. 基础切分功能展示
2. 不同策略对比
3. 智能自动选择
4. 自定义配置演示
5. 批量处理演示
6. 质量分析演示

## 常见问题

### Q: 如何选择合适的LLM模型？
A: 推荐使用 `gpt-4o-mini` 作为默认选择，平衡了性能和成本。对于高质量要求可以使用 `gpt-4`。

### Q: 切分效果不理想怎么办？
A: 
1. 调整策略类型
2. 修改块大小参数
3. 提高质量阈值
4. 检查文档预处理

### Q: 如何处理多语言文档？
A: 在配置中设置正确的语言参数，系统会相应调整处理策略。

### Q: 批量处理时如何优化性能？
A: 
1. 使用合适的并发数量
2. 按文档类型分组处理
3. 启用缓存机制
4. 监控资源使用

## 联系支持

如果您在使用过程中遇到问题或有改进建议，请通过以下方式联系：

- 项目Issue: GitHub Issues
- 文档更新: 提交PR到项目仓库
- 技术讨论: 项目Discussion区域 