import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { Loader2, Play } from 'lucide-react';
import { getItem, processItem } from '../api/items';
import { patchMemory } from '../api/memories';
import { createDecision, createIdea, createQuestion, createTask, patchDecision, patchIdea, patchQuestion, patchTask } from '../api/review';
import ExtractionReview, { ExtractionReviewPayload } from '../components/ExtractionReview';

export default function ItemDetail() {
  const { id } = useParams<{ id: string }>();
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
          <button
            onClick={() => processMutation.mutate()}
            disabled={processMutation.isPending}
            className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-50"
            title="Process item"
          >
            {processMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            {processMutation.isPending ? 'Processing' : 'Process'}
          </button>
        </div>
        {processMutation.isPending && (
          <div className="mb-4 flex items-center gap-2 rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
            <Loader2 size={16} className="animate-spin" />
            Extracting structured memories with Ollama. This can take a minute for local models.
          </div>
        )}
        <pre className="whitespace-pre-wrap rounded-md bg-slate-50 p-4 text-sm text-slate-800">{item.data.item.body_text}</pre>
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
          <ExtractionReview
            memory={memory}
            isSaving={saveReviewMutation.isPending}
            onSave={(payload) => saveReviewMutation.mutate({ memoryId: memory.id, payload })}
          />
        </section>
      ))}
      {saveReviewMutation.error && <p className="text-sm text-red-700">{saveReviewMutation.error.message}</p>}
    </div>
  );
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
