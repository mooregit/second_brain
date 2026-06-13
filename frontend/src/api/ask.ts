import { api } from './client';

export type AskResponse = {
  answer: string;
  sources: { owner_type: string; owner_id: string; score: number; title: string; raw_item_id: string | null }[];
};

export function askQuestion(question: string) {
  return api<AskResponse>('/ask', {
    method: 'POST',
    body: JSON.stringify({ question })
  });
}

