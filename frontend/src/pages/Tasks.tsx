import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import SourceLink from '../components/SourceLink';
import { listTasks } from '../api/views';

export default function Tasks() {
  const [showArchived, setShowArchived] = useState(false);
  const tasks = useQuery({ queryKey: ['tasks', showArchived], queryFn: () => listTasks(showArchived) });

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
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-medium">{task.title}</h2>
              <span className="rounded bg-slate-100 px-2 py-1 text-xs">{task.status}</span>
            </div>
            <p className="mt-1 text-sm text-slate-500">{task.description}</p>
            <div className="mt-2 text-sm"><SourceLink rawItemId={task.source_raw_item_id} label="Source" /></div>
          </article>
        ))}
      </div>
    </section>
  );
}
