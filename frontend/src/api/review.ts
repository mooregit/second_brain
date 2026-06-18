import { api } from './client';
import type { AskResponse } from './ask';
import type { Memory } from './items';
import type { OpenQuestion } from './views';

export type TaskPatch = {
  title?: string;
  description?: string | null;
  priority?: string | null;
  status?: string;
  project_id?: string | null;
};

export type TaskCreate = {
  memory_id: string;
  title: string;
  description?: string | null;
  priority?: string | null;
  status?: string;
};

export type IdeaPatch = {
  body?: string;
  status?: string;
  project_id?: string | null;
};

export type IdeaCreate = {
  memory_id: string;
  body: string;
  status?: string;
};

export type DecisionPatch = {
  title?: string;
  rationale?: string | null;
  confidence?: number;
  project_id?: string | null;
};

export type DecisionCreate = {
  memory_id: string;
  title: string;
  rationale?: string | null;
  confidence?: number;
};

export type QuestionPatch = {
  question?: string;
  status?: string;
  project_id?: string | null;
  answer_text?: string | null;
  answer_confidence?: number | null;
  answer_sources_json?: Record<string, unknown>[];
};

export type QuestionCreate = {
  memory_id: string;
  question: string;
  status?: string;
};

export function createTask(payload: TaskCreate) {
  return api<Memory['tasks'][number]>('/tasks', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function patchTask(id: string, payload: TaskPatch) {
  return api<Memory['tasks'][number]>(`/tasks/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export function deleteTask(id: string) {
  return api<{ status: string; id: string }>(`/tasks/${id}`, { method: 'DELETE' });
}

export function createIdea(payload: IdeaCreate) {
  return api<Memory['ideas'][number]>('/ideas', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function patchIdea(id: string, payload: IdeaPatch) {
  return api<Memory['ideas'][number]>(`/ideas/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export function deleteIdea(id: string) {
  return api<{ status: string; id: string }>(`/ideas/${id}`, { method: 'DELETE' });
}

export function createDecision(payload: DecisionCreate) {
  return api<Memory['decisions'][number]>('/decisions', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function patchDecision(id: string, payload: DecisionPatch) {
  return api<Memory['decisions'][number]>(`/decisions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export function deleteDecision(id: string) {
  return api<{ status: string; id: string }>(`/decisions/${id}`, { method: 'DELETE' });
}

export function createQuestion(payload: QuestionCreate) {
  return api<Memory['open_questions'][number]>('/open-questions', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function patchQuestion(id: string, payload: QuestionPatch) {
  return api<Memory['open_questions'][number]>(`/open-questions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export function deleteQuestion(id: string) {
  return api<{ status: string; id: string }>(`/open-questions/${id}`, { method: 'DELETE' });
}

export function askQuestionRecord(id: string) {
  return api<AskResponse>(`/open-questions/${id}/ask`, { method: 'POST' });
}

export function answerQuestion(id: string, payload: { answer_text: string; answer_confidence?: number | null; answer_sources_json?: Record<string, unknown>[] }) {
  return api<OpenQuestion>(`/open-questions/${id}/answer`, {
    method: 'POST',
    body: JSON.stringify({ answer_sources_json: [], ...payload })
  });
}
