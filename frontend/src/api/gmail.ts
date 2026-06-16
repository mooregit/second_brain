import { api } from './client';
import type { RawItem } from './items';

export type GmailStatus = {
  enabled: boolean;
  query: string;
  label: string;
  auto_process: boolean;
};

export type GmailSyncResponse = {
  query: string;
  imported_count: number;
  skipped_count: number;
  processed_count: number;
  failed_count: number;
  imported_items: RawItem[];
  skipped_message_ids: string[];
  processed_item_ids: string[];
  failures: { raw_item_id: string; error: string }[];
};

export function getGmailStatus() {
  return api<GmailStatus>('/gmail/status');
}

export function syncGmail(maxResults = 10) {
  return api<GmailSyncResponse>('/gmail/sync', {
    method: 'POST',
    body: JSON.stringify({ max_results: maxResults })
  });
}
