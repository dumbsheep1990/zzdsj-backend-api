# LightRAG集成与API接口文档

本文档提供了LightRAG知识图谱框架的集成方案，包括API接口清单、后端集成方案以及前端整合建议。

## 目录

- [1. LightRAG API接口清单](#1-lightrag-api接口清单)
- [2. 后端API集成方案](#2-后端api集成方案)
- [3. 前端集成方案](#3-前端集成方案)
- [4. Docker部署配置](#4-docker部署配置)
- [5. Nacos服务注册](#5-nacos服务注册)

## 1. LightRAG API接口清单

### 1.1 查询接口

| 接口路径 | 方法 | 功能描述 | 请求参数 | 响应 |
|---------|------|---------|---------|------|
| `/query` | POST | 查询知识图谱获取回答 | `query`: 查询文本<br>`mode`: 查询模式(hybrid/local/global等) | 返回完整回答及相关上下文 |
| `/query/stream` | POST | 流式响应查询结果 | 同上 | 流式返回回答内容 |

### 1.2 文档管理接口

| 接口路径 | 方法 | 功能描述 | 请求参数 | 响应 |
|---------|------|---------|---------|------|
| `/documents/text` | POST | 直接插入文本内容 | `text`: 文本内容<br>`description`: 可选描述 | 操作结果 |
| `/documents/file` | POST | 上传单个文件 | `file`: 文件<br>`description`: 可选描述 | 处理结果 |
| `/documents/batch` | POST | 批量上传多个文件 | `files`: 多个文件 | 批处理结果 |
| `/documents/scan` | POST | 扫描输入目录中的新文件 | 无 | 扫描结果 |
| `/documents` | DELETE | 清空所有文档 | 无 | 操作结果 |

### 1.3 图谱管理接口

| 接口路径 | 方法 | 功能描述 | 请求参数 | 响应 |
|---------|------|---------|---------|------|
| `/graphs` | GET | 获取所有知识图谱 | 无 | 图谱列表 |
| `/graphs/{graph_id}` | GET | 获取指定图谱信息 | `graph_id`: 图谱ID | 图谱详情 |
| `/graphs/{graph_id}` | DELETE | 删除指定图谱 | `graph_id`: 图谱ID | 操作结果 |
| `/graphs/{graph_id}/stats` | GET | 获取图谱统计信息 | `graph_id`: 图谱ID | 统计信息 |
| `/graphs/visualize/{graph_id}` | GET | 获取图谱可视化数据 | `graph_id`: 图谱ID | 可视化数据 |

### 1.4 系统管理接口

| 接口路径 | 方法 | 功能描述 | 请求参数 | 响应 |
|---------|------|---------|---------|------|
| `/health` | GET | 检查服务健康状态 | 无 | 系统状态 |
| `/config` | GET | 获取系统配置 | 无 | 配置信息 |

## 2. 后端API集成方案

我们已经实现了LightRAG的核心框架功能，现在需要创建API层与前端进行交互。以下是实现方案：

### 2.1 创建API路由模块

在`app/api`目录下创建新的`lightrag.py`文件：

```python
"""
LightRAG API 模块
提供前端UI所需的API接口
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any, Union

from app.frameworks.lightrag import get_client, get_graph_manager, get_document_processor
from app.frameworks.lightrag.config import lightrag_config
from app.config import settings

router = APIRouter(prefix="/api/lightrag", tags=["lightrag"])

# 系统状态与配置接口
@router.get("/health")
async def health_check():
    """检查LightRAG服务健康状态"""
    client = get_client()
    return {
        "status": "ok" if client.is_available() else "unavailable",
        "version": "0.1.0",  # 版本号
        "config": {
            "enabled": settings.LIGHTRAG_ENABLED,
            "storage_type": settings.LIGHTRAG_GRAPH_DB_TYPE
        }
    }

@router.get("/config")
async def get_config():
    """获取LightRAG配置信息"""
    client = get_client()
    return client.get_config()

# 图谱管理接口
@router.get("/graphs")
async def list_graphs():
    """获取所有知识图谱列表"""
    client = get_client()
    return {"graphs": client.list_graphs()}

@router.get("/graphs/{graph_id}")
async def get_graph(graph_id: str):
    """获取指定图谱信息"""
    graph_manager = get_graph_manager()
    graph = graph_manager.get_graph(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail=f"图谱 {graph_id} 不存在")
    return {"graph_id": graph_id, "exists": True}

@router.get("/graphs/{graph_id}/stats")
async def get_graph_stats(graph_id: str):
    """获取图谱统计信息"""
    client = get_client()
    stats = client.get_graph_stats(graph_id)
    if not stats:
        raise HTTPException(status_code=404, detail=f"图谱 {graph_id} 不存在")
    return stats

@router.delete("/graphs/{graph_id}")
async def delete_graph(graph_id: str):
    """删除指定图谱"""
    client = get_client()
    success = client.delete_graph(graph_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"删除图谱 {graph_id} 失败")
    return {"success": True}

# 文档处理接口
@router.post("/documents/text")
async def add_text(
    text: str,
    description: Optional[str] = None,
    graph_id: Optional[str] = None,
    use_semantic_chunking: Optional[bool] = None,
    use_knowledge_graph: Optional[bool] = None
):
    """添加文本内容到图谱"""
    client = get_client()
    
    # 如果未指定图谱ID，使用默认图谱
    if not graph_id:
        graph_id = "default"
        # 确保默认图谱存在
        graph_manager = get_graph_manager()
        if not graph_manager.get_graph(graph_id):
            graph_manager.create_graph(graph_id)
    
    # 构建文档对象
    document = {
        "content": text,
        "metadata": {
            "description": description or "通过API添加的文本"
        }
    }
    
    # 处理文档
    task_id = client.process_documents(
        documents=[document],
        graph_id=graph_id,
        use_semantic_chunking=use_semantic_chunking,
        use_knowledge_graph=use_knowledge_graph
    )
    
    return {"task_id": task_id, "graph_id": graph_id}

@router.post("/documents/file")
async def upload_file(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    graph_id: Optional[str] = Form(None),
    use_semantic_chunking: Optional[bool] = Form(None),
    use_knowledge_graph: Optional[bool] = Form(None)
):
    """上传单个文件到图谱"""
    import tempfile
    import os
    
    client = get_client()
    
    # 如果未指定图谱ID，使用默认图谱
    if not graph_id:
        graph_id = "default"
        # 确保默认图谱存在
        graph_manager = get_graph_manager()
        if not graph_manager.get_graph(graph_id):
            graph_manager.create_graph(graph_id)
    
    # 保存上传的文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp:
        content = await file.read()
        temp.write(content)
        temp_path = temp.name
    
    try:
        # 处理文件
        from app.frameworks.lightrag.document_loader import load_document
        documents = load_document(temp_path, metadata={"filename": file.filename, "description": description})
        
        if not documents:
            raise HTTPException(status_code=400, detail="无法处理上传的文件")
        
        # 处理文档
        task_id = client.process_documents(
            documents=documents,
            graph_id=graph_id,
            use_semantic_chunking=use_semantic_chunking,
            use_knowledge_graph=use_knowledge_graph
        )
        
        return {"task_id": task_id, "graph_id": graph_id, "filename": file.filename}
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)

@router.get("/documents/tasks/{task_id}")
async def get_task_status(task_id: str):
    """获取文档处理任务状态"""
    client = get_client()
    status = client.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return status

# 查询接口
@router.post("/query")
async def query(
    query: str,
    graph_id: Optional[str] = None,
    mode: str = "hybrid",
    top_k: int = 5
):
    """查询知识图谱"""
    client = get_client()
    
    # 如果未指定图谱ID，使用默认图谱或查询所有图谱
    if not graph_id:
        graph_id = "default"
    
    # 根据模式设置是否使用图谱关系
    use_graph_relations = mode in ["hybrid", "global"]
    
    # 执行查询
    result = client.query(
        query_text=query,
        graph_id=graph_id,
        top_k=top_k,
        use_graph_relations=use_graph_relations
    )
    
    return result

@router.post("/query/stream")
async def query_stream(
    query: str,
    graph_id: Optional[str] = None,
    mode: str = "hybrid",
    top_k: int = 5
):
    """流式查询知识图谱"""
    # 这里需要实现流式响应的逻辑
    async def generate_stream():
        client = get_client()
        
        # 实际实现中需要使用流式查询方法
        result = client.query(
            query_text=query,
            graph_id=graph_id or "default",
            top_k=top_k,
            use_graph_relations=mode in ["hybrid", "global"]
        )
        
        # 简化的流式响应模拟
        import json
        import asyncio
        
        # 发送源文档
        if "sources" in result:
            yield f"data: {json.dumps({'type': 'sources', 'sources': result['sources']})}\n\n"
            await asyncio.sleep(0.1)
        
        # 模拟流式发送答案
        answer = result.get("answer", "")
        chunk_size = 20
        for i in range(0, len(answer), chunk_size):
            chunk = answer[i:i+chunk_size]
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            await asyncio.sleep(0.05)
        
        # 发送完成信号
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(generate_stream(), media_type="text/event-stream")

# 可视化接口
@router.get("/graphs/{graph_id}/visualize")
async def visualize_graph(
    graph_id: str,
    query: Optional[str] = None,
    limit: int = 100
):
    """获取图谱可视化数据"""
    graph_manager = get_graph_manager()
    graph = graph_manager.get_graph(graph_id)
    
    if not graph:
        raise HTTPException(status_code=404, detail=f"图谱 {graph_id} 不存在")
    
    # 这里需要实现获取可视化数据的逻辑
    # 示例返回格式
    return {
        "nodes": [
            {"id": "node1", "label": "概念1", "type": "entity", "size": 30},
            {"id": "node2", "label": "概念2", "type": "entity", "size": 25},
            # 更多节点...
        ],
        "links": [
            {"source": "node1", "target": "node2", "label": "关联", "weight": 0.8},
            # 更多连接...
        ]
    }

# 将路由注册到主应用
def include_router(app):
    """注册LightRAG API路由"""
    app.include_router(router)
```

### 2.2 实现文档加载器模块

创建`app/frameworks/lightrag/document_loader.py`文件：

```python
"""
LightRAG文档加载器
提供从不同来源加载文档的功能
"""

from typing import List, Dict, Any, Optional, Union
import os
import tempfile
import logging
from pathlib import Path

# LlamaIndex文档处理
from llama_index.core import Document

logger = logging.getLogger(__name__)

# 支持的文件类型
SUPPORTED_FILE_TYPES = {
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.pdf': 'application/pdf',
    '.html': 'text/html',
    '.htm': 'text/html',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.csv': 'text/csv',
    '.json': 'application/json',
}

def load_document(file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    加载文档文件，返回文档列表
    
    参数:
        file_path: 文件路径
        metadata: 可选的元数据
        
    返回:
        文档列表，每个文档是字典格式
    """
    try:
        # 确保文件存在
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return []
        
        # 获取文件扩展名
        file_ext = os.path.splitext(file_path.lower())[1]
        
        # 检查文件类型是否支持
        if file_ext not in SUPPORTED_FILE_TYPES:
            logger.warning(f"不支持的文件类型: {file_ext}")
            return []
        
        # 根据文件类型选择适当的加载器
        if file_ext in ['.txt', '.md']:
            from llama_index.readers.file import SimpleDirectoryReader
            loader = SimpleDirectoryReader(input_files=[file_path])
            docs = loader.load_data()
        elif file_ext == '.pdf':
            from llama_index.readers.file import PDFReader
            loader = PDFReader()
            docs = loader.load_data(file=file_path)
        elif file_ext in ['.html', '.htm']:
            from llama_index.readers.web import SimpleWebPageReader
            # 转换为文件URL
            file_url = f"file://{os.path.abspath(file_path)}"
            loader = SimpleWebPageReader()
            docs = loader.load_data(urls=[file_url])
        elif file_ext in ['.doc', '.docx']:
            from llama_index.readers.file import DocxReader
            loader = DocxReader()
            docs = loader.load_data(file=file_path)
        elif file_ext == '.csv':
            from llama_index.readers.file import CSVReader
            loader = CSVReader()
            docs = loader.load_data(file=file_path)
        elif file_ext == '.json':
            from llama_index.readers.json import JSONReader
            loader = JSONReader()
            docs = loader.load_data(file=file_path)
        else:
            logger.error(f"不支持的文件类型: {file_ext}")
            return []
        
        # 转换为标准格式并添加元数据
        result = []
        for doc in docs:
            doc_dict = {
                "content": doc.text,
                "metadata": {
                    "source": file_path,
                    "file_type": SUPPORTED_FILE_TYPES.get(file_ext, "unknown")
                }
            }
            
            # 添加额外元数据
            if metadata:
                doc_dict["metadata"].update(metadata)
                
            # 合并文档的原始元数据
            if hasattr(doc, "metadata") and doc.metadata:
                doc_dict["metadata"].update(doc.metadata)
                
            result.append(doc_dict)
            
        return result
    except Exception as e:
        logger.error(f"加载文档失败: {str(e)}")
        return []
```

## 3. 前端集成方案

对于将LightRAG WebUI深度集成到现有前端系统，我们提供以下实现方式：

### 3.1 接口适配层

创建一个接口适配层，用于连接我们自定义的API接口：

```typescript
// src/api/lightrag.ts

import axios from 'axios';
import { API_BASE_URL } from '@/config';

const API_PREFIX = `${API_BASE_URL}/api/lightrag`;

// 知识图谱管理
export const lightragApi = {
  // 系统状态
  getHealth: () => axios.get(`${API_PREFIX}/health`),
  getConfig: () => axios.get(`${API_PREFIX}/config`),
  
  // 图谱管理
  listGraphs: () => axios.get(`${API_PREFIX}/graphs`),
  getGraphStats: (graphId: string) => axios.get(`${API_PREFIX}/graphs/${graphId}/stats`),
  deleteGraph: (graphId: string) => axios.delete(`${API_PREFIX}/graphs/${graphId}`),
  
  // 文档管理
  uploadText: (params: {
    text: string,
    description?: string,
    graph_id?: string,
    use_semantic_chunking?: boolean,
    use_knowledge_graph?: boolean
  }) => axios.post(`${API_PREFIX}/documents/text`, params),
  
  uploadFile: (file: File, params: {
    description?: string,
    graph_id?: string,
    use_semantic_chunking?: boolean,
    use_knowledge_graph?: boolean
  }) => {
    const formData = new FormData();
    formData.append('file', file);
    
    if (params.description) formData.append('description', params.description);
    if (params.graph_id) formData.append('graph_id', params.graph_id);
    if (params.use_semantic_chunking !== undefined) formData.append('use_semantic_chunking', String(params.use_semantic_chunking));
    if (params.use_knowledge_graph !== undefined) formData.append('use_knowledge_graph', String(params.use_knowledge_graph));
    
    return axios.post(`${API_PREFIX}/documents/file`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  
  getTaskStatus: (taskId: string) => axios.get(`${API_PREFIX}/documents/tasks/${taskId}`),
  
  // 查询接口
  query: (params: {
    query: string,
    graph_id?: string,
    mode?: string,
    top_k?: number
  }) => axios.post(`${API_PREFIX}/query`, params),
  
  // 流式查询
  queryStream: (params: {
    query: string,
    graph_id?: string,
    mode?: string,
    top_k?: number
  }, onChunk: (chunk: any) => void, onComplete: () => void) => {
    const url = new URL(`${API_PREFIX}/query/stream`);
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.append(key, String(value));
      }
    });
    
    const eventSource = new EventSource(url.toString());
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'done') {
        eventSource.close();
        onComplete();
      } else {
        onChunk(data);
      }
    };
    
    eventSource.onerror = () => {
      eventSource.close();
      onComplete();
    };
    
    return {
      close: () => eventSource.close()
    };
  },
  
  // 图谱可视化
  visualizeGraph: (graphId: string, params?: {
    query?: string,
    limit?: number
  }) => {
    const url = new URL(`${API_PREFIX}/graphs/${graphId}/visualize`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          url.searchParams.append(key, String(value));
        }
      });
    }
    return axios.get(url.toString());
  }
};
```

### 3.2 React组件示例

对于React前端项目，可以创建以下组件来集成LightRAG功能：

1. 图谱查询组件 (`GraphQuery`)
2. 文档上传组件 (`DocumentUpload`)
3. 图谱可视化组件 (`GraphVisualization`)
4. 图谱管理组件 (`GraphManager`)

组件代码示例请参考完整项目代码。

## 4. Docker部署配置

在`docker-compose.yml`文件中添加LightRAG服务：

```yaml
# LightRAG服务
lightrag-api:
  image: hkuds/lightrag:latest
  container_name: lightrag-api
  restart: unless-stopped
  environment:
    - LIGHTRAG_ENABLED=true
    - LIGHTRAG_GRAPH_DB_TYPE=${LIGHTRAG_GRAPH_DB_TYPE:-file}
    - LIGHTRAG_PG_HOST=${LIGHTRAG_PG_HOST:-postgres}
    - LIGHTRAG_PG_PORT=${LIGHTRAG_PG_PORT:-5432}
    - LIGHTRAG_PG_USER=${LIGHTRAG_PG_USER:-postgres}
    - LIGHTRAG_PG_PASSWORD=${LIGHTRAG_PG_PASSWORD:-password}
    - LIGHTRAG_PG_DB=${LIGHTRAG_PG_DB:-lightrag}
    - LIGHTRAG_REDIS_HOST=${LIGHTRAG_REDIS_HOST:-redis}
    - LIGHTRAG_REDIS_PORT=${LIGHTRAG_REDIS_PORT:-6379}
    - LIGHTRAG_REDIS_DB=${LIGHTRAG_REDIS_DB:-1}
    - LIGHTRAG_REDIS_PASSWORD=${LIGHTRAG_REDIS_PASSWORD:-}
  volumes:
    - ./data/lightrag:/app/data/lightrag
  ports:
    - "9621:9621"
  depends_on:
    - postgres
    - redis
  networks:
    - app-network
```

## 5. Nacos服务注册

在`app/utils/service_discovery.py`中添加LightRAG服务注册：

```python
def register_lightrag_service():
    """注册LightRAG服务到Nacos"""
    if settings.LIGHTRAG_ENABLED:
        from app.utils.service_discovery import register_service
        
        # 注册LightRAG API服务
        register_service(
            service_name="lightrag-api",
            ip="lightrag-api",  # Docker服务名称
            port=9621,
            namespace=settings.NACOS_NAMESPACE,
            group_name=settings.NACOS_GROUP,
            metadata={
                "type": "api",
                "description": "LightRAG知识图谱API服务"
            }
        )
        
        logger.info("LightRAG服务已注册到Nacos")
```

在主应用启动时添加服务注册调用：

```python
# 在app/main.py中添加
@app.on_event("startup")
async def startup_event():
    # 现有代码...
    
    # 注册LightRAG服务
    if settings.LIGHTRAG_ENABLED:
        from app.utils.service_discovery import register_lightrag_service
        register_lightrag_service()
```

---

## 后续工作

1. 实现WebUI的定制化，根据项目需求调整界面风格和功能
2. 完善图谱可视化接口，提供更强大的可视化功能
3. 为流式查询优化实现高性能的后端处理逻辑
4. 添加更多文档类型支持，例如PPT、Excel等
5. 实现知识图谱增量更新和管理功能

如需更多信息，请参考[LightRAG官方文档](https://github.com/HKUDS/LightRAG)。

## 附录

- [1] LightRAG官方文档: https://github.com/HKUDS/LightRAG
- [2] FastAPI文档: https://fastapi.tiangolo.com/
- [3] LlamaIndex文档: https://docs.llamaindex.ai/
