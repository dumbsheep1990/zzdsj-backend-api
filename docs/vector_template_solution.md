# 向量化模板方案设计文档

## 概述

基于现有系统的向量存储基础设施，我们设计了一套完整的向量化模板方案，允许用户在创建知识库时选择适合不同场景和行业的向量化模板。这套方案规定了元数据格式、向量化索引构建方式，并针对不同场景进行了优化。

**特别针对政府服务事项的字段和格式差异，我们提供了智能模板选择和动态字段组合功能。**

## 方案架构

### 1. 核心组件

```
向量化模板系统
├── 配置层
│   ├── vector_templates_industry.yaml     # 行业模板配置
│   └── vector_store_templates.yaml        # 基础向量存储模板
├── 服务层
│   ├── VectorTemplateService              # 模板管理服务
│   ├── TableVectorizer                    # 表格数据智能分析
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

#### 政府服务专业模板（新增）
- **通用政府服务模板** (`government_service_template`) - 适用于标准政府服务事项
- **不动产登记专业模板** (`real_estate_registration_template`) - 针对抵押权登记等复杂业务
- **社会保障服务模板** (`social_security_template`) - 针对社保卡申领等民生服务

#### 通用场景模板
- **通用文档模板** (`general_document_template`)
- **问答知识库模板** (`qa_knowledge_template`)
- **企业知识库模板** (`enterprise_knowledge_template`)
- **教育培训模板** (`education_training_template`)
- **客服FAQ模板** (`customer_service_template`)
- **产品说明书模板** (`product_manual_template`)

## 政府服务事项差异化处理方案

### 1. 智能服务类型识别

针对您展示的两个不同类型的政府服务表格，系统提供智能识别功能：

```python
# 服务类型自动分类
service_patterns = {
    "real_estate_registration": ["不动产", "房屋", "抵押", "登记"],
    "social_security": ["社会保障", "社保", "医保", "保险"],
    "business_registration": ["工商", "企业", "营业执照"],
    # ... 更多类型
}
```

### 2. 动态字段组合系统

#### 基础字段组合
```yaml
government_service_fields:
  basic_fields: ["service_id", "service_name", "service_department"]
  citizen_focused: ["service_conditions", "required_materials", "contact_info"]
  fee_focused: ["fee_type", "fee_standard", "fee_basis"]
  process_focused: ["process_steps", "legal_deadline", "service_channels"]
```

#### 专业领域扩展字段
```yaml
# 不动产登记专用字段
real_estate_registration_fields:
  - registration_type: "登记类型"
  - property_type: "不动产类型"
  - fee_calculation_rules: "收费计算规则"
  - policy_references: "政策依据文件列表"
  - special_conditions: "特殊办理条件"

# 社会保障专用字段  
social_security_fields:
  - benefit_type: "保障类型"
  - eligibility_criteria: "申领条件"
  - benefit_amount: "保障金额"
  - coverage_period: "保障期限"
```

### 3. 复杂收费信息处理

针对您展示的抵押权登记表格中复杂的收费结构，我们提供专门的处理策略：

#### 简单收费（如预购商品房）
```python
fee_info = {
    "is_free": False,
    "fee_type": "按件收费",
    "fee_description": "简单收费说明"
}
```

#### 复杂收费（如抵押权登记）
```python
fee_info = {
    "is_free": False,
    "fee_type": "按标准收费",
    "fee_standard": "详细收费标准说明",
    "fee_basis": "财政部、国家发展改革委相关文件",
    "fee_calculation_rules": "具体计算方法",
    "policy_references": ["《财政收费文件》", "发改价格[2019]45号"]
}
```

### 4. 智能模板推荐算法

```python
def recommend_template(content_type, industry, service_type, complexity):
    score = 0
    
    # 行业匹配 (40分)
    if industry == "government": score += 40
    
    # 服务类型匹配 (25分)
    if service_type == "real_estate": 
        recommend "real_estate_registration_template"
        score += 25
    elif service_type == "social_security":
        recommend "social_security_template" 
        score += 25
    
    # 复杂度匹配 (15分)
    if complexity == "complex" and has_policy_references:
        score += 15
        
    return sorted_recommendations
