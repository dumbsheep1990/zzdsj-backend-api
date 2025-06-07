#!/usr/bin/env python3
"""
增强的交互式AI知识图谱可视化系统
支持搜索、手动编辑、样式切换、数据持久化等高级功能
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any

class InteractiveKnowledgeGraphBuilder:
    """交互式知识图谱构建器"""
    
    def __init__(self):
        pass
    
    def create_interactive_visualization(
        self, 
        triples: List[Dict[str, Any]], 
        graph_id: str,
        title: str = "交互式知识图谱"
    ) -> str:
        """创建完全交互式的知识图谱可视化"""
        
        # 准备数据
        nodes_data, edges_data = self._prepare_graph_data(triples)
        
        # 生成HTML内容
        html_content = self._generate_interactive_html(
            nodes_data, edges_data, graph_id, title
        )
        
        # 保存文件
        filename = f"interactive_kg_{graph_id}_{int(time.time())}.html"
        file_path = Path(filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"🎨 交互式知识图谱已生成: {file_path.absolute()}")
        return str(file_path.absolute())
    
    def _prepare_graph_data(self, triples: List[Dict[str, Any]]) -> tuple:
        """准备图数据"""
        
        # 节点数据
        nodes = {}
        for triple in triples:
            subj, obj = triple['subject'], triple['object']
            
            for entity in [subj, obj]:
                if entity not in nodes:
                    nodes[entity] = {
                        'id': entity,
                        'label': entity,
                        'type': self._classify_entity(entity),
                        'connections': 0
                    }
                nodes[entity]['connections'] += 1
        
        # 边数据
        edges = []
        for i, triple in enumerate(triples):
            edges.append({
                'id': f"edge_{i}",
                'from': triple['subject'],
                'to': triple['object'],
                'label': triple['predicate'],
                'type': 'inferred' if triple.get('inferred', False) else 'original',
                'confidence': triple.get('confidence', 1.0)
            })
        
        return list(nodes.values()), edges
    
    def _classify_entity(self, entity: str) -> str:
        """实体分类"""
        entity_lower = entity.lower()
        if any(k in entity_lower for k in ['gpt', 'bert', 'resnet', 'alexnet', 'transformer']):
            return 'model'
        elif any(k in entity_lower for k in ['openai', 'google', '百度', '腾讯']):
            return 'company'
        elif any(k in entity_lower for k in ['yann', 'lecun', 'musk']):
            return 'person'
        elif '年' in entity or '时间' in entity:
            return 'time'
        elif any(k in entity_lower for k in ['学习', '网络', '技术', '算法']):
            return 'tech'
        return 'concept'
    
    def _generate_interactive_html(
        self, 
        nodes: List[Dict], 
        edges: List[Dict], 
        graph_id: str,
        title: str
    ) -> str:
        """生成完整的交互式HTML"""
        
        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style type="text/css">
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .container {{
            display: flex;
            height: calc(100vh - 80px);
        }}
        
        .sidebar {{
            width: 320px;
            background: white;
            padding: 20px;
            overflow-y: auto;
            box-shadow: 2px 0 10px rgba(0,0,0,0.1);
        }}
        
        .main-content {{
            flex: 1;
            position: relative;
        }}
        
        #mynetwork {{
            width: 100%;
            height: 100%;
            background: #fafafa;
        }}
        
        .control-group {{
            margin-bottom: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        
        .control-group h3 {{
            margin: 0 0 10px 0;
            color: #333;
            font-size: 14px;
            font-weight: 600;
        }}
        
        input, select, button {{
            width: 100%;
            padding: 8px 12px;
            margin: 5px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        }}
        
        button {{
            background: #667eea;
            color: white;
            border: none;
            cursor: pointer;
            transition: background 0.3s;
        }}
        
        button:hover {{
            background: #5a6fd8;
        }}
        
        .stats {{
            background: #e8f5e8;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 15px;
            font-size: 13px;
        }}
        
        .legend {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 5px 0;
            font-size: 12px;
        }}
        
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }}
        
        .modal-content {{
            background-color: white;
            margin: 5% auto;
            padding: 20px;
            border-radius: 8px;
            width: 80%;
            max-width: 500px;
        }}
        
        .close {{
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }}
        
        .close:hover {{
            color: black;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>图谱ID: {graph_id} | 交互式知识图谱可视化</p>
    </div>
    
    <div class="container">
        <div class="sidebar">
            <!-- 统计信息 -->
            <div class="stats">
                <strong>📊 图谱统计</strong><br>
                节点数: <span id="node-count">0</span><br>
                边数: <span id="edge-count">0</span><br>
                选中: <span id="selected-info">无</span>
            </div>
            
            <!-- 搜索控制 -->
            <div class="control-group">
                <h3>🔍 搜索与过滤</h3>
                <input type="text" id="search-input" placeholder="搜索节点...">
                <select id="filter-type">
                    <option value="all">所有类型</option>
                    <option value="model">模型</option>
                    <option value="company">公司</option>
                    <option value="person">人物</option>
                    <option value="tech">技术</option>
                    <option value="concept">概念</option>
                    <option value="time">时间</option>
                </select>
                <button onclick="searchNodes()">搜索</button>
                <button onclick="clearSearch()">清除</button>
            </div>
            
            <!-- 视图控制 -->
            <div class="control-group">
                <h3>🎨 视图样式</h3>
                <select id="layout-select" onchange="changeLayout()">
                    <option value="force">力导向布局</option>
                    <option value="hierarchical">层次布局</option>
                    <option value="circular">圆形布局</option>
                </select>
                <select id="theme-select" onchange="changeTheme()">
                    <option value="light">浅色主题</option>
                    <option value="dark">深色主题</option>
                    <option value="colorful">彩色主题</option>
                </select>
                <button onclick="togglePhysics()">切换物理引擎</button>
                <button onclick="fitNetwork()">适应屏幕</button>
            </div>
            
            <!-- 编辑控制 -->
            <div class="control-group">
                <h3>✏️ 图谱编辑</h3>
                <button onclick="openAddNodeModal()">添加节点</button>
                <button onclick="openAddEdgeModal()">添加关系</button>
                <button onclick="deleteSelected()">删除选中</button>
                <button onclick="exportGraph()">导出数据</button>
                <button onclick="saveGraph()">保存图谱</button>
            </div>
            
            <!-- 图例 -->
            <div class="legend">
                <h3>📋 图例</h3>
                <div class="legend-item">
                    <div class="legend-color" style="background: #ff6b6b;"></div>
                    <span>模型</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #4ecdc4;"></div>
                    <span>技术</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #45b7d1;"></div>
                    <span>公司</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #96ceb4;"></div>
                    <span>人物</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #ffeaa7;"></div>
                    <span>概念</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #dda0dd;"></div>
                    <span>时间</span>
                </div>
            </div>
            
            <!-- 操作提示 -->
            <div class="control-group">
                <h3>💡 操作提示</h3>
                <small>
                • 双击节点聚焦<br>
                • 拖拽移动节点<br>
                • Ctrl+S 保存<br>
                • Ctrl+F 搜索<br>
                • Delete 删除选中
                </small>
            </div>
        </div>
        
        <div class="main-content">
            <div id="mynetwork"></div>
        </div>
    </div>
    
    <!-- 添加节点模态框 -->
    <div id="addNodeModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal('addNodeModal')">&times;</span>
            <h2>添加新节点</h2>
            <input type="text" id="new-node-label" placeholder="节点名称">
            <select id="new-node-type">
                <option value="concept">概念</option>
                <option value="model">模型</option>
                <option value="company">公司</option>
                <option value="person">人物</option>
                <option value="tech">技术</option>
                <option value="time">时间</option>
            </select>
            <button onclick="addNewNode()">添加节点</button>
        </div>
    </div>
    
    <!-- 添加边模态框 -->
    <div id="addEdgeModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal('addEdgeModal')">&times;</span>
            <h2>添加新关系</h2>
            <select id="edge-from"></select>
            <input type="text" id="edge-label" placeholder="关系名称">
            <select id="edge-to"></select>
            <button onclick="addNewEdge()">添加关系</button>
        </div>
    </div>

    <script type="text/javascript">
        // 全局变量
        let network;
        let nodes;
        let edges;
        let allNodes = {json.dumps(nodes, ensure_ascii=False)};
        let allEdges = {json.dumps(edges, ensure_ascii=False)};
        let selectedNodes = [];
        let selectedEdges = [];
        let physicsEnabled = true;
        
        // 颜色映射
        const nodeColors = {{
            'model': '#ff6b6b',
            'tech': '#4ecdc4', 
            'company': '#45b7d1',
            'person': '#96ceb4',
            'concept': '#ffeaa7',
            'time': '#dda0dd'
        }};
        
        // 初始化网络
        function initNetwork() {{
            const container = document.getElementById('mynetwork');
            
            // 准备节点数据
            const nodeArray = allNodes.map(node => ({{
                id: node.id,
                label: node.label,
                color: nodeColors[node.type] || '#95a5a6',
                size: Math.max(20, Math.min(50, node.connections * 5)),
                title: `类型: ${{node.type}}\\n连接数: ${{node.connections}}`,
                font: {{ size: 14 }}
            }}));
            
            // 准备边数据
            const edgeArray = allEdges.map(edge => ({{
                id: edge.id,
                from: edge.from,
                to: edge.to,
                label: edge.label,
                color: edge.type === 'inferred' ? '#ff0000' : '#2c3e50',
                dashes: edge.type === 'inferred',
                title: `关系: ${{edge.label}}\\n类型: ${{edge.type}}\\n置信度: ${{edge.confidence}}`,
                arrows: {{ to: {{ enabled: true }} }}
            }}));
            
            nodes = new vis.DataSet(nodeArray);
            edges = new vis.DataSet(edgeArray);
            
            const data = {{ nodes: nodes, edges: edges }};
            const options = {{
                physics: {{
                    enabled: physicsEnabled,
                    stabilization: {{ iterations: 150 }}
                }},
                interaction: {{
                    hover: true,
                    multiselect: true
                }},
                manipulation: {{
                    enabled: false
                }}
            }};
            
            network = new vis.Network(container, data, options);
            
            // 事件监听
            network.on("selectNode", function(params) {{
                selectedNodes = params.nodes;
                updateSelectionInfo();
            }});
            
            network.on("selectEdge", function(params) {{
                selectedEdges = params.edges;
                updateSelectionInfo();
            }});
            
            network.on("deselectNode", function(params) {{
                selectedNodes = [];
                updateSelectionInfo();
            }});
            
            network.on("doubleClick", function(params) {{
                if (params.nodes.length > 0) {{
                    focusOnNode(params.nodes[0]);
                }}
            }});
            
            updateStats();
        }}
        
        // 更新统计信息
        function updateStats() {{
            document.getElementById('node-count').textContent = nodes.length;
            document.getElementById('edge-count').textContent = edges.length;
        }}
        
        // 更新选择信息
        function updateSelectionInfo() {{
            const info = selectedNodes.length > 0 ? 
                `节点: ${{selectedNodes.length}}` : 
                selectedEdges.length > 0 ? 
                `边: ${{selectedEdges.length}}` : '无';
            document.getElementById('selected-info').textContent = info;
        }}
        
        // 搜索节点
        function searchNodes() {{
            const searchTerm = document.getElementById('search-input').value.toLowerCase();
            const filterType = document.getElementById('filter-type').value;
            
            if (!searchTerm && filterType === 'all') {{
                clearSearch();
                return;
            }}
            
            const matchingNodes = allNodes.filter(node => {{
                const matchesSearch = !searchTerm || node.label.toLowerCase().includes(searchTerm);
                const matchesType = filterType === 'all' || node.type === filterType;
                return matchesSearch && matchesType;
            }});
            
            // 高亮匹配的节点
            const nodeUpdate = allNodes.map(node => {{
                const isMatch = matchingNodes.some(mn => mn.id === node.id);
                return {{
                    id: node.id,
                    color: isMatch ? '#ffeb3b' : (nodeColors[node.type] || '#95a5a6'),
                    size: isMatch ? 35 : Math.max(20, Math.min(50, node.connections * 5))
                }};
            }});
            
            nodes.update(nodeUpdate);
            
            if (matchingNodes.length > 0) {{
                network.fit({{ nodes: matchingNodes.map(n => n.id) }});
            }}
        }}
        
        // 清除搜索
        function clearSearch() {{
            document.getElementById('search-input').value = '';
            document.getElementById('filter-type').value = 'all';
            
            const nodeUpdate = allNodes.map(node => ({{
                id: node.id,
                color: nodeColors[node.type] || '#95a5a6',
                size: Math.max(20, Math.min(50, node.connections * 5))
            }}));
            
            nodes.update(nodeUpdate);
            network.fit();
        }}
        
        // 焦点到节点
        function focusOnNode(nodeId) {{
            network.focus(nodeId, {{ scale: 1.5, animation: true }});
        }}
        
        // 适应屏幕
        function fitNetwork() {{
            network.fit({{ animation: true }});
        }}
        
        // 切换布局
        function changeLayout() {{
            const layout = document.getElementById('layout-select').value;
            let options = {{}};
            
            switch(layout) {{
                case 'hierarchical':
                    options = {{
                        layout: {{
                            hierarchical: {{
                                enabled: true,
                                direction: 'UD',
                                sortMethod: 'directed'
                            }}
                        }}
                    }};
                    break;
                case 'circular':
                    options = {{
                        layout: {{
                            hierarchical: false
                        }},
                        physics: {{
                            enabled: false
                        }}
                    }};
                    // 手动设置圆形布局
                    setTimeout(() => {{
                        const nodePositions = {{}};
                        const nodeCount = allNodes.length;
                        const radius = 300;
                        allNodes.forEach((node, index) => {{
                            const angle = (2 * Math.PI * index) / nodeCount;
                            nodePositions[node.id] = {{
                                x: radius * Math.cos(angle),
                                y: radius * Math.sin(angle)
                            }};
                        }});
                        network.setPositions(nodePositions);
                    }}, 100);
                    break;
                default:
                    options = {{
                        layout: {{
                            hierarchical: false
                        }},
                        physics: {{
                            enabled: true
                        }}
                    }};
            }}
            
            network.setOptions(options);
        }}
        
        // 切换主题
        function changeTheme() {{
            const theme = document.getElementById('theme-select').value;
            const container = document.getElementById('mynetwork');
            
            switch(theme) {{
                case 'dark':
                    container.style.background = '#2c3e50';
                    network.setOptions({{
                        edges: {{ color: {{ color: '#ecf0f1' }} }},
                        nodes: {{ font: {{ color: 'white' }} }}
                    }});
                    break;
                case 'colorful':
                    container.style.background = 'linear-gradient(45deg, #ff9a9e 0%, #fecfef 50%, #fecfef 100%)';
                    break;
                default:
                    container.style.background = '#fafafa';
                    network.setOptions({{
                        edges: {{ color: {{ color: '#2c3e50' }} }},
                        nodes: {{ font: {{ color: 'black' }} }}
                    }});
            }}
        }}
        
        // 切换物理引擎
        function togglePhysics() {{
            physicsEnabled = !physicsEnabled;
            network.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
        }}
        
        // 模态框操作
        function openAddNodeModal() {{
            document.getElementById('addNodeModal').style.display = 'block';
        }}
        
        function openAddEdgeModal() {{
            // 更新节点选择列表
            const fromSelect = document.getElementById('edge-from');
            const toSelect = document.getElementById('edge-to');
            
            fromSelect.innerHTML = '';
            toSelect.innerHTML = '';
            
            allNodes.forEach(node => {{
                const option1 = new Option(node.label, node.id);
                const option2 = new Option(node.label, node.id);
                fromSelect.add(option1);
                toSelect.add(option2);
            }});
            
            document.getElementById('addEdgeModal').style.display = 'block';
        }}
        
        function closeModal(modalId) {{
            document.getElementById(modalId).style.display = 'none';
        }}
        
        // 添加新节点
        function addNewNode() {{
            const label = document.getElementById('new-node-label').value;
            const type = document.getElementById('new-node-type').value;
            
            if (!label) {{
                alert('请输入节点名称');
                return;
            }}
            
            const newNode = {{
                id: `custom_${{Date.now()}}`,
                label: label,
                type: type,
                connections: 0
            }};
            
            allNodes.push(newNode);
            
            nodes.add({{
                id: newNode.id,
                label: newNode.label,
                color: nodeColors[newNode.type] || '#95a5a6',
                size: 20,
                title: `类型: ${{newNode.type}}\\n连接数: 0`,
                font: {{ size: 14 }}
            }});
            
            updateStats();
            closeModal('addNodeModal');
            document.getElementById('new-node-label').value = '';
        }}
        
        // 添加新关系
        function addNewEdge() {{
            const from = document.getElementById('edge-from').value;
            const to = document.getElementById('edge-to').value;
            const label = document.getElementById('edge-label').value;
            
            if (!from || !to || !label) {{
                alert('请填写完整信息');
                return;
            }}
            
            if (from === to) {{
                alert('不能添加自环关系');
                return;
            }}
            
            const newEdge = {{
                id: `custom_edge_${{Date.now()}}`,
                from: from,
                to: to,
                label: label,
                type: 'custom',
                confidence: 1.0
            }};
            
            allEdges.push(newEdge);
            
            edges.add({{
                id: newEdge.id,
                from: newEdge.from,
                to: newEdge.to,
                label: newEdge.label,
                color: '#27ae60',
                title: `关系: ${{newEdge.label}}\\n类型: 自定义`,
                arrows: {{ to: {{ enabled: true }} }}
            }});
            
            updateStats();
            closeModal('addEdgeModal');
            document.getElementById('edge-label').value = '';
        }}
        
        // 删除选中元素
        function deleteSelected() {{
            if (selectedNodes.length > 0) {{
                nodes.remove(selectedNodes);
                allNodes = allNodes.filter(node => !selectedNodes.includes(node.id));
            }}
            
            if (selectedEdges.length > 0) {{
                edges.remove(selectedEdges);
                allEdges = allEdges.filter(edge => !selectedEdges.includes(edge.id));
            }}
            
            selectedNodes = [];
            selectedEdges = [];
            updateStats();
            updateSelectionInfo();
        }}
        
        // 导出图数据
        function exportGraph() {{
            const graphData = {{
                nodes: allNodes,
                edges: allEdges,
                exported_at: new Date().toISOString()
            }};
            
            const dataStr = JSON.stringify(graphData, null, 2);
            const dataBlob = new Blob([dataStr], {{ type: 'application/json' }});
            const url = URL.createObjectURL(dataBlob);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = `knowledge_graph_{graph_id}_${{Date.now()}}.json`;
            link.click();
            
            URL.revokeObjectURL(url);
        }}
        
        // 保存图谱
        function saveGraph() {{
            const graphData = {{
                graph_id: '{graph_id}',
                nodes: allNodes,
                edges: allEdges,
                updated_at: new Date().toISOString()
            }};
            
            localStorage.setItem(`kg_{graph_id}`, JSON.stringify(graphData));
            alert('图谱已保存到本地存储');
        }}
        
        // 初始化
        document.addEventListener('DOMContentLoaded', function() {{
            initNetwork();
        }});
        
        // 键盘快捷键
        document.addEventListener('keydown', function(e) {{
            if (e.ctrlKey || e.metaKey) {{
                switch(e.key) {{
                    case 's':
                        e.preventDefault();
                        saveGraph();
                        break;
                    case 'f':
                        e.preventDefault();
                        document.getElementById('search-input').focus();
                        break;
                }}
            }}
            if (e.key === 'Delete') {{
                deleteSelected();
            }}
        }});
    </script>
</body>
</html>'''

# 测试用数据
TEST_TRIPLES = [
    {"subject": "机器学习", "predicate": "是", "object": "人工智能技术"},
    {"subject": "深度学习", "predicate": "属于", "object": "机器学习"},
    {"subject": "OpenAI", "predicate": "开发", "object": "GPT模型"},
    {"subject": "GPT模型", "predicate": "使用", "object": "Transformer架构"},
    {"subject": "Google", "predicate": "提出", "object": "Transformer架构"},
    {"subject": "Yann LeCun", "predicate": "提出", "object": "卷积神经网络"},
    {"subject": "卷积神经网络", "predicate": "适用于", "object": "图像识别"},
    {"subject": "自然语言处理", "predicate": "使用", "object": "深度学习", "inferred": True},
    {"subject": "OpenAI", "predicate": "关联", "object": "Transformer架构", "inferred": True}
]

def main():
    """主函数：演示交互式知识图谱"""
    print("🚀 创建交互式知识图谱演示")
    
    builder = InteractiveKnowledgeGraphBuilder()
    
    # 创建交互式可视化
    html_path = builder.create_interactive_visualization(
        TEST_TRIPLES,
        "demo_interactive",
        "AI知识图谱 - 交互式演示"
    )
    
    print(f"✅ 交互式知识图谱已创建")
    print(f"📁 文件位置: {html_path}")
    print(f"🌐 浏览器打开: file://{html_path}")
    print("\n🎯 功能特性:")
    print("  • 🔍 搜索与过滤节点")
    print("  • ✏️  手动添加节点和关系")
    print("  • 🎨 切换视图样式和主题")
    print("  • 📊 实时统计信息")
    print("  • 💾 数据导出和保存")
    print("  • ⌨️  键盘快捷键支持")
    print("\n⌨️  快捷键:")
    print("  • Ctrl+S: 保存图谱")
    print("  • Ctrl+F: 搜索焦点")
    print("  • Delete: 删除选中")

if __name__ == "__main__":
    main() 