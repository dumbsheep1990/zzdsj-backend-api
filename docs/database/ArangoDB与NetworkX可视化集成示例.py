"""
ArangoDB与NetworkX可视化集成示例
展示如何无缝使用现有的可视化系统，无需重新实现
"""

import asyncio
import json
import tempfile
from pathlib import Path

async def demo_arangodb_networkx_integration():
    """演示ArangoDB与NetworkX可视化集成"""
    
    print("=== ArangoDB与NetworkX可视化集成演示 ===\n")
    
    # 1. 初始化图数据库服务
    print("1️⃣ 初始化知识图谱服务...")
    from app.services.knowledge.knowledge_graph_service import KnowledgeGraphService
    from app.dependencies import get_db
    
    # 获取数据库会话
    db_session = next(get_db())
    kg_service = KnowledgeGraphService(db_session)
    
    # 检查数据库状态
    db_info = await kg_service.get_database_info()
    print(f"   📊 数据库类型: {db_info.get('database_type')}")
    print(f"   🔧 支持NetworkX: {db_info.get('supports_networkx')}")
    print(f"   🎨 支持HTML可视化: {db_info.get('supports_html_visualization')}")
    print(f"   🏗️ 隔离策略: {db_info.get('isolation_strategy')}\n")
    
    # 2. 模拟用户和知识库
    user_id = 1
    knowledge_base_id = 101
    
    print("2️⃣ 准备测试数据...")
    
    # 模拟添加一些测试三元组
    test_triples = [
        {
            "subject": "ArangoDB",
            "predicate": "是",
            "object": "图数据库",
            "confidence": 0.95,
            "inferred": False
        },
        {
            "subject": "NetworkX",
            "predicate": "是",
            "object": "Python图库",
            "confidence": 0.98,
            "inferred": False
        },
        {
            "subject": "ArangoDB",
            "predicate": "支持",
            "object": "多模型数据",
            "confidence": 0.90,
            "inferred": False
        },
        {
            "subject": "NetworkX",
            "predicate": "用于",
            "object": "图算法计算",
            "confidence": 0.92,
            "inferred": False
        },
        {
            "subject": "PyVis",
            "predicate": "基于",
            "object": "NetworkX",
            "confidence": 0.85,
            "inferred": True
        },
        {
            "subject": "图数据库",
            "predicate": "存储",
            "object": "图结构数据",
            "confidence": 0.99,
            "inferred": False
        }
    ]
    
    # 保存到图数据库
    await kg_service.save_knowledge_graph(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        triples=test_triples,
        graph_name="demo_graph"
    )
    print(f"   ✅ 已保存 {len(test_triples)} 个三元组到ArangoDB\n")
    
    # 3. 生成各种类型的可视化
    print("3️⃣ 生成可视化（使用现有NetworkX实现）...\n")
    
    # 3.1 交互式可视化
    print("   🎯 生成交互式可视化...")
    interactive_result = await kg_service.generate_visualization(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        graph_name="demo_graph",
        visualization_type="interactive",
        config={
            "physics_enabled": True,
            "show_labels": True,
            "color_by_type": True
        }
    )
    
    if interactive_result.get("success"):
        print(f"   ✅ 交互式HTML已生成: {interactive_result['html_path']}")
        print(f"   📊 节点数: {interactive_result.get('triples_count', 0)}")
        print(f"   📈 统计: {interactive_result.get('statistics', {})}")
    else:
        print(f"   ❌ 交互式可视化失败: {interactive_result.get('error')}")
    
    print()
    
    # 3.2 简单可视化  
    print("   🎯 生成简单可视化...")
    simple_result = await kg_service.generate_visualization(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        graph_name="demo_graph",
        visualization_type="default",
        config={"theme": "light"}
    )
    
    if simple_result.get("success"):
        print(f"   ✅ 简单HTML已生成: {simple_result['html_path']}")
    else:
        print(f"   ❌ 简单可视化失败: {simple_result.get('error')}")
    
    print()
    
    # 4. 展示NetworkX兼容性
    print("4️⃣ 展示NetworkX完全兼容性...\n")
    
    # 4.1 导出NetworkX图对象
    print("   🔧 导出NetworkX图对象...")
    networkx_graph = await kg_service.export_networkx_graph(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        graph_name="demo_graph"
    )
    
    if networkx_graph:
        print(f"   ✅ NetworkX图导出成功:")
        print(f"      - 节点数: {networkx_graph.number_of_nodes()}")
        print(f"      - 边数: {networkx_graph.number_of_edges()}")
        print(f"      - 节点列表: {list(networkx_graph.nodes())}")
        
        # 4.2 使用NetworkX进行高级分析
        import networkx as nx
        
        print("\n   📊 NetworkX高级分析:")
        
        if networkx_graph.number_of_nodes() > 0:
            # 计算度中心性
            degree_centrality = nx.degree_centrality(networkx_graph)
            top_node = max(degree_centrality, key=degree_centrality.get)
            print(f"      - 最高度中心性节点: {top_node} (值: {degree_centrality[top_node]:.3f})")
            
            # 计算连通性
            is_connected = nx.is_connected(networkx_graph)
            print(f"      - 图连通性: {'连通' if is_connected else '不连通'}")
            
            # 计算密度
            density = nx.density(networkx_graph)
            print(f"      - 图密度: {density:.3f}")
            
            # 社区检测（如果有可用的算法）
            try:
                import networkx.algorithms.community as nxcom
                communities = list(nxcom.greedy_modularity_communities(networkx_graph))
                print(f"      - 社区数量: {len(communities)}")
                for i, community in enumerate(communities):
                    print(f"        社区{i+1}: {list(community)}")
            except Exception as e:
                print(f"      - 社区检测跳过: {str(e)}")
    else:
        print("   ❌ NetworkX图导出失败")
    
    print()
    
    # 5. 获取详细统计信息
    print("5️⃣ 获取图谱详细统计...")
    stats = await kg_service.get_graph_statistics(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        graph_name="demo_graph"
    )
    
    if "error" not in stats:
        print("   ✅ 统计信息:")
        print(f"      - 实体数量: {stats.get('nodes_count', 0)}")
        print(f"      - 关系数量: {stats.get('edges_count', 0)}")
        print(f"      - 关系类型数: {stats.get('relations_count', 0)}")
        if stats.get('entities'):
            print(f"      - 实体列表: {stats['entities'][:5]}{'...' if len(stats['entities']) > 5 else ''}")
        if stats.get('relations'):
            print(f"      - 关系列表: {stats['relations']}")
    else:
        print(f"   ❌ 获取统计失败: {stats.get('error')}")
    
    print()
    
    # 6. 演示桥接器直接使用
    print("6️⃣ 演示可视化桥接器直接使用...\n")
    
    from app.utils.storage.graph_storage.visualization_bridge import GraphVisualizationBridge
    
    # 获取图数据库适配器
    if not kg_service.graph_db:
        await kg_service._initialize_graph_database()
    
    bridge = GraphVisualizationBridge(kg_service.graph_db)
    
    # 使用桥接器生成可视化
    tenant_id = kg_service._build_tenant_id(user_id, knowledge_base_id)
    
    bridge_result = await bridge.generate_html_visualization(
        tenant_id=tenant_id,
        graph_name="demo_graph",
        visualization_type="interactive",
        config={"custom_style": True}
    )
    
    if bridge_result.get("success"):
        print("   ✅ 桥接器直接调用成功:")
        print(f"      - HTML路径: {bridge_result['html_path']}")
        print(f"      - 数据量: {bridge_result.get('triples_count', 0)} 三元组")
    else:
        print(f"   ❌ 桥接器调用失败: {bridge_result.get('error')}")
    
    print()
    
    # 7. 总结
    print("7️⃣ 集成总结:")
    print("   ✅ ArangoDB负责数据存储和多租户隔离")
    print("   ✅ NetworkX负责图算法计算和分析")
    print("   ✅ PyVis/Vis.js负责HTML可视化生成")
    print("   ✅ 现有可视化代码完全复用，无需重新实现")
    print("   ✅ 支持多种可视化类型：simple/interactive/enhanced/default")
    print("   ✅ 完美兼容现有的知识图谱框架和工具链")
    
    print("\n=== 演示完成 ===")

