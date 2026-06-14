import { api } from './client';

export type AskResponse = {
  ask_run_id: string | null;
  answer: string;
  sources: { owner_type: string; owner_id: string; score: number; title: string; raw_item_id: string | null }[];
};

export type AskSavePayload = {
  save_as: 'task' | 'open_question' | 'decision';
  title?: string;
  body?: string;
  rationale?: string;
  confidence?: number;
};

export type AskSaveResponse = {
  raw_item_id: string;
  memory_id: string;
  entity_type: string;
  entity_id: string;
};

export function askQuestion(question: string) {
  return api<AskResponse>('/ask', {
    method: 'POST',
    body: JSON.stringify({ question })
  });
}

export function saveAskResult(askRunId: string, payload: AskSavePayload) {
  return api<AskSaveResponse>(`/ask/${askRunId}/save`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}
