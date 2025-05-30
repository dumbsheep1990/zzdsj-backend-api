"""
语音功能API接口: 提供语音输入输出及设置管理的接口
[迁移桥接] - 该文件已迁移至 app/api/frontend/voice/processing.py
"""

from fastapi import APIRouter
import logging

# 导入新的API模块
from app.api.frontend.voice.processing import router as new_router

# 创建路由
router = APIRouter()
logger = logging.getLogger(__name__)

# 记录迁移警告
logger.warning("使用已弃用的app/api/voice.py，该文件已迁移至app/api/frontend/voice/processing.py")

# 将所有请求转发到新的路由处理器
for route in new_router.routes:
    router.routes.append(route)


def get_voice_manager():
    """依赖注入：获取语音管理器实例"""
    return VoiceAgentManager()


@router.post("/transcribe", response_model=VoiceResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    enable_voice: bool = Query(True, description="是否启用语音输入"),
    language: Optional[str] = Query(None, description="语言代码"),
    voice_manager: VoiceAgentManager = Depends(get_voice_manager),
):
    """
    将上传的音频文件转换为文本
    
    - **file**: 上传的音频文件
    - **enable_voice**: 是否启用语音输入
    - **language**: 语言代码(可选)
    
    返回转录后的文本内容，用于在前端显示
    """
    if not file.content_type.startswith("audio/"):
        logger.warning(f"Invalid content type: {file.content_type}")
        raise HTTPException(status_code=400, detail="上传的文件必须是音频格式")
    
    logger.info(f"Processing audio transcription request: {file.filename}")
    audio_data = await file.read()
    
    params = {
        "enable_voice_input": enable_voice,
        "language": language,
    }
    
    text = await voice_manager.process_voice_input(audio_data, params)
    success = bool(text)
    
    if not success:
        logger.warning("Audio transcription failed or returned empty result")
    else:
        logger.info(f"Audio transcription successful: {text[:30]}...")
    
    # 返回转录结果和成功状态，供前端显示
    return {"text": text, "success": success, "metadata": {"timestamp": time.time()}}


@router.post("/synthesize")
async def synthesize_speech(
    text: str = Body(..., embed=True),
    enable_voice: bool = Query(True, description="是否启用语音输出"),
    voice: Optional[str] = Query(None, description="语音声音"),
    speed: Optional[float] = Query(None, description="语音速度"),
    voice_manager: VoiceAgentManager = Depends(get_voice_manager),
):
    """
    将文本转换为语音
    
    - **text**: 要转换为语音的文本
    - **enable_voice**: 是否启用语音输出
    - **voice**: 语音声音(可选)
    - **speed**: 语音速度(可选)
    
    返回音频流
    """
    if not text:
        logger.warning("Empty text provided for speech synthesis")
        raise HTTPException(status_code=400, detail="文本不能为空")
    
    logger.info("Processing speech synthesis request")
    
    params = {
        "enable_voice_output": enable_voice,
        "voice": voice,
        "speed": speed,
    }
    
    audio_data = await voice_manager.process_voice_output(text, params)
    
    if not audio_data:
        logger.warning("Speech synthesis failed or returned empty result")
        raise HTTPException(status_code=500, detail="语音合成失败")
    
    logger.info(f"Speech synthesis successful, audio size: {len(audio_data)} bytes")
    
    return StreamingResponse(
        io.BytesIO(audio_data),
        media_type="audio/mp3",
        headers={"Content-Disposition": "attachment; filename=speech.mp3"}
    )


@router.put("/settings")
async def update_voice_settings(
    settings: VoiceSettingsUpdate,
    db: Session = Depends(get_db),
    voice_manager: VoiceAgentManager = Depends(get_voice_manager),
    user_id: str = Query("default", description="用户ID"),
):
    """
    更新语音设置
    
    - **settings**: 要更新的语音设置
    - **user_id**: 用户ID
    
    返回更新后的设置
    """
    logger.info(f"Updating voice settings for user: {user_id}")
    
    # 更新内存中的设置
    voice_manager.update_settings(settings.dict(exclude_unset=True))
    
    # 更新数据库中的设置
    voice_settings = db.query(VoiceSettingsDB).filter(VoiceSettingsDB.user_id == user_id).first()
    
    if voice_settings:
        # 更新现有设置
        for key, value in settings.dict(exclude_unset=True).items():
            if hasattr(voice_settings, key):
                setattr(voice_settings, key, value)
    else:
        # 创建新设置
        voice_settings = VoiceSettingsDB(
            user_id=user_id,
            **settings.dict(exclude_unset=True)
        )
        db.add(voice_settings)
    
    try:
        db.commit()
        logger.info(f"Voice settings updated in database for user: {user_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating voice settings in database: {e}")
        raise HTTPException(status_code=500, detail=f"更新设置失败: {str(e)}")
    
    return {"message": "语音设置已更新", "settings": settings}


@router.get("/settings", response_model=VoiceSettings)
async def get_voice_settings(
    db: Session = Depends(get_db),
    user_id: str = Query("default", description="用户ID"),
):
    """
    获取当前语音设置
    
    - **user_id**: 用户ID
    
    返回当前的语音设置
    """
    logger.info(f"Getting voice settings for user: {user_id}")
    
    # 从数据库中获取设置
    voice_settings = db.query(VoiceSettingsDB).filter(VoiceSettingsDB.user_id == user_id).first()
    
    if voice_settings:
        logger.info(f"Found voice settings for user: {user_id}")
        return VoiceSettings(
            enable_voice_input=voice_settings.enable_voice_input,
            enable_voice_output=voice_settings.enable_voice_output,
            stt_model_name=voice_settings.stt_model_name,
            tts_model_name=voice_settings.tts_model_name,
            language=voice_settings.language,
            voice=voice_settings.voice,
            speed=voice_settings.speed,
            audio_format=voice_settings.audio_format,
            sampling_rate=voice_settings.sampling_rate
        )
    
    # 如果没有找到，返回默认设置
    logger.info(f"No voice settings found for user: {user_id}, returning defaults")
    return VoiceSettings()
