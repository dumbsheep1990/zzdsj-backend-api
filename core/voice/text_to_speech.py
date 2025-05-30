"""
文本转语音服务
提供将文本转换为语音数据的功能
"""

from typing import Dict, Any, Optional
from app.schemas.voice import VoiceSettings
from app.frameworks.llamaindex.voice.tts_models import get_tts_model
import logging

logger = logging.getLogger(__name__)


class TextToSpeechService:
    """文本转语音服务"""
    
    def __init__(self, settings: VoiceSettings):
        """
        初始化文本转语音服务
        
        Args:
            settings: 语音设置
        """
        self.settings = settings
        self.model = get_tts_model(settings.tts_model_name)
        logger.info(f"TextToSpeechService initialized with model: {settings.tts_model_name}")
    
    async def synthesize(self, text: str, params: Optional[Dict[str, Any]] = None) -> bytes:
        """
        将文本转换为语音数据
        
        Args:
            text: 要转换的文本
            params: 转换参数，可以覆盖默认设置
            
        Returns:
            生成的音频数据
        """
        params = params or {}
        voice = params.get("voice", self.settings.voice)
        speed = params.get("speed", self.settings.speed)
        
        logger.debug(f"Synthesizing speech with voice: {voice}, speed: {speed}")
        
        try:
            # 调用模型进行语音合成
            audio_data = await self.model.synthesize(
                text,
                voice=voice,
                speed=speed,
                **{k: v for k, v in params.items() if k not in ['voice', 'speed']}
            )
            
            logger.info(f"Speech synthesis completed successfully, generated {len(audio_data)} bytes")
            return audio_data
        except Exception as e:
            logger.error(f"Error during speech synthesis: {e}")
            return b""
    
    def update_settings(self, settings: VoiceSettings) -> None:
        """
        更新服务设置
        
        Args:
            settings: 新的语音设置
        """
        self.settings = settings
        
        # 如果模型名称变更，需要重新加载模型
        if self.settings.tts_model_name != self.model.name:
            logger.info(f"Changing TTS model from {self.model.name} to {self.settings.tts_model_name}")
            self.model = get_tts_model(settings.tts_model_name)
