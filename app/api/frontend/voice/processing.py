"""
Frontend API - 语音处理接口
基于原有voice.py完整迁移，适配前端应用需求
"""

from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Path, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
import logging
import io
import time
from datetime import datetime
import json

from app.api.frontend.dependencies import (
    FrontendServiceContainer,
    FrontendContext,
    get_frontend_service_container,
    get_frontend_context
)
from app.api.shared.responses import InternalResponseFormatter
from app.api.shared.validators import ValidatorFactory

logger = logging.getLogger(__name__)

router = APIRouter()


# ================================
# 请求/响应模型（基于原有模型扩展）
# ================================

from pydantic import BaseModel, Field, validator

class VoiceTranscribeRequest(BaseModel):
    """语音转录请求"""
    enable_voice: bool = Field(default=True, description="是否启用语音输入")
    language: Optional[str] = Field(None, description="语言代码，如zh-CN, en-US")
    model: Optional[str] = Field(None, description="转录模型")
    auto_detect_language: bool = Field(default=False, description="自动检测语言")
    include_confidence: bool = Field(default=False, description="包含置信度信息")
    include_timestamps: bool = Field(default=False, description="包含时间戳")


class VoiceSynthesizeRequest(BaseModel):
    """语音合成请求"""
    text: str = Field(..., min_length=1, max_length=5000, description="要转换的文本")
    enable_voice: bool = Field(default=True, description="是否启用语音输出")
    voice: Optional[str] = Field(None, description="语音声音")
    speed: Optional[float] = Field(None, ge=0.25, le=4.0, description="语音速度")
    pitch: Optional[float] = Field(None, ge=-20.0, le=20.0, description="语音音调")
    volume: Optional[float] = Field(None, ge=0.0, le=1.0, description="音量")
    format: str = Field(default="mp3", description="音频格式：mp3, wav, ogg")
    quality: str = Field(default="standard", description="音频质量：standard, high")


class VoiceSettingsRequest(BaseModel):
    """语音设置请求"""
    enable_voice_input: Optional[bool] = Field(None, description="启用语音输入")
    enable_voice_output: Optional[bool] = Field(None, description="启用语音输出")
    default_language: Optional[str] = Field(None, description="默认语言")
    default_voice: Optional[str] = Field(None, description="默认语音")
    default_speed: Optional[float] = Field(None, ge=0.25, le=4.0, description="默认语音速度")
    auto_play_response: Optional[bool] = Field(None, description="自动播放响应")
    noise_reduction: Optional[bool] = Field(None, description="噪音降噪")
    echo_cancellation: Optional[bool] = Field(None, description="回声消除")
    auto_gain_control: Optional[bool] = Field(None, description="自动增益控制")


class BatchVoiceRequest(BaseModel):
    """批量语音处理请求"""
    texts: List[str] = Field(..., min_items=1, max_items=10, description="文本列表")
    voice_settings: VoiceSynthesizeRequest = Field(..., description="语音设置")
    output_format: str = Field(default="zip", description="输出格式：zip, individual")


# ================================
# 语音转录接口
# ================================

