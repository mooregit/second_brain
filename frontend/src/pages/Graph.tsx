import { useQuery } from '@tanstack/react-query';
import { getGraph } from '../api/graph';
import GraphCanvas from '../components/GraphCanvas';

export default function Graph() {
  const graph = useQuery({ queryKey: ['graph'], queryFn: getGraph });

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Graph</h1>
        <div className="text-sm text-slate-500">{graph.data?.nodes.length ?? 0} nodes</div>
      </div>
      {graph.data ? <GraphCanvas graph={graph.data} /> : <div>Loading...</div>}
      {graph.error && <p className="text-sm text-red-700">{graph.error.message}</p>}
    </section>
  );
}

