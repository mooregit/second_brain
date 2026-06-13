import { useQuery } from '@tanstack/react-query';
import { listDecisions } from '../api/views';
import SourceLink from '../components/SourceLink';

export default function Decisions() {
  const decisions = useQuery({ queryKey: ['decisions'], queryFn: listDecisions });

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h1 className="mb-4 text-xl font-semibold">Decisions</h1>
      <div className="divide-y divide-slate-100">
        {decisions.data?.map((decision) => (
          <article key={decision.id} className="py-3">
            <h2 className="font-medium">{decision.title}</h2>
            <p className="mt-1 text-sm text-slate-500">{decision.rationale || 'No rationale captured.'}</p>
            <div className="mt-2 text-sm"><SourceLink rawItemId={decision.source_raw_item_id} label="Source" /></div>
          </article>
        ))}
      </div>
    </section>
  );
}
