"""
知识图谱相关数据模式
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum

class GraphStatus(str, Enum):
    """图谱状态枚举"""
    CREATED = "created"           # 已创建
    PROCESSING = "processing"     # 处理中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"            # 处理失败
    OPTIMIZING = "optimizing"    # 优化中

class EntityType(str, Enum):
    """实体类型枚举"""
    MODEL = "model"              # AI模型
    COMPANY = "company"          # 公司
    PERSON = "person"            # 人物
    TECHNOLOGY = "technology"    # 技术
    CONCEPT = "concept"          # 概念
    TIME = "time"               # 时间
    PLACE = "place"             # 地点

class RelationType(str, Enum):
    """关系类型枚举"""
    BELONGS_TO = "belongs_to"    # 属于
    DEVELOPS = "develops"        # 开发
    USES = "uses"               # 使用
    PROPOSES = "proposes"       # 提出
    APPLIES_TO = "applies_to"   # 应用于
    RELATED_TO = "related_to"   # 相关
    INFERRED = "inferred"       # 推断关系

class EntityExtractionConfig(BaseModel):
    """实体提取配置"""
    llm_model: str = Field(default="gpt-3.5-turbo", description="使用的LLM模型")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(default=2000, gt=0, description="最大token数")
    chunk_size: int = Field(default=1000, gt=0, description="文本分块大小")
    chunk_overlap: int = Field(default=100, ge=0, description="分块重叠大小")
    entity_types: List[EntityType] = Field(default_factory=list, description="提取的实体类型")
    extract_relations: bool = Field(default=True, description="是否提取关系")
    relation_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="关系置信度阈值")
    enable_inference: bool = Field(default=True, description="是否启用关系推理")

class GraphVisualizationConfig(BaseModel):
    """图谱可视化配置"""
    theme: str = Field(default="light", description="主题样式")
    layout: str = Field(default="physics", description="布局类型")
    physics_enabled: bool = Field(default=True, description="是否启用物理引擎")
    width: str = Field(default="100%", description="宽度")
    height: str = Field(default="600px", description="高度")
    node_size_factor: float = Field(default=1.0, ge=0.1, le=5.0, description="节点大小因子")
    edge_width_factor: float = Field(default=1.0, ge=0.1, le=5.0, description="边宽度因子")
    show_labels: bool = Field(default=True, description="是否显示标签")
    show_legend: bool = Field(default=True, description="是否显示图例")

class EntityCreate(BaseModel):
    """创建实体请求"""
    name: str = Field(..., min_length=1, max_length=255, description="实体名称")
    entity_type: EntityType = Field(..., description="实体类型")
    description: Optional[str] = Field(None, max_length=1000, description="实体描述")
    properties: Dict[str, Any] = Field(default_factory=dict, description="实体属性")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")

class RelationCreate(BaseModel):
    """创建关系请求"""
    subject: str = Field(..., min_length=1, description="主体实体")
    predicate: str = Field(..., min_length=1, description="关系谓词")
    object: str = Field(..., min_length=1, description="客体实体")
    relation_type: RelationType = Field(default=RelationType.RELATED_TO, description="关系类型")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系属性")

class FileSelectionRequest(BaseModel):
    """文件选择请求"""
    file_ids: List[int] = Field(..., min_items=1, description="选择的文件ID列表")
    extraction_config: EntityExtractionConfig = Field(default_factory=EntityExtractionConfig, description="提取配置")

class KnowledgeGraphCreate(BaseModel):
    """创建知识图谱请求"""
    name: str = Field(..., min_length=1, max_length=255, description="图谱名称")
    description: Optional[str] = Field(None, max_length=1000, description="图谱描述")
    knowledge_base_id: Optional[int] = Field(None, description="关联的知识库ID")
    extraction_config: EntityExtractionConfig = Field(default_factory=EntityExtractionConfig, description="提取配置")
    visualization_config: GraphVisualizationConfig = Field(default_factory=GraphVisualizationConfig, description="可视化配置")
    files: Optional[List[str]] = Field(None, description="初始文件路径列表")
    is_public: bool = Field(default=False, description="是否公开")
    tags: List[str] = Field(default_factory=list, description="标签列表")

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('图谱名称不能为空')
        return v.strip()

class KnowledgeGraphUpdate(BaseModel):
    """更新知识图谱请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="图谱名称")
    description: Optional[str] = Field(None, max_length=1000, description="图谱描述")
    visualization_config: Optional[GraphVisualizationConfig] = Field(None, description="可视化配置")
    is_public: Optional[bool] = Field(None, description="是否公开")
    tags: Optional[List[str]] = Field(None, description="标签列表")

class EntityResponse(BaseModel):
    """实体响应"""
    id: str = Field(..., description="实体ID")
    name: str = Field(..., description="实体名称")
    entity_type: EntityType = Field(..., description="实体类型")
    description: Optional[str] = Field(None, description="实体描述")
    properties: Dict[str, Any] = Field(default_factory=dict, description="实体属性")
    confidence: float = Field(..., description="置信度")
    connections: int = Field(default=0, description="连接数量")
    importance: float = Field(default=0.0, description="重要性分数")
    created_at: datetime = Field(..., description="创建时间")

