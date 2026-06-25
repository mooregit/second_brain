import { api } from './client';

export type GraphNode = { id: string; type: string; label: string; metadata: Record<string, unknown> };

export type GraphResponse = {
  nodes: GraphNode[];
  edges: { id: string; source: string; target: string; label: string; relationship_type: string; origin?: string; confidence?: number | null }[];
};

export function getGraph(showArchived = false) {
  return api<GraphResponse>(`/graph?show_archived=${showArchived}`);
}

export type GraphInsightsResponse = {
  duplicate_candidates: {
    node_type: string;
    canonical_label: string;
    labels: string[];
    node_ids: string[];
    reason: string;
  }[];
  relationship_normalizations: {
    original_type: string;
    normalized_type: string;
    count: number;
  }[];
  unassigned_work_items: {
    id: string;
    type: string;
    label: string;
    memory_id: string;
    source_title?: string | null;
  }[];
  project_summaries: {
    project_id: string;
    name: string;
    open_tasks: number;
    open_questions: number;
    active_ideas: number;
    decisions: number;
    risk_flags: string[];
  }[];
};

export function getGraphInsights(showArchived = false) {
  return api<GraphInsightsResponse>(`/graph/insights?show_archived=${showArchived}`);
}

export function renameGraphTag(tagId: string, name: string) {
  return api<{ status: string; id: string; name: string }>(`/graph/tags/${tagId}`, {
    method: 'PATCH',
    body: JSON.stringify({ name })
  });
}

export function deleteGraphTag(tagId: string) {
  return api<{ status: string; id: string }>(`/graph/tags/${tagId}`, { method: 'DELETE' });
}

export function renameGraphLabel(nodeType: 'entity' | 'person', oldLabel: string, newLabel: string) {
  return api<{ status: string; updated: number }>('/graph/labels', {
    method: 'PATCH',
    body: JSON.stringify({ node_type: nodeType, old_label: oldLabel, new_label: newLabel })
  });
}

export function deleteGraphLabel(nodeType: 'entity' | 'person', label: string) {
  return api<{ status: string; deleted: number }>('/graph/labels', {
    method: 'DELETE',
    body: JSON.stringify({ node_type: nodeType, label })
  });
}

export function createGraphRelationship(payload: {
  source_label: string;
  source_node_type: string;
  target_label: string;
  target_node_type: string;
  relationship_type: string;
}) {
  return api<{ status: string; id: string; raw_item_id: string; memory_id: string }>('/graph/relationships', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export type GraphDeduplicateResult = {
  status: string;
  projects_merged: number;
  tags_merged: number;
  relationship_labels_normalized: number;
  relationship_node_types_updated: number;
  relationships_removed: number;
};

export function deduplicateGraph() {
  return api<GraphDeduplicateResult>('/graph/deduplicate', { method: 'POST' });
}

export function normalizeGraphRelationships() {
  return api<{ status: string; updated: number }>('/graph/relationships/normalize', { method: 'POST' });
}
