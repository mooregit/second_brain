import { api } from './client';
import type { Memory } from './items';

export type TaskPatch = {
  title?: string;
  description?: string | null;
  priority?: string | null;
  status?: string;
};

export type IdeaPatch = {
  body?: string;
};

export type QuestionPatch = {
  question?: string;
  status?: string;
};

export function patchTask(id: string, payload: TaskPatch) {
  return api<Memory['tasks'][number]>(`/tasks/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export function patchIdea(id: string, payload: IdeaPatch) {
  return api<Memory['ideas'][number]>(`/ideas/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export function patchQuestion(id: string, payload: QuestionPatch) {
  return api<Memory['open_questions'][number]>(`/open-questions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

