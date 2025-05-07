"""
语音功能相关的Pydantic模式定义
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class VoiceSettings(BaseModel):
    """语音设置配置模型"""
    enable_voice_input: bool = Field(default=False, description="是否启用语音输入")
    enable_voice_output: bool = Field(default=False, description="是否启用语音输出")
    stt_model_name: str = Field(default="whisper-base", description="语音转文本模型名称")
    tts_model_name: str = Field(default="edge-tts", description="文本转语音模型名称")
    language: str = Field(default="zh-CN", description="语言代码")
    voice: str = Field(default="zh-CN-XiaoxiaoNeural", description="声音名称")
    speed: float = Field(default=1.0, description="语音速度")
    audio_format: str = Field(default="mp3", description="音频格式")
    sampling_rate: int = Field(default=16000, description="采样率")


class VoiceSettingsUpdate(BaseModel):
    """语音设置更新模型"""
    enable_voice_input: Optional[bool] = None
    enable_voice_output: Optional[bool] = None
    stt_model_name: Optional[str] = None
    tts_model_name: Optional[str] = None
    language: Optional[str] = None
    voice: Optional[str] = None
    speed: Optional[float] = None
    audio_format: Optional[str] = None
    sampling_rate: Optional[int] = None


class VoiceResponse(BaseModel):
    """语音处理响应模型"""
    text: str = ""
    success: bool = True
    metadata: Optional[Dict[str, Any]] = None


class SpeechToTextResult(BaseModel):
    """语音转文本结果模型"""
    text: str
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = None
