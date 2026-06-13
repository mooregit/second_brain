import { api } from './client';

export type GraphResponse = {
  nodes: { id: string; type: string; label: string; metadata: Record<string, unknown> }[];
  edges: { id: string; source: string; target: string; label: string; relationship_type: string }[];
};

export function getGraph() {
  return api<GraphResponse>('/graph');
}

