import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getGraph } from '../api/graph';
import GraphCanvas from '../components/GraphCanvas';

const defaultTypes = ['project', 'source', 'task', 'idea', 'decision', 'question'];

export default function Graph() {
  const [showArchived, setShowArchived] = useState(false);
  const [showTags, setShowTags] = useState(true);
  const [showEntities, setShowEntities] = useState(false);
  const [showEdgeLabels, setShowEdgeLabels] = useState(false);
  const graph = useQuery({ queryKey: ['graph', showArchived], queryFn: () => getGraph(showArchived) });
  const visibleTypes = new Set([
    ...defaultTypes,
    ...(showTags ? ['tag'] : []),
    ...(showEntities ? ['entity', 'person'] : [])
  ]);

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Graph</h1>
        <div className="flex flex-wrap items-center gap-4">
          <label className="inline-flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={showArchived} onChange={(event) => setShowArchived(event.target.checked)} />
            Show archived
          </label>
          <label className="inline-flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={showTags} onChange={(event) => setShowTags(event.target.checked)} />
            Tags
          </label>
          <label className="inline-flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={showEntities} onChange={(event) => setShowEntities(event.target.checked)} />
            Entities
          </label>
          <label className="inline-flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={showEdgeLabels} onChange={(event) => setShowEdgeLabels(event.target.checked)} />
            Edge labels
          </label>
          <div className="text-sm text-slate-500">{graph.data?.nodes.length ?? 0} nodes</div>
        </div>
      </div>
      {graph.data ? <GraphCanvas graph={graph.data} visibleTypes={visibleTypes} showEdgeLabels={showEdgeLabels} /> : <div>Loading...</div>}
      {graph.error && <p className="text-sm text-red-700">{graph.error.message}</p>}
    </section>
  );
}
