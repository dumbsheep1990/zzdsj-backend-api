"""
Agno智能体模版化集成测试
测试三种模版的创建、配置解析和执行图引擎功能
"""

import pytest
import asyncio
from typing import Dict, Any

from app.frameworks.agno.templates import (
    TemplateType, 
    get_template, 
    list_available_templates,
    BASIC_CONVERSATION_TEMPLATE,
    KNOWLEDGE_BASE_TEMPLATE,
    DEEP_THINKING_TEMPLATE
)
from app.frameworks.agno.template_manager import (
    AgnoTemplateManager,
    get_template_manager,
    create_agent_from_template
)
from app.frameworks.agno.frontend_config_parser import (
    AgnoConfigParser,
    get_config_parser,
    parse_frontend_config,
    validate_frontend_config
)
from app.frameworks.agno.execution_engine import (
    AgnoExecutionEngine,
    create_execution_engine,
    execute_with_graph
)


class TestAgnoTemplates:
    """测试Agno模版定义"""
    
    def test_template_definitions(self):
        """测试模版定义完整性"""
        # 测试所有三种模版都已定义
        templates = list_available_templates()
        assert len(templates) == 3
        
        template_ids = [t.template_id for t in templates]
        assert TemplateType.BASIC_CONVERSATION.value in template_ids
        assert TemplateType.KNOWLEDGE_BASE.value in template_ids
        assert TemplateType.DEEP_THINKING.value in template_ids
    
    def test_basic_conversation_template(self):
        """测试基础对话模版"""
        template = get_template(TemplateType.BASIC_CONVERSATION.value)
        
        assert template.name == "基础对话助手"
        assert template.estimated_cost == "低"
        assert "多轮对话" in template.capabilities
        assert "search" in template.default_tools
        assert len(template.execution_graph.nodes) > 0
        assert len(template.execution_graph.edges) > 0
    
    def test_knowledge_base_template(self):
        """测试知识库问答模版"""
        template = get_template(TemplateType.KNOWLEDGE_BASE.value)
        
        assert template.name == "知识库问答专家"
        assert template.estimated_cost == "中"
        assert "知识检索" in template.capabilities
        assert "knowledge_search" in template.default_tools
        assert any(node.type == "retriever" for node in template.execution_graph.nodes)
    
    def test_deep_thinking_template(self):
        """测试深度思考模版"""
        template = get_template(TemplateType.DEEP_THINKING.value)
        
        assert template.name == "深度思考分析师"
        assert template.estimated_cost == "高"
        assert "任务分解" in template.capabilities
        assert "reasoning" in template.default_tools
        assert any(node.type == "decomposer" for node in template.execution_graph.nodes)


class TestTemplateManager:
    """测试模版管理器"""
    
    def test_get_available_templates(self):
        """测试获取可用模版"""
        manager = get_template_manager()
        templates = manager.get_available_templates()
        
        assert len(templates) == 3
        assert all("template_id" in t for t in templates)
        assert all("name" in t for t in templates)
        assert all("capabilities" in t for t in templates)
    
    def test_get_template_details(self):
        """测试获取模版详情"""
        manager = get_template_manager()
        details = manager.get_template_details(TemplateType.BASIC_CONVERSATION.value)
        
        assert details is not None
        assert details["template_id"] == TemplateType.BASIC_CONVERSATION.value
        assert "execution_graph" in details
        assert len(details["execution_graph"]["nodes"]) > 0
    
    def test_recommend_templates(self):
        """测试模版推荐"""
        manager = get_template_manager()
        
        # 测试基于使用场景的推荐
        recommendations = manager.recommend_templates({
            "use_case": "客户服务",
            "complexity": "low",
            "budget": "low"
        })
        
        assert len(recommendations) > 0
        # 基础对话模版应该得分最高
        top_recommendation = recommendations[0]
        assert top_recommendation["template"]["template_id"] == TemplateType.BASIC_CONVERSATION.value


