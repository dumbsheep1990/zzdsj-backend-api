# LlamaIndex 统一调用链集成方案

## 1. 项目背景

当前项目已将 LangChain 替换为 LlamaIndex 作为主要框架，但 Agno 和 HayStack 仍作为独立组件被调用，未深度集成到 LlamaIndex 调用链中。这种架构导致了资源利用率低、框架间集成松散，以及信息传递需要额外转换等问题。

本文档提供了一个详细的改造方案，将 Agno 和 HayStack 重构为 LlamaIndex 调用链的一部分，使 LlamaIndex 真正成为前置场景判断和引导层。

## 2. 当前架构分析

### 2.1 现有框架集成状态

1. **LlamaIndex**
   - 作为统一入口点，提供服务上下文、嵌入和聊天功能
   - 在 `app/frameworks/llamaindex` 目录下实现核心功能
   - 主要模块：`core.py`, `chat.py`, `embeddings.py`, `retrieval.py`
   
2. **Agno**
   - 作为独立代理框架，主要提供推理和规划能力
   - 通过 `app/frameworks/agno/agent.py` 实现为独立调用模块
   - 当前在 `HYBRID` 回答模式下被直接调用
   
3. **HayStack**
   - 作为独立问答框架，专注于精确问答能力
   - 通过 `app/frameworks/haystack/reader.py` 实现为独立调用模块
   - 当前在 `DOCS_ONLY` 回答模式下被直接调用

### 2.2 现有问题

1. **调用链不统一**：不同框架通过条件判断直接调用，无统一调用链
2. **信息转换开销**：框架间数据传递需要格式转换，增加了系统复杂性
3. **资源重复利用**：各框架可能创建相似资源，如嵌入缓存
4. **扩展性受限**：难以实现复杂的调用序列（如LlamaIndex→Agno→HayStack）
5. **业务逻辑耦合**：业务层需要明确了解各框架细节，增加维护成本

## 3. 改造目标与原则

### 3.1 目标

1. 将 LlamaIndex 定位为真正的前置场景判断和引导层
2. 将 Agno 和 HayStack 重构为 LlamaIndex 调用链的工具组件
3. 简化业务层代码，统一通过 LlamaIndex API 进行调用
4. 确保数据格式一致性，避免多次转换

### 3.2 设计原则

1. **统一接口**：所有框架对外提供统一的 LlamaIndex 接口
2. **最小修改**：尽量减少对现有核心逻辑的修改
3. **封装隔离**：通过适配器模式封装第三方框架
4. **松耦合**：降低组件间依赖，提高可扩展性
5. **可测试性**：确保所有集成点可以独立测试

## 4. 改造方案

### 4.1 总体架构

```
[用户查询]
      │
      ▼
[LlamaIndex Router] ─── 场景判断 ─── 选择工具链
      │
      ├─────────────┬───────────────┬───────────────┐
      │             │               │               │
      ▼             ▼               ▼               ▼
[LlamaIndex工具] [Agno工具适配器] [HayStack检索器] [MCP工具]
                    │               │
                    ▼               ▼
              [Agno Agent]    [HayStack QA]
```

### 4.2 创建适配器层

#### 4.2.1 Agno 适配器

创建 `app/frameworks/llamaindex/adapters/agno_tools.py`：

```python
from typing import Any, Dict, Optional, List
from llama_index.core.tools import BaseTool, ToolMetadata
from app.frameworks.agno.agent import AgnoAgent

class AgnoAgentTool(BaseTool):
    """将Agno代理包装为LlamaIndex工具"""
    
    def __init__(self, agent: AgnoAgent, name: str, description: str):
        self.agent = agent
        self._metadata = ToolMetadata(name=name, description=description)
    
    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata
    
    async def __call__(self, query: str, **kwargs):
        """调用Agno代理执行查询"""
        conversation_id = kwargs.get("conversation_id")
        response = await self.agent.query(query, conversation_id)
        return response["response"]
    
    def as_query_engine(self, **kwargs):
        """将工具转换为查询引擎"""
        from llama_index.core.query_engine import ToolCallbackQueryEngine
        return ToolCallbackQueryEngine.from_defaults(
            tool=self,
            **kwargs
        )
```

