import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, Pencil, Trash2, X } from 'lucide-react';
import { Decision, listDecisions, listProjects } from '../api/views';
import { deleteDecision, patchDecision } from '../api/review';
import SourceLink from '../components/SourceLink';

export default function Decisions() {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState({ title: '', rationale: '', confidence: 0, project_id: '' });
  const decisions = useQuery({ queryKey: ['decisions'], queryFn: listDecisions });
  const projects = useQuery({ queryKey: ['projects'], queryFn: listProjects });
  const patchMutation = useMutation({
    mutationFn: ({ decisionId, payload }: { decisionId: string; payload: typeof draft }) =>
      patchDecision(decisionId, {
        title: payload.title.trim(),
        rationale: payload.rationale.trim() || null,
        confidence: payload.confidence,
        project_id: payload.project_id || null
      }),
    onSuccess: () => {
      setEditingId(null);
      invalidate();
    }
  });
  const deleteMutation = useMutation({ mutationFn: deleteDecision, onSuccess: invalidate });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['decisions'] });
    queryClient.invalidateQueries({ queryKey: ['memories'] });
    queryClient.invalidateQueries({ queryKey: ['graph'] });
    queryClient.invalidateQueries({ queryKey: ['projects'] });
  }

  function startEdit(decision: Decision) {
    setEditingId(decision.id);
    setDraft({ title: decision.title, rationale: decision.rationale ?? '', confidence: decision.confidence, project_id: decision.project_id ?? '' });
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h1 className="mb-4 text-xl font-semibold">Decisions</h1>
      <div className="divide-y divide-slate-100">
        {decisions.data?.map((decision) => (
          <article key={decision.id} className="py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                {editingId === decision.id ? (
                  <div className="space-y-2">
                    <input className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm font-medium" value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} />
                    <textarea className="h-20 w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={draft.rationale} onChange={(event) => setDraft({ ...draft, rationale: event.target.value })} />
                    <input className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm" type="number" min="0" max="1" step="0.05" value={draft.confidence} onChange={(event) => setDraft({ ...draft, confidence: Number(event.target.value) })} />
                    <select className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={draft.project_id} onChange={(event) => setDraft({ ...draft, project_id: event.target.value })}>
                      <option value="">No project</option>
                      {projects.data?.map((project) => (
                        <option key={project.id} value={project.id}>{project.name}</option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <>
                    <h2 className="font-medium">{decision.title}</h2>
                    <p className="mt-1 text-sm text-slate-500">{decision.rationale || 'No rationale captured.'}</p>
                    <div className="mt-2 text-sm"><SourceLink rawItemId={decision.source_raw_item_id} label="Source" /></div>
                  </>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-1">
                {editingId === decision.id ? (
                  <>
                    <button type="button" onClick={() => patchMutation.mutate({ decisionId: decision.id, payload: draft })} disabled={patchMutation.isPending || !draft.title.trim()} className="rounded-md border border-emerald-200 p-1.5 text-emerald-700 hover:bg-emerald-50 disabled:opacity-50" title="Save decision">
                      <Check size={14} />
                    </button>
                    <button type="button" onClick={() => setEditingId(null)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Cancel edit">
                      <X size={14} />
                    </button>
                  </>
                ) : (
                  <>
                    <button type="button" onClick={() => startEdit(decision)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Edit decision">
                      <Pencil size={14} />
                    </button>
                    <button type="button" onClick={() => window.confirm(`Delete decision "${decision.title}"?`) && deleteMutation.mutate(decision.id)} disabled={deleteMutation.isPending} className="rounded-md border border-rose-200 p-1.5 text-rose-700 hover:bg-rose-50 disabled:opacity-50" title="Delete decision">
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
