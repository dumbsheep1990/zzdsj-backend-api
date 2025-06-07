#!/usr/bin/env python3
"""
AI知识图谱框架简单测试脚本
测试三元组提取、实体标准化、关系推理和可视化生成
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.frameworks.ai_knowledge_graph.processor import KnowledgeGraphProcessor
from app.frameworks.ai_knowledge_graph.config import get_config

# 测试文本
TEST_TEXT = """
人工智能（AI）是一个快速发展的技术领域。OpenAI开发了GPT系列模型，包括GPT-3和GPT-4。
这些模型使用了Transformer架构，由Vaswani等人在2017年提出。

自然语言处理（NLP）是人工智能的一个重要分支。深度学习revolutionized了NLP领域。
BERT模型由Google开发，使用了双向编码器表示。

机器学习依赖于大量数据进行训练。神经网络是深度学习的基础。
卷积神经网络（CNN）特别适合图像处理任务。循环神经网络（RNN）用于序列数据处理。

Tesla公司的自动驾驶技术使用了计算机视觉和机器学习。Elon Musk是Tesla的CEO。
自动驾驶汽车需要处理复杂的交通环境。

知识图谱可以表示实体之间的关系。图数据库用于存储知识图谱。
语义网络是知识表示的一种方法。
"""

def progress_callback(task_id: str, status: str, progress: float, info: dict = None):
    """进度回调函数"""
    print(f"[{task_id}] {status}: {progress:.1%} {info or ''}")

def test_ai_knowledge_graph():
    """测试AI知识图谱框架"""
    print("=" * 50)
    print("AI知识图谱框架测试")
    print("=" * 50)
    
    try:
        # 1. 初始化处理器
        print("\n1. 初始化知识图谱处理器...")
        config_override = {
            "chunking": {
                "chunk_size": 300,
                "overlap": 50
            },
            "extraction": {
                "model": "gpt-4o-mini",
                "max_tokens": 2000,
                "temperature": 0.1
            },
            "standardization": {
                "enabled": True,
                "use_llm_for_entities": False  # 先测试基础功能
            },
            "inference": {
                "enabled": True,
                "use_llm_for_inference": False  # 先测试基础功能
            },
            "visualization": {
                "theme": "light",
                "node_size_range": [10, 50]
            }
        }
        
        processor = KnowledgeGraphProcessor(config_override)
        print("✓ 处理器初始化成功")
        
        # 2. 处理文本
        print("\n2. 开始处理测试文本...")
        print(f"文本长度: {len(TEST_TEXT)} 字符")
        
        result = processor.process_text(
            text=TEST_TEXT,
            graph_id="test_graph",
            callback=progress_callback,
            task_id="test_task",
            save_visualization=True,
            return_visualization=True
        )
        
        print("✓ 文本处理完成")
        
        # 3. 显示结果
        print("\n3. 处理结果:")
        print(f"提取的三元组数量: {len(result['triples'])}")
        print(f"图谱统计: {result['stats']}")
        
        # 4. 显示部分三元组
        print("\n4. 前10个三元组示例:")
        for i, triple in enumerate(result['triples'][:10]):
            print(f"  {i+1}. {triple['subject']} -> {triple['predicate']} -> {triple['object']}")
        
        # 5. 检查可视化文件
        print("\n5. 可视化文件检查:")
        config = get_config()
        output_file = Path(config.base_dir) / "test_graph.html"
        
        if output_file.exists():
            file_size = output_file.stat().st_size
            print(f"✓ HTML文件生成成功: {output_file}")
            print(f"  文件大小: {file_size:,} 字节")
            print(f"  可在浏览器中打开: file://{output_file.absolute()}")
        else:
            print("✗ HTML文件未找到")
        
        # 6. 检查返回的可视化内容
        if result.get('visualization'):
            html_length = len(result['visualization'])
            print(f"✓ 返回的HTML内容长度: {html_length:,} 字符")
        else:
            print("✗ 未返回HTML内容")
        
        print("\n" + "=" * 50)
        print("测试完成!")
        print("=" * 50)
        
        return result
        
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_individual_components():
    """测试各个组件"""
    print("\n" + "=" * 50)
    print("组件单独测试")
    print("=" * 50)
    
    try:
        processor = KnowledgeGraphProcessor()
        
        # 测试仅提取三元组
        print("\n1. 测试三元组提取...")
        triples = processor.extract_triples_only(TEST_TEXT)
        print(f"提取到 {len(triples)} 个三元组")
        
        if triples:
            # 测试标准化
            print("\n2. 测试实体标准化...")
            standardized = processor.standardize_triples(triples)
            print(f"标准化后 {len(standardized)} 个三元组")
            
            # 测试推理
            print("\n3. 测试关系推理...")
            inferred = processor.infer_relationships(standardized)
            print(f"推理后 {len(inferred)} 个三元组")
            
            # 测试可视化
            print("\n4. 测试可视化生成...")
            html_content = processor.generate_visualization(inferred)
            print(f"生成的HTML长度: {len(html_content):,} 字符")
        
        print("✓ 组件测试完成")
        
    except Exception as e:
        print(f"✗ 组件测试失败: {str(e)}")

if __name__ == "__main__":
    print("开始AI知识图谱框架测试...")
    
    # 主要测试
    result = test_ai_knowledge_graph()
    
    # 组件测试
    if result:
        test_individual_components()
    
    print("\n所有测试完成!") 