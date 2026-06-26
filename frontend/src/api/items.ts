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
  metadata_json: Record<string, unknown> | null;
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
  open_questions: {
    id: string;
    question: string;
    status: string;
    answer_text: string | null;
    answer_confidence: number | null;
    answer_sources_json: unknown[];
    answered_at: string | null;
    source_raw_item_id: string;
  }[];
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

export type MediaArtifact = {
  id: string;
  artifact_type: string;
  status: string;
  text_content: string | null;
  stored_path: string | null;
  metadata_json: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string;
};

export type FileAsset = {
  id: string;
  filename: string;
  stored_path: string;
  mime_type: string | null;
  size_bytes: number | null;
  sha256: string | null;
  media_artifacts: MediaArtifact[];
};

export type ItemDetailResponse = {
  item: RawItem;
  latest_processing_run: ProcessingRun | null;
  file_assets: FileAsset[];
  document_chunks: {
    item: RawItem;
    latest_processing_run: ProcessingRun | null;
    memories: Memory[];
  }[];
  memories: Memory[];
};

export type ScanInboxResponse = {
  folder: string;
  created_count: number;
  skipped_count: number;
  created_items: RawItem[];
  skipped_files: string[];
};

export function listItems() {
  return api<RawItem[]>('/items');
}

export function deleteItem(id: string) {
  return api<{ status: string; id: string }>(`/items/${id}`, { method: 'DELETE' });
}

export function createManualItem(body_text: string, title?: string) {
  return api<RawItem>('/items/manual', {
    method: 'POST',
    body: JSON.stringify({ title, body_text })
  });
}

export function uploadItem(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  return api<RawItem>('/items/upload', {
    method: 'POST',
    body: formData
  });
}

export function scanInboxFolder() {
  return api<ScanInboxResponse>('/items/scan-inbox', { method: 'POST' });
}

export function getItem(id: string) {
  return api<ItemDetailResponse>(`/items/${id}`);
}

export function processItem(id: string) {
  return api<{ run_id: string; status: string; raw_item_status: string }>(`/items/${id}/process`, { method: 'POST' });
}

export function generateBookBrief(id: string) {
  return api<{ run_id: string; status: string }>(`/items/${id}/book-brief`, { method: 'POST' });
}

export function cancelProcessingRun(id: string) {
  return api<ProcessingRun>(`/processing-runs/${id}/cancel`, { method: 'POST' });
}

export function retryProcessingRun(id: string) {
  return api<ProcessingRun>(`/processing-runs/${id}/retry`, { method: 'POST' });
}
