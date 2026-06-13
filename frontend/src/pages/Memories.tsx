import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Memory } from '../api/items';

export default function Memories() {
  const memories = useQuery({ queryKey: ['memories'], queryFn: () => api<Memory[]>('/memories') });

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h1 className="mb-4 text-xl font-semibold">Memories</h1>
      <div className="divide-y divide-slate-100">
        {memories.data?.map((memory) => (
          <Link key={memory.id} to={`/items/${memory.raw_item_id}`} className="block py-3 hover:bg-slate-50">
            <div className="font-medium">{memory.summary}</div>
            <div className="mt-1 text-sm text-slate-500">{memory.tags.join(', ') || memory.memory_type}</div>
          </Link>
        ))}
      </div>
    </section>
  );
}
