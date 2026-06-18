import { api } from './client';

export type GraphNode = { id: string; type: string; label: string; metadata: Record<string, unknown> };

export type GraphResponse = {
  nodes: GraphNode[];
  edges: { id: string; source: string; target: string; label: string; relationship_type: string }[];
};

export function getGraph(showArchived = false) {
  return api<GraphResponse>(`/graph?show_archived=${showArchived}`);
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
