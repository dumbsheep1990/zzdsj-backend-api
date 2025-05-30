"""
模型管理器: 管理和与不同模型提供商的交互
支持OpenAI、智谱、DeepSeek、Ollama和VLLM等多种模型
"""
from typing import Dict, Any, Optional, List, Union
import logging
import httpx
import json
import os
from fastapi import HTTPException

logger = logging.getLogger(__name__)

async def test_model_connection(
    provider_type: str,
    model_id: str,
    prompt: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    api_version: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """
    测试与模型提供商的连接
    
    参数:
        provider_type: 提供商类型(openai, zhipu, deepseek, ollama, vllm等)
        model_id: 要测试的模型ID
        prompt: 测试提示
        api_key: API密钥
        api_base: API基础URL
        api_version: API版本
        config: 其他配置参数
        
    返回:
        成功返回模型响应，失败抛出异常
    """
    config = config or {}
    
    try:
        if provider_type.lower() == "openai":
            return await test_openai_connection(model_id, prompt, api_key, api_base, api_version, config)
        elif provider_type.lower() == "zhipu":
            return await test_zhipu_connection(model_id, prompt, api_key, api_base, config)
        elif provider_type.lower() == "deepseek":
            return await test_deepseek_connection(model_id, prompt, api_key, api_base, config)
        elif provider_type.lower() == "ollama":
            return await test_ollama_connection(model_id, prompt, api_base, config)
        elif provider_type.lower() == "vllm":
            return await test_vllm_connection(model_id, prompt, api_base, config)
        elif provider_type.lower() == "dashscope":
            return await test_dashscope_connection(model_id, prompt, api_key, api_base, config)
        elif provider_type.lower() == "anthropic":
            return await test_anthropic_connection(model_id, prompt, api_key, api_base, config)
        elif provider_type.lower() == "together":
            return await test_together_connection(model_id, prompt, api_key, api_base, config)
        elif provider_type.lower() == "qwen":
            return await test_qwen_connection(model_id, prompt, api_key, api_base, config)
        elif provider_type.lower() == "baidu":
            return await test_baidu_connection(model_id, prompt, api_key, api_base, config)
        elif provider_type.lower() == "moonshot":
            return await test_moonshot_connection(model_id, prompt, api_key, api_base, config)
        elif provider_type.lower() == "glm":
            return await test_glm_connection(model_id, prompt, api_key, api_base, config)
        elif provider_type.lower() == "minimax":
            return await test_minimax_connection(model_id, prompt, api_key, api_base, config)
        elif provider_type.lower() == "baichuan":
            return await test_baichuan_connection(model_id, prompt, api_key, api_base, config)
        else:
            raise ValueError(f"不支持的提供商类型: {provider_type}")
    
    except Exception as e:
        logger.error(f"测试{provider_type}连接失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"连接失败: {str(e)}")


async def test_openai_connection(
    model_id: str,
    prompt: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    api_version: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """测试OpenAI连接"""
    from openai import AsyncOpenAI
    
    # 配置客户端
    client_args = {"api_key": api_key or os.environ.get("OPENAI_API_KEY")}
    
    if api_base:
        client_args["base_url"] = api_base
    
    timeout = config.get("timeout", 30)
    client_args["timeout"] = timeout
    
    # 代理设置
    if config.get("proxy"):
        client_args["http_client"] = httpx.AsyncClient(
            proxies=config["proxy"],
            timeout=timeout
        )
    
    client = AsyncOpenAI(**client_args)
    
    response = await client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=config.get("max_tokens", 200),
        temperature=config.get("temperature", 0.7)
    )
    
    return response.choices[0].message.content


async def test_zhipu_connection(
    model_id: str,
    prompt: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """测试智谱AI连接"""
    try:
        from zhipuai import ZhipuAI
        
        # 配置客户端
        client = ZhipuAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=config.get("max_tokens", 200),
            temperature=config.get("temperature", 0.7)
        )
        
        return response.choices[0].message.content
    
    except ImportError:
        # 如果没有智谱AI SDK，使用HTTP请求
        api_base = api_base or "https://open.bigmodel.cn/api/paas/v3/model-api"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        data = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": config.get("max_tokens", 200),
            "temperature": config.get("temperature", 0.7)
        }
        
        async with httpx.AsyncClient(timeout=config.get("timeout", 30)) as client:
            response = await client.post(
                f"{api_base}/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"智谱API错误: {response.text}"
                )
            
            result = response.json()
            return result["choices"][0]["message"]["content"]


async def test_deepseek_connection(
    model_id: str,
    prompt: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """测试DeepSeek连接"""
    api_base = api_base or "https://api.deepseek.com"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": config.get("max_tokens", 200),
        "temperature": config.get("temperature", 0.7)
    }
    
    async with httpx.AsyncClient(timeout=config.get("timeout", 30)) as client:
        response = await client.post(
            f"{api_base}/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"DeepSeek API错误: {response.text}"
            )
        
        result = response.json()
        return result["choices"][0]["message"]["content"]


async def test_ollama_connection(
    model_id: str,
    prompt: str,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """测试Ollama连接"""
    api_base = api_base or "http://localhost:11434"
    
    data = {
        "model": model_id,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": config.get("temperature", 0.7),
            "num_predict": config.get("max_tokens", 200)
        }
    }
    
    # 如果提供了系统提示
    if config.get("system_prompt"):
        data["system"] = config["system_prompt"]
    
    async with httpx.AsyncClient(timeout=config.get("timeout", 60)) as client:
        response = await client.post(
            f"{api_base}/api/generate",
            json=data
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Ollama API错误: {response.text}"
            )
        
        result = response.json()
        return result["response"]


async def test_vllm_connection(
    model_id: str,
    prompt: str,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """测试vLLM连接"""
    api_base = api_base or "http://localhost:8000"
    
    data = {
        "model": model_id,
        "prompt": prompt,
        "max_tokens": config.get("max_tokens", 200),
        "temperature": config.get("temperature", 0.7),
        "stream": False
    }
    
    # 添加其他vLLM特定参数
    if config.get("stop"):
        data["stop"] = config["stop"]
    if config.get("top_p") is not None:
        data["top_p"] = config["top_p"]
    if config.get("presence_penalty") is not None:
        data["presence_penalty"] = config["presence_penalty"]
    if config.get("frequency_penalty") is not None:
        data["frequency_penalty"] = config["frequency_penalty"]
    
    async with httpx.AsyncClient(timeout=config.get("timeout", 60)) as client:
        response = await client.post(
            f"{api_base}/v1/completions",
            json=data
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"vLLM API错误: {response.text}"
            )
        
        result = response.json()
        return result["choices"][0]["text"]


async def test_dashscope_connection(
    model_id: str,
    prompt: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """测试通义千问连接"""
    try:
        from dashscope import Generation
        
        response = Generation.call(
            model=model_id,
            prompt=prompt,
            api_key=api_key,
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 200)
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"通义千问API错误: {response.output.message}"
            )
        
        return response.output.text
    
    except ImportError:
        # 如果没有DashScope SDK，使用HTTP请求
        api_base = api_base or "https://dashscope.aliyuncs.com/api/v1"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        data = {
            "model": model_id,
            "input": {"prompt": prompt},
            "parameters": {
                "temperature": config.get("temperature", 0.7),
                "max_tokens": config.get("max_tokens", 200)
            }
        }
        
        async with httpx.AsyncClient(timeout=config.get("timeout", 30)) as client:
            response = await client.post(
                f"{api_base}/services/aigc/text-generation/generation",
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"通义千问API错误: {response.text}"
                )
            
            result = response.json()
            return result["output"]["text"]


async def test_anthropic_connection(
    model_id: str,
    prompt: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """测试Anthropic Claude连接"""
    try:
        from anthropic import AsyncAnthropic
        
        client = AsyncAnthropic(api_key=api_key)
        
        response = await client.messages.create(
            model=model_id,
            max_tokens=config.get("max_tokens", 200),
            temperature=config.get("temperature", 0.7),
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
    
    except ImportError:
        # 如果没有Anthropic SDK，使用HTTP请求
        api_base = api_base or "https://api.anthropic.com"
        
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": config.get("max_tokens", 200),
            "temperature": config.get("temperature", 0.7)
        }
        
        async with httpx.AsyncClient(timeout=config.get("timeout", 30)) as client:
            response = await client.post(
                f"{api_base}/v1/messages",
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Anthropic API错误: {response.text}"
                )
            
            result = response.json()
            return result["content"][0]["text"]


async def test_together_connection(
    model_id: str,
    prompt: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """测试TogetherAI连接"""
    api_base = api_base or "https://api.together.xyz"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": model_id,
        "prompt": prompt,
        "max_tokens": config.get("max_tokens", 200),
        "temperature": config.get("temperature", 0.7),
        "stop": config.get("stop", []),
        "top_p": config.get("top_p", 0.7),
        "stream": False
    }
    
    async with httpx.AsyncClient(timeout=config.get("timeout", 30)) as client:
        response = await client.post(
            f"{api_base}/v1/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"TogetherAI API错误: {response.text}"
            )
        
        result = response.json()
        return result["choices"][0]["text"]


async def test_qwen_connection(
    model_id: str,
    prompt: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """测试阿里千问API连接"""
    import httpx
    
    config = config or {}
    api_key = api_key or os.environ.get("QWEN_API_KEY")
    
    if not api_key:
        raise ValueError("阿里千问 API密钥未提供")
    
    api_base = api_base or "https://dashscope.aliyuncs.com/api/v1"
    url = f"{api_base}/services/aigc/text-generation/generation"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "anthropic-version": "2023-06-01"
    }
    
    data = {
        "model": model_id,
        "input": {
            "messages": [{"role": "user", "content": prompt}]
        },
        "parameters": {
            "max_tokens": config.get("max_tokens", 200),
            "temperature": config.get("temperature", 0.7)
        }
    }
    
    timeout = config.get("timeout", 30)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=data)
        
        if response.status_code != 200:
            error_detail = response.json() if response.text else "无响应内容"
            raise ValueError(f"阿里千问API调用失败: {response.status_code} - {error_detail}")
        
        response_json = response.json()
        return response_json["output"]["text"]


async def test_baidu_connection(
    model_id: str,
    prompt: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """测试百度文心一言连接"""
    import httpx
    from app.config import settings
    
    config = config or {}
    api_key = api_key or os.environ.get("BAIDU_API_KEY")
    secret_key = config.get("secret_key") or os.environ.get("BAIDU_SECRET_KEY") or settings.BAIDU_SECRET_KEY
    
    if not api_key:
        raise ValueError("百度 API密钥未提供")
    
    if not secret_key:
        raise ValueError("百度 Secret Key未提供")
    
    # 先获取access token
    token_url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url)
        if token_response.status_code != 200:
            raise ValueError(f"百度 Access Token获取失败: {token_response.status_code}")
        
        access_token = token_response.json().get("access_token")
        if not access_token:
            raise ValueError("百度 Access Token获取失败")
        
        # 调用文心一言API
        api_base = api_base or "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions"
        url = f"{api_base}?access_token={access_token}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "messages": [{"role": "user", "content": prompt}],
            "model": model_id,
            "temperature": config.get("temperature", 0.7),
            "top_p": config.get("top_p", 0.8)
        }
        
        timeout = config.get("timeout", 30)
        
        response = await client.post(url, headers=headers, json=data, timeout=timeout)
        
        if response.status_code != 200:
            error_detail = response.json() if response.text else "无响应内容"
            raise ValueError(f"百度文心一言API调用失败: {response.status_code} - {error_detail}")
        
        response_json = response.json()
        return response_json["result"]


async def test_moonshot_connection(
    model_id: str,
    prompt: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """测试月之暗面API连接"""
    import httpx
    
    config = config or {}
    api_key = api_key or os.environ.get("MOONSHOT_API_KEY")
    
    if not api_key:
        raise ValueError("月之暗面 API密钥未提供")
    
    api_base = api_base or "https://api.moonshot.cn/v1"
    url = f"{api_base}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": config.get("max_tokens", 200),
        "temperature": config.get("temperature", 0.7)
    }
    
    timeout = config.get("timeout", 30)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=data)
        
        if response.status_code != 200:
            error_detail = response.json() if response.text else "无响应内容"
            raise ValueError(f"月之暗面API调用失败: {response.status_code} - {error_detail}")
        
        response_json = response.json()
        return response_json["choices"][0]["message"]["content"]