class TestFrontendConfigParser:
    """测试前端配置解析器"""
    
    @pytest.fixture
    def sample_frontend_config(self):
        """示例前端配置"""
        return {
            "template_selection": {
                "template_id": TemplateType.BASIC_CONVERSATION.value,
                "template_name": "基础对话助手"
            },
            "basic_configuration": {
                "agent_name": "测试助手",
                "agent_description": "用于测试的AI助手",
                "personality": "friendly",
                "language": "zh-CN",
                "response_length": "medium"
            },
            "model_configuration": {
                "model_provider": "openai",
                "model_name": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 1000,
                "cost_tier": "standard"
            },
            "capability_configuration": {
                "enabled_tools": ["search", "calculator"],
                "knowledge_bases": [],
                "external_integrations": [],
                "custom_instructions": ["保持友好的语调"]
            },
            "advanced_configuration": {
                "execution_timeout": 300,
                "max_iterations": 10,
                "enable_team_mode": False,
                "enable_streaming": True,
                "enable_citations": True,
                "privacy_level": "standard"
            }
        }
    
    @pytest.mark.asyncio
    async def test_config_validation(self, sample_frontend_config):
        """测试配置验证"""
        result = await validate_frontend_config(sample_frontend_config)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_config_validation_errors(self):
        """测试配置验证错误"""
        invalid_config = {
            "template_selection": {
                "template_id": "invalid_template"
            },
            "basic_configuration": {
                "agent_name": "",  # 空名称
                "agent_description": "描述"
            }
        }
        
        result = await validate_frontend_config(invalid_config)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_parse_frontend_config(self, sample_frontend_config):
        """测试配置解析"""
        parser = get_config_parser()
        agent_config = await parser.parse_frontend_config(sample_frontend_config)
        
        assert agent_config.name == "测试助手"
        assert agent_config.description == "用于测试的AI助手"
        assert "保持友好的语调" in agent_config.instructions
        assert agent_config.model_config["model_id"] == "gpt-4o-mini"
        assert agent_config.custom_params["template_id"] == TemplateType.BASIC_CONVERSATION.value
    
    def test_get_default_config(self):
        """测试获取默认配置"""
        parser = get_config_parser()
        default_config = parser.get_default_config_for_template(TemplateType.BASIC_CONVERSATION.value)
        
        assert default_config is not None
        assert default_config["template_selection"]["template_id"] == TemplateType.BASIC_CONVERSATION.value
        assert default_config["basic_configuration"]["agent_name"] == "基础对话助手"
        assert len(default_config["capability_configuration"]["enabled_tools"]) > 0


class TestExecutionEngine:
    """测试执行图引擎"""
    
    @pytest.mark.asyncio
    async def test_basic_execution_graph(self):
        """测试基础对话模版的执行图"""
        template = get_template(TemplateType.BASIC_CONVERSATION.value)
        engine = create_execution_engine(template.execution_graph)
        
        # 测试执行图可视化
        visualization = engine.visualize_graph()
        assert "nodes" in visualization
        assert "edges" in visualization
        assert len(visualization["nodes"]) > 0
    
    @pytest.mark.asyncio
    async def test_execution_with_graph(self):
        """测试使用执行图执行任务"""
        template = get_template(TemplateType.BASIC_CONVERSATION.value)
        
        test_input = "你好，请介绍一下自己"
        result = await execute_with_graph(template.execution_graph, test_input)
        
        assert result.success is True
        assert result.result is not None
        assert result.execution_time > 0
        assert "execution_path" in result.metadata
    
    @pytest.mark.asyncio
    async def test_knowledge_base_execution_graph(self):
        """测试知识库模版的执行图"""
        template = get_template(TemplateType.KNOWLEDGE_BASE.value)
        engine = create_execution_engine(template.execution_graph)
        
        test_input = "什么是人工智能？"
        
        # 创建执行上下文
        from app.frameworks.agno.orchestration.types import ExecutionContext
        import uuid
        
        context = ExecutionContext(
            request_id=str(uuid.uuid4()),
            user_id="test_user",
            session_id=None
        )
        
        result = await engine.execute(test_input, context)
        
        assert result.success is True
        # 检查执行路径中是否包含检索节点
        execution_path = result.metadata.get("execution_path", [])
        node_types = [step.get("node_type") for step in execution_path]
        assert "retriever" in node_types or "analyzer" in node_types
    
    @pytest.mark.asyncio
    async def test_deep_thinking_execution_graph(self):
        """测试深度思考模版的执行图"""
        template = get_template(TemplateType.DEEP_THINKING.value)
        engine = create_execution_engine(template.execution_graph)
        
        test_input = "分析一下当前AI技术的发展趋势和潜在风险"
        
        from app.frameworks.agno.orchestration.types import ExecutionContext
        import uuid
        
        context = ExecutionContext(
            request_id=str(uuid.uuid4()),
            user_id="test_user", 
            session_id=None
        )
        
        result = await engine.execute(test_input, context)
        
        assert result.success is True
        # 检查执行路径中是否包含分解节点
        execution_path = result.metadata.get("execution_path", [])
        node_types = [step.get("node_type") for step in execution_path]
        assert "decomposer" in node_types or "assessor" in node_types


