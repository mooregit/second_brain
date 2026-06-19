import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { Archive, GitMerge, ExternalLink, Loader2, Save, Search, Trash2, X } from 'lucide-react';
import { createGraphRelationship, deduplicateGraph, deleteGraphLabel, deleteGraphTag, GraphNode, getGraph, renameGraphLabel, renameGraphTag } from '../api/graph';
import { deleteDecision, deleteIdea, deleteQuestion, deleteTask, patchDecision, patchIdea, patchQuestion, patchTask } from '../api/review';
import { deleteProject, patchProject } from '../api/views';
import GraphCanvas, { type GraphLayoutMode } from '../components/GraphCanvas';

const defaultTypes = ['project', 'task', 'idea', 'decision', 'question'];
type GraphIntent = 'work' | 'source' | 'knowledge' | 'full';

const graphIntentConfig: Record<GraphIntent, { label: string; types: string[]; origins: string[]; layout: GraphLayoutMode }> = {
  work: {
    label: 'Work graph',
    types: ['project', 'task', 'idea', 'decision', 'question'],
    origins: ['project', 'manual', 'extracted', 'relationship'],
    layout: 'cluster'
  },
  source: {
    label: 'Source graph',
    types: ['source', 'project', 'task', 'idea', 'decision', 'question'],
    origins: ['source', 'project', 'manual', 'extracted', 'relationship'],
    layout: 'source'
  },
  knowledge: {
    label: 'Knowledge graph',
    types: ['project', 'task', 'idea', 'decision', 'question', 'tag', 'entity', 'person'],
    origins: ['project', 'tag', 'manual', 'extracted', 'relationship'],
    layout: 'cluster'
  },
  full: {
    label: 'Full graph',
    types: ['source', 'project', 'task', 'idea', 'decision', 'question', 'tag', 'entity', 'person'],
    origins: ['source', 'project', 'tag', 'manual', 'extracted', 'relationship'],
    layout: 'cluster'
  }
};

