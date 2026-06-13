import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { Play } from 'lucide-react';
import { getItem, processItem } from '../api/items';
import { patchMemory } from '../api/memories';
import ExtractionReview from '../components/ExtractionReview';

export default function ItemDetail() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const item = useQuery({ queryKey: ['item', id], queryFn: () => getItem(id!), enabled: Boolean(id) });
  const processMutation = useMutation({
    mutationFn: () => processItem(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['item', id] })
  });
  const patchMutation = useMutation({
    mutationFn: ({ memoryId, payload }: { memoryId: string; payload: { summary: string; tags: string[] } }) => patchMemory(memoryId, payload),
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
            <Play size={16} />
            Process
          </button>
        </div>
        <pre className="whitespace-pre-wrap rounded-md bg-slate-50 p-4 text-sm text-slate-800">{item.data.item.body_text}</pre>
        {processMutation.error && <p className="mt-3 text-sm text-red-700">{processMutation.error.message}</p>}
      </section>
      {item.data.memories.map((memory) => (
        <section key={memory.id} className="rounded-md border border-slate-200 bg-white p-4">
          <ExtractionReview memory={memory} onSave={(payload) => patchMutation.mutate({ memoryId: memory.id, payload })} />
        </section>
      ))}
    </div>
  );
}