class TestEndToEndIntegration:
    """端到端集成测试"""
    
    @pytest.fixture
    def complete_config_basic(self):
        """完整的基础对话配置"""
        return {
            "template_selection": {
                "template_id": TemplateType.BASIC_CONVERSATION.value
            },
            "basic_configuration": {
                "agent_name": "友好助手",
                "agent_description": "一个友好的对话助手",
                "personality": "friendly"
            },
            "model_configuration": {
                "model_provider": "openai",
                "model_name": "gpt-4o-mini",
                "temperature": 0.8,
                "max_tokens": 800
            },
            "capability_configuration": {
                "enabled_tools": ["search", "datetime"],
                "knowledge_bases": [],
                "external_integrations": [],
                "custom_instructions": ["始终保持积极正面的态度"]
            },
            "advanced_configuration": {
                "execution_timeout": 180,
                "max_iterations": 5,
                "enable_streaming": True,
                "enable_citations": False
            }
        }
    
    @pytest.fixture
    def complete_config_knowledge(self):
        """完整的知识库配置"""
        return {
            "template_selection": {
                "template_id": TemplateType.KNOWLEDGE_BASE.value
            },
            "basic_configuration": {
                "agent_name": "知识专家",
                "agent_description": "基于知识库的专业问答助手",
                "personality": "professional"
            },
            "model_configuration": {
                "model_provider": "openai",
                "model_name": "gpt-4",
                "temperature": 0.3,
                "max_tokens": 2000
            },
            "capability_configuration": {
                "enabled_tools": ["knowledge_search", "citation_generator"],
                "knowledge_bases": ["kb_1", "kb_2"],
                "external_integrations": [],
                "custom_instructions": ["总是提供准确的引用"]
            },
            "advanced_configuration": {
                "execution_timeout": 300,
                "max_iterations": 8,
                "enable_citations": True
            }
        }
    
    @pytest.mark.asyncio
    async def test_complete_workflow_basic(self, complete_config_basic):
        """测试基础对话模版的完整工作流程"""
        # 1. 验证配置
        validation_result = await validate_frontend_config(complete_config_basic)
        assert validation_result["valid"] is True
        
        # 2. 解析配置
        parser = get_config_parser()
        agent_config = await parser.parse_frontend_config(complete_config_basic)
        assert agent_config.name == "友好助手"
        
        # 3. 获取模版信息
        manager = get_template_manager()
        template_details = manager.get_template_details(TemplateType.BASIC_CONVERSATION.value)
        assert template_details is not None
        
        # 4. 测试执行图
        template = get_template(TemplateType.BASIC_CONVERSATION.value)
        result = await execute_with_graph(
            template.execution_graph, 
            "你好，今天天气怎么样？"
        )
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_complete_workflow_knowledge(self, complete_config_knowledge):
        """测试知识库模版的完整工作流程"""
        # 1. 验证配置
        validation_result = await validate_frontend_config(complete_config_knowledge)
        assert validation_result["valid"] is True
        
        # 2. 解析配置
        parser = get_config_parser()
        agent_config = await parser.parse_frontend_config(complete_config_knowledge)
        assert agent_config.name == "知识专家"
        assert "总是提供准确的引用" in agent_config.instructions
        
        # 3. 测试执行图
        template = get_template(TemplateType.KNOWLEDGE_BASE.value)
        result = await execute_with_graph(
            template.execution_graph,
            "什么是机器学习？"
        )
        assert result.success is True
        
        # 检查是否有检索相关的执行步骤
        execution_path = result.metadata.get("execution_path", [])
        assert len(execution_path) > 0
    
    @pytest.mark.asyncio
    async def test_template_recommendation_and_creation(self):
        """测试模版推荐和创建流程"""
        manager = get_template_manager()
        
        # 1. 获取推荐
        recommendations = manager.recommend_templates({
            "use_case": "技术支持",
            "complexity": "medium",
            "budget": "medium"
        })
        
        assert len(recommendations) > 0
        
        # 知识库模版应该被推荐给技术支持场景
        recommended_ids = [r["template"]["template_id"] for r in recommendations]
        assert TemplateType.KNOWLEDGE_BASE.value in recommended_ids
        
        # 2. 获取推荐模版的默认配置
        top_template_id = recommendations[0]["template"]["template_id"]
        parser = get_config_parser()
        default_config = parser.get_default_config_for_template(top_template_id)
        
        assert default_config is not None
        assert default_config["template_selection"]["template_id"] == top_template_id
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效模版ID
        with pytest.raises(ValueError):
            get_template("invalid_template_id")
        
        # 测试无效配置
        manager = get_template_manager()
        result = manager.get_template_details("nonexistent_template")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self):
        """性能基准测试"""
        import time
        
        # 测试配置解析性能
        sample_config = {
            "template_selection": {"template_id": TemplateType.BASIC_CONVERSATION.value},
            "basic_configuration": {
                "agent_name": "性能测试",
                "agent_description": "性能测试助手"
            },
            "model_configuration": {
                "model_provider": "openai",
                "model_name": "gpt-4o-mini"
            },
            "capability_configuration": {"enabled_tools": []},
            "advanced_configuration": {}
        }
        
        start_time = time.time()
        
        for _ in range(10):
            validation_result = await validate_frontend_config(sample_config)
            assert validation_result["valid"] is True
        
        validation_time = time.time() - start_time
        assert validation_time < 1.0  # 10次验证应该在1秒内完成
        
        # 测试执行图性能
        template = get_template(TemplateType.BASIC_CONVERSATION.value)
        
        start_time = time.time()
        
        for _ in range(5):
            result = await execute_with_graph(template.execution_graph, "测试输入")
            assert result.success is True
        
        execution_time = time.time() - start_time
        assert execution_time < 5.0  # 5次执行应该在5秒内完成


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])