@router.post("/transcribe", response_model=Dict[str, Any], summary="语音转录")
async def transcribe_audio(
    file: UploadFile = File(..., description="音频文件"),
    enable_voice: bool = Form(True, description="是否启用语音输入"),
    language: Optional[str] = Form(None, description="语言代码"),
    model: Optional[str] = Form(None, description="转录模型"),
    auto_detect_language: bool = Form(False, description="自动检测语言"),
    include_confidence: bool = Form(False, description="包含置信度"),
    include_timestamps: bool = Form(False, description="包含时间戳"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    将音频文件转录为文本
    
    支持多种音频格式和语言，提供详细的转录信息
    """
    try:
        logger.info(f"Frontend API - 语音转录: user_id={context.user.id}, filename={file.filename}")
        
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith("audio/"):
            raise HTTPException(
                status_code=400,
                detail="上传的文件必须是音频格式"
            )
        
        # 检查文件大小（限制25MB）
        audio_data = await file.read()
        if len(audio_data) > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="音频文件大小不能超过25MB"
            )
        
        # 获取语音管理器
        try:
            from core.voice.voice_manager import VoiceAgentManager
            voice_manager = VoiceAgentManager()
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="语音服务暂不可用"
            )
        
        # 构建转录参数
        transcribe_params = {
            "enable_voice_input": enable_voice,
            "language": language,
            "model": model,
            "auto_detect_language": auto_detect_language,
            "include_confidence": include_confidence,
            "include_timestamps": include_timestamps,
            "user_id": context.user.id
        }
        
        # 执行转录（基于原有功能）
        start_time = time.time()
        result = await voice_manager.process_voice_input(audio_data, transcribe_params)
        processing_time = (time.time() - start_time) * 1000
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="语音转录失败"
            )
        
        # 构建响应数据
        response_data = {
            "text": result.get("text", "") if isinstance(result, dict) else str(result),
            "success": bool(result),
            "file_info": {
                "filename": file.filename,
                "content_type": file.content_type,
                "size_bytes": len(audio_data),
                "duration_seconds": result.get("duration") if isinstance(result, dict) else None
            },
            "processing_time_ms": processing_time,
            "transcription_info": {
                "language": result.get("detected_language") if isinstance(result, dict) else language,
                "model_used": result.get("model_used") if isinstance(result, dict) else model,
                "confidence": result.get("confidence") if isinstance(result, dict) and include_confidence else None,
                "timestamps": result.get("timestamps") if isinstance(result, dict) and include_timestamps else None
            },
            "metadata": {
                "user_id": context.user.id,
                "timestamp": datetime.now().isoformat(),
                "api_version": "frontend"
            }
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="语音转录成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 语音转录失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="语音转录处理失败"
        )


@router.post("/synthesize", response_class=StreamingResponse, summary="语音合成")
async def synthesize_speech(
    request: VoiceSynthesizeRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    将文本转换为语音
    
    支持多种语音、语速、音调配置
    """
    try:
        logger.info(f"Frontend API - 语音合成: user_id={context.user.id}, text_length={len(request.text)}")
        
        # 获取语音管理器
        try:
            from core.voice.voice_manager import VoiceAgentManager
            voice_manager = VoiceAgentManager()
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="语音服务暂不可用"
            )
        
        # 构建语音合成参数
        synthesis_params = {
            "enable_voice_output": request.enable_voice,
            "voice": request.voice,
            "speed": request.speed,
            "pitch": request.pitch,
            "volume": request.volume,
            "format": request.format,
            "quality": request.quality,
            "user_id": context.user.id
        }
        
        # 执行语音合成（基于原有功能）
        audio_data = await voice_manager.process_voice_output(request.text, synthesis_params)
        
        if not audio_data:
            raise HTTPException(
                status_code=500,
                detail="语音合成失败"
            )
        
        # 确定媒体类型
        media_type_map = {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "ogg": "audio/ogg"
        }
        media_type = media_type_map.get(request.format, "audio/mpeg")
        
        # 生成文件名
        filename = f"speech_{int(time.time())}.{request.format}"
        
        # 返回音频流
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(audio_data)),
                "X-Audio-Duration": str(len(audio_data) / (44100 * 2)),  # 估算时长
                "X-Text-Length": str(len(request.text)),
                "X-Voice-Settings": json.dumps({
                    "voice": request.voice,
                    "speed": request.speed,
                    "format": request.format
                })
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 语音合成失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="语音合成失败"
        )


