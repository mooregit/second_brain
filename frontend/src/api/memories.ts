import { api } from './client';
import type { Memory } from './items';

export function patchMemory(id: string, payload: { summary?: string; tags?: string[] }) {
  return api<Memory>(`/memories/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

