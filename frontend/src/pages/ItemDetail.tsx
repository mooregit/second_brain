import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { FileVideo, Loader2, Paperclip, Play, Trash2 } from 'lucide-react';
import { FileAsset, MediaArtifact, deleteItem, getItem, processItem } from '../api/items';
import { deleteMemory, patchMemory } from '../api/memories';
import { createDecision, createIdea, createQuestion, createTask, patchDecision, patchIdea, patchQuestion, patchTask } from '../api/review';
import ExtractionReview, { ExtractionReviewPayload } from '../components/ExtractionReview';

export default function ItemDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const item = useQuery({ queryKey: ['item', id], queryFn: () => getItem(id!), enabled: Boolean(id) });
  const processMutation = useMutation({
    mutationFn: () => processItem(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['item', id] })
  });
  const saveReviewMutation = useMutation({
    mutationFn: async ({ memoryId, payload }: { memoryId: string; payload: ExtractionReviewPayload }) => {
      await patchMemory(memoryId, { summary: payload.summary, tags: payload.tags });
      await Promise.all([
        ...payload.tasks
          .filter((task) => task.title.trim())
          .map((task) =>
            task.isNew
              ? createTask({
                  memory_id: memoryId,
                  title: task.title.trim(),
                  description: task.description.trim() || null,
                  priority: task.priority || null,
                  status: task.status
                })
              : patchTask(task.id, {
                  title: task.title,
                  description: task.description.trim() || null,
                  priority: task.priority || null,
                  status: task.status
                })
          ),
        ...payload.ideas
          .filter((idea) => idea.body.trim())
          .map((idea) =>
            idea.isNew
              ? createIdea({ memory_id: memoryId, body: idea.body.trim(), status: idea.status })
              : patchIdea(idea.id, { body: idea.body, status: idea.status })
          ),
        ...payload.decisions
          .filter((decision) => decision.title.trim())
          .map((decision) =>
            decision.isNew
              ? createDecision({
                  memory_id: memoryId,
                  title: decision.title.trim(),
                  rationale: decision.rationale.trim() || null,
                  confidence: decision.confidence
                })
              : patchDecision(decision.id, {
                  title: decision.title,
                  rationale: decision.rationale.trim() || null,
                  confidence: decision.confidence
                })
          ),
        ...payload.open_questions
          .filter((question) => question.question.trim())
          .map((question) =>
            question.isNew
              ? createQuestion({ memory_id: memoryId, question: question.question.trim(), status: question.status })
              : patchQuestion(question.id, { question: question.question, status: question.status })
          )
      ]);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['item', id] })
  });
  const deleteItemMutation = useMutation({
    mutationFn: () => deleteItem(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['items'] });
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['graph'] });
      navigate('/');
    }
  });
  const deleteMemoryMutation = useMutation({
    mutationFn: deleteMemory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['item', id] });
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['graph'] });
    }
  });

  if (item.isLoading) return <div>Loading...</div>;
  if (!item.data) return <div>Item not found.</div>;

  return (
    <div className="space-y-5">
      <section className="rounded-md border border-slate-200 bg-white p-4">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold">{item.data.item.title}</h1>
            <div className="mt-1 text-sm text-slate-500">{item.data.item.status}</div>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <button
              onClick={() => processMutation.mutate()}
              disabled={processMutation.isPending || deleteItemMutation.isPending}
              className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-50"
              title="Process item"
            >
              {processMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
              {processMutation.isPending ? 'Processing' : 'Process'}
            </button>
            <button
              type="button"
              onClick={() => {
                if (window.confirm(`Delete inbox item "${item.data.item.title}" and all extracted records?`)) {
                  deleteItemMutation.mutate();
                }
              }}
              disabled={deleteItemMutation.isPending}
              className="inline-flex items-center gap-2 rounded-md border border-rose-200 px-3 py-2 text-sm text-rose-700 hover:bg-rose-50 disabled:opacity-50"
              title="Delete inbox item"
            >
              {deleteItemMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
              Delete
            </button>
          </div>
        </div>
        {processMutation.isPending && (
          <div className="mb-4 flex items-center gap-2 rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
            <Loader2 size={16} className="animate-spin" />
            Extracting structured memories with Ollama. This can take a minute for local models.
          </div>
        )}
        <pre className="whitespace-pre-wrap rounded-md bg-slate-50 p-4 text-sm text-slate-800">{item.data.item.body_text}</pre>
        {item.data.file_assets.length > 0 && <MediaPanel fileAssets={item.data.file_assets} />}
        {processMutation.error && <p className="mt-3 text-sm text-red-700">{processMutation.error.message}</p>}
      </section>
      {item.data.latest_processing_run && (
        <section className="rounded-md border border-slate-200 bg-white p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">Extraction Diagnostics</h2>
            <div className="flex flex-wrap gap-2 text-xs text-slate-600">
              <span className="rounded-md bg-slate-100 px-2 py-1">{item.data.latest_processing_run.status}</span>
              <span className="rounded-md bg-slate-100 px-2 py-1">{item.data.latest_processing_run.model}</span>
            </div>
          </div>
          {item.data.latest_processing_run.error && <p className="mb-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">{item.data.latest_processing_run.error}</p>}
          <div className="grid gap-3 lg:grid-cols-2">
            <DiagnosticBlock title="Original Output" value={item.data.latest_processing_run.original_output || item.data.latest_processing_run.raw_output} />
            <DiagnosticBlock title="Repaired Output" value={item.data.latest_processing_run.repaired_output} empty="No repair attempt was stored for this run." />
            <DiagnosticBlock title="Parsed JSON" value={formatJson(item.data.latest_processing_run.parsed_json)} className="lg:col-span-2" />
          </div>
        </section>
      )}
      {item.data.memories.map((memory) => (
        <section key={memory.id} className="rounded-md border border-slate-200 bg-white p-4">
          <div className="mb-3 flex justify-end">
            <button
              type="button"
              onClick={() => {
                if (window.confirm('Delete this memory and its extracted records? The source inbox item will stay.')) {
                  deleteMemoryMutation.mutate(memory.id);
                }
              }}
              disabled={deleteMemoryMutation.isPending}
              className="inline-flex items-center gap-2 rounded-md border border-rose-200 px-3 py-2 text-sm text-rose-700 hover:bg-rose-50 disabled:opacity-50"
              title="Delete memory"
            >
              {deleteMemoryMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
              Delete Memory
            </button>
          </div>
          <ExtractionReview
            memory={memory}
            isSaving={saveReviewMutation.isPending}
            onSave={(payload) => saveReviewMutation.mutate({ memoryId: memory.id, payload })}
          />
        </section>
      ))}
      {saveReviewMutation.error && <p className="text-sm text-red-700">{saveReviewMutation.error.message}</p>}
      {deleteMemoryMutation.error && <p className="text-sm text-red-700">{deleteMemoryMutation.error.message}</p>}
      {deleteItemMutation.error && <p className="text-sm text-red-700">{deleteItemMutation.error.message}</p>}
    </div>
  );
}

function MediaPanel({ fileAssets }: { fileAssets: FileAsset[] }) {
  return (
    <div className="mt-4 rounded-md border border-slate-200 bg-white">
      <div className="flex items-center gap-2 border-b border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700">
        <Paperclip size={16} />
        Attached Files
      </div>
      <div className="divide-y divide-slate-200">
        {fileAssets.map((asset) => (
          <div key={asset.id} className="p-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                  <FileVideo size={16} />
                  <span className="break-all">{asset.filename}</span>
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {asset.mime_type || 'unknown type'} {asset.size_bytes !== null ? `- ${formatBytes(asset.size_bytes)}` : ''}
                </div>
              </div>
              <StatusPill status={overallMediaStatus(asset.media_artifacts)} />
            </div>
            <div className="mt-3 grid gap-2">
              {asset.media_artifacts.length === 0 ? (
                <p className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">Media analysis has not run yet.</p>
              ) : (
                asset.media_artifacts.map((artifact) => <ArtifactBlock key={artifact.id} artifact={artifact} />)
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ArtifactBlock({ artifact }: { artifact: MediaArtifact }) {
  return (
    <details className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <summary className="cursor-pointer text-sm font-medium text-slate-700">
        {artifact.artifact_type.replace(/_/g, ' ')} <StatusPill status={artifact.status} />
      </summary>
      {artifact.text_content && <pre className="mt-3 whitespace-pre-wrap text-xs text-slate-800">{artifact.text_content}</pre>}
      {artifact.stored_path && <p className="mt-2 break-all text-xs text-slate-500">{artifact.stored_path}</p>}
      {artifact.error && <p className="mt-2 rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-800">{artifact.error}</p>}
    </details>
  );
}

function StatusPill({ status }: { status: string }) {
  const color = status === 'processed' ? 'bg-emerald-50 text-emerald-700' : status === 'failed' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700';
  return <span className={`inline-flex rounded-md px-2 py-1 text-xs font-medium ${color}`}>{status}</span>;
}

function overallMediaStatus(artifacts: MediaArtifact[]): string {
  if (!artifacts.length) return 'pending';
  if (artifacts.some((artifact) => artifact.status === 'failed')) return 'failed';
  if (artifacts.every((artifact) => artifact.status === 'processed')) return 'processed';
  return 'pending';
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function DiagnosticBlock({ title, value, empty, className = '' }: { title: string; value: string | null | undefined; empty?: string; className?: string }) {
  return (
    <details className={`rounded-md border border-slate-200 bg-slate-50 p-3 ${className}`}>
      <summary className="cursor-pointer text-sm font-semibold text-slate-700">{title}</summary>
      <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap text-xs text-slate-800">{value || empty || 'Nothing stored.'}</pre>
    </details>
  );
}

function formatJson(value: unknown): string {
  if (!value) return '';
  return JSON.stringify(value, null, 2);
}