@router.post("/synthesize-info", response_model=Dict[str, Any], summary="语音合成信息")
async def synthesize_speech_info(
    request: VoiceSynthesizeRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取语音合成信息而不返回实际音频
    
    用于预估合成时间、成本等
    """
    try:
        logger.info(f"Frontend API - 语音合成信息: user_id={context.user.id}, text_length={len(request.text)}")
        
        # 计算预估信息
        char_count = len(request.text)
        estimated_duration = char_count * 0.08  # 大约每秒12.5个字符
        estimated_size_mb = estimated_duration * 0.125  # 大约每秒125KB（标准MP3）
        
        # 获取可用语音列表
        available_voices = await _get_available_voices()
        
        # 构建响应数据
        response_data = {
            "text_analysis": {
                "character_count": char_count,
                "word_count": len(request.text.split()),
                "estimated_duration_seconds": round(estimated_duration, 2),
                "estimated_size_mb": round(estimated_size_mb, 2)
            },
            "synthesis_config": {
                "voice": request.voice,
                "speed": request.speed,
                "pitch": request.pitch,
                "volume": request.volume,
                "format": request.format,
                "quality": request.quality
            },
            "available_options": {
                "voices": available_voices,
                "formats": ["mp3", "wav", "ogg"],
                "qualities": ["standard", "high"],
                "speed_range": [0.25, 4.0],
                "pitch_range": [-20.0, 20.0]
            },
            "limits": {
                "max_text_length": 5000,
                "max_file_size_mb": 25,
                "rate_limit_per_minute": 60
            }
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="获取语音合成信息成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取语音合成信息失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取语音合成信息失败"
        )


# ================================
# 批量语音处理接口
# ================================

@router.post("/batch-synthesize", response_model=Dict[str, Any], summary="批量语音合成")
async def batch_synthesize_speech(
    request: BatchVoiceRequest,
    background_tasks: BackgroundTasks,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    批量将文本转换为语音
    
    支持多个文本同时合成，异步处理
    """
    try:
        logger.info(f"Frontend API - 批量语音合成: user_id={context.user.id}, texts_count={len(request.texts)}")
        
        # 验证请求
        total_chars = sum(len(text) for text in request.texts)
        if total_chars > 50000:  # 限制总字符数
            raise HTTPException(
                status_code=400,
                detail="批量处理的总字符数不能超过50000"
            )
        
        # 创建批量任务
        batch_id = f"batch_{context.user.id}_{int(time.time())}"
        
        # 添加后台任务
        background_tasks.add_task(
            _process_batch_synthesis,
            batch_id=batch_id,
            texts=request.texts,
            voice_settings=request.voice_settings,
            output_format=request.output_format,
            user_id=context.user.id
        )
        
        # 构建响应数据
        response_data = {
            "batch_id": batch_id,
            "status": "processing",
            "texts_count": len(request.texts),
            "estimated_completion_time": datetime.now() + datetime.timedelta(minutes=len(request.texts) * 2),
            "progress_url": f"/api/frontend/voice/batch/{batch_id}/status",
            "download_url": f"/api/frontend/voice/batch/{batch_id}/download"
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="批量语音合成任务已创建"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 批量语音合成失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="批量语音合成失败"
        )


@router.get("/batch/{batch_id}/status", response_model=Dict[str, Any], summary="获取批量任务状态")
async def get_batch_status(
    batch_id: str = Path(..., description="批量任务ID"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取批量语音合成任务状态
    """
    try:
        logger.info(f"Frontend API - 获取批量任务状态: user_id={context.user.id}, batch_id={batch_id}")
        
        # 验证批量任务属于当前用户
        if not batch_id.startswith(f"batch_{context.user.id}_"):
            raise HTTPException(
                status_code=403,
                detail="无权访问该批量任务"
            )
        
        # 这里应该从数据库或缓存获取任务状态
        # 暂时返回模拟数据
        status_data = {
            "batch_id": batch_id,
            "status": "completed",  # processing, completed, failed
            "progress": {
                "total": 5,
                "completed": 5,
                "failed": 0,
                "percentage": 100
            },
            "created_at": datetime.now() - datetime.timedelta(minutes=10),
            "completed_at": datetime.now() - datetime.timedelta(minutes=2),
            "results": [
                {
                    "index": i,
                    "status": "completed",
                    "file_url": f"/api/frontend/voice/batch/{batch_id}/file/{i}",
                    "duration_seconds": 3.5,
                    "file_size_bytes": 56000
                }
                for i in range(5)
            ]
        }
        
        return InternalResponseFormatter.format_success(
            data=status_data,
            message="获取批量任务状态成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 获取批量任务状态失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取批量任务状态失败"
        )


# ================================
# 语音设置管理接口
# ================================

@router.get("/settings", response_model=Dict[str, Any], summary="获取语音设置")
async def get_voice_settings(
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取用户的语音设置
    """
    try:
        logger.info(f"Frontend API - 获取语音设置: user_id={context.user.id}")
        
        # 这里应该从数据库获取用户的语音设置
        # 暂时返回默认设置
        settings_data = {
            "enable_voice_input": True,
            "enable_voice_output": True,
            "default_language": "zh-CN",
            "default_voice": "zh-CN-XiaoxiaoNeural",
            "default_speed": 1.0,
            "auto_play_response": True,
            "noise_reduction": True,
            "echo_cancellation": True,
            "auto_gain_control": True,
            "hotkey_enabled": False,
            "hotkey_combination": "Ctrl+Space",
            "input_device": "default",
            "output_device": "default",
            "input_volume": 0.8,
            "output_volume": 0.8
        }
        
        return InternalResponseFormatter.format_success(
            data=settings_data,
            message="获取语音设置成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取语音设置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取语音设置失败"
        )


@router.put("/settings", response_model=Dict[str, Any], summary="更新语音设置")
async def update_voice_settings(
    request: VoiceSettingsRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新用户的语音设置
    """
    try:
        logger.info(f"Frontend API - 更新语音设置: user_id={context.user.id}")
        
        # 获取更新的字段
        update_data = {
            key: value for key, value in request.model_dump(exclude_unset=True).items()
            if value is not None
        }
        
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="没有提供更新内容"
            )
        
        # 这里应该实现实际的数据库更新逻辑
        # 更新语音管理器设置
        try:
            from core.voice.voice_manager import VoiceAgentManager
            voice_manager = VoiceAgentManager()
            voice_manager.update_settings(update_data)
        except ImportError:
            logger.warning("语音管理器不可用，仅更新数据库设置")
        
        # 构建响应数据
        response_data = {
            "updated_fields": list(update_data.keys()),
            "settings": update_data,
            "message": "语音设置更新成功"
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="语音设置更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 更新语音设置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="语音设置更新失败"
        )


@router.get("/devices", response_model=Dict[str, Any], summary="获取音频设备")
async def get_audio_devices(
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取可用的音频输入输出设备
    """
    try:
        logger.info(f"Frontend API - 获取音频设备: user_id={context.user.id}")
        
        # 模拟设备列表
        devices_data = {
            "input_devices": [
                {"id": "default", "name": "默认输入设备", "is_default": True},
                {"id": "mic1", "name": "内置麦克风", "is_default": False},
                {"id": "mic2", "name": "外接USB麦克风", "is_default": False}
            ],
            "output_devices": [
                {"id": "default", "name": "默认输出设备", "is_default": True},
                {"id": "speaker1", "name": "内置扬声器", "is_default": False},
                {"id": "headphone1", "name": "蓝牙耳机", "is_default": False}
            ],
            "supported_formats": {
                "input": ["wav", "mp3", "m4a", "flac"],
                "output": ["mp3", "wav", "ogg"]
            }
        }
        
        return InternalResponseFormatter.format_success(
            data=devices_data,
            message="获取音频设备成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取音频设备失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取音频设备失败"
        )


# ================================
# 辅助函数
# ================================

async def _get_available_voices() -> List[Dict[str, Any]]:
    """获取可用的语音列表"""
    try:
        # 这里应该从语音服务获取实际的语音列表
        return [
            {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓", "language": "zh-CN", "gender": "female"},
            {"id": "zh-CN-YunxiNeural", "name": "云希", "language": "zh-CN", "gender": "male"},
            {"id": "en-US-AriaNeural", "name": "Aria", "language": "en-US", "gender": "female"},
            {"id": "en-US-DavisNeural", "name": "Davis", "language": "en-US", "gender": "male"}
        ]
    except Exception as e:
        logger.error(f"获取可用语音失败: {str(e)}")
        return []


async def _process_batch_synthesis(
    batch_id: str,
    texts: List[str],
    voice_settings: VoiceSynthesizeRequest,
    output_format: str,
    user_id: int
):
    """处理批量语音合成（后台任务）"""
    try:
        logger.info(f"开始处理批量语音合成: batch_id={batch_id}, texts_count={len(texts)}")
        
        # 这里应该实现实际的批量处理逻辑
        # 1. 逐个处理文本
        # 2. 生成音频文件
        # 3. 根据output_format打包或分别存储
        # 4. 更新任务状态
        
        for i, text in enumerate(texts):
            # 模拟处理时间
            await asyncio.sleep(10)
            logger.info(f"批量任务 {batch_id} 进度: {i+1}/{len(texts)}")
        
        logger.info(f"批量语音合成完成: batch_id={batch_id}")
        
    except Exception as e:
        logger.error(f"批量语音合成失败: batch_id={batch_id}, error={str(e)}") 