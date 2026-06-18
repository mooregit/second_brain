import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Archive, Check, Pencil, Trash2, X } from 'lucide-react';
import { Idea, listIdeas } from '../api/views';
import { deleteIdea, patchIdea } from '../api/review';
import SourceLink from '../components/SourceLink';

export default function Ideas() {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState({ body: '', status: 'active' });
  const ideas = useQuery({ queryKey: ['ideas'], queryFn: listIdeas });
  const patchMutation = useMutation({
    mutationFn: ({ ideaId, payload }: { ideaId: string; payload: typeof draft }) =>
      patchIdea(ideaId, { body: payload.body.trim(), status: payload.status }),
    onSuccess: () => {
      setEditingId(null);
      invalidate();
    }
  });
  const deleteMutation = useMutation({ mutationFn: deleteIdea, onSuccess: invalidate });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['ideas'] });
    queryClient.invalidateQueries({ queryKey: ['memories'] });
    queryClient.invalidateQueries({ queryKey: ['graph'] });
  }

  function startEdit(idea: Idea) {
    setEditingId(idea.id);
    setDraft({ body: idea.body, status: idea.status });
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h1 className="mb-4 text-xl font-semibold">Ideas</h1>
      <div className="divide-y divide-slate-100">
        {ideas.data?.map((idea) => (
          <article key={idea.id} className="py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                {editingId === idea.id ? (
                  <div className="space-y-2">
                    <textarea className="h-24 w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={draft.body} onChange={(event) => setDraft({ ...draft, body: event.target.value })} />
                    <select className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}>
                      <option value="active">Active</option>
                      <option value="archived">Archived</option>
                    </select>
                  </div>
                ) : (
                  <>
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-medium">{idea.body}</h2>
                      <span className="rounded bg-slate-100 px-2 py-1 text-xs">{idea.status}</span>
                    </div>
                    <div className="mt-2 text-sm"><SourceLink rawItemId={idea.source_raw_item_id} label="Source" /></div>
                  </>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-1">
                {editingId === idea.id ? (
                  <>
                    <button type="button" onClick={() => patchMutation.mutate({ ideaId: idea.id, payload: draft })} disabled={patchMutation.isPending || !draft.body.trim()} className="rounded-md border border-emerald-200 p-1.5 text-emerald-700 hover:bg-emerald-50 disabled:opacity-50" title="Save idea">
                      <Check size={14} />
                    </button>
                    <button type="button" onClick={() => setEditingId(null)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Cancel edit">
                      <X size={14} />
                    </button>
                  </>
                ) : (
                  <>
                    <button type="button" onClick={() => startEdit(idea)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Edit idea">
                      <Pencil size={14} />
                    </button>
                    {idea.status !== 'archived' && (
                      <button type="button" onClick={() => patchIdea(idea.id, { status: 'archived' }).then(invalidate)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Archive idea">
                        <Archive size={14} />
                      </button>
                    )}
                    <button type="button" onClick={() => window.confirm('Delete this idea?') && deleteMutation.mutate(idea.id)} disabled={deleteMutation.isPending} className="rounded-md border border-rose-200 p-1.5 text-rose-700 hover:bg-rose-50 disabled:opacity-50" title="Delete idea">
                      <Trash2 size={14} />
                    </button>
                  </>
                )}
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
