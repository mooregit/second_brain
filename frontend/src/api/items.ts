import { api } from './client';

export type RawItem = {
  id: string;
  source_type: string;
  title: string;
  body_text: string;
  content_type: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type Memory = {
  id: string;
  raw_item_id: string;
  memory_type: string;
  summary: string;
  confidence: number;
  tags: string[];
  tasks: { id: string; title: string; description: string | null; priority: string | null; status: string; source_raw_item_id: string }[];
  ideas: { id: string; body: string; status: string; source_raw_item_id: string }[];
  decisions: { id: string; title: string; rationale: string | null; confidence: number; source_raw_item_id: string }[];
  open_questions: { id: string; question: string; status: string; source_raw_item_id: string }[];
  created_at: string;
};

export type ProcessingRun = {
  id: string;
  raw_item_id: string;
  status: string;
  model: string;
  prompt_version: string;
  started_at: string;
  finished_at: string | null;
  error: string | null;
  raw_output: string | null;
  original_output: string | null;
  repaired_output: string | null;
  parsed_json: unknown;
};

export type ItemDetailResponse = {
  item: RawItem;
  latest_processing_run: ProcessingRun | null;
  memories: Memory[];
};

export function listItems() {
  return api<RawItem[]>('/items');
}

export function createManualItem(body_text: string, title?: string) {
  return api<RawItem>('/items/manual', {
    method: 'POST',
    body: JSON.stringify({ title, body_text })
  });
}

export function getItem(id: string) {
  return api<ItemDetailResponse>(`/items/${id}`);
}

export function processItem(id: string) {
  return api<{ memory_id: string; status: string }>(`/items/${id}/process`, { method: 'POST' });
}
