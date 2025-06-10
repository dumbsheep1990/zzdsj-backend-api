"""
模型配置适配器使用示例
展示如何在ZZDSJ Agno框架中使用配置化的模型
"""

import asyncio
import logging
from typing import Optional, Dict, Any

try:
    from agno import Agent, Team, OpenAIChat
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False
    Agent = object
    Team = object
    OpenAIChat = object

from .model_config_adapter import (
    get_model_adapter,
    create_default_agno_model,
    create_agno_model_by_provider,
    create_agno_model_by_id
)

logger = logging.getLogger(__name__)


async def example_create_agent_with_configured_model():
    """示例：使用配置化模型创建代理"""
    if not AGNO_AVAILABLE:
        logger.warning("Agno框架不可用，跳过示例")
        return None
    
    try:
        # 方法1：使用默认模型配置
        default_model = await create_default_agno_model()
        if default_model:
            agent = Agent(
                model=default_model,
                name="配置化代理示例",
                description="使用系统配置的模型创建的代理",
                instructions=["作为一个友好的AI助手", "使用系统配置的模型"]
            )
            logger.info("使用默认模型配置创建代理成功")
            return agent
        else:
            logger.warning("无法获取默认模型配置")
            return None
            
    except Exception as e:
        logger.error(f"创建配置化代理失败: {e}")
        return None


async def example_create_agent_with_specific_provider():
    """示例：使用特定提供商创建代理"""
    if not AGNO_AVAILABLE:
        logger.warning("Agno框架不可用，跳过示例")
        return None
    
    try:
        # 方法2：使用特定提供商
        anthropic_model = await create_agno_model_by_provider("anthropic")
        if anthropic_model:
            agent = Agent(
                model=anthropic_model,
                name="Anthropic代理示例",
                description="使用Anthropic模型的代理",
                instructions=["使用Anthropic Claude模型", "提供深度思考的回答"]
            )
            logger.info("使用Anthropic提供商创建代理成功")
            return agent
        else:
            # 回退到默认模型
            default_model = await create_default_agno_model()
            if default_model:
                agent = Agent(
                    model=default_model,
                    name="回退代理示例",
                    description="使用回退模型的代理",
                    instructions=["Anthropic不可用，使用默认模型"]
                )
                logger.info("使用回退模型创建代理成功")
                return agent
            
    except Exception as e:
        logger.error(f"创建特定提供商代理失败: {e}")
        return None


async def example_create_team_with_configured_models():
    """示例：使用配置化模型创建团队"""
    if not AGNO_AVAILABLE:
        logger.warning("Agno框架不可用，跳过示例")
        return None
    
    try:
        adapter = get_model_adapter()
        
        # 创建不同的代理，使用不同的模型配置
        members = []
        
        # 研究代理 - 使用OpenAI模型
        research_model = await adapter.create_agno_model(provider_type="openai")
        if research_model:
            research_agent = Agent(
                model=research_model,
                name="Research Agent",
                description="研究专家代理",
                instructions=["进行深度研究", "提供详细分析"]
            )
            members.append(research_agent)
        
        # 分析代理 - 使用Anthropic模型（如果可用）
        analysis_model = await adapter.create_agno_model(provider_type="anthropic")
        if analysis_model:
            analysis_agent = Agent(
                model=analysis_model,
                name="Analysis Agent",
                description="分析专家代理",
                instructions=["进行逻辑分析", "提供客观判断"]
            )
            members.append(analysis_agent)
        
        # 如果没有足够的成员，添加默认代理
        if len(members) < 2:
            default_model = await adapter.create_agno_model()
            if default_model:
                default_agent = Agent(
                    model=default_model,
                    name="Default Agent",
                    description="默认代理",
                    instructions=["提供通用帮助"]
                )
                members.append(default_agent)
        
        if members:
            # 创建团队协调模型
            coordinator_model = await adapter.create_agno_model(provider_type="openai")
            if not coordinator_model:
                coordinator_model = await adapter.create_agno_model()
            
            if coordinator_model:
                team = Team(
                    mode="coordinate",
                    members=members,
                    model=coordinator_model,
                    name="配置化团队示例",
                    instructions=[
                        "协调团队成员的工作",
                        "整合不同专家的意见",
                        "提供全面的解决方案"
                    ]
                )
                logger.info(f"创建配置化团队成功，成员数量: {len(members)}")
                return team
        
        logger.warning("无法创建团队成员")
        return None
        
    except Exception as e:
        logger.error(f"创建配置化团队失败: {e}")
        return None


