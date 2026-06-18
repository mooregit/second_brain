import { api } from './client';

export type GraphNode = { id: string; type: string; label: string; metadata: Record<string, unknown> };

export type GraphResponse = {
  nodes: GraphNode[];
  edges: { id: string; source: string; target: string; label: string; relationship_type: string }[];
};

export function getGraph(showArchived = false) {
  return api<GraphResponse>(`/graph?show_archived=${showArchived}`);
}