#### 4.2.2 HayStack 适配器

创建 `app/frameworks/llamaindex/adapters/haystack_retriever.py`：

```python
from typing import List, Dict, Any, Optional
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, Document
from app.frameworks.haystack.reader import extract_answers

class HaystackRetriever(BaseRetriever):
    """基于Haystack的LlamaIndex检索器"""
    
    def __init__(self, knowledge_base_id: Optional[int] = None, model_name: Optional[str] = None, top_k: int = 3):
        """初始化Haystack检索器"""
        self.model_name = model_name
        self.top_k = top_k
        self.knowledge_base_id = knowledge_base_id
        super().__init__()
    
    async def _aretrieve(self, query_str: str, contexts: List[Dict[str, Any]] = None, **kwargs) -> List[NodeWithScore]:
        """使用Haystack执行检索"""
        # 如果未提供上下文，可以从知识库获取（通过其他检索器）
        if contexts is None and hasattr(self, "_get_contexts"):
            contexts = await self._get_contexts(query_str, self.knowledge_base_id, self.top_k)
        
        if not contexts:
            return []
        
        # 使用Haystack提取答案
        answers = extract_answers(
            question=query_str,
            contexts=contexts,
            model_name=self.model_name,
            top_k=self.top_k
        )
        
        # 转换为LlamaIndex节点
        nodes = []
        for ans in answers:
            node = NodeWithScore(
                node=Document.from_dict({
                    "text": ans["context"],
                    "metadata": {
                        "answer": ans["answer"],
                        "document_id": ans.get("document_id"),
                        "start_idx": ans.get("start_idx"),
                        "end_idx": ans.get("end_idx")
                    }
                }),
                score=ans["score"]
            )
            nodes.append(node)
        
        return nodes
    
    def as_query_engine(self, **kwargs):
        """将检索器转换为查询引擎"""
        from llama_index.core.query_engine import RetrieverQueryEngine
        return RetrieverQueryEngine.from_args(
            retriever=self,
            **kwargs
        )
```

### 4.3 创建统一工具集成层

创建 `app/frameworks/llamaindex/tools.py`：

```python
from typing import Dict, Any, List, Optional
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from app.frameworks.agno.agent import create_knowledge_agent
from app.frameworks.llamaindex.adapters.agno_tools import AgnoAgentTool
from app.frameworks.llamaindex.adapters.haystack_retriever import HaystackRetriever

def get_agno_tool(
    knowledge_base_ids: List[int] = None,
    name: str = "knowledge_reasoning",
    description: str = "复杂知识推理和多步骤问答"
) -> QueryEngineTool:
    """获取Agno代理工具"""
    # 转换为字符串列表
    kb_ids = [str(kb_id) for kb_id in knowledge_base_ids] if knowledge_base_ids else []
    
    # 创建知识代理
    agent = create_knowledge_agent(kb_ids)
    
    # 包装为工具
    agno_tool = AgnoAgentTool(
        agent=agent,
        name=name,
        description=description
    )
    
    # 转换为查询引擎工具
    return QueryEngineTool(
        query_engine=agno_tool.as_query_engine(),
        metadata=ToolMetadata(
            name=name,
            description=description
        )
    )

def get_haystack_tool(
    knowledge_base_id: Optional[int] = None,
    name: str = "fact_extraction",
    description: str = "精确的事实提取和问答"
) -> QueryEngineTool:
    """获取Haystack检索工具"""
    # 创建检索器
    retriever = HaystackRetriever(knowledge_base_id=knowledge_base_id)
    
    # 转换为查询引擎工具
    return QueryEngineTool(
        query_engine=retriever.as_query_engine(),
        metadata=ToolMetadata(
            name=name,
            description=description
        )
    )
```

### 4.4 创建场景路由模块

创建 `app/frameworks/llamaindex/router.py`：

