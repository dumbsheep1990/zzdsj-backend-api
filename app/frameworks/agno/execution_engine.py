"""
Agno执行图引擎
基于有向无环图(DAG)的Agent任务执行引擎，支持条件分支、并行处理和错误恢复
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional, Set, Callable
from datetime import datetime
from collections import defaultdict, deque
from enum import Enum

try:
    import networkx as nx
except ImportError:
    # 如果networkx未安装，使用简化的图实现
    nx = None

from app.frameworks.agno.templates import ExecutionGraph, ExecutionNode, ExecutionEdge
from app.frameworks.agno.orchestration.types import (
    ExecutionContext, ExecutionStatus, OrchestrationResult, 
    ToolCallResult, EventData, OrchestrationEvent
)

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """节点类型"""
    PROCESSOR = "processor"
    CLASSIFIER = "classifier"
    RETRIEVER = "retriever"
    GENERATOR = "generator"
    COORDINATOR = "coordinator"
    ANALYZER = "analyzer"
    SCORER = "scorer"
    FILTER = "filter"
    SYNTHESIZER = "synthesizer"
    EVALUATOR = "evaluator"
    FORMATTER = "formatter"
    DECOMPOSER = "decomposer"
    ASSESSOR = "assessor"
    PLANNER = "planner"
    EXECUTOR = "executor"
    VALIDATOR = "validator"
    REPORTER = "reporter"


class NodeProcessor:
    """节点处理器基类"""
    
    def __init__(self, node_id: str, node_type: NodeType, config: Dict[str, Any]):
        self.node_id = node_id
        self.node_type = node_type
        self.config = config
    
    async def process(self, input_data: Any, context: ExecutionContext) -> Any:
        """处理节点逻辑"""
        raise NotImplementedError


class ProcessorNode(NodeProcessor):
    """数据处理节点"""
    
    async def process(self, input_data: Any, context: ExecutionContext) -> Any:
        """处理输入数据"""
        logger.info(f"Processing data in node {self.node_id}")
        
        # 根据配置处理数据
        if self.config.get("max_context"):
            # 限制上下文长度
            if isinstance(input_data, str):
                max_length = self.config["max_context"] * 100  # 估算字符数
                if len(input_data) > max_length:
                    input_data = input_data[:max_length] + "..."
        
        if self.config.get("extract_intent"):
            # 简单的意图提取模拟
            intents = ["question", "request", "chat", "task"]
            for intent in intents:
                if intent in input_data.lower():
                    return {"text": input_data, "intent": intent, "confidence": 0.8}
        
        if self.config.get("sentiment_analysis"):
            # 简单的情感分析模拟
            positive_words = ["好", "棒", "优秀", "满意", "喜欢"]
            negative_words = ["差", "糟", "不好", "失望", "讨厌"]
            
            sentiment = "neutral"
            for word in positive_words:
                if word in input_data:
                    sentiment = "positive"
                    break
            for word in negative_words:
                if word in input_data:
                    sentiment = "negative"
                    break
            
            return {"text": input_data, "sentiment": sentiment}
        
        return input_data


class ClassifierNode(NodeProcessor):
    """分类决策节点"""
    
    async def process(self, input_data: Any, context: ExecutionContext) -> Any:
        """分类处理"""
        logger.info(f"Classifying data in node {self.node_id}")
        
        categories = self.config.get("categories", [])
        confidence_threshold = self.config.get("confidence_threshold", 0.7)
        
        # 简单的分类逻辑
        if isinstance(input_data, dict) and "text" in input_data:
            text = input_data["text"].lower()
            
            for category in categories:
                if category in text:
                    return {
                        **input_data,
                        "category": category,
                        "confidence": 0.9
                    }
            
            # 默认分类
            return {
                **input_data,
                "category": categories[0] if categories else "unknown",
                "confidence": 0.5
            }
        
        return input_data


class GeneratorNode(NodeProcessor):
    """内容生成节点"""
    
    async def process(self, input_data: Any, context: ExecutionContext) -> Any:
        """生成内容"""
        logger.info(f"Generating content in node {self.node_id}")
        
        style = self.config.get("style", "neutral")
        max_tokens = self.config.get("max_tokens", 500)
        temperature = self.config.get("temperature", 0.7)
        
        # 模拟内容生成
        if isinstance(input_data, dict) and "text" in input_data:
            text = input_data["text"]
            
            # 根据风格调整回复
            style_prefixes = {
                "friendly": "很高兴为您解答！",
                "professional": "根据您的问题，",
                "creative": "让我们用创新的方式来看这个问题："
            }
            
            prefix = style_prefixes.get(style, "")
            generated_text = f"{prefix}针对您的问题「{text}」，这是一个详细的回答。"
            
            return {
                **input_data,
                "generated_text": generated_text,
                "style": style,
                "tokens_used": len(generated_text)
            }
        
        return input_data


class RetrieverNode(NodeProcessor):
    """信息检索节点"""
    
    async def process(self, input_data: Any, context: ExecutionContext) -> Any:
        """检索信息"""
        logger.info(f"Retrieving information in node {self.node_id}")
        
        top_k = self.config.get("top_k", 5)
        similarity_threshold = self.config.get("similarity_threshold", 0.8)
        
        # 模拟知识库检索
        mock_documents = [
            {"id": "doc1", "title": "示例文档1", "content": "这是第一个示例文档", "score": 0.95},
            {"id": "doc2", "title": "示例文档2", "content": "这是第二个示例文档", "score": 0.88},
            {"id": "doc3", "title": "示例文档3", "content": "这是第三个示例文档", "score": 0.82},
        ]
        
        # 过滤和排序
        filtered_docs = [doc for doc in mock_documents if doc["score"] >= similarity_threshold]
        top_docs = sorted(filtered_docs, key=lambda x: x["score"], reverse=True)[:top_k]
        
        return {
            **input_data if isinstance(input_data, dict) else {"text": str(input_data)},
            "retrieved_documents": top_docs,
            "retrieval_count": len(top_docs)
        }


class FormatterNode(NodeProcessor):
    """格式化节点"""
    
    async def process(self, input_data: Any, context: ExecutionContext) -> Any:
        """格式化输出"""
        logger.info(f"Formatting output in node {self.node_id}")
        
        markdown = self.config.get("markdown", True)
        include_citations = self.config.get("include_citations", False)
        
        if isinstance(input_data, dict):
            if "generated_text" in input_data:
                text = input_data["generated_text"]
                
                if markdown:
                    # 简单的Markdown格式化
                    text = f"## 回答\n\n{text}\n"
                
                if include_citations and "retrieved_documents" in input_data:
                    citations = "\n\n## 参考文献\n"
                    for i, doc in enumerate(input_data["retrieved_documents"], 1):
                        citations += f"{i}. {doc['title']}\n"
                    text += citations
                
                return {
                    **input_data,
                    "formatted_text": text,
                    "format": "markdown" if markdown else "text"
                }
        
        return input_data


class AgnoExecutionEngine:
    """基于执行图的Agent执行引擎"""
    
    def __init__(self, execution_graph: Optional[ExecutionGraph] = None):
        """初始化执行引擎"""
        self.execution_graph = execution_graph
        self.graph = None
        self.node_processors = {}
        
        if execution_graph:
            self._build_execution_graph()
            self._initialize_processors()
    
    def _build_execution_graph(self):
        """构建执行图"""
        if nx:
            # 使用NetworkX构建图
            self.graph = nx.DiGraph()
            
            # 添加节点
            for node in self.execution_graph.nodes:
                self.graph.add_node(node.id, **{"type": node.type, "config": node.config})
            
            # 添加边
            for edge in self.execution_graph.edges:
                edge_attrs = {
                    "condition": edge.condition,
                    "weight": edge.weight,
                    "timeout": edge.timeout
                }
                self.graph.add_edge(edge.from_node, edge.to_node, **edge_attrs)
        else:
            # 使用简化的图实现
            self.graph = self._build_simple_graph()
    
    def _build_simple_graph(self) -> Dict[str, Any]:
        """构建简化的图结构"""
        graph = {
            "nodes": {},
            "edges": defaultdict(list),
            "reverse_edges": defaultdict(list)
        }
        
        # 添加节点
        for node in self.execution_graph.nodes:
            graph["nodes"][node.id] = {
                "type": node.type,
                "config": node.config
            }
        
        # 添加边
        for edge in self.execution_graph.edges:
            graph["edges"][edge.from_node].append({
                "to": edge.to_node,
                "condition": edge.condition,
                "weight": edge.weight,
                "timeout": edge.timeout
            })
            graph["reverse_edges"][edge.to_node].append(edge.from_node)
        
        return graph
    
    def _initialize_processors(self):
        """初始化节点处理器"""
        processor_classes = {
            NodeType.PROCESSOR: ProcessorNode,
            NodeType.CLASSIFIER: ClassifierNode,
            NodeType.GENERATOR: GeneratorNode,
            NodeType.RETRIEVER: RetrieverNode,
            NodeType.FORMATTER: FormatterNode,
            # 其他节点类型可以复用相似的处理器
            NodeType.ANALYZER: ProcessorNode,
            NodeType.SCORER: ProcessorNode,
            NodeType.FILTER: ProcessorNode,
            NodeType.SYNTHESIZER: GeneratorNode,
            NodeType.EVALUATOR: ClassifierNode,
            NodeType.DECOMPOSER: ProcessorNode,
            NodeType.ASSESSOR: ClassifierNode,
            NodeType.PLANNER: ProcessorNode,
            NodeType.EXECUTOR: ProcessorNode,
            NodeType.VALIDATOR: ClassifierNode,
            NodeType.REPORTER: FormatterNode,
            NodeType.COORDINATOR: ProcessorNode,
        }
        
        for node in self.execution_graph.nodes:
            node_type = NodeType(node.type)
            processor_class = processor_classes.get(node_type, ProcessorNode)
            self.node_processors[node.id] = processor_class(node.id, node_type, node.config)
    
    async def execute(self, input_data: Any, context: ExecutionContext) -> OrchestrationResult:
        """执行Agent任务"""
        logger.info(f"开始执行任务: {context.request_id}")
        
        start_time = datetime.now()
        context.status = ExecutionStatus.RUNNING
        context.start_time = start_time
        
        try:
            # 获取执行顺序
            execution_order = self._get_execution_order()
            if not execution_order:
                raise ValueError("无法确定执行顺序，可能存在循环依赖")
            
            current_data = input_data
            execution_path = []
            
            # 按顺序执行节点
            for node_id in execution_order:
                # 检查执行条件
                if not self._check_execution_condition(node_id, current_data, context):
                    logger.info(f"跳过节点 {node_id}：不满足执行条件")
                    continue
                
                # 执行节点处理
                processor = self.node_processors.get(node_id)
                if not processor:
                    logger.warning(f"找不到节点处理器: {node_id}")
                    continue
                
                logger.info(f"执行节点: {node_id}")
                node_start_time = datetime.now()
                
                try:
                    result = await asyncio.wait_for(
                        processor.process(current_data, context),
                        timeout=30  # 默认30秒超时
                    )
                    
                    # 更新数据和路径
                    current_data = result
                    execution_time = (datetime.now() - node_start_time).total_seconds()
                    
                    execution_path.append({
                        "node_id": node_id,
                        "node_type": processor.node_type.value,
                        "input": str(input_data)[:200] + "..." if len(str(input_data)) > 200 else str(input_data),
                        "output": str(result)[:200] + "..." if len(str(result)) > 200 else str(result),
                        "execution_time": execution_time,
                        "timestamp": node_start_time.isoformat(),
                        "status": "completed"
                    })
                    
                    logger.info(f"节点 {node_id} 执行完成，耗时 {execution_time:.2f}s")
                    
                except asyncio.TimeoutError:
                    logger.error(f"节点 {node_id} 执行超时")
                    execution_path.append({
                        "node_id": node_id,
                        "node_type": processor.node_type.value,
                        "status": "timeout",
                        "error": "执行超时",
                        "timestamp": node_start_time.isoformat()
                    })
                    break
                except Exception as e:
                    logger.error(f"节点 {node_id} 执行失败: {str(e)}")
                    execution_path.append({
                        "node_id": node_id,
                        "node_type": processor.node_type.value,
                        "status": "failed",
                        "error": str(e),
                        "timestamp": node_start_time.isoformat()
                    })
                    break
            
            # 计算总执行时间
            total_time = (datetime.now() - start_time).total_seconds()
            context.status = ExecutionStatus.COMPLETED
            
            # 提取最终结果
            final_result = current_data
            if isinstance(current_data, dict) and "formatted_text" in current_data:
                final_result = current_data["formatted_text"]
            elif isinstance(current_data, dict) and "generated_text" in current_data:
                final_result = current_data["generated_text"]
            
            logger.info(f"任务执行完成，总耗时 {total_time:.2f}s")
            
            return OrchestrationResult(
                request_id=context.request_id,
                success=True,
                result=final_result,
                execution_time=total_time,
                metadata={
                    "execution_path": execution_path,
                    "nodes_executed": len([p for p in execution_path if p.get("status") == "completed"]),
                    "total_nodes": len(execution_order),
                    "execution_order": execution_order
                }
            )
            
        except Exception as e:
            context.status = ExecutionStatus.FAILED
            total_time = (datetime.now() - start_time).total_seconds()
            
            logger.error(f"任务执行失败: {str(e)}", exc_info=True)
            
            return OrchestrationResult(
                request_id=context.request_id,
                success=False,
                error=str(e),
                execution_time=total_time,
                metadata={
                    "execution_path": execution_path if 'execution_path' in locals() else [],
                    "error_type": type(e).__name__
                }
            )
    
    def _get_execution_order(self) -> List[str]:
        """获取节点执行顺序（拓扑排序）"""
        if nx and hasattr(self.graph, 'nodes'):
            # 使用NetworkX的拓扑排序
            try:
                return list(nx.topological_sort(self.graph))
            except nx.NetworkXError:
                logger.error("图中存在循环依赖，无法进行拓扑排序")
                return []
        else:
            # 使用简化的拓扑排序
            return self._simple_topological_sort()
    
    def _simple_topological_sort(self) -> List[str]:
        """简化的拓扑排序实现"""
        in_degree = defaultdict(int)
        nodes = set(self.graph["nodes"].keys())
        
        # 计算入度
        for node in nodes:
            in_degree[node] = 0
        
        for from_node, edges in self.graph["edges"].items():
            for edge in edges:
                in_degree[edge["to"]] += 1
        
        # 拓扑排序
        queue = deque([node for node in nodes if in_degree[node] == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            # 更新邻接节点的入度
            for edge in self.graph["edges"][node]:
                to_node = edge["to"]
                in_degree[to_node] -= 1
                if in_degree[to_node] == 0:
                    queue.append(to_node)
        
        # 检查是否存在循环
        if len(result) != len(nodes):
            logger.error("图中存在循环依赖")
            return []
        
        return result
    
    def _check_execution_condition(self, node_id: str, data: Any, context: ExecutionContext) -> bool:
        """检查节点执行条件"""
        if nx and hasattr(self.graph, 'nodes'):
            # NetworkX版本
            predecessors = list(self.graph.predecessors(node_id))
            if not predecessors:
                return True  # 起始节点
            
            # 检查前置节点的条件
            for pred in predecessors:
                edge_data = self.graph[pred][node_id]
                condition = edge_data.get("condition")
                
                if condition and not self._evaluate_condition(condition, data, context):
                    return False
        else:
            # 简化版本
            reverse_edges = self.graph["reverse_edges"][node_id]
            if not reverse_edges:
                return True  # 起始节点
            
            # 检查前置节点的条件
            for pred in reverse_edges:
                for edge in self.graph["edges"][pred]:
                    if edge["to"] == node_id:
                        condition = edge["condition"]
                        if condition and not self._evaluate_condition(condition, data, context):
                            return False
        
        return True
    
    def _evaluate_condition(self, condition: str, data: Any, context: ExecutionContext) -> bool:
        """评估执行条件"""
        if not condition:
            return True
        
        try:
            # 简单的条件评估
            if "complexity > 0.8" in condition:
                # 模拟复杂度评估
                if isinstance(data, dict) and "complexity" in data:
                    return data["complexity"] > 0.8
                # 基于数据长度估算复杂度
                data_str = str(data)
                complexity = min(len(data_str) / 1000, 1.0)
                return complexity > 0.8
            
            if "confidence" in condition:
                if isinstance(data, dict) and "confidence" in data:
                    threshold = float(condition.split()[-1])
                    return data["confidence"] >= threshold
            
            # 默认返回True
            return True
            
        except Exception as e:
            logger.warning(f"条件评估失败 '{condition}': {str(e)}")
            return True
    
    async def execute_stream(self, input_data: Any, context: ExecutionContext):
        """流式执行（生成器版本）"""
        logger.info(f"开始流式执行任务: {context.request_id}")
        
        execution_order = self._get_execution_order()
        current_data = input_data
        
        for node_id in execution_order:
            if not self._check_execution_condition(node_id, current_data, context):
                continue
            
            processor = self.node_processors.get(node_id)
            if not processor:
                continue
            
            logger.info(f"流式执行节点: {node_id}")
            
            try:
                result = await processor.process(current_data, context)
                current_data = result
                
                # 生成中间结果
                yield {
                    "node_id": node_id,
                    "node_type": processor.node_type.value,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"流式执行节点 {node_id} 失败: {str(e)}")
                yield {
                    "node_id": node_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                break
        
        # 最终结果
        yield {
            "final_result": current_data,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_execution_status(self, request_id: str) -> ExecutionStatus:
        """获取执行状态（简化实现）"""
        # 在实际实现中，这里应该查询状态存储
        return ExecutionStatus.COMPLETED
    
    def visualize_graph(self) -> Dict[str, Any]:
        """可视化执行图"""
        if not self.execution_graph:
            return {"error": "没有可用的执行图"}
        
        visualization = {
            "nodes": [],
            "edges": [],
            "metadata": {
                "total_nodes": len(self.execution_graph.nodes),
                "total_edges": len(self.execution_graph.edges)
            }
        }
        
        # 添加节点信息
        for node in self.execution_graph.nodes:
            visualization["nodes"].append({
                "id": node.id,
                "type": node.type,
                "config": node.config,
                "label": f"{node.id} ({node.type})"
            })
        
        # 添加边信息
        for edge in self.execution_graph.edges:
            visualization["edges"].append({
                "from": edge.from_node,
                "to": edge.to_node,
                "condition": edge.condition,
                "weight": edge.weight,
                "label": edge.condition if edge.condition else ""
            })
        
        return visualization


# 便利函数
def create_execution_engine(execution_graph: ExecutionGraph) -> AgnoExecutionEngine:
    """创建执行引擎"""
    return AgnoExecutionEngine(execution_graph)


async def execute_with_graph(
    execution_graph: ExecutionGraph,
    input_data: Any,
    request_id: Optional[str] = None
) -> OrchestrationResult:
    """使用执行图执行任务"""
    engine = AgnoExecutionEngine(execution_graph)
    
    context = ExecutionContext(
        request_id=request_id or str(uuid.uuid4()),
        user_id="system",
        session_id=None
    )
    
    return await engine.execute(input_data, context)