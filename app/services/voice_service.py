"""
语音服务模块
处理语音转文本和文本转语音相关的业务逻辑
"""

from app.utils.service_decorators import register_service

from typing import List, Dict, Any, Optional, BinaryIO
from fastapi import Depends, HTTPException, status, UploadFile
from sqlalchemy.orm import Session
import uuid
import os
import tempfile
from datetime import datetime

from app.utils.database import get_db
from app.models.voice import VoiceConfig, VoiceTask
from app.repositories.voice_repository import VoiceConfigRepository, VoiceTaskRepository
from app.services.resource_permission_service import ResourcePermissionService
from app.services.model_provider_service import ModelProviderService

@register_service(service_type="voice", priority="medium", description="语音识别和合成服务")
class VoiceService:
    """语音服务类"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 permission_service: ResourcePermissionService = Depends(),
                 model_provider_service: ModelProviderService = Depends()):
        """初始化语音服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
            model_provider_service: 模型提供商服务
        """
        self.db = db
        self.config_repository = VoiceConfigRepository()
        self.task_repository = VoiceTaskRepository()
        self.permission_service = permission_service
        self.model_provider_service = model_provider_service
        self.temp_dir = tempfile.gettempdir()
    
    async def create_voice_config(self, config_data: Dict[str, Any], user_id: str) -> VoiceConfig:
        """创建语音配置
        
        Args:
            config_data: 语音配置数据
            user_id: 用户ID
            
        Returns:
            VoiceConfig: 创建的语音配置实例
            
        Raises:
            HTTPException: 如果配置名称已存在或没有权限
        """
        # 检查配置名称是否已存在
        existing_config = await self.config_repository.get_by_name(
            config_data.get("name"), self.db
        )
        if existing_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"语音配置名称 '{config_data.get('name')}' 已存在"
            )
        
        # 检查模型提供商
        if provider_id := config_data.get("provider_id"):
            provider = await self.model_provider_service.get_model_provider(provider_id, user_id)
            if not provider:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="指定的模型提供商不存在或没有访问权限"
                )
        
        # 创建语音配置
        config = await self.config_repository.create(config_data, self.db)
        
        # 为创建者分配所有者权限
        await self.permission_service.ensure_owner_permission(
            "voice_config", config.id, user_id
        )
        
        return config
    
    async def get_voice_config(self, config_id: str, user_id: str) -> Optional[VoiceConfig]:
        """获取语音配置
        
        Args:
            config_id: 语音配置ID
            user_id: 用户ID
            
        Returns:
            Optional[VoiceConfig]: 获取的语音配置实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取语音配置
        config = await self.config_repository.get_by_id(config_id, self.db)
        if not config:
            return None
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "voice_config", config_id, user_id, "read"
        ) or config.is_public or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此语音配置"
            )
        
        return config
    
    async def list_voice_configs(self, user_id: str, skip: int = 0, limit: int = 100) -> List[VoiceConfig]:
        """获取语音配置列表
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[VoiceConfig]: 语音配置列表
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        
        # 管理员可以查看所有配置
        if is_admin:
            return await self.config_repository.list_all(skip, limit, self.db)
        
        # 获取用户有权限的语音配置
        user_permissions = await self.permission_service.list_user_permissions(user_id)
        config_permissions = [p for p in user_permissions if p.resource_type == "voice_config"]
        
        # 获取有权限的配置ID
        config_ids = [p.resource_id for p in config_permissions]
        
        # 获取公共配置
        public_configs = await self.config_repository.list_public_configs(self.db)
        
        # 合并结果
        result = []
        
        # 添加有权限的配置
        for config_id in config_ids:
            config = await self.config_repository.get_by_id(config_id, self.db)
            if config and config not in result:
                result.append(config)
        
        # 添加公共配置
        for config in public_configs:
            if config not in result:
                result.append(config)
        
        return result
    
    async def update_voice_config(self, config_id: str, update_data: Dict[str, Any], user_id: str) -> Optional[VoiceConfig]:
        """更新语音配置
        
        Args:
            config_id: 语音配置ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Optional[VoiceConfig]: 更新后的语音配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或语音配置不存在
        """
        # 获取语音配置
        config = await self.config_repository.get_by_id(config_id, self.db)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="语音配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "voice_config", config_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此语音配置"
            )
        
        # 检查模型提供商
        if provider_id := update_data.get("provider_id"):
            provider = await self.model_provider_service.get_model_provider(provider_id, user_id)
            if not provider:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="指定的模型提供商不存在或没有访问权限"
                )
        
        # 更新语音配置
        return await self.config_repository.update(config_id, update_data, self.db)
    
    async def delete_voice_config(self, config_id: str, user_id: str) -> bool:
        """删除语音配置
        
        Args:
            config_id: 语音配置ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功删除
            
        Raises:
            HTTPException: 如果没有权限或语音配置不存在
        """
        # 获取语音配置
        config = await self.config_repository.get_by_id(config_id, self.db)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="语音配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "voice_config", config_id, user_id, "admin"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此语音配置"
            )
        
        # 删除语音配置
        return await self.config_repository.delete(config_id, self.db)
    
    async def speech_to_text(self, audio_file: UploadFile, config_id: str, user_id: str) -> Dict[str, Any]:
        """将语音转换为文本
        
        Args:
            audio_file: 音频文件
            config_id: 语音配置ID
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 转换结果
            
        Raises:
            HTTPException: 如果没有权限或语音配置不存在
        """
        # 获取语音配置
        config = await self.get_voice_config(config_id, user_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="语音配置不存在"
            )
        
        # 检查文件类型
        allowed_formats = ["audio/wav", "audio/mp3", "audio/mpeg", "audio/webm"]
        if audio_file.content_type not in allowed_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的音频格式: {audio_file.content_type}"
            )
        
        # 保存文件
        temp_file_path = os.path.join(self.temp_dir, f"{uuid.uuid4()}-{audio_file.filename}")
        with open(temp_file_path, "wb") as temp_file:
            content = await audio_file.read()
            temp_file.write(content)
        
        try:
            # 创建任务记录
            task_data = {
                "user_id": user_id,
                "config_id": config_id,
                "task_type": "speech_to_text",
                "status": "processing",
                "input_file": audio_file.filename,
                "file_size": len(content)
            }
            task = await self.task_repository.create(task_data, self.db)
            
            # 根据提供商类型选择不同的处理逻辑
            provider_type = config.provider_type
            result = await self._process_speech_to_text(temp_file_path, provider_type, config.model_config)
            
            # 更新任务状态
            if result.get("success", False):
                await self.task_repository.update(
                    task.id, 
                    {
                        "status": "completed", 
                        "result": result.get("text", ""),
                        "metadata": {
                            "duration": result.get("duration"),
                            "language": result.get("language")
                        }
                    }, 
                    self.db
                )
            else:
                await self.task_repository.update(
                    task.id, 
                    {
                        "status": "failed", 
                        "error": result.get("error", "未知错误")
                    }, 
                    self.db
                )
            
            return {
                "task_id": task.id,
                "success": result.get("success", False),
                "text": result.get("text", ""),
                "duration": result.get("duration"),
                "language": result.get("language"),
                "error": result.get("error")
            }
            
        except Exception as e:
            # 处理异常
            # 如果任务已创建，更新任务状态
            if 'task' in locals():
                await self.task_repository.update(
                    task.id, 
                    {"status": "failed", "error": str(e)}, 
                    self.db
                )
                
            # 返回错误信息
            return {
                "success": False,
                "error": f"语音转文本失败: {str(e)}"
            }
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    async def text_to_speech(self, text: str, config_id: str, user_id: str) -> Dict[str, Any]:
        """将文本转换为语音
        
        Args:
            text: 文本内容
            config_id: 语音配置ID
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 转换结果
            
        Raises:
            HTTPException: 如果没有权限或语音配置不存在
        """
        # 获取语音配置
        config = await self.get_voice_config(config_id, user_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="语音配置不存在"
            )
        
        try:
            # 创建任务记录
            task_data = {
                "user_id": user_id,
                "config_id": config_id,
                "task_type": "text_to_speech",
                "status": "processing",
                "input_text": text[:1000],  # 限制输入文本长度
                "text_length": len(text)
            }
            task = await self.task_repository.create(task_data, self.db)
            
            # 生成输出文件名
            output_file = f"{uuid.uuid4()}.mp3"
            output_path = os.path.join(self.temp_dir, output_file)
            
            # 根据提供商类型选择不同的处理逻辑
            provider_type = config.provider_type
            result = await self._process_text_to_speech(text, output_path, provider_type, config.model_config)
            
            # 更新任务状态
            if result.get("success", False):
                await self.task_repository.update(
                    task.id, 
                    {
                        "status": "completed", 
                        "output_file": output_file,
                        "metadata": {
                            "duration": result.get("duration"),
                            "format": result.get("format", "mp3"),
                            "file_size": result.get("file_size")
                        }
                    }, 
                    self.db
                )
                
                # 返回文件路径和元数据
                return {
                    "task_id": task.id,
                    "success": True,
                    "file_path": output_path,
                    "duration": result.get("duration"),
                    "format": result.get("format", "mp3"),
                    "file_size": result.get("file_size")
                }
            else:
                await self.task_repository.update(
                    task.id, 
                    {
                        "status": "failed", 
                        "error": result.get("error", "未知错误")
                    }, 
                    self.db
                )
                
                # 返回错误信息
                return {
                    "task_id": task.id,
                    "success": False,
                    "error": result.get("error", "未知错误")
                }
            
        except Exception as e:
            # 处理异常
            # 如果任务已创建，更新任务状态
            if 'task' in locals():
                await self.task_repository.update(
                    task.id, 
                    {"status": "failed", "error": str(e)}, 
                    self.db
                )
                
            # 返回错误信息
            return {
                "success": False,
                "error": f"文本转语音失败: {str(e)}"
            }
    
    async def get_task_status(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """获取任务状态
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 任务状态信息
            
        Raises:
            HTTPException: 如果没有权限或任务不存在
        """
        # 获取任务
        task = await self.task_repository.get_by_id(task_id, self.db)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="任务不存在"
            )
        
        # 检查权限
        is_admin = await self._check_admin_permission(user_id)
        if task.user_id != user_id and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限查看此任务"
            )
        
        # 返回任务状态
        result = {
            "task_id": task.id,
            "type": task.task_type,
            "status": task.status,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
        
        # 添加任务类型特定的字段
        if task.task_type == "speech_to_text":
            if task.status == "completed":
                result.update({
                    "text": task.result,
                    "duration": task.metadata.get("duration") if task.metadata else None,
                    "language": task.metadata.get("language") if task.metadata else None
                })
            elif task.status == "failed":
                result.update({"error": task.error})
                
        elif task.task_type == "text_to_speech":
            if task.status == "completed":
                result.update({
                    "output_file": task.output_file,
                    "duration": task.metadata.get("duration") if task.metadata else None,
                    "format": task.metadata.get("format") if task.metadata else None,
                    "file_size": task.metadata.get("file_size") if task.metadata else None
                })
            elif task.status == "failed":
                result.update({"error": task.error})
        
        return result
    
    async def list_user_tasks(self, user_id: str, task_type: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """获取用户任务列表
        
        Args:
            user_id: 用户ID
            task_type: 任务类型过滤器（可选）
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[Dict[str, Any]]: 任务列表
        """
        # 获取用户任务
        tasks = await self.task_repository.list_by_user(user_id, task_type, skip, limit, self.db)
        
        # 格式化结果
        result = []
        for task in tasks:
            task_info = {
                "task_id": task.id,
                "type": task.task_type,
                "status": task.status,
                "created_at": task.created_at
            }
            
            # 添加任务类型特定的字段
            if task.task_type == "speech_to_text":
                if task.status == "completed":
                    task_info.update({
                        "text": task.result[:100] + "..." if len(task.result) > 100 else task.result,
                        "input_file": task.input_file
                    })
                elif task.status == "failed":
                    task_info.update({
                        "error": task.error,
                        "input_file": task.input_file
                    })
                    
            elif task.task_type == "text_to_speech":
                if task.status == "completed":
                    task_info.update({
                        "output_file": task.output_file,
                        "input_text": task.input_text[:50] + "..." if len(task.input_text) > 50 else task.input_text
                    })
                elif task.status == "failed":
                    task_info.update({
                        "error": task.error,
                        "input_text": task.input_text[:50] + "..." if len(task.input_text) > 50 else task.input_text
                    })
            
            result.append(task_info)
        
        return result
    
    async def _process_speech_to_text(self, file_path: str, provider_type: str, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """处理语音转文本
        
        Args:
            file_path: 音频文件路径
            provider_type: 提供商类型
            model_config: 模型配置
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        # 根据提供商类型选择不同的处理逻辑
        # 这里是简化的示例，实际实现需要根据不同提供商调用不同API
        
        try:
            if provider_type == "openai":
                # 调用OpenAI Whisper API
                return await self._process_openai_speech_to_text(file_path, model_config)
            elif provider_type == "local":
                # 调用本地语音识别服务
                return await self._process_local_speech_to_text(file_path, model_config)
            else:
                return {
                    "success": False,
                    "error": f"不支持的提供商类型: {provider_type}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"处理失败: {str(e)}"
            }
    
    async def _process_text_to_speech(self, text: str, output_path: str, provider_type: str, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """处理文本转语音
        
        Args:
            text: 文本内容
            output_path: 输出文件路径
            provider_type: 提供商类型
            model_config: 模型配置
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        # 根据提供商类型选择不同的处理逻辑
        # 这里是简化的示例，实际实现需要根据不同提供商调用不同API
        
        try:
            if provider_type == "openai":
                # 调用OpenAI TTS API
                return await self._process_openai_text_to_speech(text, output_path, model_config)
            elif provider_type == "local":
                # 调用本地语音合成服务
                return await self._process_local_text_to_speech(text, output_path, model_config)
            else:
                return {
                    "success": False,
                    "error": f"不支持的提供商类型: {provider_type}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"处理失败: {str(e)}"
            }
    
    async def _process_openai_speech_to_text(self, file_path: str, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """处理OpenAI语音转文本
        
        Args:
            file_path: 音频文件路径
            model_config: 模型配置
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        # 这里应该实现调用OpenAI Whisper API的逻辑
        # 简化示例
        return {
            "success": True,
            "text": "这是通过OpenAI Whisper API转换的示例文本。实际实现需要调用真实API。",
            "duration": 10.5,
            "language": "zh"
        }
    
    async def _process_local_speech_to_text(self, file_path: str, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """处理本地语音转文本
        
        Args:
            file_path: 音频文件路径
            model_config: 模型配置
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        # 这里应该实现调用本地语音识别服务的逻辑
        # 简化示例
        return {
            "success": True,
            "text": "这是通过本地语音识别服务转换的示例文本。实际实现需要调用真实服务。",
            "duration": 8.2,
            "language": "zh"
        }
    
    async def _process_openai_text_to_speech(self, text: str, output_path: str, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """处理OpenAI文本转语音
        
        Args:
            text: 文本内容
            output_path: 输出文件路径
            model_config: 模型配置
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        # 这里应该实现调用OpenAI TTS API的逻辑
        # 简化示例
        
        # 模拟生成音频文件
        with open(output_path, "wb") as f:
            f.write(b"demo audio data")
        
        # 获取文件大小
        file_size = os.path.getsize(output_path)
        
        return {
            "success": True,
            "duration": len(text) * 0.1,  # 模拟计算持续时间
            "format": "mp3",
            "file_size": file_size
        }
    
    async def _process_local_text_to_speech(self, text: str, output_path: str, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """处理本地文本转语音
        
        Args:
            text: 文本内容
            output_path: 输出文件路径
            model_config: 模型配置
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        # 这里应该实现调用本地语音合成服务的逻辑
        # 简化示例
        
        # 模拟生成音频文件
        with open(output_path, "wb") as f:
            f.write(b"demo audio data")
        
        # 获取文件大小
        file_size = os.path.getsize(output_path)
        
        return {
            "success": True,
            "duration": len(text) * 0.08,  # 模拟计算持续时间
            "format": "mp3",
            "file_size": file_size
        }
    
    async def _check_admin_permission(self, user_id: str) -> bool:
        """检查用户是否为管理员
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否为管理员
        """
        from app.services.user_service import UserService
        user_service = UserService(self.db)
        user = await user_service.get_by_id(user_id)
        return user and user.role == "admin"
