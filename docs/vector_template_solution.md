# 向量化模板方案设计文档

## 概述

基于现有系统的向量存储基础设施，我们设计了一套完整的向量化模板方案，允许用户在创建知识库时选择适合不同场景和行业的向量化模板。这套方案规定了元数据格式、向量化索引构建方式，并针对不同场景进行了优化。

## 方案架构

### 1. 核心组件

```
向量化模板系统
├── 配置层
│   ├── vector_templates_industry.yaml     # 行业模板配置
│   └── vector_store_templates.yaml        # 基础向量存储模板
├── 服务层
│   ├── VectorTemplateService              # 模板管理服务
│   └── VectorTemplateAPI                  # API接口层
└── 存储层
    ├── Milvus适配器
    ├── PostgreSQL+pgvector适配器
    └── Elasticsearch适配器
```

### 2. 模板分类体系

#### 行业特定模板
- **政策文档模板** (`policy_document_template`)
- **法律文档模板** (`legal_document_template`)
- **医疗文档模板** (`medical_document_template`)
- **技术文档模板** (`technical_document_template`)
- **学术论文模板** (`academic_paper_template`)

#### 通用场景模板
- **通用文档模板** (`general_document_template`)
- **问答知识库模板** (`qa_knowledge_template`)
- **企业知识库模板** (`enterprise_knowledge_template`)
- **教育培训模板** (`education_training_template`)
- **客服FAQ模板** (`customer_service_template`)
- **产品说明书模板** (`product_manual_template`)

## 模板配置详解

### 1. 元数据字段定义

每个模板都定义了专门的元数据字段，以政策文档为例：

```yaml
policy_document_fields:
  - name: "doc_id"           # 文档唯一标识符
  - name: "title"            # 政策文档标题
  - name: "source_url"       # 原始文档URL
  - name: "publish_date"     # 发布日期
  - name: "effective_date"   # 生效日期  
  - name: "topic"            # 政策主题分类
  - name: "category"         # 政策类别
  - name: "agency"           # 发布机构
  - name: "region"           # 适用地域
  - name: "doc_type"         # 文档类型
  - name: "chunk_id"         # 文档块ID
```

### 2. 向量化配置

```yaml
vectorization_config:
  embedding_model: "text-embedding-ada-002"    # 嵌入模型
  chunk_size: 1000                             # 切片大小
  chunk_overlap: 200                           # 切片重叠
  chunk_strategy: "semantic"                   # 切分策略
  language: "zh"                               # 语言
```

### 3. 索引配置

```yaml
index_config:
  vector_index:
    type: "HNSW"                               # 索引类型
    metric: "cosine"                           # 距离度量
    parameters:
      M: 16                                    # HNSW参数
      efConstruction: 200
  metadata_indexes:
    - fields: ["topic", "category"]            # 组合索引
      type: "composite"
    - fields: ["publish_date"]                 # 时间索引
      type: "btree"
```

### 4. 搜索优化配置

```yaml
search_config:
  default_top_k: 10                           # 默认返回数量
  similarity_threshold: 0.7                   # 相似度阈值
  rerank_enabled: true                        # 重排序
  hybrid_search:
    enabled: true                             # 混合搜索
    keyword_weight: 0.3                       # 关键词权重
    vector_weight: 0.7                        # 向量权重
```

## 向量数据库后端适配

### 1. Milvus配置

```yaml
milvus:
  policy_document:
    collection_name: "policy_documents"
    partition_config:
      enabled: true
      partition_key: "agency"                 # 按发布机构分区
      auto_partition: true
    sharding_config:
      shard_num: 2
      replicas: 1
```

### 2. PostgreSQL+pgvector配置

```yaml
pgvector:
  policy_document:
    table_name: "policy_document_vectors"
    index_type: "ivfflat"
    index_parameters:
      lists: 100
    partitioning:
      enabled: true
      partition_key: "agency"
      partition_type: "hash"
```

### 3. Elasticsearch配置

```yaml
elasticsearch:
  policy_document:
    index_name: "policy_documents"
    settings:
      number_of_shards: 3
      number_of_replicas: 1
    analysis:
      analyzer:
        policy_analyzer:
          type: "custom"
          tokenizer: "ik_smart"
          filter: ["lowercase", "stop"]
```

## API接口设计

### 1. 模板管理接口

```http
GET /api/frontend/knowledge/vector-templates/templates
# 获取所有可用模板

GET /api/frontend/knowledge/vector-templates/templates/{template_id}
# 获取指定模板配置

POST /api/frontend/knowledge/vector-templates/templates/recommend
# 推荐适合的模板

POST /api/frontend/knowledge/vector-templates/templates/apply
# 应用模板到知识库

GET /api/frontend/knowledge/vector-templates/templates/{template_id}/metadata-schema
# 获取模板元数据Schema

POST /api/frontend/knowledge/vector-templates/templates/check-compatibility
# 检查模板兼容性

GET /api/frontend/knowledge/vector-templates/backends
# 获取支持的向量数据库后端
```