export default function Graph() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [showArchived, setShowArchived] = useState(false);
  const [graphIntent, setGraphIntent] = useState<GraphIntent>('work');
  const [showEdgeLabels, setShowEdgeLabels] = useState(false);
  const [layoutMode, setLayoutMode] = useState<GraphLayoutMode>('cluster');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [labelDraft, setLabelDraft] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [searchMessage, setSearchMessage] = useState('');
  const [projectFilter, setProjectFilter] = useState('');
  const [tagFilter, setTagFilter] = useState('');
  const [sourceTypeFilter, setSourceTypeFilter] = useState('');
  const [relationshipTypeFilter, setRelationshipTypeFilter] = useState('');
  const [dateFromFilter, setDateFromFilter] = useState('');
  const [dateToFilter, setDateToFilter] = useState('');
  const [relationshipTargetId, setRelationshipTargetId] = useState('');
  const [manualRelationshipType, setManualRelationshipType] = useState('related_to');
  const [manualRelationshipDirection, setManualRelationshipDirection] = useState<'out' | 'in'>('out');
  const [dedupeMessage, setDedupeMessage] = useState('');
  const graph = useQuery({ queryKey: ['graph', showArchived], queryFn: () => getGraph(showArchived) });
  const selectedNode = graph.data?.nodes.find((node) => node.id === selectedNodeId) ?? null;
  const editMutation = useMutation({
    mutationFn: ({ node, label }: { node: GraphNode; label: string }) => patchGraphNode(node, label),
    onSuccess: () => invalidateGraphData(queryClient)
  });
  const cleanupMutation = useMutation({
    mutationFn: runGraphCleanup,
    onSuccess: () => {
      setSelectedNodeId(null);
      setLabelDraft('');
      invalidateGraphData(queryClient);
    }
  });
  const relationshipMutation = useMutation({
    mutationFn: createGraphRelationship,
    onSuccess: () => {
      setRelationshipTargetId('');
      setManualRelationshipType('related_to');
      setManualRelationshipDirection('out');
      invalidateGraphData(queryClient);
    }
  });
  const deduplicateMutation = useMutation({
    mutationFn: deduplicateGraph,
    onSuccess: (result) => {
      setDedupeMessage(
        `Merged ${result.projects_merged} projects, ${result.tags_merged} tags; normalized ${result.relationship_labels_normalized} labels; updated ${result.relationship_node_types_updated} relationship node types; removed ${result.relationships_removed} duplicate relationships.`
      );
      setSelectedNodeId(null);
      setLabelDraft('');
      invalidateGraphData(queryClient);
    }
  });
  const intentConfig = graphIntentConfig[graphIntent];
  const visibleTypes = new Set(intentConfig.types);
  const visibleEdgeOrigins = new Set(intentConfig.origins);
  const projectOptions = useMemo(() => graph.data?.nodes.filter((node) => node.type === 'project').map((node) => ({ id: String(node.metadata.project_id ?? ''), label: node.label })).filter((project) => project.id) ?? [], [graph.data?.nodes]);
  const tagOptions = useMemo(() => graph.data?.nodes.filter((node) => node.type === 'tag').map((node) => node.label).sort((left, right) => left.localeCompare(right)) ?? [], [graph.data?.nodes]);
  const sourceTypeOptions = useMemo(() => {
    const sourceTypes = new Set<string>();
    for (const node of graph.data?.nodes ?? []) {
      const sourceType = stringMetadata(node, 'source_type');
      if (sourceType) sourceTypes.add(sourceType);
    }
    return [...sourceTypes].sort();
  }, [graph.data?.nodes]);
  const relationshipTypeOptions = useMemo(() => {
    const relationshipTypes = new Set<string>();
    for (const edge of graph.data?.edges ?? []) {
      if (edge.relationship_type) relationshipTypes.add(edge.relationship_type);
    }
    return [...relationshipTypes].sort();
  }, [graph.data?.edges]);
  const visibleGraphEdges = useMemo(() => {
    if (!graph.data) return [];
    return graph.data.edges.filter((edge) => visibleEdgeOrigins.has(edge.origin ?? 'relationship') && (!relationshipTypeFilter || edge.relationship_type === relationshipTypeFilter));
  }, [graph.data, relationshipTypeFilter, visibleEdgeOrigins]);
  const visibleNodeIds = useMemo(() => {
    if (!graph.data) return new Set<string>();
    return new Set(graph.data.nodes.filter((node) => passesGraphFilters(node, { projectFilter, tagFilter, sourceTypeFilter, dateFromFilter, dateToFilter })).map((node) => node.id));
  }, [dateFromFilter, dateToFilter, graph.data, projectFilter, sourceTypeFilter, tagFilter]);
  const visibleNodes = graph.data?.nodes.filter((node) => visibleTypes.has(node.type) && visibleNodeIds.has(node.id)) ?? [];
  const orphanNodes = useMemo(() => {
    if (!graph.data) return [];
    const renderedNodeIds = new Set(visibleNodes.map((node) => node.id));
    const connectedNodeIds = new Set<string>();
    for (const edge of visibleGraphEdges) {
      if (!renderedNodeIds.has(edge.source) || !renderedNodeIds.has(edge.target)) continue;
      connectedNodeIds.add(edge.source);
      connectedNodeIds.add(edge.target);
    }
    return visibleNodes.filter((node) => defaultTypes.includes(node.type) && !connectedNodeIds.has(node.id));
  }, [graph.data, visibleGraphEdges, visibleNodes]);

  function selectNode(nodeId: string | null) {
    const node = graph.data?.nodes.find((candidate) => candidate.id === nodeId);
    setSelectedNodeId(nodeId);
    setLabelDraft(node?.label ?? '');
    setRelationshipTargetId('');
    if (nodeId) setSearchMessage('');
  }

  function focusSearchResult() {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    if (!normalizedSearch) {
      setSearchMessage('');
      return;
    }
    const match = visibleNodes.find((node) => node.label.toLowerCase().includes(normalizedSearch));
    if (!match) {
      setSearchMessage('No visible node matched that search.');
      return;
    }
    selectNode(match.id);
    setSearchMessage(`Focused ${match.label}`);
  }

  function openNode(nodeId: string) {
    const node = graph.data?.nodes.find((candidate) => candidate.id === nodeId);
    if (!node) return;
    const rawItemId = stringMetadata(node, 'raw_item_id');
    if (rawItemId) {
      navigate(`/items/${rawItemId}`);
      return;
    }
    const routeByType: Record<string, string> = {
      project: '/projects',
      task: '/tasks',
      idea: '/ideas',
      decision: '/decisions',
      question: '/open-questions'
    };
    const route = routeByType[node.type];
    if (route) navigate(route);
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Graph</h1>
        <div className="flex flex-wrap items-center gap-4">
          <label className="inline-flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={showArchived} onChange={(event) => setShowArchived(event.target.checked)} />
            Show archived
          </label>
          <label className="inline-flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={showEdgeLabels} onChange={(event) => setShowEdgeLabels(event.target.checked)} />
            Edge labels
          </label>
          <div className="text-sm text-slate-500">{graph.data?.nodes.length ?? 0} nodes</div>
          <button
            type="button"
            onClick={() => deduplicateMutation.mutate()}
            disabled={deduplicateMutation.isPending}
            className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-white disabled:opacity-50"
          >
            {deduplicateMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <GitMerge size={16} />}
            Deduplicate
          </button>
        </div>
      </div>
      {(dedupeMessage || deduplicateMutation.error) && (
        <div className="rounded-md border border-slate-200 bg-white p-3 text-sm">
          {dedupeMessage && <p className="text-slate-700">{dedupeMessage}</p>}
          {deduplicateMutation.error && <p className="text-red-700">{deduplicateMutation.error.message}</p>}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-3 rounded-md border border-slate-200 bg-white p-3">
        <label className="flex items-center gap-2 text-sm text-slate-600">
          View
          <select
            className="rounded-md border border-slate-300 px-2 py-2 text-sm"
            value={graphIntent}
            onChange={(event) => {
              const nextIntent = event.target.value as GraphIntent;
              setGraphIntent(nextIntent);
              setLayoutMode(graphIntentConfig[nextIntent].layout);
              setSelectedNodeId(null);
            }}
          >
            {(Object.keys(graphIntentConfig) as GraphIntent[]).map((intent) => (
              <option key={intent} value={intent}>{graphIntentConfig[intent].label}</option>
            ))}
          </select>
        </label>
        <div className="relative min-w-[260px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-2.5 text-slate-400" size={16} />
          <input
            className="w-full rounded-md border border-slate-300 py-2 pl-9 pr-9 text-sm"
            placeholder="Search graph nodes..."
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') focusSearchResult();
              if (event.key === 'Escape') {
                setSearchTerm('');
                setSearchMessage('');
              }
            }}
          />
          {searchTerm && (
            <button
              type="button"
              className="absolute right-2 top-2 rounded p-1 text-slate-500 hover:bg-slate-100"
              onClick={() => {
                setSearchTerm('');
                setSearchMessage('');
              }}
              aria-label="Clear search"
            >
              <X size={14} />
            </button>
          )}
        </div>
        <button type="button" onClick={focusSearchResult} className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm text-white">
          <Search size={16} />
          Focus
        </button>
        {searchMessage && <div className="text-sm text-slate-500">{searchMessage}</div>}
        <label className="ml-auto flex items-center gap-2 text-sm text-slate-600">
          Layout
          <select
            className="rounded-md border border-slate-300 px-2 py-2 text-sm"
            value={layoutMode}
            onChange={(event) => setLayoutMode(event.target.value as GraphLayoutMode)}
          >
            <option value="cluster">Cluster map</option>
            <option value="project">Project map</option>
            <option value="source">Source map</option>
            <option value="task">Task map</option>
            <option value="entity">Entity map</option>
          </select>
        </label>
      </div>
      {orphanNodes.length > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <div className="text-sm font-medium text-amber-950">Needs connection</div>
            <div className="text-xs text-amber-800">{orphanNodes.length} visible work nodes are not connected in this view.</div>
          </div>
          <div className="flex flex-wrap gap-2">
            {orphanNodes.slice(0, 10).map((node) => (
              <button
                key={node.id}
                type="button"
                onClick={() => selectNode(node.id)}
                className="rounded-md border border-amber-200 bg-white px-2 py-1 text-xs text-amber-950 hover:bg-amber-100"
              >
                {node.label}
              </button>
            ))}
            {orphanNodes.length > 10 && <span className="px-2 py-1 text-xs text-amber-800">+{orphanNodes.length - 10} more</span>}
          </div>
        </div>
      )}
      <div className="grid gap-3 rounded-md border border-slate-200 bg-white p-3 md:grid-cols-6">
        <label className="block text-xs font-medium text-slate-600">
          Project
          <select className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm" value={projectFilter} onChange={(event) => setProjectFilter(event.target.value)}>
            <option value="">All projects</option>
            {projectOptions.map((project) => (
              <option key={project.id} value={project.id}>{project.label}</option>
            ))}
          </select>
        </label>
        <label className="block text-xs font-medium text-slate-600">
          Tag
          <select className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm" value={tagFilter} onChange={(event) => setTagFilter(event.target.value)}>
            <option value="">All tags</option>
            {tagOptions.map((tag) => (
              <option key={tag} value={tag}>{tag}</option>
            ))}
          </select>
        </label>
        <label className="block text-xs font-medium text-slate-600">
          Source
          <select className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm" value={sourceTypeFilter} onChange={(event) => setSourceTypeFilter(event.target.value)}>
            <option value="">All sources</option>
            {sourceTypeOptions.map((sourceType) => (
              <option key={sourceType} value={sourceType}>{sourceType}</option>
            ))}
          </select>
        </label>
        <label className="block text-xs font-medium text-slate-600">
          Relationship
          <select className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm" value={relationshipTypeFilter} onChange={(event) => setRelationshipTypeFilter(event.target.value)}>
            <option value="">All relationships</option>
            {relationshipTypeOptions.map((relationshipType) => (
              <option key={relationshipType} value={relationshipType}>{relationshipType}</option>
            ))}
          </select>
        </label>
        <label className="block text-xs font-medium text-slate-600">
          From
          <input className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm" type="date" value={dateFromFilter} onChange={(event) => setDateFromFilter(event.target.value)} />
        </label>
        <label className="block text-xs font-medium text-slate-600">
          To
          <input className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm" type="date" value={dateToFilter} onChange={(event) => setDateToFilter(event.target.value)} />
        </label>
      </div>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        {graph.data ? (
          <GraphCanvas
            graph={graph.data}
            visibleTypes={visibleTypes}
            visibleNodeIds={visibleNodeIds}
            visibleEdgeOrigins={visibleEdgeOrigins}
            relationshipTypeFilter={relationshipTypeFilter}
            layoutMode={layoutMode}
            showEdgeLabels={showEdgeLabels}
            selectedNodeId={selectedNodeId}
            onNodeSelect={selectNode}
            onNodeOpen={openNode}
          />
        ) : (
          <div>Loading...</div>
        )}
        <GraphDetailDrawer
          node={selectedNode}
          labelDraft={labelDraft}
          setLabelDraft={setLabelDraft}
          isSaving={editMutation.isPending}
          isCleaning={cleanupMutation.isPending}
          isAttaching={relationshipMutation.isPending}
          projectOptions={projectOptions}
          graphNodes={graph.data?.nodes ?? []}
          relationshipTargetId={relationshipTargetId}
          setRelationshipTargetId={setRelationshipTargetId}
          manualRelationshipType={manualRelationshipType}
          setManualRelationshipType={setManualRelationshipType}
          manualRelationshipDirection={manualRelationshipDirection}
          setManualRelationshipDirection={setManualRelationshipDirection}
          onSave={() => {
            if (selectedNode && labelDraft.trim()) editMutation.mutate({ node: selectedNode, label: labelDraft.trim() });
          }}
          onArchive={() => {
            if (selectedNode) cleanupMutation.mutate({ kind: 'archive', node: selectedNode });
          }}
          onDelete={() => {
            if (selectedNode && window.confirm(`Delete "${selectedNode.label}" from the graph?`)) {
              cleanupMutation.mutate({ kind: 'delete', node: selectedNode });
            }
          }}
          onReassign={(projectId) => {
            if (selectedNode) cleanupMutation.mutate({ kind: 'reassign', node: selectedNode, projectId });
          }}
          onAttach={() => {
            if (!selectedNode || !graph.data || !relationshipTargetId) return;
            const targetNode = graph.data.nodes.find((candidate) => candidate.id === relationshipTargetId);
            if (!targetNode) return;
            const source = manualRelationshipDirection === 'out' ? selectedNode : targetNode;
            const target = manualRelationshipDirection === 'out' ? targetNode : selectedNode;
            relationshipMutation.mutate({
              source_label: source.label,
              source_node_type: source.type,
              target_label: target.label,
              target_node_type: target.type,
              relationship_type: manualRelationshipType.trim() || 'related_to'
            });
          }}
        />
      </div>
      {graph.error && <p className="text-sm text-red-700">{graph.error.message}</p>}
      {editMutation.error && <p className="text-sm text-red-700">{editMutation.error.message}</p>}
      {relationshipMutation.error && <p className="text-sm text-red-700">{relationshipMutation.error.message}</p>}
    </section>
  );
}

