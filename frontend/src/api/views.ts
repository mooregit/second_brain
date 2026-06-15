import { api } from './client';

export type Project = { id: string; name: string; description: string | null; created_at: string };
export type Task = { id: string; title: string; description: string | null; priority: string | null; status: string; source_raw_item_id: string };
export type Decision = { id: string; title: string; rationale: string | null; confidence: number; source_raw_item_id: string };
export type OpenQuestion = { id: string; question: string; status: string; source_raw_item_id: string };
export type Settings = {
  ollama_base_url: string;
  ollama_extraction_model: string;
  ollama_embedding_model: string;
  inbox_folder: string;
  gmail_status: string;
};

export const listProjects = () => api<Project[]>('/projects');
export const listTasks = (showArchived = false) => api<Task[]>(`/tasks?show_archived=${showArchived}`);
export const listDecisions = () => api<Decision[]>('/decisions');
export const listOpenQuestions = (showArchived = false) => api<OpenQuestion[]>(`/open-questions?show_archived=${showArchived}`);
export const getSettings = () => api<Settings>('/settings');
export const patchSettings = (payload: Partial<Pick<Settings, 'inbox_folder'>>) =>
  api<Settings>('/settings', {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
