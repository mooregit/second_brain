import { api } from './client';

export type GitHubSyncResult = {
  status: string;
  repositories: string[];
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
  failures: { repository?: string; raw_item_id?: string; error: string }[];
};

export function syncGitHub(payload: { max_results?: number; auto_process?: boolean | null } = {}) {
  return api<GitHubSyncResult>('/github/sync', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}
