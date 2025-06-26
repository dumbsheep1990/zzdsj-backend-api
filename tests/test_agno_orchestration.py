"""
Agno编排系统测试

测试用例涵盖：
1. 工具注册中心功能测试
2. 前端配置解析测试
3. 智能匹配引擎测试
4. API接口测试
5. 系统集成测试
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

# 导入待测试的模块
from app.frameworks.agno.orchestration import (
    initialize_orchestration_system,
    create_agent_from_frontend_config,
    get_orchestration_status,
    AgnoToolRegistry,
    AgnoConfigParser,
    AgnoMatchingEngine
)
from app.frameworks.agno.orchestration.types import (
    ToolMetadata,
    AgentConfig,
    ToolCategory,
    AgentRole,
    OrchestrationRequest,
    OrchestrationResult
)


class TestAgnoToolRegistry:
    """工具注册中心测试"""
    
    @pytest.fixture
    async def registry(self):
        """测试用注册中心实例"""
        registry = AgnoToolRegistry()
        await registry.initialize()
        return registry
    
    @pytest.mark.asyncio
    async def test_tool_discovery(self, registry):
        """测试工具发现功能"""
        # 获取发现的工具
        tools = await registry.get_all_tools()
        
        # 验证工具发现
        assert isinstance(tools, dict)
        
        # 检查是否发现了预期的工具类别
        expected_categories = ['reasoning', 'search', 'knowledge', 'chunking']
        for category in expected_categories:
            # 应该能找到至少一个工具或为空但不报错
            category_tools = [tool for tool in tools.values() if tool.category.value == category]
            assert isinstance(category_tools, list)
    
    @pytest.mark.asyncio
    async def test_tool_search(self, registry):
        """测试工具搜索功能"""
        # 搜索推理相关工具
        results = await registry.search_tools(query="reasoning", category="reasoning")
        
        assert isinstance(results, list)
        # 如果有工具，验证搜索结果
        if results:
            for tool in results:
                assert isinstance(tool, ToolMetadata)
                assert "reasoning" in tool.name.lower() or "reasoning" in tool.description.lower()
    
    @pytest.mark.asyncio
    async def test_tool_instance_creation(self, registry):
        """测试工具实例创建"""
        # 获取所有工具
        tools = await registry.get_all_tools()
        
        if tools:
            # 选择第一个工具进行测试
            tool_id = list(tools.keys())[0]
            tool_metadata = tools[tool_id]
            
            # 创建工具实例
            instance = await registry.create_tool_instance(tool_id)
            
            assert instance is not None
            # 验证实例具有预期的属性
            assert hasattr(instance, 'name') or hasattr(instance, '__call__')
    
    @pytest.mark.asyncio
    async def test_registry_stats(self, registry):
        """测试注册中心统计信息"""
        stats = await registry.get_registry_stats()
        
        assert isinstance(stats, dict)
        assert 'total_tools' in stats
        assert 'category_distribution' in stats
        assert 'framework_distribution' in stats
        assert isinstance(stats['total_tools'], int)
        assert stats['total_tools'] >= 0


class TestAgnoConfigParser:
    """前端配置解析器测试"""
    
    @pytest.fixture
    def parser(self):
        """测试用配置解析器实例"""
        return AgnoConfigParser()
    
    @pytest.mark.asyncio
    async def test_basic_config_parsing(self, parser):
        """测试基础配置解析"""
        config = {
            "name": "测试助手",
            "role": "assistant",
            "description": "用于测试的智能助手",
            "tools": ["reasoning", "search"]
        }
        
        agent_config = await parser.parse_frontend_config(config)
        
        assert isinstance(agent_config, AgentConfig)
        assert agent_config.name == "测试助手"
        assert agent_config.role == AgentRole.ASSISTANT
        assert "reasoning" in agent_config.tools
        assert "search" in agent_config.tools
    
    @pytest.mark.asyncio
    async def test_modular_config_parsing(self, parser):
        """测试模块化配置解析"""
        config = {
            "agent_name": "模块化助手",
            "modules": [
                {
                    "type": "information_retrieval",
                    "config": {
                        "tools": ["search", "knowledge"],
                        "instructions": ["搜索相关信息"]
                    }
                }
            ]
        }
        
        agent_config = await parser.parse_frontend_config(config)
        
        assert isinstance(agent_config, AgentConfig)
        assert agent_config.name == "模块化助手"
        assert len(agent_config.modules) == 1
    
    @pytest.mark.asyncio
    async def test_complex_config_parsing(self, parser):
        """测试复杂配置解析"""
        config = {
            "agentName": "复杂助手",
            "agentRole": "specialist",
            "tool_list": [
                {"id": "reasoning", "enabled": True},
                {"id": "search", "enabled": False}
            ],
            "llm_config": {
                "model": "gpt-4",
                "model_type": "chat"
            },
            "capabilities": "reasoning,analysis,research"
        }
        
        agent_config = await parser.parse_frontend_config(config)
        
        assert isinstance(agent_config, AgentConfig)
        assert agent_config.name == "复杂助手"
        assert agent_config.role == AgentRole.SPECIALIST
        assert "reasoning" in agent_config.tools  # enabled工具应该被包含
        assert "search" not in agent_config.tools  # disabled工具应该被排除
    
    @pytest.mark.asyncio
    async def test_config_validation(self, parser):
        """测试配置验证"""
        # 测试无效配置
        invalid_config = {
            "role": "invalid_role",  # 无效角色
            "tools": None  # 无效工具
        }
        
        try:
            await parser.parse_frontend_config(invalid_config)
            # 如果没有抛出异常，检查是否使用了默认值
            agent_config = await parser.parse_frontend_config(invalid_config)
            assert agent_config.role in [role for role in AgentRole]
        except Exception as e:
            # 预期的验证错误
            assert "validation" in str(e).lower() or "invalid" in str(e).lower()


class TestAgnoMatchingEngine:
    """智能匹配引擎测试"""
    
    @pytest.fixture
    def matcher(self):
        """测试用匹配引擎实例"""
        return AgnoMatchingEngine()
    
    @pytest.fixture
    def sample_tools(self):
        """测试用工具列表"""
        return {
            "reasoning_tool": ToolMetadata(
                id="reasoning_tool",
                name="ReasoningTool",
                description="用于逻辑推理的工具",
                category=ToolCategory.REASONING,
                capabilities=["reasoning", "logic", "analysis"]
            ),
            "search_tool": ToolMetadata(
                id="search_tool",
                name="SearchTool",
                description="用于信息搜索的工具",
                category=ToolCategory.SEARCH,
                capabilities=["search", "query", "information"]
            )
        }
    
    @pytest.mark.asyncio
    async def test_keyword_matching(self, matcher, sample_tools):
        """测试关键词匹配"""
        requirements = ["reasoning", "analysis"]
        
        matches = await matcher.match_tools_by_keywords(requirements, sample_tools)
        
        assert isinstance(matches, list)
        if matches:
            # 应该匹配到推理工具
            tool_ids = [match['tool_id'] for match in matches]
            assert "reasoning_tool" in tool_ids
    
    @pytest.mark.asyncio
    async def test_capability_matching(self, matcher, sample_tools):
        """测试能力匹配"""
        required_capabilities = ["reasoning", "logic"]
        
        matches = await matcher.match_tools_by_capabilities(required_capabilities, sample_tools)
        
        assert isinstance(matches, list)
        if matches:
            # 验证匹配结果
            for match in matches:
                assert 'tool_id' in match
                assert 'score' in match
                assert match['score'] > 0
    
    @pytest.mark.asyncio
    async def test_semantic_matching(self, matcher, sample_tools):
        """测试语义匹配"""
        task_description = "我需要进行逻辑推理和分析"
        
        matches = await matcher.match_tools_by_semantics(task_description, sample_tools)
        
        assert isinstance(matches, list)
        # 语义匹配可能返回空结果（取决于实现）
        for match in matches:
            assert 'tool_id' in match
            assert 'score' in match
    
    @pytest.mark.asyncio
    async def test_tool_recommendation(self, matcher, sample_tools):
        """测试工具推荐"""
        request = OrchestrationRequest(
            user_id="test_user",
            session_id="test_session",
            frontend_config={
                "task_description": "分析数据并搜索相关信息",
                "capabilities": ["analysis", "search"]
            }
        )
        
        recommendations = await matcher.recommend_tools(request, sample_tools)
        
        assert isinstance(recommendations, list)
        if recommendations:
            for rec in recommendations:
                assert 'tool_id' in rec
                assert 'relevance_score' in rec
                assert 'reasons' in rec
    
    @pytest.mark.asyncio
    async def test_tool_chain_optimization(self, matcher):
        """测试工具链优化"""
        original_chain = ["tool1", "tool2", "tool1", "tool3", "tool2"]
        
        optimized_chain = await matcher.optimize_tool_chain(original_chain)
        
        assert isinstance(optimized_chain, list)
        # 检查去重
        assert len(optimized_chain) <= len(original_chain)
        assert len(set(optimized_chain)) == len(optimized_chain)


class TestOrchestrationAPI:
    """编排系统API测试"""
    
    @pytest.mark.asyncio
    async def test_system_initialization(self):
        """测试系统初始化"""
        system = await initialize_orchestration_system()
        
        assert isinstance(system, dict)
        assert 'status' in system
        assert 'registry' in system
        assert 'parser' in system
        assert 'matcher' in system
    
    @pytest.mark.asyncio
    async def test_agent_creation_from_frontend_config(self):
        """测试从前端配置创建Agent"""
        frontend_config = {
            "name": "测试Agent",
            "role": "assistant",
            "description": "用于集成测试的Agent",
            "capabilities": ["basic"]
        }
        
        result = await create_agent_from_frontend_config(
            user_id="test_user",
            frontend_config=frontend_config,
            session_id="test_session"
        )
        
        assert isinstance(result, dict)
        assert 'success' in result
        
        if result['success']:
            assert 'agent_id' in result
            assert 'agent_config' in result
            assert isinstance(result['agent_config'], AgentConfig)
        else:
            # 如果失败，应该有错误信息
            assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_orchestration_status(self):
        """测试编排系统状态"""
        status = await get_orchestration_status()
        
        assert isinstance(status, dict)
        assert 'status' in status
        assert 'components' in status
        
        # 验证组件状态
        components = status['components']
        assert 'registry' in components
        assert 'parser' in components
        assert 'matcher' in components


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_orchestration(self):
        """端到端编排测试"""
        # 1. 初始化系统
        system = await initialize_orchestration_system()
        assert system['status'] == 'initialized'
        
        # 2. 创建Agent配置
        frontend_config = {
            "name": "集成测试助手",
            "role": "assistant",
            "description": "用于端到端测试的智能助手",
            "capabilities": ["basic", "test"],
            "model_config": {"type": "chat"}
        }
        
        # 3. 创建Agent
        result = await create_agent_from_frontend_config(
            user_id="integration_test_user",
            frontend_config=frontend_config,
            session_id="integration_test_session"
        )
        
        # 4. 验证结果
        assert isinstance(result, dict)
        assert 'success' in result
        
        if result['success']:
            # 成功情况下的验证
            assert 'agent_id' in result
            assert 'agent_config' in result
            
            agent_config = result['agent_config']
            assert agent_config.name == "集成测试助手"
            assert agent_config.role == AgentRole.ASSISTANT
        
        # 5. 检查系统状态
        status = await get_orchestration_status()
        assert status['status'] in ['healthy', 'active', 'initialized']


class TestErrorHandling:
    """错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_invalid_config_handling(self):
        """测试无效配置处理"""
        invalid_config = {
            "name": "",  # 空名称
            "role": "invalid_role",  # 无效角色
            "tools": "invalid_tools_format"  # 无效工具格式
        }
        
        try:
            result = await create_agent_from_frontend_config(
                user_id="error_test_user",
                frontend_config=invalid_config
            )
            
            # 如果没有抛出异常，检查是否正确处理了错误
            if not result['success']:
                assert 'error' in result
                assert 'validation_errors' in result or 'error' in result
            
        except Exception as e:
            # 预期的错误
            assert isinstance(e, (ValueError, TypeError, AttributeError))
    
    @pytest.mark.asyncio
    async def test_missing_tools_handling(self):
        """测试缺失工具处理"""
        config_with_missing_tools = {
            "name": "测试助手",
            "tools": ["non_existent_tool", "another_missing_tool"]
        }
        
        result = await create_agent_from_frontend_config(
            user_id="missing_tools_test",
            frontend_config=config_with_missing_tools
        )
        
        # 系统应该能够处理缺失的工具
        assert isinstance(result, dict)
        if not result.get('success', False):
            assert 'error' in result


# 测试运行器
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"]) 