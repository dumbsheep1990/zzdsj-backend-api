"""
Agno编排系统使用示例
展示完全解耦合的前端参数→解析→匹配→组装→执行→返回完整流程
"""

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

from . import (
    initialize_orchestration_system,
    create_agent_from_frontend_config,
    get_orchestration_status,
    AgentRole,
    ToolCategory
)

logger = logging.getLogger(__name__)

async def example_basic_orchestration():
    """基础编排示例"""
    print("=== Agno编排系统基础示例 ===")
    
    # 模拟前端配置 - 支持任意格式
    frontend_config = {
        "name": "智能研究助手",
        "role": "researcher",
        "description": "帮助用户进行深度研究和分析的AI助手",
        "instructions": [
            "你是一个专业的研究助手",
            "请提供准确和深入的分析",
            "使用逻辑推理解决问题"
        ],
        "capabilities": ["research", "analysis", "reasoning"],
        "model_config": {
            "type": "chat",
            "model_id": "gpt-4"
        }
    }
    
    try:
        # 创建Agent
        result = await create_agent_from_frontend_config(
            user_id="demo_user",
            frontend_config=frontend_config,
            session_id="demo_session"
        )
        
        if result['success']:
            print(f"✅ 成功创建Agent: {result['agent_config'].name}")
            print(f"   角色: {result['agent_config'].role.value}")
            print(f"   推荐工具: {result['recommended_tools']}")
            print(f"   系统信息: {result['system_info']}")
        else:
            print(f"❌ 创建失败: {result['error']}")
            
        return result
        
    except Exception as e:
        print(f"❌ 示例执行失败: {str(e)}")
        return None

async def example_modular_orchestration():
    """模块化编排示例 - 兼容现有orchestration系统"""
    print("\n=== 模块化编排示例 ===")
    
    # 模拟orchestration系统的模块化配置
    frontend_config = {
        "agent_name": "数据分析专家",
        "agent_type": "analyst",
        "modules": [
            {
                "type": "information_retrieval",
                "config": {
                    "tools": ["search", "knowledge"],
                    "instructions": ["搜索相关信息", "检索知识库"]
                }
            },
            {
                "type": "data_analysis_reasoning", 
                "config": {
                    "tools": ["reasoning", "analysis"],
                    "instructions": ["分析数据模式", "进行逻辑推理"]
                }
            },
            {
                "type": "output_generation",
                "config": {
                    "instructions": ["生成结构化报告"]
                }
            }
        ],
        "workflow": {
            "strategy": "sequential",
            "steps": [
                {"name": "信息收集", "tools": ["search"]},
                {"name": "数据分析", "tools": ["reasoning"]},
                {"name": "结果输出", "tools": ["formatting"]}
            ]
        }
    }
    
    try:
        result = await create_agent_from_frontend_config(
            user_id="analyst_user",
            frontend_config=frontend_config
        )
        
        if result['success']:
            print(f"✅ 模块化Agent创建成功")
            print(f"   名称: {result['agent_config'].name}")
            print(f"   指令数量: {len(result['agent_config'].instructions)}")
            print(f"   工具链: {result['recommended_tools']}")
        else:
            print(f"❌ 创建失败: {result['error']}")
            
        return result
        
    except Exception as e:
        print(f"❌ 模块化示例失败: {str(e)}")
        return None

async def example_tool_discovery():
    """工具发现示例"""
    print("\n=== 工具发现示例 ===")
    
    try:
        # 初始化系统
        system = await initialize_orchestration_system()
        
        if system['status'] == 'initialized':
            registry = system['registry']
            
            # 获取工具统计
            stats = await registry.get_registry_stats()
            print(f"✅ 工具注册中心状态:")
            print(f"   总工具数: {stats['total_tools']}")
            print(f"   工具实例数: {stats['total_instances']}")
            print(f"   类别分布: {stats['category_distribution']}")
            print(f"   框架分布: {stats['framework_distribution']}")
            
            # 按类别列出工具
            for category in ToolCategory:
                tools = await registry.list_tools(category)
                if tools:
                    print(f"\n   {category.value}类工具:")
                    for tool in tools[:3]:  # 只显示前3个
                        print(f"     - {tool.name}: {tool.description}")
            
            # 工具搜索示例
            search_results = await registry.search_tools("reasoning")
            print(f"\n🔍 搜索'reasoning'相关工具: 找到 {len(search_results)} 个")
            
            return stats
        else:
            print(f"❌ 系统初始化失败: {system.get('error')}")
            return None
            
    except Exception as e:
        print(f"❌ 工具发现失败: {str(e)}")
        return None