class RelationResponse(BaseModel):
    """关系响应"""
    id: str = Field(..., description="关系ID")
    subject: str = Field(..., description="主体实体")
    predicate: str = Field(..., description="关系谓词")
    object: str = Field(..., description="客体实体")
    relation_type: RelationType = Field(..., description="关系类型")
    confidence: float = Field(..., description="置信度")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系属性")
    is_inferred: bool = Field(default=False, description="是否为推断关系")
    created_at: datetime = Field(..., description="创建时间")

class GraphStatistics(BaseModel):
    """图谱统计信息"""
    total_entities: int = Field(..., description="实体总数")
    total_relations: int = Field(..., description="关系总数")
    entity_type_distribution: Dict[str, int] = Field(default_factory=dict, description="实体类型分布")
    relation_type_distribution: Dict[str, int] = Field(default_factory=dict, description="关系类型分布")
    graph_density: float = Field(..., description="图谱密度")
    average_degree: float = Field(..., description="平均度数")
    connected_components: int = Field(..., description="连通分量数")
    clustering_coefficient: float = Field(..., description="聚类系数")

class ProcessingProgress(BaseModel):
    """处理进度"""
    total_files: int = Field(..., description="总文件数")
    processed_files: int = Field(..., description="已处理文件数")
    total_entities: int = Field(default=0, description="提取的实体总数")
    total_relations: int = Field(default=0, description="提取的关系总数")
    current_step: str = Field(..., description="当前处理步骤")
    progress_percentage: float = Field(..., ge=0.0, le=100.0, description="进度百分比")
    estimated_remaining_time: Optional[int] = Field(None, description="预估剩余时间(秒)")
    error_message: Optional[str] = Field(None, description="错误信息")

class KnowledgeGraphResponse(BaseModel):
    """知识图谱响应"""
    id: str = Field(..., description="图谱ID")
    name: str = Field(..., description="图谱名称")
    description: Optional[str] = Field(None, description="图谱描述")
    status: GraphStatus = Field(..., description="图谱状态")
    knowledge_base_id: Optional[int] = Field(None, description="关联的知识库ID")
    user_id: int = Field(..., description="创建用户ID")
    is_public: bool = Field(..., description="是否公开")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    
    # 统计信息
    statistics: Optional[GraphStatistics] = Field(None, description="图谱统计")
    
    # 处理信息
    processing_progress: Optional[ProcessingProgress] = Field(None, description="处理进度")
    
    # 配置信息
    extraction_config: EntityExtractionConfig = Field(..., description="提取配置")
    visualization_config: GraphVisualizationConfig = Field(..., description="可视化配置")
    
    # 时间信息
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    
    # 文件信息
    source_files: List[str] = Field(default_factory=list, description="源文件列表")
    
    class Config:
        from_attributes = True

class GraphAnalytics(BaseModel):
    """图谱分析结果"""
    basic_stats: GraphStatistics = Field(..., description="基础统计")
    
    # 中心性分析
    degree_centrality: Dict[str, float] = Field(default_factory=dict, description="度中心性")
    betweenness_centrality: Dict[str, float] = Field(default_factory=dict, description="介数中心性")
    closeness_centrality: Dict[str, float] = Field(default_factory=dict, description="接近中心性")
    pagerank: Dict[str, float] = Field(default_factory=dict, description="PageRank值")
    
    # 社区检测
    communities: List[List[str]] = Field(default_factory=list, description="社区划分")
    modularity: float = Field(default=0.0, description="模块度")
    
    # 重要实体
    top_entities: List[Dict[str, Union[str, float]]] = Field(default_factory=list, description="重要实体排名")
    
    # 关系分析
    relation_strength: Dict[str, float] = Field(default_factory=dict, description="关系强度")
    
    # 图谱质量
    completeness_score: float = Field(default=0.0, ge=0.0, le=1.0, description="完整性分数")
    consistency_score: float = Field(default=0.0, ge=0.0, le=1.0, description="一致性分数")
    
class ExportFormat(str, Enum):
    """导出格式枚举"""
    JSON = "json"
    CSV = "csv"
    RDF = "rdf"
    CYPHER = "cypher"
    GRAPHML = "graphml"

class GraphExportRequest(BaseModel):
    """图谱导出请求"""
    format: ExportFormat = Field(default=ExportFormat.JSON, description="导出格式")
    include_metadata: bool = Field(default=True, description="是否包含元数据")
    filter_config: Optional[Dict[str, Any]] = Field(None, description="过滤配置")

class OptimizationConfig(BaseModel):
    """图谱优化配置"""
    algorithm: str = Field(default="force_atlas", description="布局算法")
    iterations: int = Field(default=100, gt=0, description="迭代次数")
    node_repulsion: float = Field(default=50.0, gt=0.0, description="节点排斥力")
    edge_attraction: float = Field(default=0.1, gt=0.0, description="边吸引力")
    gravity: float = Field(default=0.01, gt=0.0, description="重力")
    optimize_overlaps: bool = Field(default=True, description="是否优化重叠")
    clustering_enabled: bool = Field(default=False, description="是否启用聚类")

class BatchProcessingRequest(BaseModel):
    """批量处理请求"""
    file_paths: List[str] = Field(..., min_items=1, description="文件路径列表")
    extraction_config: EntityExtractionConfig = Field(default_factory=EntityExtractionConfig)
    batch_size: int = Field(default=10, gt=0, le=100, description="批处理大小")
    parallel_workers: int = Field(default=4, gt=0, le=16, description="并行工作者数量") 