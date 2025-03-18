import React, { useRef, useEffect, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { GraphNode, GraphLink } from '../../../utils/types';
import { generateKnowledgeGraphData } from '../../../utils/mockData';

interface KnowledgeGraphProps {
  width?: number;
  height?: number;
  selectedKeywordId?: number;
  onNodeClick?: (node: GraphNode) => void;
}

// 
interface ForceGraphNode extends GraphNode {
  x?: number;
  y?: number;
  // 
  id: string;
  label: string;
  type: 'keyword' | 'file';
  value?: number;
  color?: string;
}

const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({
  width = 800,
  height = 600,
  selectedKeywordId,
  onNodeClick
}) => {
  const [graphData, setGraphData] = useState<{ nodes: ForceGraphNode[], links: GraphLink[] }>({ nodes: [], links: [] });
  const graphRef = useRef<any>(null);

  useEffect(() => {
    // 
    const data = generateKnowledgeGraphData();
    setGraphData(data);

    // 
    if (selectedKeywordId && graphRef.current) {
      const selectedNode = data.nodes.find(node => 
        node.id === `keyword-${selectedKeywordId}`) as ForceGraphNode;
      
      if (selectedNode && selectedNode.x !== undefined && selectedNode.y !== undefined) {
        graphRef.current.centerAt(
          selectedNode.x,
          selectedNode.y,
          1000
        );
        graphRef.current.zoom(2.5, 1000);
      }
    }
  }, [selectedKeywordId]);

  const handleNodeClick = (node: ForceGraphNode) => {
    if (onNodeClick) {
      onNodeClick(node);
    }
  };

  return (
    <div className="knowledge-graph-container bg-white rounded-lg shadow-md p-4">
      <h3 className="text-lg font-semibold mb-4">知识图谱</h3>
      <div className="border rounded-lg overflow-hidden" style={{ height }}>
        {graphData.nodes.length > 0 && (
          <ForceGraph2D
            ref={graphRef}
            graphData={graphData}
            nodeLabel="label"
            nodeColor={(node: ForceGraphNode) => node.color || '#1f77b4'}
            nodeVal={(node: ForceGraphNode) => node.value || 1}
            linkWidth={(link: GraphLink) => link.value || 1}
            linkColor={() => '#999'}
            width={width}
            height={height}
            onNodeClick={handleNodeClick}
            cooldownTicks={100}
            onEngineStop={() => graphRef.current?.zoomToFit(400, 30)}
          />
        )}
      </div>
      <div className="flex mt-4 text-sm">
        <div className="legend-item flex items-center mr-4">
          <span className="w-3 h-3 rounded-full bg-red-500 mr-1"></span>
          <span>高重要度关键词</span>
        </div>
        <div className="legend-item flex items-center mr-4">
          <span className="w-3 h-3 rounded-full bg-amber-500 mr-1"></span>
          <span>中重要度关键词</span>
        </div>
        <div className="legend-item flex items-center mr-4">
          <span className="w-3 h-3 rounded-full bg-emerald-500 mr-1"></span>
          <span>低重要度关键词</span>
        </div>
        <div className="legend-item flex items-center">
          <span className="w-3 h-3 rounded-full bg-blue-500 mr-1"></span>
          <span>文件</span>
        </div>
      </div>
    </div>
  );
};

export default KnowledgeGraph;