def demo_architecture_summary():
    """展示架构总结"""
    
    print("\n=== 🏗️ 架构设计总结 ===\n")
    
    print("📋 核心优势:")
    print("   ✅ 存储与计算分离：ArangoDB存储 + NetworkX计算")
    print("   ✅ 完全复用现有代码：无需重新实现HTML生成")
    print("   ✅ 双数据库支持：ArangoDB + PostgreSQL+AGE")
    print("   ✅ 统一API接口：配置驱动的数据库切换")
    print("   ✅ 多租户隔离：数据库级别完全隔离")
    
    print("\n🔧 技术栈组合:")
    print("   • ArangoDB: 多模型图数据库，支持原生图查询")
    print("   • NetworkX: Python图分析库，丰富的算法支持")
    print("   • PyVis: 基于Vis.js的Python可视化库")
    print("   • Vis.js: 前端交互式图可视化引擎")
    
    print("\n📊 数据流架构:")
    print("   文档输入 → AI提取三元组 → 存储到ArangoDB")
    print("                    ↓")
    print("   前端展示 ← HTML生成 ← NetworkX处理 ← 从ArangoDB查询")
    
    print("\n🎨 可视化类型支持:")
    print("   • simple: 基础PyVis可视化")
    print("   • interactive: 交互式控制界面") 
    print("   • enhanced: 高级组件和功能")
    print("   • default: 标准HTML生成")
    
    print("\n🚀 部署建议:")
    print("   • 开发环境: 使用PostgreSQL+AGE（完全免费）")
    print("   • 生产环境: 使用ArangoDB（高性能+多租户）")
    print("   • 混合环境: 配置驱动切换，支持平滑迁移")
    
    print("\n=== 架构总结完成 ===")

if __name__ == "__main__":
    print("🔥 ArangoDB与NetworkX可视化集成完整演示\n")
    
    # 运行主演示
    asyncio.run(demo_arangodb_networkx_integration())
    
    # 架构总结
    demo_architecture_summary()
    
    print("\n🎉 所有演示完成！现有NetworkX可视化代码完全可以复用，无需重新实现！") 