async def example_config_parsing():
    """配置解析示例"""
    print("\n=== 配置解析示例 ===")
    
    try:
        system = await initialize_orchestration_system()
        parser = system['parser']
        
        # 测试不同格式的配置
        test_configs = [
            # 简单格式
            {
                "name": "简单助手",
                "tools": "reasoning,search,knowledge"
            },
            
            # 复杂嵌套格式
            {
                "agentName": "复杂助手",
                "agentRole": "specialist",
                "tool_list": [
                    {"id": "reasoning", "enabled": True},
                    {"id": "search", "enabled": True}
                ],
                "llm_config": {
                    "model": "gpt-4",
                    "model_type": "chat"
                },
                "prompts": {
                    "system": "你是专业助手\n请提供准确答案",
                    "guidelines": ["保持专业", "逻辑清晰"]
                }
            },
            
            # 工作流格式
            {
                "title": "工作流助手",
                "type": "coordinator",
                "workflow": {
                    "strategy": "parallel",
                    "steps": [
                        {"tools": ["search", "knowledge"]},
                        {"tools": ["reasoning", "analysis"]}
                    ]
                }
            }
        ]
        
        for i, config in enumerate(test_configs, 1):
            print(f"\n--- 测试配置 {i} ---")
            try:
                agent_config = await parser.parse_frontend_config(config)
                print(f"✅ 解析成功:")
                print(f"   名称: {agent_config.name}")
                print(f"   角色: {agent_config.role.value}")
                print(f"   工具: {agent_config.tools}")
                print(f"   指令数: {len(agent_config.instructions)}")
                
                # 验证配置
                errors = await parser.validate_config(agent_config)
                if errors:
                    print(f"⚠️  验证警告: {errors}")
                else:
                    print(f"✅ 配置验证通过")
                    
            except Exception as e:
                print(f"❌ 解析失败: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置解析示例失败: {str(e)}")
        return False

async def example_tool_matching():
    """工具匹配示例"""
    print("\n=== 工具匹配示例 ===")
    
    try:
        system = await initialize_orchestration_system()
        matcher = system['matcher']
        registry = system['registry']
        
        # 获取可用工具
        available_tools = await registry.list_tools()
        
        # 测试不同的需求匹配
        test_requirements = [
            ["reasoning", "analysis"],
            ["search", "knowledge", "qa"],
            ["chunking", "processing"],
            ["file management", "system"]
        ]
        
        for i, requirements in enumerate(test_requirements, 1):
            print(f"\n--- 需求 {i}: {requirements} ---")
            
            # 匹配工具
            matched_tools = await matcher.match_tools(requirements, available_tools)
            print(f"✅ 匹配到工具: {matched_tools}")
            
            # 优化工具链
            optimized_tools = await matcher.optimize_tool_chain(matched_tools)
            print(f"🔧 优化后工具链: {optimized_tools}")
        
        # 测试智能推荐
        task_descriptions = [
            "我需要分析一些文档数据",
            "帮我搜索和整理研究资料", 
            "处理文件并提取关键信息",
            "进行逻辑推理和问题解决"
        ]
        
        print(f"\n--- 智能推荐测试 ---")
        for desc in task_descriptions:
            recommended = await matcher.recommend_tools(desc, {})
            print(f"任务: {desc}")
            print(f"推荐: {recommended}\n")
        
        return True
        
    except Exception as e:
        print(f"❌ 工具匹配示例失败: {str(e)}")
        return False

async def example_system_status():
    """系统状态示例"""
    print("\n=== 系统状态示例 ===")
    
    try:
        status = await get_orchestration_status()
        
        print(f"🔍 编排系统状态:")
        print(f"   状态: {status['status']}")
        print(f"   版本: {status.get('version', 'unknown')}")
        
        if status['status'] == 'healthy':
            print(f"   组件状态: {status['components']}")
            
            registry_info = status['registry']
            print(f"\n📊 注册中心信息:")
            print(f"   总工具数: {registry_info['total_tools']}")
            print(f"   初始化状态: {registry_info['initialized']}")
            print(f"   发现路径: {len(registry_info['discovery_paths'])}")
        else:
            print(f"❌ 系统错误: {status.get('error')}")
        
        return status
        
    except Exception as e:
        print(f"❌ 状态检查失败: {str(e)}")
        return None

async def run_all_examples():
    """运行所有示例"""
    print("🚀 开始运行Agno编排系统示例...")
    print(f"时间: {datetime.now()}")
    
    examples = [
        ("基础编排", example_basic_orchestration),
        ("模块化编排", example_modular_orchestration),
        ("工具发现", example_tool_discovery),
        ("配置解析", example_config_parsing),
        ("工具匹配", example_tool_matching),
        ("系统状态", example_system_status)
    ]
    
    results = {}
    
    for name, example_func in examples:
        print(f"\n{'='*50}")
        try:
            result = await example_func()
            results[name] = result
            print(f"✅ {name} 示例完成")
        except Exception as e:
            print(f"❌ {name} 示例失败: {str(e)}")
            results[name] = None
    
    print(f"\n{'='*50}")
    print("📈 示例运行总结:")
    for name, result in results.items():
        status = "✅ 成功" if result is not None else "❌ 失败"
        print(f"   {name}: {status}")
    
    return results

if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 运行示例
    asyncio.run(run_all_examples()) 