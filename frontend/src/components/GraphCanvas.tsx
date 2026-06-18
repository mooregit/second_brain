import { useEffect, useMemo, useState } from 'react';
import { BadgeCheck, Box, Briefcase, CheckSquare, CircleHelp, FileText, GitBranch, Lightbulb, Tag, User, type LucideIcon } from 'lucide-react';
import ReactFlow, { Background, Controls, Edge, Node, ReactFlowProvider, useReactFlow } from 'reactflow';
import 'reactflow/dist/style.css';
import type { GraphResponse } from '../api/graph';

export type GraphLayoutMode = 'project' | 'source' | 'task' | 'entity';

const columnByTypeByLayout: Record<GraphLayoutMode, Record<string, number>> = {
  project: {
    project: 0,
    source: 0,
    task: 1,
    idea: 1,
    decision: 1,
    question: 1,
    tag: 2,
    person: 2,
    entity: 3
  },
  source: {
    source: 0,
    project: 1,
    task: 1,
    idea: 1,
    decision: 1,
    question: 1,
    tag: 2,
    person: 2,
    entity: 3
  },
  task: {
    task: 0,
    question: 1,
    decision: 1,
    idea: 1,
    project: 2,
    source: 2,
    tag: 3,
    person: 3,
    entity: 3
  },
  entity: {
    tag: 0,
    person: 0,
    entity: 0,
    project: 1,
    source: 1,
    task: 2,
    idea: 2,
    decision: 2,
    question: 2
  }
};

const rowWeightByType: Record<string, number> = {
  project: 0,
  source: 1,
  task: 2,
  question: 3,
  decision: 4,
  idea: 5,
  tag: 6,
  person: 7,
  entity: 8
};

export default function GraphCanvas({
  graph,
  visibleTypes,
  visibleNodeIds,
  relationshipTypeFilter,
  layoutMode = 'project',
  showEdgeLabels,
  selectedNodeId,
  onNodeSelect,
  onNodeOpen
}: {
  graph: GraphResponse;
  visibleTypes?: Set<string>;
  visibleNodeIds?: Set<string>;
  relationshipTypeFilter?: string;
  layoutMode?: GraphLayoutMode;
  showEdgeLabels?: boolean;
  selectedNodeId?: string | null;
  onNodeSelect?: (nodeId: string | null) => void;
  onNodeOpen?: (nodeId: string) => void;
}) {
  return (
    <ReactFlowProvider>
      <GraphCanvasInner
        graph={graph}
        visibleTypes={visibleTypes}
        visibleNodeIds={visibleNodeIds}
        relationshipTypeFilter={relationshipTypeFilter}
        layoutMode={layoutMode}
        showEdgeLabels={showEdgeLabels}
        selectedNodeId={selectedNodeId}
        onNodeSelect={onNodeSelect}
        onNodeOpen={onNodeOpen}
      />
    </ReactFlowProvider>
  );
}