async def test_glm_connection(
    model_id: str,
    prompt: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """测试智谱GLM API连接"""
    import httpx
    import hmac
    import hashlib
    import base64
    import time
    
    config = config or {}
    api_key = api_key or os.environ.get("GLM_API_KEY")
    
    if not api_key:
        raise ValueError("智谱GLM API密钥未提供")
    
    # 智谱AI签名认证
    api_base = api_base or "https://open.bigmodel.cn/api/paas/v4"
    url = f"{api_base}/chat/completions"
    
    # 解析API Key
    if "." not in api_key:
        raise ValueError("智谱GLM API Key格式不正确")
    
    id, secret = api_key.split(".")
    
    # 生成签名
    timestamp = int(time.time())
    signature_raw = f"{timestamp}\n{id}"
    signature = base64.b64encode(
        hmac.new(
            secret.encode("utf-8"),
            signature_raw.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
    ).decode("utf-8")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {id}.{timestamp}.{signature}"
    }
    
    data = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": config.get("max_tokens", 200),
        "temperature": config.get("temperature", 0.7)
    }
    
    timeout = config.get("timeout", 30)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=data)
        
        if response.status_code != 200:
            error_detail = response.json() if response.text else "无响应内容"
            raise ValueError(f"智谱GLM API调用失败: {response.status_code} - {error_detail}")
        
        response_json = response.json()
        return response_json["choices"][0]["message"]["content"]


