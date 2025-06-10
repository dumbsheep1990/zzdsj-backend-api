"""
模型配置管理API
提供默认模型配置和模型管理相关的API接口
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.utils.core.database import get_db
from core.system_config import SystemConfigManager
from app.api.frontend.dependencies import ResponseFormatter, get_current_user, require_permission
from app.models.user import User

router = APIRouter(prefix="/api/frontend/system/model-config", tags=["模型配置管理"])

# ============ 请求/响应模型 ============

class DefaultModelConfig(BaseModel):
    """默认模型配置"""
    model_name: str = Field(..., description="模型名称")
    provider: str = Field(..., description="模型提供商")
    description: Optional[str] = Field(None, description="模型描述")
    
class ModelProviderConfig(BaseModel):
    """模型提供商配置"""
    provider_name: str = Field(..., description="提供商名称")
    api_key: Optional[str] = Field(None, description="API密钥")
    api_base: Optional[str] = Field(None, description="API基础URL")
    api_version: Optional[str] = Field(None, description="API版本")
    enabled: bool = Field(True, description="是否启用")
    
class ModelConfigResponse(BaseModel):
    """模型配置响应"""
    default_model: DefaultModelConfig
    providers: List[Dict[str, Any]]
    available_models: Dict[str, List[str]]

# ============ API路由 ============

@router.get("/default", response_model=Dict[str, Any])
async def get_default_model_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取默认模型配置"""
    try:
        config_manager = SystemConfigManager(db)
        
        # 获取默认模型配置
        default_model = await config_manager.get_config_value("llm.default_model", "gpt-3.5-turbo")
        default_provider = await config_manager.get_config_value("llm.default_provider", "openai")
        model_description = await config_manager.get_config_value("llm.default_model.description", "")
        
        # 获取提供商配置
        providers_config = {}
        provider_keys = [
            ("openai", ["api_key", "api_base", "organization"]),
            ("zhipu", ["api_key"]),
            ("anthropic", ["api_key"]),
            ("baidu", ["api_key", "secret_key"]),
        ]
        
        for provider, keys in provider_keys:
            provider_config = {}
            for key in keys:
                config_key = f"llm.{provider}.{key}"
                value = await config_manager.get_config_value(config_key, "")
                # 对敏感信息进行脱敏
                if "key" in key.lower() and value:
                    provider_config[key] = "***" + value[-4:] if len(value) > 4 else "***"
                else:
                    provider_config[key] = value
            providers_config[provider] = provider_config
        
        return ResponseFormatter.success({
            "default_model": {
                "model_name": default_model,
                "provider": default_provider,
                "description": model_description
            },
            "providers": providers_config,
            "supported_providers": ["openai", "zhipu", "anthropic", "baidu", "ollama"]
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取默认模型配置失败: {str(e)}")

@router.put("/default")
async def update_default_model_config(
    config: DefaultModelConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system:model:write"))
):
    """更新默认模型配置"""
    try:
        config_manager = SystemConfigManager(db)
        
        # 验证提供商
        supported_providers = ["openai", "zhipu", "anthropic", "baidu", "ollama"]
        if config.provider not in supported_providers:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的提供商: {config.provider}"
            )
        
        # 更新配置
        results = []
        
        # 更新默认模型
        result = await config_manager.update_config_value(
            "llm.default_model", 
            config.model_name,
            change_source="api",
            changed_by=current_user.username,
            change_notes=f"更新默认模型为: {config.model_name}"
        )
        results.append(("default_model", result))
        
        # 更新默认提供商
        result = await config_manager.update_config_value(
            "llm.default_provider", 
            config.provider,
            change_source="api",
            changed_by=current_user.username,
            change_notes=f"更新默认提供商为: {config.provider}"
        )
        results.append(("default_provider", result))
        
        # 更新模型描述
        if config.description:
            result = await config_manager.update_config_value(
                "llm.default_model.description", 
                config.description,
                change_source="api",
                changed_by=current_user.username,
                change_notes="更新模型描述"
            )
            results.append(("model_description", result))
        
        # 检查是否所有更新都成功
        failed_updates = [name for name, result in results if not result.get("success")]
        if failed_updates:
            raise HTTPException(
                status_code=500,
                detail=f"部分配置更新失败: {failed_updates}"
            )
        
        return ResponseFormatter.success({
            "message": "默认模型配置更新成功",
            "updated_config": {
                "model_name": config.model_name,
                "provider": config.provider,
                "description": config.description
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新默认模型配置失败: {str(e)}")

@router.get("/providers/{provider_name}")
async def get_provider_config(
    provider_name: str = Path(..., description="提供商名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定提供商的配置"""
    try:
        config_manager = SystemConfigManager(db)
        
        # 提供商配置键映射
        provider_keys = {
            "openai": ["api_key", "api_base", "organization"],
            "zhipu": ["api_key"],
            "anthropic": ["api_key"],
            "baidu": ["api_key", "secret_key"],
            "ollama": ["api_base"]
        }
        
        if provider_name not in provider_keys:
            raise HTTPException(status_code=404, detail=f"不支持的提供商: {provider_name}")
        
        provider_config = {}
        for key in provider_keys[provider_name]:
            config_key = f"llm.{provider_name}.{key}"
            value = await config_manager.get_config_value(config_key, "")
            # 对敏感信息进行脱敏
            if "key" in key.lower() and value:
                provider_config[key] = "***" + value[-4:] if len(value) > 4 else "***"
            else:
                provider_config[key] = value
        
        return ResponseFormatter.success({
            "provider": provider_name,
            "config": provider_config,
            "available_keys": provider_keys[provider_name]
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提供商配置失败: {str(e)}")

@router.put("/providers/{provider_name}")
async def update_provider_config(
    provider_name: str = Path(..., description="提供商名称"),
    config: Dict[str, str] = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system:model:write"))
):
    """更新提供商配置"""
    try:
        config_manager = SystemConfigManager(db)
        
        # 提供商配置键映射
        provider_keys = {
            "openai": ["api_key", "api_base", "organization"],
            "zhipu": ["api_key"],
            "anthropic": ["api_key"],
            "baidu": ["api_key", "secret_key"],
            "ollama": ["api_base"]
        }
        
        if provider_name not in provider_keys:
            raise HTTPException(status_code=404, detail=f"不支持的提供商: {provider_name}")
        
        # 验证配置键
        allowed_keys = provider_keys[provider_name]
        invalid_keys = [key for key in config.keys() if key not in allowed_keys]
        if invalid_keys:
            raise HTTPException(
                status_code=400,
                detail=f"无效的配置键: {invalid_keys}, 支持的键: {allowed_keys}"
            )
        
        # 更新配置
        results = []
        for key, value in config.items():
            config_key = f"llm.{provider_name}.{key}"
            result = await config_manager.update_config_value(
                config_key,
                value,
                change_source="api",
                changed_by=current_user.username,
                change_notes=f"更新{provider_name}提供商的{key}配置"
            )
            results.append((key, result))
        
        # 检查是否所有更新都成功
        failed_updates = [key for key, result in results if not result.get("success")]
        if failed_updates:
            raise HTTPException(
                status_code=500,
                detail=f"部分配置更新失败: {failed_updates}"
            )
        
        return ResponseFormatter.success({
            "message": f"{provider_name}提供商配置更新成功",
            "updated_keys": list(config.keys())
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新提供商配置失败: {str(e)}")

@router.get("/available-models")
async def get_available_models(
    provider: Optional[str] = Query(None, description="指定提供商"),
    model_type: Optional[str] = Query(None, description="模型类别：chat, embedding, rerank"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取可用的模型列表，支持按提供商和模型类别筛选"""
    try:
        # 从数据库获取模型提供商和模型信息
        from app.models.model_provider import ModelProvider, ModelInfo
        
        query = db.query(ModelProvider).filter(ModelProvider.is_active == True)
        if provider:
            query = query.filter(ModelProvider.provider_type == provider)
        
        providers = query.all()
        
        # 构建模型列表
        available_models = {}
        models_by_type = {"chat": [], "embedding": [], "rerank": []}
        
        for provider_obj in providers:
            provider_name = provider_obj.provider_type
            provider_models = []
            
            # 解析JSON格式的模型列表
            import json
            if provider_obj.models:
                try:
                    models_data = json.loads(provider_obj.models) if isinstance(provider_obj.models, str) else provider_obj.models
                    for model_data in models_data:
                        model_info = {
                            "id": model_data.get("id"),
                            "name": model_data.get("name"),
                            "type": model_data.get("type", "chat"),
                            "provider": provider_name,
                            "provider_display_name": provider_obj.name,
                            "context_window": model_data.get("context_window", 8192),
                            "is_default": model_data.get("is_default", False),
                            "description": model_data.get("description", ""),
                            "is_multimodal": model_data.get("multimodal", False)
                        }
                        
                        # 按类别分类
                        model_type_key = model_info["type"]
                        if model_type_key in models_by_type:
                            models_by_type[model_type_key].append(model_info)
                        
                        provider_models.append(model_info)
                        
                except json.JSONDecodeError:
                    logger.error(f"解析提供商 {provider_name} 的模型配置失败")
                    continue
            
            available_models[provider_name] = provider_models
        
        # 如果指定了模型类别，只返回该类别的模型
        if model_type and model_type in models_by_type:
            return ResponseFormatter.success({
                "model_type": model_type,
                "models": models_by_type[model_type],
                "total_models": len(models_by_type[model_type])
            })
        
        # 返回完整信息
        result = {
            "available_models": available_models,
            "models_by_type": models_by_type,
            "total_providers": len(available_models),
            "total_models": sum(len(models) for models in available_models.values()),
            "supported_types": ["chat", "embedding", "rerank"]
        }
        
        if provider:
            result["filtered_provider"] = provider
            
        return ResponseFormatter.success(result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取可用模型失败: {str(e)}")

@router.get("/models/by-type/{model_type}")
async def get_models_by_type(
    model_type: str = Path(..., description="模型类别：chat, embedding, rerank"),
    provider: Optional[str] = Query(None, description="指定提供商"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """按模型类别获取模型列表"""
    if model_type not in ["chat", "embedding", "rerank"]:
        raise HTTPException(status_code=400, detail="不支持的模型类别，支持：chat, embedding, rerank")
    
    try:
        from app.models.model_provider import ModelProvider
        import json
        
        query = db.query(ModelProvider).filter(ModelProvider.is_active == True)
        if provider:
            query = query.filter(ModelProvider.provider_type == provider)
        
        providers = query.all()
        models = []
        
        for provider_obj in providers:
            if provider_obj.models:
                try:
                    models_data = json.loads(provider_obj.models) if isinstance(provider_obj.models, str) else provider_obj.models
                    for model_data in models_data:
                        if model_data.get("type") == model_type:
                            models.append({
                                "id": model_data.get("id"),
                                "name": model_data.get("name"),
                                "type": model_type,
                                "provider": provider_obj.provider_type,
                                "provider_display_name": provider_obj.name,
                                "context_window": model_data.get("context_window", 8192),
                                "is_default": model_data.get("is_default", False),
                                "description": model_data.get("description", ""),
                                "api_key_required": provider_obj.auth_type != "none",
                                "api_key_configured": bool(provider_obj.api_key),
                                "is_enabled": provider_obj.is_enabled
                            })
                except json.JSONDecodeError:
                    continue
        
        return ResponseFormatter.success({
            "model_type": model_type,
            "models": models,
            "total_models": len(models),
            "filtered_provider": provider
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取{model_type}模型失败: {str(e)}")

@router.post("/models/configure")
async def configure_models(
    config_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system:model:write"))
):
    """配置模型选择（前端传递的模型配置）"""
    try:
        config_manager = SystemConfigManager(db)
        
        # 处理三个类别的模型配置
        if "chat_models" in config_data:
            await config_manager.set_config_value(
                "llm.models.chat.selected", 
                json.dumps(config_data["chat_models"])
            )
        
        if "embedding_models" in config_data:
            await config_manager.set_config_value(
                "llm.models.embedding.selected", 
                json.dumps(config_data["embedding_models"])
            )
        
        if "rerank_models" in config_data:
            await config_manager.set_config_value(
                "llm.models.rerank.selected", 
                json.dumps(config_data["rerank_models"])
            )
        
        # 设置默认模型
        if "default_chat_model" in config_data:
            await config_manager.set_config_value(
                "llm.default_model.chat", 
                config_data["default_chat_model"]
            )
        
        if "default_embedding_model" in config_data:
            await config_manager.set_config_value(
                "llm.default_model.embedding", 
                config_data["default_embedding_model"]
            )
        
        if "default_rerank_model" in config_data:
            await config_manager.set_config_value(
                "llm.default_model.rerank", 
                config_data["default_rerank_model"]
            )
        
        return ResponseFormatter.success({
            "message": "模型配置更新成功",
            "configured_types": list(config_data.keys())
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置模型失败: {str(e)}")

@router.get("/models/current-config")
async def get_current_model_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前的模型配置"""
    try:
        config_manager = SystemConfigManager(db)
        import json
        
        # 获取当前配置
        chat_models = await config_manager.get_config_value("llm.models.chat.selected", "[]")
        embedding_models = await config_manager.get_config_value("llm.models.embedding.selected", "[]")
        rerank_models = await config_manager.get_config_value("llm.models.rerank.selected", "[]")
        
        default_chat = await config_manager.get_config_value("llm.default_model.chat", "")
        default_embedding = await config_manager.get_config_value("llm.default_model.embedding", "")
        default_rerank = await config_manager.get_config_value("llm.default_model.rerank", "")
        
        try:
            chat_models = json.loads(chat_models) if isinstance(chat_models, str) else chat_models
            embedding_models = json.loads(embedding_models) if isinstance(embedding_models, str) else embedding_models
            rerank_models = json.loads(rerank_models) if isinstance(rerank_models, str) else rerank_models
        except json.JSONDecodeError:
            chat_models = []
            embedding_models = []
            rerank_models = []
        
        return ResponseFormatter.success({
            "selected_models": {
                "chat": chat_models,
                "embedding": embedding_models,
                "rerank": rerank_models
            },
            "default_models": {
                "chat": default_chat,
                "embedding": default_embedding,
                "rerank": default_rerank
            }
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取当前模型配置失败: {str(e)}")

@router.post("/test-connection")
async def test_model_connection(
    model_name: str = Query(..., description="模型名称"),
    provider: str = Query(..., description="提供商名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system:model:test"))
):
    """测试模型连接"""
    try:
        config_manager = SystemConfigManager(db)
        
        # 获取提供商配置
        api_key = await config_manager.get_config_value(f"llm.{provider}.api_key", "")
        api_base = await config_manager.get_config_value(f"llm.{provider}.api_base", "")
        
        if not api_key and provider != "ollama":
            raise HTTPException(
                status_code=400,
                detail=f"{provider}提供商的API密钥未配置"
            )
        
        # 这里可以调用模型管理器来测试连接
        from core.model_manager.manager import test_model_connection
        
        test_prompt = "Hello, this is a test message."
        response = await test_model_connection(
            provider_type=provider,
            model_id=model_name,
            prompt=test_prompt,
            api_key=api_key,
            api_base=api_base
        )
        
        return ResponseFormatter.success({
            "message": "模型连接测试成功",
            "model": model_name,
            "provider": provider,
            "test_response": response[:100] + "..." if len(response) > 100 else response
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模型连接测试失败: {str(e)}") 