```python
from typing import List, Dict, Any, Optional
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from app.frameworks.llamaindex.tools import get_agno_tool, get_haystack_tool
from app.frameworks.llamaindex.core import get_service_context

class QueryRouter:
    """场景路由器，根据查询类型选择适当的处理引擎"""
    
    def __init__(self, 
                knowledge_base_id: Optional[int] = None,
                model_name: Optional[str] = None,
                service_context=None):
        """初始化路由器"""
        self.knowledge_base_id = knowledge_base_id
        self.model_name = model_name
        self.service_context = service_context or get_service_context(model_name)
        self.engines = {}
        self._setup_engines()
    
    def _setup_engines(self):
        """设置各种引擎和工具"""
        # 1. 创建Agno工具
        if self.knowledge_base_id:
            self.engines["knowledge_reasoning"] = get_agno_tool(
                knowledge_base_ids=[self.knowledge_base_id]
            )
        
        # 2. 创建Haystack工具
        if self.knowledge_base_id:
            self.engines["fact_extraction"] = get_haystack_tool(
                knowledge_base_id=self.knowledge_base_id
            )
        
        # 3. 创建通用检索工具
        # 可以添加其他工具...
    
    def get_router_engine(self) -> RouterQueryEngine:
        """获取路由查询引擎"""
        tools = list(self.engines.values())
        
        router_engine = RouterQueryEngine.from_defaults(
            query_engine_tools=tools,
            service_context=self.service_context,
            select_multi=True  # 可以选择多个引擎
        )
        
        return router_engine

def create_unified_engine(
    knowledge_base_id: Optional[int] = None,
    model_name: Optional[str] = None,
    service_context=None
) -> RouterQueryEngine:
    """创建统一查询引擎的便捷函数"""
    router = QueryRouter(
        knowledge_base_id=knowledge_base_id,
        model_name=model_name,
        service_context=service_context
    )
    return router.get_router_engine()
```

### 4.5 重构助手问答管理器

修改 `app/core/assistant_qa_manager.py` 中的 `_generate_answer` 方法：

```python
async def _generate_answer(self, question: Question) -> str:
    """根据问题和回答模式生成回答"""
    try:
        # 获取助手信息
        assistant = self.db.query(Assistant).filter(Assistant.id == question.assistant_id).first()
        if not assistant:
            return "无法找到关联的助手信息"
        
        # 获取启用的文档分段内容
        document_segments = []
        for doc_seg in question.document_segments:
            if doc_seg.is_enabled:
                segment = self.db.query(DocumentSegment).filter(
                    DocumentSegment.id == doc_seg.segment_id
                ).first()
                
                if segment:
                    document_segments.append({
                        "content": segment.content,
                        "metadata": {
                            "document_id": doc_seg.document_id,
                            "segment_id": doc_seg.segment_id,
                            "score": doc_seg.relevance_score
                        }
                    })
        
        # 创建系统提示
        system_prompt = f"你是一个{assistant.name}，需要回答关于{assistant.description or '相关主题'}的问题。"
        
        # 根据回答模式选择不同的处理方式
        if question.answer_mode == AnswerModeEnum.DEFAULT or question.answer_mode == AnswerModeEnum.HYBRID:
            # 使用统一的LlamaIndex路由引擎
            from app.frameworks.llamaindex.router import create_unified_engine
            
            # 创建统一引擎
            engine = create_unified_engine(
                knowledge_base_id=assistant.knowledge_base_id,
                model_name=assistant.model_id
            )
            
            # 准备上下文
            from app.frameworks.llamaindex.core import process_query
            
            # 处理查询
            result = await process_query(
                query=question.question_text,
                engine=engine,
                system_prompt=system_prompt,
                conversation_history=[{"role": "user", "content": question.question_text}]
            )
            
            return result["answer"]
            
        elif question.answer_mode == AnswerModeEnum.DOCS_ONLY:
            # 仍然保持DOCS_ONLY模式的直接调用
            # 但在内部已改为通过LlamaIndex的Haystack适配器调用
            from app.frameworks.llamaindex.adapters.haystack_retriever import HaystackRetriever
            
            retriever = HaystackRetriever(top_k=3)
            answers = await retriever._aretrieve(question.question_text, document_segments)
            
            if answers and len(answers) > 0:
                return answers[0].node.metadata.get("answer", "无法从文档中提取相关答案")
            else:
                return "无法从文档中提取相关答案"
            
        elif question.answer_mode == AnswerModeEnum.MODEL_ONLY:
            # 仅使用模型回答，不使用文档
            from app.frameworks.llamaindex.chat import generate_response
            
            response = await generate_response(
                system_prompt=system_prompt,
                conversation_history=[{"role": "user", "content": question.question_text}],
                model_name=assistant.model_id
            )
            
            return response
            
        # 默认返回
        return "无法确定回答模式"
            
    except Exception as e:
        logger.error(f"生成回答错误: {str(e)}")
        return f"生成回答时出错: {str(e)}"
```