async def test_minimax_connection(
    model_id: str,
    prompt: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """测试MiniMax API连接"""
    import httpx
    from app.config import settings
    
    config = config or {}
    api_key = api_key or os.environ.get("MINIMAX_API_KEY")
    group_id = config.get("group_id") or os.environ.get("MINIMAX_GROUP_ID") or settings.MINIMAX_GROUP_ID
    
    if not api_key:
        raise ValueError("MiniMax API密钥未提供")
    
    if not group_id:
        raise ValueError("MiniMax Group ID未提供")
    
    api_base = api_base or "https://api.minimax.chat/v1"
    url = f"{api_base}/text/chatcompletion?GroupId={group_id}"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model_id,
        "messages": [{"sender_type": "USER", "text": prompt}],
        "tokens_to_generate": config.get("max_tokens", 200),
        "temperature": config.get("temperature", 0.7),
        "top_p": config.get("top_p", 0.8)
    }
    
    timeout = config.get("timeout", 30)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=data)
        
        if response.status_code != 200:
            error_detail = response.json() if response.text else "无响应内容"
            raise ValueError(f"MiniMax API调用失败: {response.status_code} - {error_detail}")
        
        response_json = response.json()
        return response_json["reply"]


async def test_baichuan_connection(
    model_id: str,
    prompt: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """测试百川API连接"""
    import httpx
    import hmac
    import hashlib
    import time
    from app.config import settings
    
    config = config or {}
    api_key = api_key or os.environ.get("BAICHUAN_API_KEY")
    secret_key = config.get("secret_key") or os.environ.get("BAICHUAN_SECRET_KEY") or settings.BAICHUAN_SECRET_KEY
    
    if not api_key:
        raise ValueError("百川 API密钥未提供")
    
    if not secret_key:
        raise ValueError("百川 Secret Key未提供")
    
    api_base = api_base or "https://api.baichuan-ai.com/v1"
    url = f"{api_base}/chat/completions"
    
    # 生成百川API签名
    timestamp = int(time.time())
    signature = hmac.new(
        secret_key.encode("utf-8"),
        f"{timestamp}{api_key}".encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "X-BC-Timestamp": str(timestamp),
        "X-BC-Signature": signature,
        "X-BC-Sign-Algo": "MD5"
    }
    
    data = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": config.get("max_tokens", 200),
        "temperature": config.get("temperature", 0.7)
    }
    
    timeout = config.get("timeout", 30)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=data)
        
        if response.status_code != 200:
            error_detail = response.json() if response.text else "无响应内容"
            raise ValueError(f"百川API调用失败: {response.status_code} - {error_detail}")
        
        response_json = response.json()
        return response_json["choices"][0]["message"]["content"]


