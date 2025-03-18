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
}

const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({
  width = 800,
  height = 600,
  selectedKeywordId,
  onNodeClick
}) => {
  const graphRef = useRef<any>(null);
  const [graphData, setGraphData] = useState<{ nodes: ForceGraphNode[], links: GraphLink[] }>({ nodes: [], links: [] });

  useEffect(() => {
    const data = generateKnowledgeGraphData();
    setGraphData(data);

    // u5982u679cu6709u9009u4e2du7684u5173u952eu8bcduff0cu5c06u5176u9ad8u4eaeu663eu793a
    if (selectedKeywordId && graphRef.current) {
      // u5c06u9009u4e2du8282u70b9u7c7bu578bu8f6cu6362u4e3a ForceGraphNode
      const selectedNode = data.nodes.find(node => node.id === selectedKeywordId.toString()) as ForceGraphNode;
      if (selectedNode && selectedNode.x !== undefined && selectedNode.y !== undefined) {
        graphRef.current.centerAt(selectedNode.x, selectedNode.y, 1000);
        graphRef.current.zoom(2, 1000);
      }
    }
  }, [selectedKeywordId]);

  const handleNodeClick = (node: ForceGraphNode) => {
    if (onNodeClick) {
      onNodeClick(node);
    }
  };

  return (
    <div className="knowledge-graph-container" style={{ width, height }}>
      {graphData.nodes.length > 0 ? (
        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          nodeLabel="label"
          nodeColor={(node: ForceGraphNode) => {
            if (selectedKeywordId && node.id === selectedKeywordId.toString()) {
              return '#ff6600'; 
            }
            return node.type === 'keyword' ? '#4299e1' : '#48bb78'; 
          }}
          nodeRelSize={width < 400 ? 5 : 8}
          linkWidth={1}
          linkColor={() => '#999'}
          cooldownTicks={100}
          onNodeClick={handleNodeClick}
          width={width}
          height={height}
        />
      ) : (
        <div className="flex items-center justify-center h-full text-gray-500">
          ...
        </div>
      )}
    </div>
  );
};

export default KnowledgeGraph;
