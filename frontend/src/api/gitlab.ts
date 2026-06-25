import { api } from './client';

export type GitLabSyncResult = {
  status: string;
  base_url: string;
  project_paths: string[];
  auto_process: boolean;
  max_results: number;
  synced_at: string;
  imported_count: number;
  skipped_count: number;
  queued_count: number;
  failed_count: number;
  imported_items: unknown[];
  skipped_source_uris: string[];
  queued_item_ids: string[];
  queued_run_ids: string[];
  failures: { project_path?: string; raw_item_id?: string; error: string }[];
};

export function syncGitLab(payload: { max_results?: number; auto_process?: boolean | null } = {}) {
  return api<GitLabSyncResult>('/gitlab/sync', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}
