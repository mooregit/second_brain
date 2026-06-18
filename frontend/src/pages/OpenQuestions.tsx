import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Archive, Check, Pencil, Trash2, X } from 'lucide-react';
import { OpenQuestion, listOpenQuestions, listProjects } from '../api/views';
import { deleteQuestion, patchQuestion } from '../api/review';
import SourceLink from '../components/SourceLink';

export default function OpenQuestions() {
  const queryClient = useQueryClient();
  const [showArchived, setShowArchived] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState({ question: '', status: 'open', project_id: '' });
  const questions = useQuery({ queryKey: ['open-questions', showArchived], queryFn: () => listOpenQuestions(showArchived) });
  const projects = useQuery({ queryKey: ['projects'], queryFn: listProjects });
  const patchMutation = useMutation({
    mutationFn: ({ questionId, payload }: { questionId: string; payload: typeof draft }) =>
      patchQuestion(questionId, { question: payload.question.trim(), status: payload.status, project_id: payload.project_id || null }),
    onSuccess: () => {
      setEditingId(null);
      invalidate();
    }
  });
  const deleteMutation = useMutation({ mutationFn: deleteQuestion, onSuccess: invalidate });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['open-questions'] });
    queryClient.invalidateQueries({ queryKey: ['memories'] });
    queryClient.invalidateQueries({ queryKey: ['graph'] });
    queryClient.invalidateQueries({ queryKey: ['projects'] });
  }

  function startEdit(question: OpenQuestion) {
    setEditingId(question.id);
    setDraft({ question: question.question, status: question.status, project_id: question.project_id ?? '' });
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Open Questions</h1>
        <label className="inline-flex items-center gap-2 text-sm text-slate-600">
          <input type="checkbox" checked={showArchived} onChange={(event) => setShowArchived(event.target.checked)} />
          Show archived
        </label>
      </div>
      <div className="divide-y divide-slate-100">
        {questions.data?.map((question) => (
          <article key={question.id} className="py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                {editingId === question.id ? (
                  <div className="space-y-2">
                    <textarea className="h-20 w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={draft.question} onChange={(event) => setDraft({ ...draft, question: event.target.value })} />
                    <select className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}>
                      <option value="open">Open</option>
                      <option value="answered">Answered</option>
                      <option value="archived">Archived</option>
                    </select>
                    <select className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={draft.project_id} onChange={(event) => setDraft({ ...draft, project_id: event.target.value })}>
                      <option value="">No project</option>
                      {projects.data?.map((project) => (
                        <option key={project.id} value={project.id}>{project.name}</option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <>
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-medium">{question.question}</h2>
                      <span className="rounded bg-slate-100 px-2 py-1 text-xs">{question.status}</span>
                    </div>
                    <div className="mt-2 text-sm"><SourceLink rawItemId={question.source_raw_item_id} label="Source" /></div>
                  </>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-1">
                {editingId === question.id ? (
                  <>
                    <button type="button" onClick={() => patchMutation.mutate({ questionId: question.id, payload: draft })} disabled={patchMutation.isPending || !draft.question.trim()} className="rounded-md border border-emerald-200 p-1.5 text-emerald-700 hover:bg-emerald-50 disabled:opacity-50" title="Save open question">
                      <Check size={14} />
                    </button>
                    <button type="button" onClick={() => setEditingId(null)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Cancel edit">
                      <X size={14} />
                    </button>
                  </>
                ) : (
                  <>
                    <button type="button" onClick={() => startEdit(question)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Edit open question">
                      <Pencil size={14} />
                    </button>
                    {question.status !== 'archived' && (
                      <button type="button" onClick={() => patchQuestion(question.id, { status: 'archived' }).then(invalidate)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Archive open question">
                        <Archive size={14} />
                      </button>
                    )}
                    <button type="button" onClick={() => window.confirm('Delete this open question?') && deleteMutation.mutate(question.id)} disabled={deleteMutation.isPending} className="rounded-md border border-rose-200 p-1.5 text-rose-700 hover:bg-rose-50 disabled:opacity-50" title="Delete open question">
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
