# 智政知识库混合检索配置指南

## 概述

混合检索是智政知识库系统的核心功能，结合了语义搜索（基于向量相似度）和关键词搜索（基于BM25算法）的优势，为用户提供更准确、更全面的搜索结果。

## 🎯 功能特点

- **智能语义理解**: 通过向量嵌入理解查询的语义含义
- **精确关键词匹配**: 传统BM25算法确保关键词的精确匹配
- **权重可调**: 灵活调整语义搜索和关键词搜索的比重
- **多层次架构**: 支持核心层、服务层、框架层的统一调用
- **容器化部署**: 完整的Docker Compose配置支持

## 🚀 快速开始

### 1. 环境配置

确保以下环境变量正确设置：

```bash
# 必需配置
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_HYBRID_SEARCH=true
ELASTICSEARCH_HYBRID_WEIGHT=0.7

# 可选配置
ELASTICSEARCH_USERNAME=
ELASTICSEARCH_PASSWORD=
ELASTICSEARCH_INDEX=document_index
```

### 2. 使用Docker Compose启动

```bash
# 启动完整服务栈 (包括Elasticsearch)
docker-compose up -d

# 等待服务就绪
docker-compose ps
```

### 3. 使用专用启动脚本

```bash
# 推荐：使用混合检索专用启动脚本
chmod +x scripts/start_with_hybrid_search.sh
./scripts/start_with_hybrid_search.sh development

# 或生产模式
./scripts/start_with_hybrid_search.sh production
```

## 🔧 配置说明

### 核心配置项

| 配置项 | 默认值 | 描述 |
|--------|--------|------|
| `ELASTICSEARCH_HYBRID_SEARCH` | `true` | 是否启用混合检索 |
| `ELASTICSEARCH_HYBRID_WEIGHT` | `0.7` | 语义搜索权重（0-1） |
| `ELASTICSEARCH_URL` | `http://localhost:9200` | ES服务地址 |
| `ELASTICSEARCH_INDEX` | `document_index` | 默认索引名 |

### 权重配置建议

```bash
# 语义搜索优先 (推荐)
ELASTICSEARCH_HYBRID_WEIGHT=0.7  # 70%语义 + 30%关键词

# 平衡模式
ELASTICSEARCH_HYBRID_WEIGHT=0.5  # 50%语义 + 50%关键词

# 关键词优先
ELASTICSEARCH_HYBRID_WEIGHT=0.3  # 30%语义 + 70%关键词
```

## 🏗️ 架构说明

### 分层架构

```
┌─────────────────────────────────┐
│        API 端点层               │
├─────────────────────────────────┤
│     服务层 (Service Layer)      │
│  - HybridSearchService          │
│  - UnifiedService               │
├─────────────────────────────────┤
│     核心层 (Core Layer)         │
│  - RetrievalManager             │
│  - VectorManager                │
├─────────────────────────────────┤
│    存储层 (Storage Layer)       │
│  - ElasticsearchManager         │
│  - StorageDetector              │
├─────────────────────────────────┤
│    框架层 (Framework Layer)     │
│  - LlamaIndex                   │
│  - Haystack                     │
└─────────────────────────────────┘
```

### 核心组件

1. **HybridSearchService**: 混合检索服务的主要入口
2. **RetrievalManager**: 核心检索管理器，统一三种搜索模式
3. **ElasticsearchManager**: ES存储管理，支持知识库分区
4. **StorageDetector**: 自动检测和配置存储引擎

## 🔍 使用方法

### API调用示例

```python
from app.services.knowledge.hybrid_search_service import HybridSearchService, SearchConfig
from sqlalchemy.orm import Session

# 创建搜索配置
config = SearchConfig(
    query_text="人工智能的发展趋势",
    knowledge_base_ids=["kb_001", "kb_002"],
    vector_weight=0.7,
    text_weight=0.3,
    size=10,
    search_engine="hybrid"
)

# 执行搜索
service = HybridSearchService(db_session)
results = await service.search(config)

print(f"找到 {results['total']} 个结果")
for result in results['results']:
    print(f"标题: {result['title']}")
    print(f"内容: {result['content'][:100]}...")
    print(f"分数: {result['score']}")
```

### 三种搜索模式

