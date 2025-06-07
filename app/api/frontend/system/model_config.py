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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取可用的模型列表"""
    try:
        # 模型列表
        available_models = {
            "openai": [
                "gpt-4", "gpt-4-turbo", "gpt-4-vision-preview",
                "gpt-3.5-turbo", "gpt-3.5-turbo-16k",
                "text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"
            ],
            "zhipu": [
                "glm-4", "glm-4v", "glm-3-turbo", "embedding-2"
            ],
            "anthropic": [
                "claude-3-opus-20240229", "claude-3-sonnet-20240229", 
                "claude-3-haiku-20240307", "claude-2.1", "claude-2.0"
            ],
            "baidu": [
                "ernie-bot", "ernie-bot-turbo", "ernie-bot-4.0", "embedding-v1"
            ],
            "ollama": [
                "llama3", "llama2", "mistral", "mixtral", "qwen", "yi", "gemma"
            ]
        }
        
        if provider:
            if provider not in available_models:
                raise HTTPException(status_code=404, detail=f"不支持的提供商: {provider}")
            return ResponseFormatter.success({
                "provider": provider,
                "models": available_models[provider]
            })
        
        return ResponseFormatter.success({
            "available_models": available_models,
            "total_providers": len(available_models),
            "total_models": sum(len(models) for models in available_models.values())
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取可用模型失败: {str(e)}")

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