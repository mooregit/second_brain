import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Trash2 } from 'lucide-react';
import { api } from '../api/client';
import type { Memory } from '../api/items';
import { deleteMemory } from '../api/memories';

export default function Memories() {
  const queryClient = useQueryClient();
  const memories = useQuery({ queryKey: ['memories'], queryFn: () => api<Memory[]>('/memories') });
  const deleteMutation = useMutation({
    mutationFn: deleteMemory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['graph'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    }
  });

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h1 className="mb-4 text-xl font-semibold">Memories</h1>
      <div className="divide-y divide-slate-100">
        {memories.data?.map((memory) => (
          <Link key={memory.id} to={`/items/${memory.raw_item_id}`} className="block py-3 hover:bg-slate-50">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="font-medium">{memory.summary}</div>
                <div className="mt-1 text-sm text-slate-500">{memory.tags.join(', ') || memory.memory_type}</div>
              </div>
              <button
                type="button"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
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
          </Link>
        ))}
      </div>
    </section>
  );
}