def get_model_client(
    provider_type: str,
    model_id: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    api_version: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Any:
    """
    获取模型客户端实例
    
    参数:
        provider_type: 提供商类型
        model_id: 模型ID
        api_key: API密钥
        api_base: API基础URL
        api_version: API版本
        config: 其他配置参数
        
    返回:
        模型客户端实例
    """
    config = config or {}
    
    if provider_type.lower() == "openai":
        return get_openai_client(api_key, api_base, api_version, config)
    elif provider_type.lower() == "zhipu":
        return get_zhipu_client(api_key, api_base, config)
    elif provider_type.lower() == "deepseek":
        return get_deepseek_client(api_key, api_base, config)
    elif provider_type.lower() == "ollama":
        return get_ollama_client(api_base, config)
    elif provider_type.lower() == "vllm":
        return get_vllm_client(api_base, config)
    elif provider_type.lower() == "dashscope":
        return get_dashscope_client(api_key, config)
    elif provider_type.lower() == "anthropic":
        return get_anthropic_client(api_key, api_base, config)
    elif provider_type.lower() == "together":
        return get_together_client(api_key, api_base, config)
    elif provider_type.lower() == "qwen":
        return get_qwen_client(api_key, api_base, config)
    elif provider_type.lower() == "baidu":
        return get_baidu_client(api_key, api_base, config)
    elif provider_type.lower() == "moonshot":
        return get_moonshot_client(api_key, api_base, config)
    elif provider_type.lower() == "glm":
        return get_glm_client(api_key, api_base, config)
    elif provider_type.lower() == "minimax":
        return get_minimax_client(api_key, api_base, config)
    elif provider_type.lower() == "baichuan":
        return get_baichuan_client(api_key, api_base, config)
    else:
        raise ValueError(f"不支持的提供商类型: {provider_type}")


def get_openai_client(
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    api_version: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Any:
    """获取OpenAI客户端"""
    from openai import OpenAI, AsyncOpenAI
    
    # 配置客户端
    client_args = {"api_key": api_key or os.environ.get("OPENAI_API_KEY")}
    
    if api_base:
        client_args["base_url"] = api_base
    
    timeout = config.get("timeout", 30)
    client_args["timeout"] = timeout
    
    # 代理设置
    if config.get("proxy"):
        client_args["http_client"] = httpx.Client(
            proxies=config["proxy"],
            timeout=timeout
        )
    
    # 同步客户端
    client = OpenAI(**client_args)
    
    return client


def get_zhipu_client(
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Any:
    """获取智谱AI客户端"""
    try:
        from zhipuai import ZhipuAI
        return ZhipuAI(api_key=api_key)
    except ImportError:
        logger.warning("智谱AI SDK未安装，将使用HTTP客户端")
        class ZhipuHttpClient:
            def __init__(self, api_key, api_base=None):
                self.api_key = api_key
                self.api_base = api_base or "https://open.bigmodel.cn/api/paas/v3/model-api"
                self.timeout = config.get("timeout", 30)
            
            def chat_completion(self, model, messages, **kwargs):
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                data = {
                    "model": model,
                    "messages": messages,
                    **kwargs
                }
                
                response = httpx.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=self.timeout
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"智谱API错误: {response.text}"
                    )
                
                return response.json()
        
        return ZhipuHttpClient(api_key=api_key, api_base=api_base)


def get_ollama_client(
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Any:
    """获取Ollama客户端"""
    try:
        import ollama
        ollama.set_host(api_base or "http://localhost:11434")
        return ollama
    except ImportError:
        logger.warning("Ollama SDK未安装，将使用HTTP客户端")
        class OllamaHttpClient:
            def __init__(self, api_base=None):
                self.api_base = api_base or "http://localhost:11434"
                self.timeout = config.get("timeout", 60)
            
            def chat(self, model, messages, **kwargs):
                # 转换消息格式
                data = {
                    "model": model,
                    "messages": messages,
                    "options": kwargs,
                    "stream": False
                }
                
                response = httpx.post(
                    f"{self.api_base}/api/chat",
                    json=data,
                    timeout=self.timeout
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Ollama API错误: {response.text}"
                    )
                
                return response.json()
            
            def generate(self, model, prompt, **kwargs):
                data = {
                    "model": model,
                    "prompt": prompt,
                    "options": kwargs,
                    "stream": False
                }
                
                response = httpx.post(
                    f"{self.api_base}/api/generate",
                    json=data,
                    timeout=self.timeout
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Ollama API错误: {response.text}"
                    )
                
                return response.json()
        
        return OllamaHttpClient(api_base=api_base)


def get_vllm_client(
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Any:
    """获取vLLM客户端"""
    class VllmHttpClient:
        def __init__(self, api_base=None):
            self.api_base = api_base or "http://localhost:8000"
            self.timeout = config.get("timeout", 60)
        
        def completions(self, model, prompt, **kwargs):
            data = {
                "model": model,
                "prompt": prompt,
                **kwargs,
                "stream": False
            }
            
            response = httpx.post(
                f"{self.api_base}/v1/completions",
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"vLLM API错误: {response.text}"
                )
            
            return response.json()
    
    return VllmHttpClient(api_base=api_base)


def get_qwen_client(
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Any:
    """获取阿里千问客户端"""
    class QwenHttpClient:
        def __init__(self, api_key, api_base=None):
            self.api_key = api_key
            self.api_base = api_base or "https://dashscope.aliyuncs.com/api/v1"
            self.timeout = config.get("timeout", 30)
        
        def generation(self, model, input, **kwargs):
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": model,
                "input": input,
                "parameters": kwargs
            }
            
            response = httpx.post(
                f"{self.api_base}/services/aigc/text-generation/generation",
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"阿里千问API错误: {response.text}"
                )
            
            return response.json()
    
    return QwenHttpClient(api_key=api_key, api_base=api_base)


def get_baidu_client(
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Any:
    """获取百度文心一言客户端"""
    from app.config import settings
    
    class BaiduHttpClient:
        def __init__(self, api_key, api_base=None):
            self.api_key = api_key
            self.api_base = api_base or "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions"
            self.secret_key = config.get("secret_key") or os.environ.get("BAIDU_SECRET_KEY") or settings.BAIDU_SECRET_KEY
            self.timeout = config.get("timeout", 30)
        
        def chat_completion(self, model, messages, **kwargs):
            # 先获取access token
            token_url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={self.api_key}&client_secret={self.secret_key}"
            
            response = httpx.post(token_url)
            if response.status_code != 200:
                raise ValueError(f"百度 Access Token获取失败: {response.status_code}")
            
            access_token = response.json().get("access_token")
            if not access_token:
                raise ValueError("百度 Access Token获取失败")
            
            # 调用文心一言API
            url = f"{self.api_base}?access_token={access_token}"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.8)
            }
            
            response = httpx.post(url, headers=headers, json=data, timeout=self.timeout)
            
            if response.status_code != 200:
                raise ValueError(f"百度文心一言API调用失败: {response.status_code}")
            
            return response.json()
    
    return BaiduHttpClient(api_key=api_key, api_base=api_base)


def get_moonshot_client(
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Any:
    """获取月之暗面客户端"""
    class MoonshotHttpClient:
        def __init__(self, api_key, api_base=None):
            self.api_key = api_key
            self.api_base = api_base or "https://api.moonshot.cn/v1"
            self.timeout = config.get("timeout", 30)
        
        def chat_completion(self, model, messages, **kwargs):
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": model,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", 200),
                "temperature": kwargs.get("temperature", 0.7)
            }
            
            response = httpx.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"月之暗面API错误: {response.text}"
                )
            
            return response.json()
    
    return MoonshotHttpClient(api_key=api_key, api_base=api_base)


def get_glm_client(
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Any:
    """获取智谱GLM客户端"""
    class GlmHttpClient:
        def __init__(self, api_key, api_base=None):
            self.api_key = api_key
            self.api_base = api_base or "https://open.bigmodel.cn/api/paas/v4"
            self.timeout = config.get("timeout", 30)
        
        def chat_completion(self, model, messages, **kwargs):
            # 解析API Key
            if "." not in self.api_key:
                raise ValueError("智谱GLM API Key格式不正确")
            
            id, secret = self.api_key.split(".")
            
            # 生成签名
            timestamp = int(time.time())
            signature_raw = f"{timestamp}\n{id}"
            signature = base64.b64encode(
                hmac.new(
                    secret.encode("utf-8"),
                    signature_raw.encode("utf-8"),
                    digestmod=hashlib.sha256
                ).digest()
            ).decode("utf-8")
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {id}.{timestamp}.{signature}"
            }
            
            data = {
                "model": model,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", 200),
                "temperature": kwargs.get("temperature", 0.7)
            }
            
            response = httpx.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"智谱GLM API错误: {response.text}"
                )
            
            return response.json()
    
    return GlmHttpClient(api_key=api_key, api_base=api_base)


