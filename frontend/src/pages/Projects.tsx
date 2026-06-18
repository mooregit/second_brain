import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, Pencil, Trash2, X } from 'lucide-react';
import { Project, deleteProject, listProjects, patchProject } from '../api/views';

export default function Projects() {
  const queryClient = useQueryClient();
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);
  const [nameDraft, setNameDraft] = useState('');
  const [descriptionDraft, setDescriptionDraft] = useState('');
  const projects = useQuery({ queryKey: ['projects'], queryFn: listProjects });
  const deleteMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['graph'] });
      queryClient.invalidateQueries({ queryKey: ['item-detail'] });
    }
  });
  const patchMutation = useMutation({
    mutationFn: ({ projectId, name, description }: { projectId: string; name: string; description: string }) => patchProject(projectId, { name, description: description.trim() || null }),
    onSuccess: () => {
      setEditingProjectId(null);
      setNameDraft('');
      setDescriptionDraft('');
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['graph'] });
    }
  });

  function startEdit(project: Project) {
    setEditingProjectId(project.id);
    setNameDraft(project.name);
    setDescriptionDraft(project.description ?? '');
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h1 className="mb-4 text-xl font-semibold">Projects</h1>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {projects.data?.map((project) => (
          <article key={project.id} className="rounded-md border border-slate-200 p-3">
            <div className="flex items-start justify-between gap-3">
              {editingProjectId === project.id ? (
                <div className="min-w-0 flex-1 space-y-2">
                  <input className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={nameDraft} onChange={(event) => setNameDraft(event.target.value)} />
                  <textarea className="h-20 w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={descriptionDraft} onChange={(event) => setDescriptionDraft(event.target.value)} placeholder="Description" />
                </div>
              ) : (
                <h2 className="font-semibold">{project.name}</h2>
              )}
              <div className="flex shrink-0 items-center gap-1">
                {editingProjectId === project.id ? (
                  <>
                    <button
                      type="button"
                      onClick={() => patchMutation.mutate({ projectId: project.id, name: nameDraft.trim(), description: descriptionDraft })}
                      className="rounded-md border border-emerald-200 p-1.5 text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
                      disabled={patchMutation.isPending || !nameDraft.trim()}
                      title="Save project"
                    >
                      <Check size={14} />
                    </button>
                    <button type="button" onClick={() => setEditingProjectId(null)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Cancel edit">
                      <X size={14} />
                    </button>
                  </>
                ) : (
                  <button type="button" onClick={() => startEdit(project)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Rename project">
                    <Pencil size={14} />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => {
                    if (window.confirm(`Delete project "${project.name}"? This detaches related records.`)) {
                      deleteMutation.mutate(project.id);
                    }
                  }}
                  className="rounded-md border border-rose-200 p-1.5 text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                  disabled={deleteMutation.isPending}
                  aria-label={`Delete ${project.name}`}
                  title="Delete project"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
            {editingProjectId !== project.id && <p className="mt-1 text-sm text-slate-500">{project.description || 'No description yet.'}</p>}
          </article>
        ))}
      </div>
    </section>
  );
}
