import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Archive, Check, Pencil, Trash2, X } from 'lucide-react';
import SourceLink from '../components/SourceLink';
import { Task, listTasks } from '../api/views';
import { deleteTask, patchTask } from '../api/review';

export default function Tasks() {
  const queryClient = useQueryClient();
  const [showArchived, setShowArchived] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState({ title: '', description: '', priority: '', status: 'open' });
  const tasks = useQuery({ queryKey: ['tasks', showArchived], queryFn: () => listTasks(showArchived) });
  const patchMutation = useMutation({
    mutationFn: ({ taskId, payload }: { taskId: string; payload: typeof draft }) =>
      patchTask(taskId, {
        title: payload.title.trim(),
        description: payload.description.trim() || null,
        priority: payload.priority || null,
        status: payload.status
      }),
    onSuccess: () => {
      setEditingId(null);
      invalidate();
    }
  });
  const deleteMutation = useMutation({ mutationFn: deleteTask, onSuccess: invalidate });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['tasks'] });
    queryClient.invalidateQueries({ queryKey: ['graph'] });
    queryClient.invalidateQueries({ queryKey: ['memories'] });
  }

  function startEdit(task: Task) {
    setEditingId(task.id);
    setDraft({ title: task.title, description: task.description ?? '', priority: task.priority ?? '', status: task.status });
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Tasks</h1>
        <label className="inline-flex items-center gap-2 text-sm text-slate-600">
          <input type="checkbox" checked={showArchived} onChange={(event) => setShowArchived(event.target.checked)} />
          Show archived
        </label>
      </div>
      <div className="divide-y divide-slate-100">
        {tasks.data?.map((task) => (
          <article key={task.id} className="py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                {editingId === task.id ? (
                  <div className="space-y-2">
                    <input className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm font-medium" value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} />
                    <textarea className="h-20 w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} />
                    <div className="grid gap-2 sm:grid-cols-2">
                      <select className="rounded-md border border-slate-300 px-2 py-1 text-sm" value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}>
                        <option value="open">Open</option>
                        <option value="in_progress">In progress</option>
                        <option value="done">Done</option>
                        <option value="archived">Archived</option>
                      </select>
                      <select className="rounded-md border border-slate-300 px-2 py-1 text-sm" value={draft.priority} onChange={(event) => setDraft({ ...draft, priority: event.target.value })}>
                        <option value="">No priority</option>
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                      </select>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-medium">{task.title}</h2>
                      <span className="rounded bg-slate-100 px-2 py-1 text-xs">{task.status}</span>
                    </div>
                    <p className="mt-1 text-sm text-slate-500">{task.description}</p>
                    <div className="mt-2 text-sm"><SourceLink rawItemId={task.source_raw_item_id} label="Source" /></div>
                  </>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-1">
                {editingId === task.id ? (
                  <>
                    <button type="button" onClick={() => patchMutation.mutate({ taskId: task.id, payload: draft })} disabled={patchMutation.isPending || !draft.title.trim()} className="rounded-md border border-emerald-200 p-1.5 text-emerald-700 hover:bg-emerald-50 disabled:opacity-50" title="Save task">
                      <Check size={14} />
                    </button>
                    <button type="button" onClick={() => setEditingId(null)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Cancel edit">
                      <X size={14} />
                    </button>
                  </>
                ) : (
                  <>
                    <button type="button" onClick={() => startEdit(task)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Edit task">
                      <Pencil size={14} />
                    </button>
                    {task.status !== 'archived' && (
                      <button type="button" onClick={() => patchTask(task.id, { status: 'archived' }).then(invalidate)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Archive task">
                        <Archive size={14} />
                      </button>
                    )}
                    <button type="button" onClick={() => window.confirm(`Delete task "${task.title}"?`) && deleteMutation.mutate(task.id)} disabled={deleteMutation.isPending} className="rounded-md border border-rose-200 p-1.5 text-rose-700 hover:bg-rose-50 disabled:opacity-50" title="Delete task">
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
