from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
import json

from app.services_new.lightrag import LightRAGService
from app.schemas_new.knowledge_base import *

router = APIRouter()


def get_lightrag_service() -> LightRAGService:
    return LightRAGService()


@router.post("/workdirs", response_model=BaseResponse)
async def create_workdir(
        name: str,
        description: Optional[str] = None,
        service: LightRAGService = Depends(get_lightrag_service),
        current_user=Depends(get_current_user)
):
    """创建LightRAG工作目录"""
    try:
        workdir = await service.create_workdir(name, description, current_user.id)
        return success_response(data=workdir, message="工作目录创建成功")
    except Exception as e:
        logger.error(f"创建工作目录失败: {e}")
        return error_response(error=str(e))


@router.get("/graph/{kb_id}", response_model=BaseResponse)
async def get_knowledge_graph(
        kb_id: str,
        service: LightRAGService = Depends(get_lightrag_service),
        current_user=Depends(get_current_user)
):
    """获取知识图谱数据"""
    try:
        graph_data = await service.get_graph_data(kb_id)
        return success_response(data=graph_data)
    except Exception as e:
        logger.error(f"获取图谱数据失败: {e}")
        return error_response(error="获取失败")


@router.post("/query/stream")
async def query_stream(
        request: QueryRequest,
        service: LightRAGService = Depends(get_lightrag_service),
        current_user=Depends(get_current_user)
):
    """流式查询接口"""

    async def generate():
        try:
            async for chunk in service.query_stream(request):
                yield json.dumps(chunk) + "\n"
        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")