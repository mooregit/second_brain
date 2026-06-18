import { useEffect, useMemo, useState } from 'react';
import { forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY } from 'd3-force';
import { BadgeCheck, Box, Briefcase, CheckSquare, CircleHelp, FileText, GitBranch, Lightbulb, Tag, User, type LucideIcon } from 'lucide-react';
import ReactFlow, { Background, Controls, Edge, Node, ReactFlowProvider, useReactFlow } from 'reactflow';
import 'reactflow/dist/style.css';
import type { GraphNode, GraphResponse } from '../api/graph';

export type GraphLayoutMode = 'cluster' | 'project' | 'source' | 'task' | 'entity';

type ColumnLayoutMode = Exclude<GraphLayoutMode, 'cluster'>;

const columnByTypeByLayout: Record<ColumnLayoutMode, Record<string, number>> = {
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
  const { fitView, getZoom, setCenter } = useReactFlow();
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
  const nodePositions = useMemo(
    () => (layoutMode === 'cluster' ? clusterPositions(filteredNodes, filteredEdges) : columnPositions(filteredNodes, layoutMode)),
    [filteredEdges, filteredNodes, layoutMode]
  );
  const nodes: Node[] = filteredNodes.map((node) => {
    const isSelected = selectedNodeId === node.id;
    const isDimmed = relatedNodeIds ? !relatedNodeIds.has(node.id) : false;
    const theme = nodeTheme(node.type);
    const position = nodePositions.get(node.id) ?? { x: 0, y: 0 };
    return {
      id: node.id,
      data: { label: <NodeLabel label={node.label} type={node.type} /> },
      position,
      type: 'default',
      className: `graph-node-${node.type}`,
      style: {
        width: 170,
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

  const fitViewKey = `${layoutMode}:${filteredNodes.map((node) => node.id).join('|')}`;

  useEffect(() => {
    void fitView({ padding: 0.18, minZoom: 0.15, maxZoom: 1.1, duration: 250 });
  }, [fitView, fitViewKey]);

  useEffect(() => {
    if (!selectedNodeId) return;
    const node = nodes.find((candidate) => candidate.id === selectedNodeId);
    if (!node) return;
    void setCenter(node.position.x + 90, node.position.y + 35, { zoom: getZoom(), duration: 250 });
  }, [getZoom, nodes, selectedNodeId, setCenter]);

  return (
    <div className="h-[680px] w-full overflow-hidden rounded-md border border-slate-300 bg-white">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        minZoom={0.08}
        maxZoom={4}
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

function columnPositions(nodes: GraphNode[], layoutMode: ColumnLayoutMode): Map<string, { x: number; y: number }> {
  const rowByColumn = new Map<number, number>();
  const columnByType = columnByTypeByLayout[layoutMode];
  const sortedNodes = [...nodes].sort((left, right) => {
    const columnDiff = (columnByType[left.type] ?? 3) - (columnByType[right.type] ?? 3);
    if (columnDiff !== 0) return columnDiff;
    const typeDiff = (rowWeightByType[left.type] ?? 99) - (rowWeightByType[right.type] ?? 99);
    if (typeDiff !== 0) return typeDiff;
    return left.label.localeCompare(right.label);
  });
  return new Map(
    sortedNodes.map((node) => {
      const column = columnByType[node.type] ?? 3;
      const row = rowByColumn.get(column) ?? 0;
      rowByColumn.set(column, row + 1);
      return [node.id, { x: column * 260, y: row * 96 }];
    })
  );
}

function clusterPositions(nodes: GraphNode[], edges: GraphResponse['edges']): Map<string, { x: number; y: number }> {
  const sortedNodes = [...nodes].sort((left, right) => left.id.localeCompare(right.id));
  const clusterKeys = [...new Set(sortedNodes.map(clusterKey))].sort();
  const clusterCenters = new Map<string, { x: number; y: number }>();
  const radius = Math.max(180, Math.ceil(clusterKeys.length / 4) * 150);
  clusterKeys.forEach((key, index) => {
    const angle = (index / Math.max(clusterKeys.length, 1)) * Math.PI * 2;
    clusterCenters.set(key, { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius });
  });
  const simulationNodes = sortedNodes.map((node, index) => {
    const center = clusterCenters.get(clusterKey(node)) ?? { x: 0, y: 0 };
    const angle = index * 2.399963229728653;
    return {
      id: node.id,
      cluster: clusterKey(node),
      x: center.x + Math.cos(angle) * 55,
      y: center.y + Math.sin(angle) * 55
    };
  });
  const simulationLinks = edges.map((edge) => ({ source: edge.source, target: edge.target }));
  const simulation = forceSimulation(simulationNodes)
    .force('link', forceLink(simulationLinks).id((node: any) => node.id).distance(120).strength(0.48))
    .force('charge', forceManyBody().strength(-300))
    .force('collide', forceCollide(104).strength(0.92))
    .force('x', forceX((node: any) => clusterCenters.get(node.cluster)?.x ?? 0).strength(0.13))
    .force('y', forceY((node: any) => clusterCenters.get(node.cluster)?.y ?? 0).strength(0.13))
    .stop();
  for (let tick = 0; tick < 220; tick += 1) simulation.tick();
  const minX = Math.min(...simulationNodes.map((node) => node.x ?? 0));
  const minY = Math.min(...simulationNodes.map((node) => node.y ?? 0));
  return new Map(
    simulationNodes.map((node) => [
      node.id,
      {
        x: Math.round((node.x ?? 0) - minX + 60),
        y: Math.round((node.y ?? 0) - minY + 60)
      }
    ])
  );
}

function clusterKey(node: GraphNode): string {
  const projectId = stringMetadata(node, 'project_id');
  if (projectId) return `project:${projectId}`;
  const tags = arrayMetadata(node, 'tags');
  if (tags.length) return `tag:${tags[0].toLowerCase()}`;
  const rawItemId = stringMetadata(node, 'raw_item_id');
  if (rawItemId) return `source:${rawItemId}`;
  return `${node.type}:${node.label.slice(0, 24).toLowerCase()}`;
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

function stringMetadata(node: GraphNode, key: string) {
  const value = node.metadata[key];
  return typeof value === 'string' && value.trim() ? value : null;
}

function arrayMetadata(node: GraphNode, key: string) {
  const value = node.metadata[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}
