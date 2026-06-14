import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { Loader2, Play } from 'lucide-react';
import { getItem, processItem } from '../api/items';
import { patchMemory } from '../api/memories';
import { createIdea, createQuestion, createTask, patchIdea, patchQuestion, patchTask } from '../api/review';
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
          .map((idea) => (idea.isNew ? createIdea({ memory_id: memoryId, body: idea.body.trim() }) : patchIdea(idea.id, { body: idea.body }))),
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