def get_minimax_client(
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Any:
    """获取MiniMax客户端"""
    from app.config import settings
    
    class MinimaxHttpClient:
        def __init__(self, api_key, api_base=None):
            self.api_key = api_key
            self.api_base = api_base or "https://api.minimax.chat/v1"
            self.group_id = config.get("group_id") or os.environ.get("MINIMAX_GROUP_ID") or settings.MINIMAX_GROUP_ID
            self.timeout = config.get("timeout", 30)
        
        def chat_completion(self, model, messages, **kwargs):
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": messages,
                "tokens_to_generate": kwargs.get("max_tokens", 200),
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.8)
            }
            
            response = httpx.post(
                f"{self.api_base}/text/chatcompletion?GroupId={self.group_id}",
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"MiniMax API错误: {response.text}"
                )
            
            return response.json()
    
    return MinimaxHttpClient(api_key=api_key, api_base=api_base)


def get_baichuan_client(
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Any:
    """获取百川客户端"""
    from app.config import settings
    
    class BaichuanHttpClient:
        def __init__(self, api_key, api_base=None):
            self.api_key = api_key
            self.api_base = api_base or "https://api.baichuan-ai.com/v1"
            self.secret_key = config.get("secret_key") or os.environ.get("BAICHUAN_SECRET_KEY") or settings.BAICHUAN_SECRET_KEY
            self.timeout = config.get("timeout", 30)
        
        def chat_completion(self, model, messages, **kwargs):
            # 生成百川API签名
            timestamp = int(time.time())
            signature = hmac.new(
                self.secret_key.encode("utf-8"),
                f"{timestamp}{self.api_key}".encode("utf-8"),
                digestmod=hashlib.sha256
            ).hexdigest()
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "X-BC-Timestamp": str(timestamp),
                "X-BC-Signature": signature,
                "X-BC-Sign-Algo": "MD5"
            }
            
            data = {
                "model": model,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", 200),
                "temperature": kwargs.get("temperature", 0.7)
            }
            
            response = httpx.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"百川API错误: {response.text}"
                )
            
            return response.json()
    
    return BaichuanHttpClient(api_key=api_key, api_base=api_base)


