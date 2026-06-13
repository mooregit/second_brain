import ReactFlow, { Background, Controls, Edge, Node } from 'reactflow';
import 'reactflow/dist/style.css';
import type { GraphResponse } from '../api/graph';

export default function GraphCanvas({ graph }: { graph: GraphResponse }) {
  const nodes: Node[] = graph.nodes.map((node, index) => ({
    id: node.id,
    data: { label: node.label },
    position: { x: (index % 4) * 260, y: Math.floor(index / 4) * 130 },
    type: 'default'
  }));
  const edges: Edge[] = graph.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label
  }));

  return (
    <div className="h-[680px] w-full overflow-hidden rounded-md border border-slate-300 bg-white">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}

