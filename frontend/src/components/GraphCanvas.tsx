import ReactFlow, { Background, Controls, Edge, Node } from 'reactflow';
import 'reactflow/dist/style.css';
import type { GraphResponse } from '../api/graph';

const columnByType: Record<string, number> = {
  project: 0,
  source: 0,
  task: 1,
  idea: 1,
  decision: 1,
  question: 1,
  tag: 2,
  person: 2,
  entity: 3
};

export default function GraphCanvas({
  graph,
  visibleTypes,
  showEdgeLabels
}: {
  graph: GraphResponse;
  visibleTypes?: Set<string>;
  showEdgeLabels?: boolean;
}) {
  const filteredNodes = visibleTypes ? graph.nodes.filter((node) => visibleTypes.has(node.type)) : graph.nodes;
  const visibleNodeIds = new Set(filteredNodes.map((node) => node.id));
  const rowByColumn = new Map<number, number>();
  const nodes: Node[] = filteredNodes.map((node) => {
    const column = columnByType[node.type] ?? 3;
    const row = rowByColumn.get(column) ?? 0;
    rowByColumn.set(column, row + 1);
    return {
      id: node.id,
      data: { label: node.label },
      position: { x: column * 310, y: row * 120 },
      type: 'default',
      className: `graph-node-${node.type}`
    };
  });
  const edges: Edge[] = graph.edges.filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)).map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: showEdgeLabels ? edge.label : undefined
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