def get_model_names_for_provider(provider_type: str) -> List[str]:
    """获取指定提供商支持的模型列表"""
    if provider_type.lower() == "openai":
        return [
            "gpt-4", "gpt-4-turbo", "gpt-4-vision", "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k", "text-embedding-ada-002"
        ]
    elif provider_type.lower() == "zhipu":
        return ["glm-4", "glm-4v", "glm-3-turbo"]
    elif provider_type.lower() == "deepseek":
        return ["deepseek-chat", "deepseek-coder"]
    elif provider_type.lower() == "ollama":
        return ["llama3", "llama2", "mistral", "mixtral", "qwen", "yi", "gemma"]
    elif provider_type.lower() == "vllm":
        return ["llama-2-7b", "llama-2-13b", "llama-2-70b", "mistral-7b", "mixtral-8x7b"]
    elif provider_type.lower() == "dashscope":
        return ["qwen-turbo", "qwen-plus", "qwen-max"]
    elif provider_type.lower() == "anthropic":
        return ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
    elif provider_type.lower() == "together":
        return ["Llama-3-70b-Instruct", "Llama-3-8b-Instruct"]
    elif provider_type.lower() == "qwen":
        return ["qwen-base", "qwen-large"]
    elif provider_type.lower() == "baidu":
        return ["wenxin-yiyan"]
    elif provider_type.lower() == "moonshot":
        return ["moonshot-base", "moonshot-large"]
    elif provider_type.lower() == "glm":
        return ["glm-base", "glm-large"]
    elif provider_type.lower() == "minimax":
        return ["minimax-base", "minimax-large"]
    elif provider_type.lower() == "baichuan":
        return ["baichuan-base", "baichuan-large"]
    else:
        return []
