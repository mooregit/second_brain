import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ExternalLink, Loader2, Save, Search, X } from 'lucide-react';
import { GraphNode, getGraph } from '../api/graph';
import { patchDecision, patchIdea, patchQuestion, patchTask } from '../api/review';
import { patchProject } from '../api/views';
import GraphCanvas from '../components/GraphCanvas';

const defaultTypes = ['project', 'source', 'task', 'idea', 'decision', 'question'];

export default function Graph() {
  const queryClient = useQueryClient();
  const [showArchived, setShowArchived] = useState(false);
  const [showTags, setShowTags] = useState(true);
  const [showEntities, setShowEntities] = useState(false);
  const [showEdgeLabels, setShowEdgeLabels] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [labelDraft, setLabelDraft] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [searchMessage, setSearchMessage] = useState('');
  const [projectFilter, setProjectFilter] = useState('');
  const [tagFilter, setTagFilter] = useState('');
  const [sourceTypeFilter, setSourceTypeFilter] = useState('');
  const [dateFromFilter, setDateFromFilter] = useState('');
  const [dateToFilter, setDateToFilter] = useState('');
  const graph = useQuery({ queryKey: ['graph', showArchived], queryFn: () => getGraph(showArchived) });
  const selectedNode = graph.data?.nodes.find((node) => node.id === selectedNodeId) ?? null;
  const editMutation = useMutation({
    mutationFn: ({ node, label }: { node: GraphNode; label: string }) => patchGraphNode(node, label),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['graph'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['items'] });
    }
  });
  const visibleTypes = new Set([
    ...defaultTypes,
    ...(showTags ? ['tag'] : []),
    ...(showEntities ? ['entity', 'person'] : [])
  ]);
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
  const visibleNodeIds = useMemo(() => {
    if (!graph.data) return new Set<string>();
    return new Set(graph.data.nodes.filter((node) => passesGraphFilters(node, { projectFilter, tagFilter, sourceTypeFilter, dateFromFilter, dateToFilter })).map((node) => node.id));
  }, [dateFromFilter, dateToFilter, graph.data, projectFilter, sourceTypeFilter, tagFilter]);
  const visibleNodes = graph.data?.nodes.filter((node) => visibleTypes.has(node.type) && visibleNodeIds.has(node.id)) ?? [];

  function selectNode(nodeId: string | null) {
    const node = graph.data?.nodes.find((candidate) => candidate.id === nodeId);
    setSelectedNodeId(nodeId);
    setLabelDraft(node?.label ?? '');
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
            <input type="checkbox" checked={showTags} onChange={(event) => setShowTags(event.target.checked)} />
            Tags
          </label>
          <label className="inline-flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={showEntities} onChange={(event) => setShowEntities(event.target.checked)} />
            Entities
          </label>
          <label className="inline-flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={showEdgeLabels} onChange={(event) => setShowEdgeLabels(event.target.checked)} />
            Edge labels
          </label>
          <div className="text-sm text-slate-500">{graph.data?.nodes.length ?? 0} nodes</div>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-3 rounded-md border border-slate-200 bg-white p-3">
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
      </div>
      <div className="grid gap-3 rounded-md border border-slate-200 bg-white p-3 md:grid-cols-5">
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
            showEdgeLabels={showEdgeLabels}
            selectedNodeId={selectedNodeId}
            onNodeSelect={selectNode}
          />
        ) : (
          <div>Loading...</div>
        )}
        <GraphDetailDrawer
          node={selectedNode}
          labelDraft={labelDraft}
          setLabelDraft={setLabelDraft}
          isSaving={editMutation.isPending}
          onSave={() => {
            if (selectedNode && labelDraft.trim()) editMutation.mutate({ node: selectedNode, label: labelDraft.trim() });
          }}
        />
      </div>
      {graph.error && <p className="text-sm text-red-700">{graph.error.message}</p>}
      {editMutation.error && <p className="text-sm text-red-700">{editMutation.error.message}</p>}
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
  onSave
}: {
  node: GraphNode | null;
  labelDraft: string;
  setLabelDraft: (value: string) => void;
  isSaving: boolean;
  onSave: () => void;
}) {
  if (!node) {
    return (
      <aside className="rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-600">
        Select a graph node to inspect it, highlight nearby records, or edit supported node labels.
      </aside>
    );
  }
  const editable = isEditableNode(node);
  const rawItemId = typeof node.metadata.raw_item_id === 'string' ? node.metadata.raw_item_id : null;
  const tags = Array.isArray(node.metadata.tags) ? node.metadata.tags.filter((tag): tag is string => typeof tag === 'string') : [];
  const body = stringMetadata(node, 'body') ?? stringMetadata(node, 'description') ?? stringMetadata(node, 'rationale');

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
          disabled={isSaving || !labelDraft.trim()}
          className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-50"
        >
          {isSaving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
          Save
        </button>
      ) : (
        <p className="mt-3 rounded-md bg-slate-50 p-2 text-sm text-slate-600">This node is derived from source text or tags and is not directly editable yet.</p>
      )}
      {rawItemId && (
        <Link className="mt-3 inline-flex items-center gap-2 text-sm text-sky-700 underline-offset-2 hover:underline" to={`/items/${rawItemId}`}>
          <ExternalLink size={14} />
          Open source item
        </Link>
      )}
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
  return ['project', 'task', 'idea', 'decision', 'question'].includes(node.type);
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
  throw new Error('This graph node cannot be edited directly.');
}
