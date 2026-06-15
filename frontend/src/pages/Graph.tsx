import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getGraph } from '../api/graph';
import GraphCanvas from '../components/GraphCanvas';

export default function Graph() {
  const [showArchived, setShowArchived] = useState(false);
  const graph = useQuery({ queryKey: ['graph', showArchived], queryFn: () => getGraph(showArchived) });

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Graph</h1>
        <div className="flex items-center gap-4">
          <label className="inline-flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={showArchived} onChange={(event) => setShowArchived(event.target.checked)} />
            Show archived
          </label>
          <div className="text-sm text-slate-500">{graph.data?.nodes.length ?? 0} nodes</div>
        </div>
      </div>
      {graph.data ? <GraphCanvas graph={graph.data} /> : <div>Loading...</div>}
      {graph.error && <p className="text-sm text-red-700">{graph.error.message}</p>}
    </section>
  );
}