```python
# 1. 语义搜索 (仅向量搜索)
results = await service.semantic_search(
    query="机器学习算法",
    knowledge_base_ids=["kb_001"],
    top_k=5,
    threshold=0.7
)

# 2. 关键词搜索 (仅文本搜索)
results = await service.keyword_search(
    query="深度学习 神经网络",
    knowledge_base_ids=["kb_001"],
    top_k=5
)

# 3. 混合搜索 (推荐)
config = SearchConfig(
    query_text="深度学习在图像识别中的应用",
    search_engine="hybrid",
    vector_weight=0.7,
    text_weight=0.3
)
results = await service.search(config)
```

## 🛠️ 初始化和验证

### 初始化Elasticsearch

```bash
# 运行ES初始化脚本
python3 scripts/init_elasticsearch.py

# 成功输出示例：
# ✅ Elasticsearch混合检索初始化完成
# 系统已配置为优先使用混合检索模式
```

### 验证配置

```bash
# 运行配置验证脚本
python3 scripts/validate_hybrid_search.py

# 查看验证报告
cat validation_report.json
```

## 📊 监控和调优

### 性能监控

```python
# 搜索结果包含性能指标
{
    "results": [...],
    "total": 10,
    "search_time_ms": 45.2,
    "strategy_used": "weighted_sum",
    "engine_used": "core_layer"
}
```

### 权重调优建议

根据不同场景调整权重：

- **学术文档**: `ELASTICSEARCH_HYBRID_WEIGHT=0.8` (语义优先)
- **技术文档**: `ELASTICSEARCH_HYBRID_WEIGHT=0.6` (平衡)
- **法律文件**: `ELASTICSEARCH_HYBRID_WEIGHT=0.4` (关键词优先)

## 🐛 故障排除

### 常见问题

1. **ES连接失败**
   ```bash
   # 检查ES服务状态
   curl -X GET "localhost:9200/_cluster/health"
   
   # 检查Docker容器
   docker-compose ps elasticsearch
   ```

2. **混合检索未生效**
   ```bash
   # 验证配置
   python3 scripts/validate_hybrid_search.py
   
   # 检查环境变量
   echo $ELASTICSEARCH_HYBRID_SEARCH
   ```

3. **搜索结果质量差**
   ```bash
   # 调整权重
   export ELASTICSEARCH_HYBRID_WEIGHT=0.8
   
   # 重启服务
   ./scripts/start_with_hybrid_search.sh development
   ```

### 日志调试

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG

# 查看搜索日志
tail -f logs/hybrid_search.log
```

## 🔧 高级配置

### 知识库级别配置

```python
# 为特定知识库配置混合检索参数
kb_config = {
    "use_hybrid_search": True,
    "hybrid_weight": 0.8,
    "search_strategy": "cascade",  # weighted_sum, rank_fusion, cascade
    "rerank_enabled": True
}
```

### 自定义搜索模板

ES支持自定义搜索模板，可以通过`init_elasticsearch.py`脚本进行配置：

- `hybrid_search_template`: 混合搜索模板
- `vector_search_template`: 纯向量搜索模板  
- `keyword_search_template`: 纯关键词搜索模板

### 批量搜索

```python
# 支持多知识库批量搜索
config = SearchConfig(
    query_text="人工智能",
    knowledge_base_ids=["kb_001", "kb_002", "kb_003"],
    search_engine="hybrid"
)

results = await service.search(config)
```

## 📚 最佳实践

1. **启动时验证**: 使用`start_with_hybrid_search.sh`确保配置正确
2. **定期验证**: 运行`validate_hybrid_search.py`检查系统状态
3. **权重调优**: 根据业务场景调整`ELASTICSEARCH_HYBRID_WEIGHT`
4. **监控性能**: 关注`search_time_ms`指标
5. **日志分析**: 定期查看搜索日志，优化查询

## 🆘 支持和联系

如果在配置或使用过程中遇到问题：

1. 查看本文档的故障排除部分
2. 运行验证脚本获取详细报告
3. 检查系统日志文件
4. 联系技术支持团队

---

**注意**: 混合检索是系统的核心功能，建议在生产环境中始终保持启用状态，以获得最佳的搜索体验。 