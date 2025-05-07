"""
语音转文本服务
提供将语音数据转换为文本的功能
"""

from typing import Dict, Any, Optional
from app.schemas.voice import VoiceSettings, SpeechToTextResult
from app.frameworks.llamaindex.voice.stt_models import get_stt_model
import logging

logger = logging.getLogger(__name__)


class SpeechToTextService:
    """语音转文本服务"""
    
    def __init__(self, settings: VoiceSettings):
        """
        初始化语音转文本服务
        
        Args:
            settings: 语音设置
        """
        self.settings = settings
        self.model = get_stt_model(settings.stt_model_name)
        logger.info(f"SpeechToTextService initialized with model: {settings.stt_model_name}")
    
    async def transcribe(self, audio_data: bytes, params: Optional[Dict[str, Any]] = None) -> SpeechToTextResult:
        """
        将语音数据转换为文本
        
        Args:
            audio_data: 二进制音频数据
            params: 转换参数，可以覆盖默认设置
            
        Returns:
            转录结果
        """
        params = params or {}
        language = params.get("language", self.settings.language)
        
        logger.debug(f"Transcribing audio with language: {language}")
        
        try:
            # 调用模型进行语音识别
            result = await self.model.transcribe(
                audio_data,
                language=language,
                **{k: v for k, v in params.items() if k not in ['language']}
            )
            
            logger.info(f"Audio transcription completed successfully: {result.text[:30]}...")
            return result
        except Exception as e:
            logger.error(f"Error during audio transcription: {e}")
            return SpeechToTextResult(
                text="",
                confidence=0.0,
                metadata={"error": str(e)}
            )
    
    def update_settings(self, settings: VoiceSettings) -> None:
        """
        更新服务设置
        
        Args:
            settings: 新的语音设置
        """
        self.settings = settings
        
        # 如果模型名称变更，需要重新加载模型
        if self.settings.stt_model_name != self.model.name:
            logger.info(f"Changing STT model from {self.model.name} to {self.settings.stt_model_name}")
            self.model = get_stt_model(settings.stt_model_name)
