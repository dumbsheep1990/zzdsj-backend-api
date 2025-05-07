"""
语音服务管理器
负责协调语音转文本和文本转语音服务
"""

from typing import Optional, Dict, Any, Union
from app.schemas.voice import VoiceSettings, SpeechToTextResult
from app.core.voice.speech_to_text import SpeechToTextService
from app.core.voice.text_to_speech import TextToSpeechService
import logging

logger = logging.getLogger(__name__)


class VoiceAgentManager:
    """统一管理语音输入输出服务的管理器"""
    
    def __init__(self, settings: Optional[VoiceSettings] = None):
        """
        初始化语音服务管理器
        
        Args:
            settings: 语音设置，如果未提供则使用默认设置
        """
        self.settings = settings or VoiceSettings()
        self.stt_service = SpeechToTextService(self.settings)
        self.tts_service = TextToSpeechService(self.settings)
        logger.info(f"VoiceAgentManager initialized with STT model: {self.settings.stt_model_name} "
                    f"and TTS model: {self.settings.tts_model_name}")
    
    async def process_voice_input(self, audio_data: bytes, params: Dict[str, Any] = None) -> str:
        """
        处理语音输入，转换为文本
        
        Args:
            audio_data: 二进制音频数据
            params: 处理参数，可以覆盖默认设置
            
        Returns:
            转换后的文本
        """
        params = params or {}
        if not params.get("enable_voice_input", self.settings.enable_voice_input):
            logger.debug("Voice input disabled, skipping transcription")
            return ""
            
        try:
            result = await self.stt_service.transcribe(audio_data, params)
            logger.info(f"Voice input processed successfully, confidence: {result.confidence}")
            return result.text
        except Exception as e:
            logger.error(f"Error processing voice input: {e}")
            return ""
    
    async def process_voice_output(self, text: str, params: Dict[str, Any] = None) -> bytes:
        """
        处理文本输出，转换为语音
        
        Args:
            text: 要转换的文本
            params: 处理参数，可以覆盖默认设置
            
        Returns:
            生成的音频数据
        """
        params = params or {}
        if not params.get("enable_voice_output", self.settings.enable_voice_output):
            logger.debug("Voice output disabled, skipping synthesis")
            return b""
            
        try:
            audio_data = await self.tts_service.synthesize(text, params)
            logger.info(f"Voice output generated successfully, size: {len(audio_data)} bytes")
            return audio_data
        except Exception as e:
            logger.error(f"Error processing voice output: {e}")
            return b""
    
    def update_settings(self, settings: Dict[str, Any]) -> None:
        """
        更新语音服务设置
        
        Args:
            settings: 要更新的设置项
        """
        for key, value in settings.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
                logger.debug(f"Updated voice setting: {key} = {value}")
        
        # 更新子服务的设置
        self.stt_service.update_settings(self.settings)
        self.tts_service.update_settings(self.settings)
        logger.info("Voice settings updated successfully")
