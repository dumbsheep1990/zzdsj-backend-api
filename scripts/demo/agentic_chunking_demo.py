#!/usr/bin/env python3
"""
Agentic文档切分功能演示脚本
展示基于Agno框架的智能文档切分能力
"""

import asyncio
import sys
import os
from pathlib import Path
import json
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.tools.advanced.agentic_chunking import (
    AgenticDocumentChunker,
    AgenticChunkingConfig,
    AgenticChunkingStrategy,
    create_agentic_chunker,
    agentic_chunk_text
)

from app.tools.advanced.agentic_chunking_integration import (
    get_agentic_chunking_manager,
    smart_chunk_text,
    get_chunking_recommendations
)

class AgenticChunkingDemo:
    """Agentic切分演示类"""
    
    def __init__(self):
        """初始化演示"""
        self.sample_texts = self._prepare_sample_texts()
        print("🚀 Agentic文档切分演示初始化完成")
    
    def _prepare_sample_texts(self) -> dict:
        """准备示例文本"""
        return {
            "technical_doc": """
# API文档示例

## 用户认证接口

### POST /api/auth/login
用于用户登录认证。

**请求参数：**
- username: 用户名（必填）
- password: 密码（必填）

**响应示例：**
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
      "id": 1,
      "username": "admin"
    }
  }
}
```

## 数据查询接口

### GET /api/data/users
获取用户列表。

**查询参数：**
- page: 页码（可选，默认1）
- limit: 每页数量（可选，默认10）

**响应格式：**
```json
{
  "success": true,
  "data": {
    "users": [...],
    "total": 100,
    "page": 1
  }
}
```
""",
            
            "academic_paper": """
摘要

本研究探讨了人工智能在医疗诊断中的应用及其发展前景。通过深度学习算法的应用，医疗AI系统在图像识别、疾病预测和治疗方案推荐方面展现出巨大潜力。

1. 引言

人工智能（AI）技术在近年来取得了显著进展，特别是在医疗健康领域的应用日益广泛。机器学习、深度学习等技术为医疗诊断带来了革命性的变化。

2. 相关工作

2.1 图像诊断技术
卷积神经网络（CNN）在医学影像分析中表现出色。研究表明，AI系统在某些疾病的诊断准确率已经达到或超过专业医生的水平。

2.2 自然语言处理在医疗中的应用
通过分析电子病历和医学文献，NLP技术能够辅助医生进行诊断决策，提高医疗服务效率。

3. 方法论

本研究采用多模态深度学习方法，结合图像数据和文本数据，构建了综合性的医疗诊断系统。

4. 实验结果

实验表明，我们提出的方法在多个医疗数据集上取得了优异的性能，平均准确率达到95.2%。

5. 结论

AI技术在医疗诊断领域具有广阔的应用前景，但仍需要解决数据隐私、算法可解释性等挑战。
""",
            
            "conversation": """
客服: 您好！欢迎咨询我们的在线客服，有什么可以帮助您的吗？

用户: 你好，我想了解一下你们的产品保修政策。

客服: 好的，我来为您详细介绍。我们的产品根据不同类别有不同的保修期：
- 电子产品：1年保修
- 家电产品：2年保修  
- 数码配件：6个月保修

用户: 那如果产品在保修期内出现质量问题怎么办？

客服: 如果是质量问题，我们提供以下服务：
1. 免费维修
2. 如果无法维修，可以免费更换同型号产品
3. 如果没有同型号，可以更换同价值的其他产品

用户: 需要提供什么材料吗？

客服: 需要您提供：
- 购买凭证（发票或订单截图）
- 产品序列号
- 问题描述和照片

用户: 明白了，谢谢！

客服: 不客气！如果您还有其他问题，随时联系我们。祝您生活愉快！
""",
            
            "news_article": """
科技前沿：量子计算机取得重大突破

据最新报道，IBM公司宣布其量子计算机在处理特定算法方面实现了重大突破，量子优势得到进一步验证。

量子计算的发展历程

量子计算技术的发展可以追溯到20世纪80年代。1982年，物理学家理查德·费曼首次提出了量子计算的概念。此后，这一领域经历了几个重要的发展阶段。

技术突破的意义

此次突破的意义在于：首先，它证明了量子计算机在某些特定问题上确实能够超越经典计算机。其次，这为未来的商业应用奠定了基础。

应用前景展望

专家预测，量子计算将在以下领域产生重大影响：
- 密码学和网络安全
- 药物研发和分子模拟
- 金融建模和风险分析
- 人工智能和机器学习

挑战与困难

尽管取得了进展，量子计算仍面临诸多挑战：量子比特的稳定性问题、量子纠错技术的完善、以及大规模商业化的成本问题。

结语

量子计算技术的发展前景广阔，但仍需要持续的研究投入和技术创新。
"""
        }
    
    async def demo_basic_chunking(self):
        """演示基础切分功能"""
        print("\n" + "="*60)
        print("📝 基础Agentic切分演示")
        print("="*60)
        
        strategy = AgenticChunkingStrategy.SEMANTIC_BOUNDARY
        sample_text = self.sample_texts["academic_paper"]
        
        print(f"✨ 使用策略: {strategy.value}")
        print(f"📄 文档长度: {len(sample_text)} 字符")
        
        try:
            # 创建基础配置
            config = AgenticChunkingConfig(
                strategy=strategy,
                max_chunk_size=1000,
                min_chunk_size=100,
                language="zh"
            )
            
            chunker = AgenticDocumentChunker(config)
            result = await chunker.chunk_document(sample_text)
            
            print(f"✅ 切分完成!")
            print(f"📊 生成块数: {result.total_chunks}")
            print(f"📏 块大小范围: {min(result.chunk_sizes)} - {max(result.chunk_sizes)} 字符")
            
            # 显示切分结果
            for i, chunk in enumerate(result.chunks):
                print(f"\n📋 块 {i+1} ({len(chunk.content)} 字符):")
                print("-" * 40)
                preview = chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
                print(preview)
                
        except Exception as e:
            print(f"❌ 切分失败: {str(e)}")
    
    async def demo_strategy_comparison(self):
        """演示不同策略的对比"""
        print("\n" + "="*60)
        print("🔍 策略对比演示")
        print("="*60)
        
        sample_text = self.sample_texts["technical_doc"]
        strategies = [
            AgenticChunkingStrategy.SEMANTIC_BOUNDARY,
            AgenticChunkingStrategy.TOPIC_TRANSITION,
            AgenticChunkingStrategy.TECHNICAL_DOCUMENT
        ]
        
        results = {}
        
        for strategy in strategies:
            print(f"\n🚀 测试策略: {strategy.value}")
            
            try:
                config = AgenticChunkingConfig(
                    strategy=strategy,
                    max_chunk_size=800,
                    language="zh"
                )
                
                chunker = AgenticDocumentChunker(config)
                result = await chunker.chunk_document(sample_text)
                
                results[strategy.value] = result
                
                print(f"  📊 块数: {result.total_chunks}")
                print(f"  📏 平均大小: {sum(result.chunk_sizes)/len(result.chunk_sizes):.0f} 字符")
                
            except Exception as e:
                print(f"  ❌ 策略 {strategy.value} 失败: {str(e)}")
        
        if results:
            best_strategy = max(results.items(), key=lambda x: x[1].total_chunks)
            print(f"\n🏆 最多块数策略: {best_strategy[0]} ({best_strategy[1].total_chunks} 个块)")
    
    async def demo_smart_chunking(self):
        """演示智能切分功能"""
        print("\n" + "="*60)
        print("🧠 智能切分演示")
        print("="*60)
        
        test_cases = [
            ("technical_doc", "技术文档"),
            ("conversation", "对话记录"),
            ("news_article", "新闻文章"),
            ("academic_paper", "学术论文")
        ]
        
        for text_key, description in test_cases:
            print(f"\n📝 处理 {description}...")
            content = self.sample_texts[text_key]
            
            try:
                # 获取切分建议
                recommendations = get_chunking_recommendations(content[:500])  # 使用前500字符分析
                print(f"  🔍 推荐工具: {recommendations['recommended_tool']}")
                print(f"  📈 内容复杂度: {recommendations['content_features']['complexity']}")
                
                # 执行智能切分
                result = await smart_chunk_text(content, content_type=description)
                
                print(f"  ✅ 切分完成: {result.total_chunks} 个块")
                print(f"  📏 大小范围: {min(result.chunk_sizes)} - {max(result.chunk_sizes)} 字符")
                
            except Exception as e:
                print(f"  ❌ 处理失败: {str(e)}")
    
    async def demo_custom_configuration(self):
        """演示自定义配置"""
        print("\n" + "="*60)
        print("⚙️ 自定义配置演示")
        print("="*60)
        
        # 创建自定义配置
        custom_config = AgenticChunkingConfig(
            strategy=AgenticChunkingStrategy.SEMANTIC_BOUNDARY,
            max_chunk_size=1500,
            min_chunk_size=300,
            chunk_overlap=100,
            llm_model="gpt-4o-mini",
            language="zh",
            semantic_threshold=0.8,
            quality_threshold=0.85
        )
        
        print("🛠️ 自定义配置参数:")
        config_dict = custom_config.to_dict()
        for key, value in config_dict.items():
            print(f"  {key}: {value}")
        
        # 使用自定义配置创建切分器
        chunker = AgenticDocumentChunker(custom_config)
        
        sample_text = self.sample_texts["news_article"]
        
        try:
            result = await chunker.chunk_document(sample_text)
            
            print(f"\n✅ 自定义配置切分完成!")
            print(f"📊 生成 {result.total_chunks} 个块")
            
            # 显示详细信息
            for i, chunk in enumerate(result.chunks):
                print(f"\n📋 块 {i+1}:")
                print(f"  📏 大小: {len(chunk.content)} 字符")
                print(f"  🏷️ 元数据: {chunk.metadata}")
                
        except Exception as e:
            print(f"❌ 自定义配置切分失败: {str(e)}")
    
    async def demo_batch_processing(self):
        """演示批量处理"""
        print("\n" + "="*60)
        print("🔄 批量处理演示")
        print("="*60)
        
        # 准备批量数据
        documents = []
        for text_key, content in self.sample_texts.items():
            documents.append({
                "content": content,
                "content_type": text_key,
                "metadata": {
                    "source": f"demo_{text_key}",
                    "timestamp": datetime.now().isoformat()
                }
            })
        
        print(f"📦 准备处理 {len(documents)} 个文档")
        
        try:
            manager = get_agentic_chunking_manager()
            results = await manager.batch_chunk_documents(
                documents, 
                auto_select=True,
                max_workers=3
            )
            
            print(f"✅ 批量处理完成!")
            
            # 统计结果
            total_chunks = sum(result.total_chunks for result in results)
            successful_docs = sum(1 for result in results if result.total_chunks > 0)
            
            print(f"📊 处理统计:")
            print(f"  成功文档: {successful_docs}/{len(documents)}")
            print(f"  总块数: {total_chunks}")
            print(f"  平均每文档: {total_chunks/successful_docs:.1f} 块")
            
            # 显示每个文档的结果
            for i, (doc, result) in enumerate(zip(documents, results)):
                content_type = doc["content_type"]
                print(f"\n📄 文档 {i+1} ({content_type}):")
                print(f"  块数: {result.total_chunks}")
                if result.chunk_sizes:
                    print(f"  平均块大小: {sum(result.chunk_sizes)/len(result.chunk_sizes):.0f} 字符")
                
                # 显示使用的策略
                if "strategy" in result.processing_metadata:
                    print(f"  使用策略: {result.processing_metadata['strategy']}")
            
            # 显示管理器统计
            stats = manager.get_stats()
            print(f"\n📈 管理器统计:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
                
        except Exception as e:
            print(f"❌ 批量处理失败: {str(e)}")
    
    async def demo_quality_analysis(self):
        """演示质量分析"""
        print("\n" + "="*60)
        print("📊 质量分析演示")
        print("="*60)
        
        sample_text = self.sample_texts["academic_paper"]
        
        # 使用高质量配置
        config = AgenticChunkingConfig(
            strategy=AgenticChunkingStrategy.SEMANTIC_BOUNDARY,
            max_chunk_size=1200,
            min_chunk_size=200,
            quality_threshold=0.8,
            semantic_threshold=0.75
        )
        
        chunker = AgenticDocumentChunker(config)
        
        try:
            result = await chunker.chunk_document(sample_text)
            
            print(f"✅ 质量分析完成!")
            print(f"📊 文档统计:")
            print(f"  总块数: {result.total_chunks}")
            print(f"  平均质量: {result.processing_metadata.get('average_quality', 0):.3f}")
            
            # 详细质量分析
            if "quality_scores" in result.processing_metadata:
                quality_scores = result.processing_metadata["quality_scores"]
                
                print(f"\n🎯 质量维度分析:")
                
                # 计算各维度平均分
                dimensions = ["semantic_coherence", "size_appropriateness", 
                            "boundary_naturalness", "structure_preservation"]
                
                for dim in dimensions:
                    avg_score = sum(score[dim] for score in quality_scores) / len(quality_scores)
                    print(f"  {dim}: {avg_score:.3f}")
                
                # 显示最佳和最差块
                overall_scores = [score["overall_score"] for score in quality_scores]
                best_idx = overall_scores.index(max(overall_scores))
                worst_idx = overall_scores.index(min(overall_scores))
                
                print(f"\n🏆 最佳块 (块 {best_idx+1}, 分数: {overall_scores[best_idx]:.3f}):")
                best_chunk_preview = result.chunks[best_idx].content[:150] + "..."
                print(f"  {best_chunk_preview}")
                
                print(f"\n⚠️ 最差块 (块 {worst_idx+1}, 分数: {overall_scores[worst_idx]:.3f}):")
                worst_chunk_preview = result.chunks[worst_idx].content[:150] + "..."
                print(f"  {worst_chunk_preview}")
                
        except Exception as e:
            print(f"❌ 质量分析失败: {str(e)}")
    
    async def run_all_demos(self):
        """运行所有演示"""
        print("🎉 Agentic文档切分全功能演示")
        print("基于Agno框架的智能文档切分系统")
        print("=" * 60)
        
        demos = [
            ("基础切分功能", self.demo_basic_chunking),
            ("策略对比", self.demo_strategy_comparison),
            ("智能切分", self.demo_smart_chunking),
            ("自定义配置", self.demo_custom_configuration),
            ("批量处理", self.demo_batch_processing),
            ("质量分析", self.demo_quality_analysis)
        ]
        
        for demo_name, demo_func in demos:
            try:
                print(f"\n🚀 开始演示: {demo_name}")
                await demo_func()
                print(f"✅ {demo_name} 演示完成")
            except Exception as e:
                print(f"❌ {demo_name} 演示失败: {str(e)}")
            
            # 等待用户确认继续
            input("\n按 Enter 键继续下一个演示...")
        
        print("\n🎊 所有演示完成！")
        print("感谢使用 Agentic文档切分系统")

async def main():
    """主函数"""
    demo = AgenticChunkingDemo()
    
    print("请选择演示模式:")
    print("1. 运行所有演示")
    print("2. 基础切分功能")
    print("3. 策略对比")
    print("4. 智能切分")
    print("5. 自定义配置")
    print("6. 批量处理")
    print("7. 质量分析")
    
    try:
        choice = input("\n请输入选择 (1-7): ").strip()
        
        if choice == "1":
            await demo.run_all_demos()
        elif choice == "2":
            await demo.demo_basic_chunking()
        elif choice == "3":
            await demo.demo_strategy_comparison()
        elif choice == "4":
            await demo.demo_smart_chunking()
        elif choice == "5":
            await demo.demo_custom_configuration()
        elif choice == "6":
            await demo.demo_batch_processing()
        elif choice == "7":
            await demo.demo_quality_analysis()
        else:
            print("❌ 无效选择")
            return
            
    except KeyboardInterrupt:
        print("\n👋 演示已取消")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 