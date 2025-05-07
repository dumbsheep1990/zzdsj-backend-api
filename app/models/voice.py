"""
语音功能相关数据模型
"""
from sqlalchemy import Column, Integer, String, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from typing import Optional

Base = declarative_base()


class VoiceSettingsDB(Base):
    """数据库中的语音设置表"""
    __tablename__ = "voice_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    enable_voice_input = Column(Boolean, default=False)
    enable_voice_output = Column(Boolean, default=False)
    stt_model_name = Column(String, default="whisper-base")
    tts_model_name = Column(String, default="edge-tts")
    language = Column(String, default="zh-CN")
    voice = Column(String, default="zh-CN-XiaoxiaoNeural")
    speed = Column(Float, default=1.0)
    audio_format = Column(String, default="mp3")
    sampling_rate = Column(Integer, default=16000)