async def example_list_available_configurations():
    """示例：列出可用的模型配置"""
    try:
        adapter = get_model_adapter()
        
        # 列出可用提供商
        providers = await adapter.list_available_providers()
        logger.info(f"可用提供商数量: {len(providers)}")
        for provider in providers:
            logger.info(f"  - {provider['name']} ({provider['provider_type']}) - "
                       f"模型数量: {provider['model_count']}")
        
        # 列出可用模型
        models = await adapter.list_available_models()
        logger.info(f"可用模型数量: {len(models)}")
        for model in models[:5]:  # 只显示前5个
            logger.info(f"  - {model['model_id']} ({model['provider']}) - "
                       f"上下文: {model['context_window']}")
        
        return {
            "providers": providers,
            "models": models
        }
        
    except Exception as e:
        logger.error(f"列出配置失败: {e}")
        return None


async def example_validate_model_configuration():
    """示例：验证模型配置"""
    try:
        adapter = get_model_adapter()
        
        # 获取默认配置并验证
        default_config = await adapter.get_default_model_config()
        if default_config:
            is_valid = await adapter.validate_model_config(default_config)
            logger.info(f"默认模型配置验证结果: {is_valid}")
            logger.info(f"默认模型: {default_config.model_id} ({default_config.provider_type})")
            return is_valid
        else:
            logger.warning("无法获取默认模型配置")
            return False
            
    except Exception as e:
        logger.error(f"验证模型配置失败: {e}")
        return False


async def example_model_fallback_mechanism():
    """示例：模型回退机制"""
    try:
        adapter = get_model_adapter()
        
        # 尝试使用不存在的模型
        model = await adapter.create_agno_model(model_id="non-existent-model")
        if model:
            logger.info("意外地创建了不存在的模型（可能是回退机制）")
        else:
            logger.info("正确地无法创建不存在的模型")
        
        # 尝试使用不存在的提供商
        model = await adapter.create_agno_model(provider_type="non-existent-provider")
        if model:
            logger.info("使用回退机制创建了模型")
        else:
            logger.info("无法创建不存在提供商的模型")
        
        # 测试默认回退
        default_model = await adapter.create_agno_model()
        if default_model:
            logger.info("默认回退机制工作正常")
            return True
        else:
            logger.warning("默认回退机制失败")
            return False
            
    except Exception as e:
        logger.error(f"测试回退机制失败: {e}")
        return False


async def run_all_examples():
    """运行所有示例"""
    logger.info("开始运行模型配置适配器示例")
    
    # 1. 基本代理创建
    logger.info("\n=== 1. 基本代理创建示例 ===")
    agent = await example_create_agent_with_configured_model()
    if agent:
        logger.info("✓ 基本代理创建成功")
    
    # 2. 特定提供商代理创建
    logger.info("\n=== 2. 特定提供商代理创建示例 ===")
    provider_agent = await example_create_agent_with_specific_provider()
    if provider_agent:
        logger.info("✓ 特定提供商代理创建成功")
    
    # 3. 团队创建
    logger.info("\n=== 3. 配置化团队创建示例 ===")
    team = await example_create_team_with_configured_models()
    if team:
        logger.info("✓ 配置化团队创建成功")
    
    # 4. 列出配置
    logger.info("\n=== 4. 列出可用配置示例 ===")
    configs = await example_list_available_configurations()
    if configs:
        logger.info("✓ 配置列出成功")
    
    # 5. 验证配置
    logger.info("\n=== 5. 验证模型配置示例 ===")
    is_valid = await example_validate_model_configuration()
    if is_valid:
        logger.info("✓ 模型配置验证成功")
    
    # 6. 回退机制
    logger.info("\n=== 6. 模型回退机制示例 ===")
    fallback_works = await example_model_fallback_mechanism()
    if fallback_works:
        logger.info("✓ 回退机制工作正常")
    
    logger.info("\n所有示例运行完成")


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行示例
    asyncio.run(run_all_examples()) 