function passesGraphFilters(
  node: GraphNode,
  filters: { projectFilter: string; tagFilter: string; sourceTypeFilter: string; dateFromFilter: string; dateToFilter: string }
) {
  if (filters.projectFilter) {
    const nodeProjectId = stringMetadata(node, 'project_id');
    const isProjectNode = node.type === 'project' && stringMetadata(node, 'project_id') === filters.projectFilter;
    if (!isProjectNode && nodeProjectId !== filters.projectFilter) return false;
  }
  if (filters.tagFilter) {
    const nodeTags = arrayMetadata(node, 'tags');
    const isTagNode = node.type === 'tag' && node.label === filters.tagFilter;
    if (!isTagNode && !nodeTags.includes(filters.tagFilter)) return false;
  }
  if (filters.sourceTypeFilter && stringMetadata(node, 'source_type') !== filters.sourceTypeFilter) {
    return false;
  }
  const sourceDate = stringMetadata(node, 'source_created_at')?.slice(0, 10) ?? null;
  if (filters.dateFromFilter && (!sourceDate || sourceDate < filters.dateFromFilter)) return false;
  if (filters.dateToFilter && (!sourceDate || sourceDate > filters.dateToFilter)) return false;
  return true;
}

function GraphDetailDrawer({
  node,
  labelDraft,
  setLabelDraft,
  isSaving,
  isCleaning,
  isAttaching,
  projectOptions,
  graphNodes,
  relationshipTargetId,
  setRelationshipTargetId,
  manualRelationshipType,
  setManualRelationshipType,
  manualRelationshipDirection,
  setManualRelationshipDirection,
  onSave,
  onArchive,
  onDelete,
  onReassign,
  onAttach
}: {
  node: GraphNode | null;
  labelDraft: string;
  setLabelDraft: (value: string) => void;
  isSaving: boolean;
  isCleaning: boolean;
  isAttaching: boolean;
  projectOptions: { id: string; label: string }[];
  graphNodes: GraphNode[];
  relationshipTargetId: string;
  setRelationshipTargetId: (value: string) => void;
  manualRelationshipType: string;
  setManualRelationshipType: (value: string) => void;
  manualRelationshipDirection: 'out' | 'in';
  setManualRelationshipDirection: (value: 'out' | 'in') => void;
  onSave: () => void;
  onArchive: () => void;
  onDelete: () => void;
  onReassign: (projectId: string | null) => void;
  onAttach: () => void;
}) {
  if (!node) {
    return (
      <aside className="rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-600">
        Select a graph node to inspect it, highlight nearby records, or edit supported node labels. Double-click a node to open its source or native page.
      </aside>
    );
  }
  const editable = isEditableNode(node);
  const rawItemId = typeof node.metadata.raw_item_id === 'string' ? node.metadata.raw_item_id : null;
  const tags = Array.isArray(node.metadata.tags) ? node.metadata.tags.filter((tag): tag is string => typeof tag === 'string') : [];
  const body = stringMetadata(node, 'body') ?? stringMetadata(node, 'description') ?? stringMetadata(node, 'rationale') ?? stringMetadata(node, 'answer');
  const status = stringMetadata(node, 'status');
  const canArchive = ['task', 'idea', 'question'].includes(node.type) && status !== 'archived';
  const canDelete = ['project', 'task', 'idea', 'decision', 'question', 'tag', 'entity', 'person'].includes(node.type);
  const canReassign = ['task', 'idea', 'decision', 'question'].includes(node.type);
  const projectId = stringMetadata(node, 'project_id') ?? '';

  return (
    <aside className="rounded-md border border-slate-200 bg-white p-4">
      <div className="mb-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{node.type}</div>
        <div className="mt-1 break-words text-base font-semibold text-slate-900">{node.label}</div>
      </div>
      <div className="mb-4 space-y-2 rounded-md bg-slate-50 p-3 text-sm">
        <DetailRow label="Status" value={stringMetadata(node, 'status')} />
        <DetailRow label="Project" value={stringMetadata(node, 'project_name')} />
        <DetailRow label="Source" value={stringMetadata(node, 'source_title')} />
        <DetailRow label="Priority" value={stringMetadata(node, 'priority')} />
        <DetailRow label="Due" value={stringMetadata(node, 'due_date')} />
        <DetailRow label="Confidence" value={numberMetadata(node, 'confidence')} />
        <DetailRow label="Answer" value={numberMetadata(node, 'answer_confidence')} />
        <DetailRow label="Answered" value={stringMetadata(node, 'answered_at')} />
        {body && (
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Details</div>
            <p className="mt-1 whitespace-pre-wrap break-words text-slate-700">{body}</p>
          </div>
        )}
        {tags.length > 0 && (
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Tags</div>
            <div className="mt-1 flex flex-wrap gap-1">
              {tags.map((tag) => (
                <span key={tag} className="rounded bg-white px-2 py-1 text-xs text-slate-600 ring-1 ring-slate-200">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
      <label className="block text-sm font-medium text-slate-700">
        Label
        <textarea
          className="mt-1 h-28 w-full rounded-md border border-slate-300 p-2 text-sm"
          value={labelDraft}
          onChange={(event) => setLabelDraft(event.target.value)}
          disabled={!editable}
        />
      </label>
      {editable ? (
        <button
          type="button"
          onClick={onSave}
          disabled={isSaving || isCleaning || !labelDraft.trim()}
          className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-50"
        >
          {isSaving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
          Save
        </button>
      ) : (
        <p className="mt-3 rounded-md bg-slate-50 p-2 text-sm text-slate-600">This node is derived from source text or tags and is not directly editable yet.</p>
      )}
      {canReassign && (
        <label className="mt-3 block text-sm font-medium text-slate-700">
          Project
          <select
            className="mt-1 w-full rounded-md border border-slate-300 px-2 py-2 text-sm"
            value={projectId}
            disabled={isCleaning}
            onChange={(event) => onReassign(event.target.value || null)}
          >
            <option value="">No project</option>
            {projectOptions.map((project) => (
              <option key={project.id} value={project.id}>
                {project.label}
              </option>
            ))}
          </select>
        </label>
      )}
      {(canArchive || canDelete) && (
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {canArchive && (
            <button
              type="button"
              onClick={onArchive}
              disabled={isCleaning}
              className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              {isCleaning ? <Loader2 size={16} className="animate-spin" /> : <Archive size={16} />}
              Archive
            </button>
          )}
          {canDelete && (
            <button
              type="button"
              onClick={onDelete}
              disabled={isCleaning}
              className="inline-flex items-center justify-center gap-2 rounded-md border border-red-200 px-3 py-2 text-sm text-red-700 hover:bg-red-50 disabled:opacity-50"
            >
              {isCleaning ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
              Delete
            </button>
          )}
        </div>
      )}
      <div className="mt-4 border-t border-slate-100 pt-4">
        <div className="text-sm font-medium text-slate-800">Create Relationship</div>
        <label className="mt-2 block text-xs font-medium text-slate-600">
          Target node
          <select
            className="mt-1 w-full rounded-md border border-slate-300 px-2 py-2 text-sm"
            value={relationshipTargetId}
            disabled={isAttaching}
            onChange={(event) => setRelationshipTargetId(event.target.value)}
          >
            <option value="">Select a node...</option>
            {graphNodes
              .filter((candidate) => candidate.id !== node.id)
              .sort((left, right) => left.label.localeCompare(right.label))
              .map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {candidate.label} ({candidate.type})
                </option>
              ))}
          </select>
        </label>
        <label className="mt-2 block text-xs font-medium text-slate-600">
          Relationship
          <input
            className="mt-1 w-full rounded-md border border-slate-300 px-2 py-2 text-sm"
            value={manualRelationshipType}
            disabled={isAttaching}
            onChange={(event) => setManualRelationshipType(event.target.value)}
            placeholder="related_to"
          />
        </label>
        <label className="mt-2 block text-xs font-medium text-slate-600">
          Direction
          <select
            className="mt-1 w-full rounded-md border border-slate-300 px-2 py-2 text-sm"
            value={manualRelationshipDirection}
            disabled={isAttaching}
            onChange={(event) => setManualRelationshipDirection(event.target.value as 'out' | 'in')}
          >
            <option value="out">Selected node to target</option>
            <option value="in">Target to selected node</option>
          </select>
        </label>
        <button
          type="button"
          onClick={onAttach}
          disabled={isAttaching || !relationshipTargetId || !manualRelationshipType.trim()}
          className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {isAttaching ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
          Attach node
        </button>
      </div>
      {rawItemId && (
        <Link className="mt-3 inline-flex items-center gap-2 text-sm text-sky-700 underline-offset-2 hover:underline" to={`/items/${rawItemId}`}>
          <ExternalLink size={14} />
          Open source item
        </Link>
      )}
      <p className="mt-3 text-xs text-slate-500">Double-click this node in the graph to open its source or native page.</p>
      <div className="mt-4 break-all border-t border-slate-100 pt-3 text-xs text-slate-400">{node.id}</div>
    </aside>
  );
}

function DetailRow({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div className="grid grid-cols-[84px_minmax(0,1fr)] gap-2">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="break-words text-slate-700">{value}</div>
    </div>
  );
}

function stringMetadata(node: GraphNode, key: string) {
  const value = node.metadata[key];
  return typeof value === 'string' && value.trim() ? value : null;
}

function numberMetadata(node: GraphNode, key: string) {
  const value = node.metadata[key];
  return typeof value === 'number' ? value.toFixed(2) : null;
}

function arrayMetadata(node: GraphNode, key: string) {
  const value = node.metadata[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

function isEditableNode(node: GraphNode): boolean {
  return ['project', 'task', 'idea', 'decision', 'question', 'tag', 'entity', 'person'].includes(node.type);
}

async function patchGraphNode(node: GraphNode, label: string) {
  if (node.type === 'project' && typeof node.metadata.project_id === 'string') {
    return patchProject(node.metadata.project_id, { name: label });
  }
  if (node.type === 'task' && typeof node.metadata.task_id === 'string') {
    return patchTask(node.metadata.task_id, { title: label });
  }
  if (node.type === 'idea' && typeof node.metadata.idea_id === 'string') {
    return patchIdea(node.metadata.idea_id, { body: label });
  }
  if (node.type === 'decision' && typeof node.metadata.decision_id === 'string') {
    return patchDecision(node.metadata.decision_id, { title: label });
  }
  if (node.type === 'question' && typeof node.metadata.question_id === 'string') {
    return patchQuestion(node.metadata.question_id, { question: label });
  }
  if (node.type === 'tag' && typeof node.metadata.tag_id === 'string') {
    return renameGraphTag(node.metadata.tag_id, label);
  }
  if ((node.type === 'entity' || node.type === 'person') && node.label !== label) {
    return renameGraphLabel(node.type, node.label, label);
  }
  throw new Error('This graph node cannot be edited directly.');
}

type CleanupAction =
  | { kind: 'archive'; node: GraphNode }
  | { kind: 'delete'; node: GraphNode }
  | { kind: 'reassign'; node: GraphNode; projectId: string | null };

async function runGraphCleanup(action: CleanupAction) {
  const { node } = action;
  if (action.kind === 'archive') {
    if (node.type === 'task' && typeof node.metadata.task_id === 'string') return patchTask(node.metadata.task_id, { status: 'archived' });
    if (node.type === 'idea' && typeof node.metadata.idea_id === 'string') return patchIdea(node.metadata.idea_id, { status: 'archived' });
    if (node.type === 'question' && typeof node.metadata.question_id === 'string') return patchQuestion(node.metadata.question_id, { status: 'archived' });
  }
  if (action.kind === 'reassign') {
    if (node.type === 'task' && typeof node.metadata.task_id === 'string') return patchTask(node.metadata.task_id, { project_id: action.projectId });
    if (node.type === 'idea' && typeof node.metadata.idea_id === 'string') return patchIdea(node.metadata.idea_id, { project_id: action.projectId });
    if (node.type === 'decision' && typeof node.metadata.decision_id === 'string') return patchDecision(node.metadata.decision_id, { project_id: action.projectId });
    if (node.type === 'question' && typeof node.metadata.question_id === 'string') return patchQuestion(node.metadata.question_id, { project_id: action.projectId });
  }
  if (action.kind === 'delete') {
    if (node.type === 'project' && typeof node.metadata.project_id === 'string') return deleteProject(node.metadata.project_id);
    if (node.type === 'task' && typeof node.metadata.task_id === 'string') return deleteTask(node.metadata.task_id);
    if (node.type === 'idea' && typeof node.metadata.idea_id === 'string') return deleteIdea(node.metadata.idea_id);
    if (node.type === 'decision' && typeof node.metadata.decision_id === 'string') return deleteDecision(node.metadata.decision_id);
    if (node.type === 'question' && typeof node.metadata.question_id === 'string') return deleteQuestion(node.metadata.question_id);
    if (node.type === 'tag' && typeof node.metadata.tag_id === 'string') return deleteGraphTag(node.metadata.tag_id);
    if (node.type === 'entity' || node.type === 'person') return deleteGraphLabel(node.type, node.label);
  }
  throw new Error('This graph cleanup action is not supported for the selected node.');
}

function invalidateGraphData(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ['graph'] });
  queryClient.invalidateQueries({ queryKey: ['projects'] });
  queryClient.invalidateQueries({ queryKey: ['memories'] });
  queryClient.invalidateQueries({ queryKey: ['items'] });
  queryClient.invalidateQueries({ queryKey: ['tasks'] });
  queryClient.invalidateQueries({ queryKey: ['ideas'] });
  queryClient.invalidateQueries({ queryKey: ['decisions'] });
  queryClient.invalidateQueries({ queryKey: ['open-questions'] });
}
