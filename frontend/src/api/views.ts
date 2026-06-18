import { api } from './client';

export type Project = { id: string; name: string; description: string | null; created_at: string };
export type Task = { id: string; project_id: string | null; title: string; description: string | null; priority: string | null; status: string; source_raw_item_id: string };
export type Idea = { id: string; project_id: string | null; body: string; status: string; source_raw_item_id: string };
export type Decision = { id: string; project_id: string | null; title: string; rationale: string | null; confidence: number; source_raw_item_id: string };
export type OpenQuestion = {
  id: string;
  project_id: string | null;
  question: string;
  status: string;
  answer_text: string | null;
  answer_confidence: number | null;
  answer_sources_json: { raw_item_id?: string | null; title?: string; owner_type?: string; owner_id?: string; score?: number }[];
  answered_at: string | null;
  source_raw_item_id: string;
};
export type Settings = {
  ollama_base_url: string;
  ollama_extraction_model: string;
  ollama_embedding_model: string;
  inbox_folder: string;
  gmail_enabled: boolean;
  gmail_label: string;
  gmail_query: string;
  gmail_auto_process: boolean;
  gmail_credentials_path: string;
  gmail_token_path: string;
  gmail_status: string;
};

export const listProjects = () => api<Project[]>('/projects');
export const patchProject = (projectId: string, payload: { name?: string; description?: string | null }) =>
  api<Project>(`/projects/${projectId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
export const deleteProject = (projectId: string) => api<{ status: string; id: string }>(`/projects/${projectId}`, { method: 'DELETE' });
export const listTasks = (showArchived = false) => api<Task[]>(`/tasks?show_archived=${showArchived}`);
export const listIdeas = () => api<Idea[]>('/ideas');
export const listDecisions = () => api<Decision[]>('/decisions');
export const listOpenQuestions = (showArchived = false) => api<OpenQuestion[]>(`/open-questions?show_archived=${showArchived}`);
export const getSettings = () => api<Settings>('/settings');
export const patchSettings = (payload: Partial<Pick<Settings, 'inbox_folder' | 'gmail_enabled' | 'gmail_label' | 'gmail_query' | 'gmail_auto_process'>>) =>
  api<Settings>('/settings', {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