## 5. AI辅助实施加速计划

### 5.1 阶段一：基础结构与适配器开发（3天）

1. **第1天**：设计与搭建
   - 上午：创建适配器目录结构，设计接口规范
   - 下午：使用AI生成Agno适配器代码框架和基础实现
   - 晚上：使用AI生成HayStack适配器代码框架和基础实现

2. **第2天**：实现与单元测试
   - 上午：在AI辅助下完成适配器的功能实现
   - 下午：使用AI生成单元测试用例
   - 晚上：执行测试并修复问题

3. **第3天**：完善与调试
   - 上午：处理边缘情况和异常处理
   - 下午：使用AI优化适配器性能
   - 晚上：完成适配器文档和示例代码

### 5.2 阶段二：工具集成与路由（2天）

1. **第4天**：工具集成
   - 上午：使用AI生成统一工具集成层代码
   - 下午：实现工具工厂函数和辅助方法
   - 晚上：编写工具集成层的单元测试

2. **第5天**：路由实现
   - 上午：使用AI生成场景路由模块
   - 下午：实现智能路由逻辑和决策规则
   - 晚上：编写并执行集成测试

### 5.3 阶段三：业务层重构与集成（2天）

1. **第6天**：核心功能重构
   - 上午：使用AI重构assistant_qa_manager.py中的_generate_answer方法
   - 下午：调整其他依赖方法和接口
   - 晚上：进行核心功能测试

2. **第7天**：全局集成
   - 上午：更新服务层代码，统一使用新接口
   - 下午：使用AI生成端到端测试脚本
   - 晚上：执行测试并解决集成问题

### 5.4 阶段四：优化与文档（1天）

1. **第8天**：完善与部署
   - 上午：使用AI分析性能瓶颈并优化
   - 下午：完成API文档和开发指南
   - 晚上：部署测试和最终验证

## 6. AI辅助开发策略

### 6.1 代码生成与优化

1. **适配器生成**：使用AI生成Agno和HayStack适配器的代码框架和基础实现
2. **工具集成**：使用AI生成统一工具集成层代码
3. **路由实现**：使用AI生成场景路由模块
4. **单元测试**：使用AI生成单元测试用例
5. **性能优化**：使用AI分析性能瓶颈并优化

### 6.2 代码评审与测试

1. **人工评审**：人工评审AI生成的代码，确保质量和安全
2. **自动测试**：使用自动化测试工具执行单元测试和集成测试
3. **端到端测试**：使用AI生成端到端测试脚本，确保功能完整

### 6.3 文档与部署

1. **API文档**：完成API文档和开发指南
2. **部署测试**：部署测试和最终验证
3. **持续集成**：配置持续集成环境，确保代码变更后自动测试和部署

## 7. 结论

本改造方案将使LlamaIndex成为真正的前置场景判断和引导层，同时将Agno和HayStack作为其调用链的一部分。这一架构将显著提高系统集成度、简化业务逻辑、并为未来扩展奠定基础。

通过AI辅助开发，我们可以在短时间内完成复杂的代码开发和测试工作，提高开发效率和质量。

```