function GraphCanvasInner({
  graph,
  visibleTypes,
  visibleNodeIds,
  relationshipTypeFilter,
  layoutMode,
  showEdgeLabels,
  selectedNodeId,
  onNodeSelect,
  onNodeOpen
}: {
  graph: GraphResponse;
  visibleTypes?: Set<string>;
  visibleNodeIds?: Set<string>;
  relationshipTypeFilter?: string;
  layoutMode: GraphLayoutMode;
  showEdgeLabels?: boolean;
  selectedNodeId?: string | null;
  onNodeSelect?: (nodeId: string | null) => void;
  onNodeOpen?: (nodeId: string) => void;
}) {
  const { setCenter } = useReactFlow();
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null);
  const filteredNodes = useMemo(
    () => graph.nodes.filter((node) => (!visibleTypes || visibleTypes.has(node.type)) && (!visibleNodeIds || visibleNodeIds.has(node.id))),
    [graph.nodes, visibleNodeIds, visibleTypes]
  );
  const renderedNodeIds = useMemo(() => new Set(filteredNodes.map((node) => node.id)), [filteredNodes]);
  const filteredEdges = useMemo(
    () => graph.edges.filter((edge) => renderedNodeIds.has(edge.source) && renderedNodeIds.has(edge.target) && (!relationshipTypeFilter || edge.relationship_type === relationshipTypeFilter)),
    [graph.edges, relationshipTypeFilter, renderedNodeIds]
  );
  const relatedNodeIds = useMemo(() => {
    if (!selectedNodeId) return null;
    const ids = new Set([selectedNodeId]);
    for (const edge of filteredEdges) {
      if (edge.source === selectedNodeId) ids.add(edge.target);
      if (edge.target === selectedNodeId) ids.add(edge.source);
    }
    return ids;
  }, [filteredEdges, selectedNodeId]);
  const rowByColumn = new Map<number, number>();
  const columnByType = columnByTypeByLayout[layoutMode];
  const sortedNodes = [...filteredNodes].sort((left, right) => {
    const columnDiff = (columnByType[left.type] ?? 3) - (columnByType[right.type] ?? 3);
    if (columnDiff !== 0) return columnDiff;
    const typeDiff = (rowWeightByType[left.type] ?? 99) - (rowWeightByType[right.type] ?? 99);
    if (typeDiff !== 0) return typeDiff;
    return left.label.localeCompare(right.label);
  });
  const nodes: Node[] = sortedNodes.map((node) => {
    const column = columnByType[node.type] ?? 3;
    const row = rowByColumn.get(column) ?? 0;
    rowByColumn.set(column, row + 1);
    const isSelected = selectedNodeId === node.id;
    const isDimmed = relatedNodeIds ? !relatedNodeIds.has(node.id) : false;
    const theme = nodeTheme(node.type);
    return {
      id: node.id,
      data: { label: <NodeLabel label={node.label} type={node.type} /> },
      position: { x: column * 310, y: row * 120 },
      type: 'default',
      className: `graph-node-${node.type}`,
      style: {
        width: 180,
        minHeight: 54,
        border: isSelected ? '2px solid #f97316' : `1px solid ${theme.border}`,
        background: theme.background,
        color: '#0f172a',
        opacity: isDimmed ? 0.22 : 1,
        boxShadow: isSelected ? '0 0 0 3px rgba(249, 115, 22, 0.18)' : undefined,
        transition: 'opacity 160ms ease, box-shadow 160ms ease, border-color 160ms ease'
      }
    };
  });
  const edges: Edge[] = filteredEdges.map((edge) => {
    const isRelated = selectedNodeId ? edge.source === selectedNodeId || edge.target === selectedNodeId : true;
    const isHovered = hoveredEdgeId === edge.id;
    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: showEdgeLabels || isHovered || (selectedNodeId && isRelated) ? edge.label : undefined,
      animated: Boolean((selectedNodeId && isRelated) || isHovered),
      style: {
        stroke: isHovered ? '#f97316' : isRelated ? '#64748b' : '#cbd5e1',
        opacity: selectedNodeId && !isRelated && !isHovered ? 0.14 : 0.9,
        strokeWidth: (selectedNodeId && isRelated) || isHovered ? 2 : 1
      },
      labelStyle: { fill: '#475569', fontSize: 11 }
    };
  });

  useEffect(() => {
    if (!selectedNodeId) return;
    const node = nodes.find((candidate) => candidate.id === selectedNodeId);
    if (!node) return;
    void setCenter(node.position.x + 90, node.position.y + 35, { zoom: 1.2, duration: 450 });
  }, [nodes, selectedNodeId, setCenter]);

  return (
    <div className="h-[680px] w-full overflow-hidden rounded-md border border-slate-300 bg-white">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        onNodeClick={(_, node) => onNodeSelect?.(node.id)}
        onNodeDoubleClick={(_, node) => onNodeOpen?.(node.id)}
        onEdgeMouseEnter={(_, edge) => setHoveredEdgeId(edge.id)}
        onEdgeMouseLeave={() => setHoveredEdgeId(null)}
        onPaneClick={() => onNodeSelect?.(null)}
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}

function NodeLabel({ label, type }: { label: string; type: string }) {
  const theme = nodeTheme(type);
  const Icon = theme.icon;
  return (
    <div className="flex min-h-[34px] items-center gap-2 text-left">
      <span className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md" style={{ background: theme.badgeBackground, color: theme.accent }}>
        <Icon size={14} strokeWidth={2.2} />
      </span>
      <span className="min-w-0 break-words text-xs leading-snug text-slate-800">{label}</span>
    </div>
  );
}

function nodeTheme(type: string): { background: string; border: string; badgeBackground: string; accent: string; icon: LucideIcon } {
  const themes: Record<string, { background: string; border: string; badgeBackground: string; accent: string; icon: LucideIcon }> = {
    project: { background: '#fff7ed', border: '#fed7aa', badgeBackground: '#ffedd5', accent: '#c2410c', icon: Briefcase },
    source: { background: '#f8fafc', border: '#cbd5e1', badgeBackground: '#e2e8f0', accent: '#475569', icon: FileText },
    task: { background: '#eef2ff', border: '#c7d2fe', badgeBackground: '#e0e7ff', accent: '#4f46e5', icon: CheckSquare },
    idea: { background: '#ecfdf5', border: '#bbf7d0', badgeBackground: '#dcfce7', accent: '#15803d', icon: Lightbulb },
    decision: { background: '#fefce8', border: '#fde68a', badgeBackground: '#fef3c7', accent: '#a16207', icon: BadgeCheck },
    question: { background: '#fdf2f8', border: '#fbcfe8', badgeBackground: '#fce7f3', accent: '#be185d', icon: CircleHelp },
    tag: { background: '#f1f5f9', border: '#cbd5e1', badgeBackground: '#e2e8f0', accent: '#334155', icon: Tag },
    person: { background: '#eff6ff', border: '#bfdbfe', badgeBackground: '#dbeafe', accent: '#1d4ed8', icon: User },
    entity: { background: '#f5f3ff', border: '#ddd6fe', badgeBackground: '#ede9fe', accent: '#6d28d9', icon: GitBranch }
  };
  return themes[type] ?? { background: '#ffffff', border: '#cbd5e1', badgeBackground: '#f1f5f9', accent: '#475569', icon: Box };
}
