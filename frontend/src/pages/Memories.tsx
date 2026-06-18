import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Check, Pencil, Trash2, X } from 'lucide-react';
import { api } from '../api/client';
import type { Memory } from '../api/items';
import { deleteMemory, patchMemory } from '../api/memories';

export default function Memories() {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [summaryDraft, setSummaryDraft] = useState('');
  const [tagsDraft, setTagsDraft] = useState('');
  const memories = useQuery({ queryKey: ['memories'], queryFn: () => api<Memory[]>('/memories') });
  const deleteMutation = useMutation({
    mutationFn: deleteMemory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['graph'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    }
  });
  const patchMutation = useMutation({
    mutationFn: ({ memoryId, summary, tags }: { memoryId: string; summary: string; tags: string[] }) => patchMemory(memoryId, { summary, tags }),
    onSuccess: () => {
      setEditingId(null);
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['graph'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    }
  });

  function startEdit(memory: Memory) {
    setEditingId(memory.id);
    setSummaryDraft(memory.summary);
    setTagsDraft(memory.tags.join(', '));
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h1 className="mb-4 text-xl font-semibold">Memories</h1>
      <div className="divide-y divide-slate-100">
        {memories.data?.map((memory) => (
          <div key={memory.id} className="py-3 hover:bg-slate-50">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                {editingId === memory.id ? (
                  <div className="space-y-2">
                    <textarea className="h-20 w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={summaryDraft} onChange={(event) => setSummaryDraft(event.target.value)} />
                    <input className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={tagsDraft} onChange={(event) => setTagsDraft(event.target.value)} />
                  </div>
                ) : (
                  <>
                    <Link to={`/items/${memory.raw_item_id}`} className="font-medium underline-offset-2 hover:underline">
                      {memory.summary}
                    </Link>
                    <div className="mt-1 text-sm text-slate-500">{memory.tags.join(', ') || memory.memory_type}</div>
                  </>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-1">
                {editingId === memory.id ? (
                  <>
                    <button
                      type="button"
                      onClick={() =>
                        patchMutation.mutate({
                          memoryId: memory.id,
                          summary: summaryDraft.trim(),
                          tags: tagsDraft
                            .split(',')
                            .map((tag) => tag.trim())
                            .filter(Boolean)
                        })
                      }
                      disabled={patchMutation.isPending || !summaryDraft.trim()}
                      className="rounded-md border border-emerald-200 p-1.5 text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
                      title="Save memory"
                    >
                      <Check size={14} />
                    </button>
                    <button type="button" onClick={() => setEditingId(null)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Cancel edit">
                      <X size={14} />
                    </button>
                  </>
                ) : (
                  <button type="button" onClick={() => startEdit(memory)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Edit memory">
                    <Pencil size={14} />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => {
                    if (window.confirm('Delete this memory and its extracted records? The source inbox item will stay.')) {
                      deleteMutation.mutate(memory.id);
                    }
                  }}
                  disabled={deleteMutation.isPending}
                  className="rounded-md border border-rose-200 p-1.5 text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                  title="Delete memory"
                  aria-label="Delete memory"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