### 2. 知识库创建流程

```python
# 1. 获取模板推荐
recommendations = await recommend_vector_templates({
    "content_type": "document",
    "industry": "government", 
    "use_case": "policy_search",
    "document_count": 1000
})

# 2. 选择模板并检查兼容性
compatibility = await check_template_compatibility({
    "template_id": "policy_document_template",
    "backend_type": "milvus",
    "document_count": 1000
})

# 3. 应用模板到知识库
result = await apply_vector_template({
    "kb_id": "kb_12345",
    "template_id": "policy_document_template", 
    "backend_type": "milvus",
    "custom_config": {}
})
```

## 模板推荐算法

### 1. 推荐评分机制

```python
def calculate_recommendation_score(template, criteria):
    score = 0
    
    # 行业匹配 (40分)
    if template.industry == criteria.industry:
        score += 40
    elif template.industry == "general":
        score += 10
    
    # 内容类型匹配 (30分)
    if criteria.content_type in template.scenario:
        score += 30
    
    # 使用场景匹配 (20分)
    if criteria.use_case in template.scenario:
        score += 20
        
    # 规模适配 (10分)
    if criteria.document_count:
        score += calculate_scale_score(template, criteria.document_count)
    
    return score
```

### 2. 性能预估

系统会根据模板配置和预期数据量估算性能指标：

- **搜索延迟**: low/medium/high
- **索引速度**: slow/medium/fast  
- **内存使用**: low/medium/high
- **准确性**: medium/high/very_high

## 使用示例

### 1. 政策文档知识库创建

```python
# 推荐模板
recommendations = await template_service.recommend_template(
    content_type="policy",
    industry="government",
    document_count=5000
)

# 应用政策文档模板
await template_service.apply_template_to_knowledge_base(
    kb_id="policy_kb_001",
    template_id="policy_document_template",
    backend_type=VectorBackendType.MILVUS
)
```

### 2. 通用企业知识库创建

```python
# 应用企业知识库模板
await template_service.apply_template_to_knowledge_base(
    kb_id="enterprise_kb_001", 
    template_id="enterprise_knowledge_template",
    backend_type=VectorBackendType.PGVECTOR,
    custom_config={
        "chunk_size": 1500,
        "department_filter": ["IT", "HR", "Finance"]
    }
)
```

## 扩展能力

### 1. 自定义模板

用户可以基于现有模板创建自定义模板：

```yaml
custom_template:
  name: "自定义医疗模板"
  base_template: "medical_document_template"
  custom_fields:
    - name: "hospital_level"
      data_type: "VARCHAR"
      description: "医院等级"
  vectorization_overrides:
    chunk_size: 800
    language: "zh"
```

### 2. 模板版本管理

支持模板的版本管理和升级：

- 版本控制
- 向后兼容
- 平滑升级
- 回滚机制

## 性能优化

### 1. 批处理配置

```yaml
performance_configs:
  batch_processing:
    policy_document:
      batch_size: 100
      parallel_workers: 4
      memory_limit_mb: 1024
```

### 2. 缓存策略

- 模板配置缓存
- 查询结果缓存  
- 元数据索引缓存

### 3. 监控指标

```yaml
monitoring_configs:
  metrics:
    - name: "vector_search_latency"
      type: "histogram"
    - name: "vector_index_size" 
      type: "gauge"
    - name: "search_accuracy"
      type: "gauge"
```

## 安全配置

### 1. 数据脱敏

```yaml
security_configs:
  data_masking:
    medical_document:
      enabled: true
      fields_to_mask: ["patient_id"]
      masking_strategy: "hash"
```

### 2. 访问控制

```yaml
access_control:
  enterprise_knowledge:
    public_access: false
    requires_authentication: true
    role_based_access: true
```

## 部署建议

### 1. 开发环境
- 使用通用文档模板
- PostgreSQL+pgvector后端
- 简化配置

### 2. 生产环境  
- 根据业务场景选择专业模板
- Milvus后端（大规模）
- 完整监控和安全配置

### 3. 性能调优
- 根据数据量调整索引参数
- 开启分区功能
- 配置缓存策略

## 总结

这套向量化模板方案提供了：

1. **场景化适配**：针对不同行业和场景的专门优化
2. **灵活配置**：支持多种向量数据库后端和自定义配置
3. **智能推荐**：基于使用场景的模板推荐算法
4. **性能优化**：针对不同规模和场景的性能调优
5. **易于扩展**：支持自定义模板和版本管理

通过这套方案，用户可以轻松创建适合自己业务场景的知识库，获得最佳的向量化处理效果和检索性能。 