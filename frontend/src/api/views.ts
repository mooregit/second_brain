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

export type ProjectBrief = {
  project: Project;
  summary: string;
  counts: {
    open_tasks: number;
    active_ideas: number;
    decisions: number;
    open_questions: number;
    answered_questions: number;
  };
  risks: string[];
  next_actions: string[];
  github_failures: {
    raw_item_id: string;
    name: string;
    repository: string;
    conclusion: string;
    branch?: string | null;
    url?: string | null;
    source_title: string;
  }[];
  recent_sources: { raw_item_id: string; title: string; source_type: string; created_at: string }[];
  open_tasks: Omit<Task, 'project_id'>[];
  open_questions: Omit<OpenQuestion, 'project_id' | 'answer_confidence' | 'answer_sources_json' | 'answered_at'>[];
  active_ideas: Omit<Idea, 'project_id'>[];
  recent_decisions: Omit<Decision, 'project_id'>[];
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
  gmail_credentials_exists: boolean;
  gmail_token_exists: boolean;
  gmail_status: string;
  gmail_last_sync: {
    status: string;
    query: string;
    synced_at: string;
    imported_count: number;
    skipped_count: number;
    processed_count: number;
    queued_count?: number;
    failed_count: number;
    error?: string;
  } | null;
  gitlab_enabled: boolean;
  gitlab_base_url: string;
  gitlab_projects: string;
  gitlab_auto_process: boolean;
  gitlab_token_configured: boolean;
  gitlab_status: string;
  gitlab_last_sync: {
    status: string;
    synced_at: string;
    imported_count: number;
    skipped_count: number;
    queued_count: number;
    failed_count: number;
    error?: string;
  } | null;
  github_enabled: boolean;
  github_repositories: string;
  github_auto_process: boolean;
  github_token_configured: boolean;
  github_status: string;
  github_last_sync: {
    status: string;
    synced_at: string;
    imported_count: number;
    skipped_count: number;
    queued_count: number;
    failed_count: number;
    error?: string;
  } | null;
};

export type OllamaModelInfo = {
  name: string;
  model: string;
  size: number | null;
  modified_at: string | null;
  capabilities: string[];
  supports_completion: boolean;
  supports_embedding: boolean;
  parameter_size?: string | null;
  context_length?: number | null;
  embedding_length?: number | null;
};

export type OllamaModelsResponse = {
  models: OllamaModelInfo[];
  completion_models: OllamaModelInfo[];
  embedding_models: OllamaModelInfo[];
};

export const listProjects = () => api<Project[]>('/projects');
export const getProject = (projectId: string) => api<Project>(`/projects/${projectId}`);
export const getProjectBrief = (projectId: string) => api<ProjectBrief>(`/projects/${projectId}/brief`);
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
export const listOllamaModels = () => api<OllamaModelsResponse>('/settings/ollama/models');
export const patchSettings = (payload: Partial<Pick<Settings, 'inbox_folder' | 'ollama_extraction_model' | 'ollama_embedding_model' | 'gmail_enabled' | 'gmail_label' | 'gmail_query' | 'gmail_auto_process' | 'gitlab_enabled' | 'gitlab_base_url' | 'gitlab_projects' | 'gitlab_auto_process' | 'github_enabled' | 'github_repositories' | 'github_auto_process'>> & { gitlab_token?: string; github_token?: string }) =>
  api<Settings>('/settings', {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
