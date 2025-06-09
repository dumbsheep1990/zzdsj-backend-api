#!/usr/bin/env python3
"""
AI知识图谱框架高级演示
展示完整的三阶段处理流程和高级可视化
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any
from pyvis.network import Network
import networkx as nx

# 丰富的AI领域文本
DEMO_TEXT = """
机器学习是人工智能的核心技术。深度学习是机器学习的重要分支，取得了突破性进展。

卷积神经网络（CNN）适用于图像识别。LeNet-5是早期CNN架构，由Yann LeCun在1998年提出。
后来有AlexNet、VGG、ResNet等架构。ResNet引入残差连接，解决梯度消失问题。

循环神经网络（RNN）处理序列数据。LSTM和GRU是RNN改进版。
Transformer架构改变了序列建模，由Google在2017年提出。

自然语言处理（NLP）因Transformer发生革命。BERT模型使用双向编码器。
GPT系列采用生成式预训练，GPT-3有1750亿参数。

OpenAI开发ChatGPT，基于GPT-3.5架构。Google开发Bard，基于LaMDA模型。
百度发布文心一言，腾讯推出混元助手。

计算机视觉快速发展。目标检测从R-CNN发展到YOLO系列。
强化学习结合深度学习。AlphaGo使用蒙特卡洛树搜索，击败围棋世界冠军。
"""

class AdvancedMockLLM:
    """高级模拟LLM"""
    
    def __init__(self):
        self.responses = [
            '''[
                {"subject": "机器学习", "predicate": "是", "object": "人工智能技术"},
                {"subject": "深度学习", "predicate": "属于", "object": "机器学习"},
                {"subject": "卷积神经网络", "predicate": "简称", "object": "cnn"},
                {"subject": "cnn", "predicate": "适用于", "object": "图像识别"},
                {"subject": "lenet-5", "predicate": "是", "object": "早期cnn"},
                {"subject": "yann lecun", "predicate": "提出", "object": "lenet-5"},
                {"subject": "yann lecun", "predicate": "提出时间", "object": "1998年"}
            ]''',
            '''[
                {"subject": "alexnet", "predicate": "是", "object": "cnn架构"},
                {"subject": "vgg", "predicate": "是", "object": "cnn架构"},
                {"subject": "resnet", "predicate": "引入", "object": "残差连接"},
                {"subject": "残差连接", "predicate": "解决", "object": "梯度消失"},
                {"subject": "rnn", "predicate": "处理", "object": "序列数据"},
                {"subject": "lstm", "predicate": "是", "object": "rnn改进版"},
                {"subject": "transformer", "predicate": "改变", "object": "序列建模"},
                {"subject": "google", "predicate": "提出", "object": "transformer"}
            ]''',
            '''[
                {"subject": "nlp", "predicate": "因", "object": "transformer革命"},
                {"subject": "bert", "predicate": "使用", "object": "双向编码器"},
                {"subject": "gpt系列", "predicate": "采用", "object": "生成式预训练"},
                {"subject": "gpt-3", "predicate": "有", "object": "1750亿参数"},
                {"subject": "openai", "predicate": "开发", "object": "chatgpt"},
                {"subject": "chatgpt", "predicate": "基于", "object": "gpt-3.5"},
                {"subject": "google", "predicate": "开发", "object": "bard"},
                {"subject": "百度", "predicate": "发布", "object": "文心一言"}
            ]'''
        ]
        self.index = 0
    
    def call_llm(self, prompt: str, **kwargs) -> str:
        if self.index < len(self.responses):
            response = self.responses[self.index]
            self.index += 1
            return response
        return '[]'

class EnhancedProcessor:
    """增强的知识图谱处理器"""
    
    def __init__(self):
        self.llm = AdvancedMockLLM()
    
    def extract_triples(self, text: str) -> List[Dict[str, Any]]:
        """提取三元组"""
        chunks = text.split('\n\n')
        all_triples = []
        
        print(f"📝 文本分为 {len(chunks)} 个段落")
        
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            response = self.llm.call_llm(f"提取: {chunk}")
            try:
                triples = json.loads(response)
                for triple in triples:
                    triple['chunk'] = i + 1
                all_triples.extend(triples)
                print(f"  📍 段落 {i+1}: {len(triples)} 个三元组")
            except:
                pass
        
        return all_triples
    
    def standardize_entities(self, triples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """实体标准化"""
        print("🔧 实体标准化...")
        entity_map = {
            'cnn': '卷积神经网络',
            'rnn': '循环神经网络', 
            'nlp': '自然语言处理',
            'gpt-3': 'gpt3',
            'gpt-3.5': 'gpt3.5'
        }
        
        for triple in triples:
            for field in ['subject', 'object']:
                for key, value in entity_map.items():
                    if key in triple[field].lower():
                        triple[field] = triple[field].replace(key, value)
        return triples
    
    def infer_relationships(self, triples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """关系推理"""
        print("🧠 关系推理...")
        
        # 构建简单的传递关系
        relationships = {}
        for triple in triples:
            subj = triple['subject']
            if subj not in relationships:
                relationships[subj] = []
            relationships[subj].append(triple['object'])
        
        inferred = []
        for entity1, related in relationships.items():
            for rel_entity in related:
                if rel_entity in relationships:
                    for entity2 in relationships[rel_entity]:
                        if entity1 != entity2:
                            inferred.append({
                                'subject': entity1,
                                'predicate': '间接关联',
                                'object': entity2,
                                'inferred': True
                            })
        
        print(f"  ✅ 推理出 {len(inferred)} 个关系")
        return triples + inferred[:20]  # 限制推理关系数量
    
    def create_visualization(self, triples: List[Dict[str, Any]], filename: str) -> str:
        """创建可视化"""
        print("🎨 生成可视化...")
        
        net = Network(height="800px", width="100%", bgcolor="#f8f9fa", directed=True)
        
        # 节点颜色分类
        colors = {
            'model': '#ff6b6b',     # 模型-红
            'tech': '#4ecdc4',      # 技术-青
            'company': '#45b7d1',   # 公司-蓝
            'default': '#95a5a6'    # 默认-灰
        }
        
        def get_node_color(entity: str) -> str:
            entity_lower = entity.lower()
            if any(k in entity_lower for k in ['gpt', 'bert', 'resnet', 'alexnet']):
                return colors['model']
            elif any(k in entity_lower for k in ['openai', 'google', '百度']):
                return colors['company']
            elif any(k in entity_lower for k in ['学习', '网络', '技术']):
                return colors['tech']
            return colors['default']
        
        # 添加节点
        nodes = set()
        for triple in triples:
            nodes.add(triple['subject'])
            nodes.add(triple['object'])
        
        for node in nodes:
            net.add_node(node, label=node, color=get_node_color(node), size=20)
        
        # 添加边
        for triple in triples:
            is_inferred = triple.get('inferred', False)
            color = '#ff0000' if is_inferred else '#0066cc'
            net.add_edge(
                triple['subject'], 
                triple['object'],
                label=triple['predicate'],
                color=color,
                dashes=is_inferred
            )
        
        # 保存
        output_path = Path(filename)
        net.save_graph(str(output_path))
        print(f"  ✅ 保存到: {output_path.absolute()}")
        return str(output_path.absolute())
    
    def process_text(self, text: str) -> Dict[str, Any]:
        """完整处理"""
        print("=" * 50)
        print("🚀 AI知识图谱演示")
        print("=" * 50)
        
        # 提取
        triples = self.extract_triples(text)
        print(f"📊 提取: {len(triples)} 个三元组")
        
        # 标准化
        triples = self.standardize_entities(triples)
        
        # 推理
        triples = self.infer_relationships(triples)
        print(f"📊 最终: {len(triples)} 个三元组")
        
        # 可视化
        filename = f"demo_kg_{int(time.time())}.html"
        viz_path = self.create_visualization(triples, filename)
        
        # 统计
        original = len([t for t in triples if not t.get('inferred', False)])
        inferred = len([t for t in triples if t.get('inferred', False)])
        entities = len(set([t['subject'] for t in triples] + [t['object'] for t in triples]))
        
        result = {
            'triples': triples,
            'stats': {
                'total': len(triples),
                'original': original,
                'inferred': inferred,
                'entities': entities,
                'file': viz_path
            }
        }
        
        print("\n✅ 完成!")
        print(f"📊 统计: 总{len(triples)} (原{original}+推{inferred}), 实体{entities}")
        print(f"🌐 文件: {viz_path}")
        
        return result

def main():
    """主函数"""
    try:
        processor = EnhancedProcessor()
        result = processor.process_text(DEMO_TEXT)
        
        print(f"\n🔍 三元组示例:")
        for i, triple in enumerate(result['triples'][:10]):
            mark = " (推理)" if triple.get('inferred') else ""
            print(f"  {i+1}. {triple['subject']} → {triple['predicate']} → {triple['object']}{mark}")
        
        print(f"\n🌐 浏览器打开: file://{result['stats']['file']}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    main() 