```

## 模板配置详解

### 1. 不动产登记专业模板

```yaml
real_estate_registration_template:
  name: "不动产登记专业向量化模板"
  description: "适用于不动产登记、抵押权登记等复杂不动产业务"
  
  metadata_schema:
    fields: "real_estate_registration_fields"
    required_fields: ["service_id", "service_name", "registration_type"]
    searchable_fields: ["service_name", "registration_type", "fee_calculation_rules"]
    
  vectorization_config:
    chunk_size: 1000
    chunk_strategy: "legal_document_oriented"
    legal_document_processing: true
    policy_reference_extraction: true
    
  search_config:
    legal_precision: true
    policy_context_aware: true
```

### 2. 社会保障服务模板

```yaml
social_security_template:
  name: "社会保障服务向量化模板" 
  description: "适用于社保卡申领等民生服务"
  
  vectorization_config:
    chunk_size: 700
    chunk_strategy: "citizen_service_oriented"
    citizen_friendly_processing: true
    
  search_config:
    citizen_intent_optimization: true
    accessibility_enhanced: true
```

## API接口功能

### 1. 智能表格分析接口

```http
POST /knowledge/vector-templates/analyze-table
{
  "table_data": {
    "事项名称": "一般抵押权登记首次登记",
    "权力部门": "六盘水市自然资源局",
    "收费": "复杂收费信息..."
  }
}
```

**返回：**
- 自动识别服务类型
- 推荐最适合的模板
- 提供字段组合建议
- 分析复杂度和特殊处理需求

### 2. 动态字段组合接口

```http
POST /knowledge/vector-templates/field-combinations
{
  "template_id": "real_estate_registration_template",
  "scenario": "fee_analysis"
}
```

**返回：**
- 针对收费分析优化的字段组合
- 搜索优化建议
- 性能调优建议

### 3. 智能政府服务分析接口

```http
POST /knowledge/vector-templates/government-service/smart-analysis
{
  "table_data": {...},
  "service_name": "一般抵押权登记首次登记"
}
```

**返回：**
- 服务类型分类
- 复杂度评估
- 特殊处理建议
- 字段优化方案

## 使用示例

### 1. 处理预购商品房登记表格

```python
# 自动识别为简单政府服务
analysis_result = analyze_table({
    "事项名称": "预购商品房、保障性住房预告登记",
    "办理形式": "快速申请",
    "收费": "是否收费"
})

# 推荐：government_service_template
# 字段组合：基础字段 + 简单收费字段
```

### 2. 处理抵押权登记表格

```python
# 自动识别为复杂不动产登记
analysis_result = analyze_table({
    "事项名称": "一般抵押权登记首次登记",
    "收费": "收费依据和描述: 《财政部 国家发展改革委...》",
    "收费标准": "详细的政策文件引用..."
})

# 推荐：real_estate_registration_template  
# 字段组合：专业字段 + 复杂收费字段 + 政策引用字段
```

## 技术优势

### 1. 自适应字段配置
- 根据服务类型动态选择字段组合
- 支持复杂收费信息的结构化存储
- 政策文件引用的专门处理

### 2. 智能内容处理
- 法律文档导向的chunk策略
- 政策引用自动提取
- 市民友好的搜索优化

### 3. 性能优化
- 针对不同复杂度的索引策略
- 分区存储支持
- 混合搜索优化

## 部署建议

### 1. 政府服务场景部署
```yaml
# 推荐配置
backend: "milvus"  # 支持复杂查询
templates: 
  - "government_service_template" 
  - "real_estate_registration_template"
  - "social_security_template"
features:
  - smart_table_analysis
  - dynamic_field_combination  
  - policy_reference_extraction
```

### 2. 性能调优建议
- 复杂服务事项使用HNSW索引
- 启用分区功能处理大量数据
- 收费信息单独索引优化检索

通过这套智能化的向量模板系统，可以有效处理不同政府服务事项的字段和格式差异，为用户提供最优的向量化配置方案。 